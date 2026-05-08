"""
core/async_batch.py — Async batch data fetching with adaptive rate limiting.

Provides:
  - Batch fetcher: parallel async fetching with concurrency control
  - PollingThrottle: adaptive rate limiter with exponential backoff
  - Batch fetcher with retry: handles transient failures gracefully

Usage:
    from core.async_batch import BatchFetcher, PollingThrottle

    # Simple batch fetch
    fetcher = BatchFetcher(max_concurrent=10)
    results = await fetcher.fetch_batch(urls)

    # With throttle
    throttle = PollingThrottle(requests_per_second=5)
    async with throttle:
        await fetcher.fetch_one(url)

    # Combined
    async with throttle:
        results = await fetcher.fetch_batch_with_retry(
            items=[{"url": f"/quote/{s}"} for s in symbols],
            fetch_fn=lambda item: fetch_quote(item["url"]),
            max_retries=3,
        )

Context Variables (Python 3.12+):
    Batch operations preserve task-local context via contextvars.
    Set request context before batch calls:
        from core.async_batch import request_id_var
        token = request_id_var.set("req-123")
        try:
            await fetcher.fetch_batch(urls)
        finally:
            request_id_var.reset(token)
"""
from __future__ import annotations

import asyncio
import logging
import time
from collections.abc import Awaitable, Callable
from contextvars import ContextVar
from typing import Any, TypeVar

request_id_var: ContextVar[str] = ContextVar("request_id", default="")

logger = logging.getLogger(__name__)

T = TypeVar("T")


class PollingThrottle:
    """Adaptive rate limiter with exponential backoff.

    Tracks request rates per endpoint and backs off when rate limited.
    Thread-safe for use across async tasks.

    Usage:
        throttle = PollingThrottle(requests_per_second=10)

        async with throttle:
            await fetch_data()
    """

    def __init__(
        self,
        requests_per_second: float = 10.0,
        burst_size: int = 5,
        initial_backoff: float = 1.0,
        max_backoff: float = 60.0,
        backoff_factor: float = 2.0,
    ) -> None:
        self._rps = requests_per_second
        self._burst = burst_size
        self._min_interval = 1.0 / requests_per_second
        self._initial_backoff = initial_backoff
        self._max_backoff = max_backoff
        self._backoff_factor = backoff_factor

        self._lock = asyncio.Lock()
        self._last_request_time: float = 0.0
        self._tokens = float(burst_size)
        self._backoff_until: float = 0.0
        self._consecutive_errors: int = 0

    async def acquire(self) -> None:
        async with self._lock:
            now = time.monotonic()

            if now < self._backoff_until:
                sleep_time = self._backoff_until - now
                if sleep_time > 0:
                    await asyncio.sleep(sleep_time)
                    now = time.monotonic()

            if self._tokens < 1.0:
                deficit = 1.0 - self._tokens
                sleep_time = deficit * self._min_interval
                await asyncio.sleep(sleep_time)
                now = time.monotonic()

            self._tokens -= 1.0
            self._last_request_time = now

    def record_success(self) -> None:
        self._consecutive_errors = 0
        self._tokens = min(self._tokens + 0.5, float(self._burst))

    def record_rate_limit(self) -> None:
        self._consecutive_errors += 1
        backoff = min(
            self._initial_backoff * (self._backoff_factor ** (self._consecutive_errors - 1)),
            self._max_backoff,
        )
        self._backoff_until = time.monotonic() + backoff
        self._tokens = 0.0
        logger.debug("Rate limit hit, backing off for %ss (attempt %s)", backoff, self)

    def record_error(self) -> None:
        self._consecutive_errors += 1

    def reset(self) -> None:
        self._tokens = float(self._burst)
        self._backoff_until = 0.0
        self._consecutive_errors = 0

    async def __aenter__(self) -> None:
        await self.acquire()

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        if exc_type is not None:
            self.record_error()
        else:
            self.record_success()


class BatchFetcher:
    """Async batch fetcher with concurrency control and retry logic.

    Fetches multiple items in parallel while respecting concurrency limits.
    Supports retry with exponential backoff and graceful error handling.

    Usage:
        fetcher = BatchFetcher(max_concurrent=10)

        # Fetch multiple URLs in parallel
        results = await fetcher.fetch_batch([url1, url2, url3])

        # Fetch with custom function
        results = await fetcher.fetch_batch_with_retry(
            items=symbols,
            fetch_fn=lambda s: fetch_quote(s),
            max_retries=3,
        )
    """

    def __init__(
        self,
        max_concurrent: int = 20,
        default_timeout: float = 30.0,
    ) -> None:
        self._semaphore = asyncio.Semaphore(max_concurrent)
        self._timeout = default_timeout
        self._active: int = 0
        self._active_lock = asyncio.Lock()

    @property
    def active_count(self) -> int:
        return self._active

    async def _throttled_fetch(
        self,
        coro: Awaitable[T],
        throttle: PollingThrottle | None = None,
    ) -> T:
        async with self._semaphore:
            if throttle is not None:
                await throttle.acquire()
            async with self._active_lock:
                self._active += 1
            try:
                result = await asyncio.wait_for(coro, timeout=self._timeout)
                if throttle is not None:
                    throttle.record_success()
                return result
            except TimeoutError:
                if throttle is not None:
                    throttle.record_error()
                raise
            finally:
                async with self._active_lock:
                    self._active -= 1

    async def fetch_one(
        self,
        coro: Awaitable[T],
        throttle: PollingThrottle | None = None,
    ) -> T:
        return await self._throttled_fetch(coro, throttle)

    async def fetch_batch(
        self,
        coros: list[Awaitable[T]],
        throttle: PollingThrottle | None = None,
    ) -> list[T | Exception]:
        tasks = [self._throttled_fetch(coro, throttle) for coro in coros]
        results: list[T | Exception] = []
        for future in asyncio.as_completed(tasks):
            try:
                result = await future
                results.append(result)
            except Exception as e:
                results.append(e)
        return results

    async def fetch_batch_with_retry(
        self,
        items: list[Any],
        fetch_fn: Callable[[Any], Awaitable[T]],
        max_retries: int = 3,
        throttle: PollingThrottle | None = None,
        initial_backoff: float = 0.5,
        backoff_factor: float = 2.0,
    ) -> list[tuple[Any, T | Exception]]:
        async def fetch_with_retry(item: Any) -> tuple[Any, T | Exception]:
            last_error: Exception | None = None
            for attempt in range(max_retries):
                try:
                    coro = fetch_fn(item)
                    result = await self._throttled_fetch(coro, throttle)
                    return item, result
                except Exception as e:
                    last_error = e
                    if attempt < max_retries - 1:
                        backoff = initial_backoff * (backoff_factor ** attempt)
                        logger.debug("Retry %s/%s for item after %ss: %s", attempt, max_retries, backoff, e)
                        await asyncio.sleep(backoff)

            assert last_error is not None
            return item, last_error

        tasks = [fetch_with_retry(item) for item in items]
        return await asyncio.gather(*tasks)

    async def fetch_dict_batch(
        self,
        items: list[dict[str, Any]],
        key_field: str,
        fetch_fn: Callable[[Any], Awaitable[T]],
        throttle: PollingThrottle | None = None,
    ) -> dict[str, T | Exception]:
        pairs = await self.fetch_batch_with_retry(
            items=items,
            fetch_fn=lambda item: fetch_fn(item[key_field]),
            throttle=throttle,
        )
        return dict(pairs)


class RateLimitTracker:
    """Tracks rate limit status across multiple endpoints.

    Detects rate limiting patterns and suggests optimal polling intervals.

    Usage:
        tracker = RateLimitTracker()

        tracker.record_request(endpoint="/quote")
        tracker.record_response(endpoint="/quote", status_code=429, elapsed=0.05)

        suggested_interval = tracker.suggest_interval("/quote")
    """

    def __init__(self, window_seconds: float = 60.0) -> None:
        self._window = window_seconds
        self._lock = asyncio.Lock()
        self._request_times: dict[str, list[float]] = {}
        self._rate_limit_hits: dict[str, int] = {}
        self._total_requests: dict[str, int] = {}

    def record_request(self, endpoint: str) -> None:
        now = time.monotonic()
        if endpoint not in self._request_times:
            self._request_times[endpoint] = []
            self._rate_limit_hits[endpoint] = 0
            self._total_requests[endpoint] = 0
        self._request_times[endpoint].append(now)
        self._total_requests[endpoint] += 1

    def record_response(self, endpoint: str, status_code: int, elapsed: float) -> None:
        now = time.monotonic()
        if status_code == 429:
            self._rate_limit_hits[endpoint] = self._rate_limit_hits.get(endpoint, 0) + 1
        cutoff = now - self._window
        if endpoint in self._request_times:
            self._request_times[endpoint] = [
                t for t in self._request_times[endpoint] if t > cutoff
            ]

    def request_rate(self, endpoint: str) -> float:
        if endpoint not in self._request_times:
            return 0.0
        times = self._request_times[endpoint]
        if not times:
            return 0.0
        cutoff = time.monotonic() - self._window
        recent = [t for t in times if t > cutoff]
        return len(recent) / self._window

    def rate_limit_ratio(self, endpoint: str) -> float:
        total = self._total_requests.get(endpoint, 0)
        if total == 0:
            return 0.0
        hits = self._rate_limit_hits.get(endpoint, 0)
        return hits / total

    def suggest_interval(self, endpoint: str, target_rate: float = 0.7) -> float:
        rate = self.request_rate(endpoint)
        ratio = self.rate_limit_ratio(endpoint)

        if ratio > 0.1:
            base = 1.0 / max(rate, 0.1)
            return base * 2.0
        elif rate > 0:
            return (1.0 / rate) * target_rate
        else:
            return 1.0

    def reset(self) -> None:
        self._request_times.clear()
        self._rate_limit_hits.clear()
        self._total_requests.clear()
