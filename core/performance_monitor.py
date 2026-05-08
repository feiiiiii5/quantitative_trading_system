"""Performance monitoring middleware for API endpoints."""
from __future__ import annotations

import logging
import time
from collections import defaultdict
from collections.abc import Callable
from dataclasses import dataclass, field

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

logger = logging.getLogger(__name__)


@dataclass
class EndpointMetrics:
    total_calls: int = 0
    total_duration: float = 0.0
    error_count: int = 0
    min_duration: float = float("inf")
    max_duration: float = 0.0
    status_codes: dict[int, int] = field(default_factory=dict)

    @property
    def avg_duration(self) -> float:
        return self.total_duration / self.total_calls if self.total_calls > 0 else 0.0

    @property
    def error_rate(self) -> float:
        return self.error_count / self.total_calls if self.total_calls > 0 else 0.0

    def to_dict(self) -> dict:
        return {
            "total_calls": self.total_calls,
            "avg_duration_ms": round(self.avg_duration * 1000, 2),
            "min_duration_ms": round(self.min_duration * 1000, 2) if self.min_duration != float("inf") else 0,
            "max_duration_ms": round(self.max_duration * 1000, 2),
            "error_rate": round(self.error_rate * 100, 2),
            "status_codes": self.status_codes,
        }


class PerformanceMonitor:
    _instance: PerformanceMonitor | None = None
    _metrics: dict[str, EndpointMetrics] = defaultdict(EndpointMetrics)
    _lock: bool = False

    def __new__(cls) -> PerformanceMonitor:
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def record_call(
        self,
        endpoint: str,
        duration: float,
        status_code: int,
        is_error: bool = False,
    ) -> None:
        metrics = self._metrics[endpoint]
        metrics.total_calls += 1
        metrics.total_duration += duration
        metrics.min_duration = min(metrics.min_duration, duration)
        metrics.max_duration = max(metrics.max_duration, duration)
        metrics.status_codes[status_code] = metrics.status_codes.get(status_code, 0) + 1
        if is_error or status_code >= 400:
            metrics.error_count += 1

    def get_metrics(self, endpoint: str | None = None) -> dict:
        if endpoint:
            return self._metrics.get(endpoint, EndpointMetrics()).to_dict()
        return {ep: m.to_dict() for ep, m in self._metrics.items()}

    def reset(self, endpoint: str | None = None) -> None:
        if endpoint:
            self._metrics.pop(endpoint, None)
        else:
            self._metrics.clear()

    def get_slow_endpoints(self, threshold_ms: float = 100) -> list[tuple[str, float]]:
        results = []
        for endpoint, metrics in self._metrics.items():
            avg_ms = metrics.avg_duration * 1000
            if avg_ms > threshold_ms:
                results.append((endpoint, avg_ms))
        return sorted(results, key=lambda x: x[1], reverse=True)


class PerformanceMonitorMiddleware(BaseHTTPMiddleware):
    def __init__(
        self,
        app,
        slow_threshold_ms: float = 1000,
        log_slow_requests: bool = True,
    ):
        super().__init__(app)
        self.slow_threshold_ms = slow_threshold_ms
        self.log_slow_requests = log_slow_requests
        self.monitor = PerformanceMonitor()

    async def dispatch(
        self, request: Request, call_next: Callable
    ) -> Response:
        endpoint = self._get_endpoint_name(request)
        start_time = time.perf_counter()

        try:
            response = await call_next(request)
            duration = time.perf_counter() - start_time
            is_error = response.status_code >= 400

            self.monitor.record_call(
                endpoint, duration, response.status_code, is_error
            )

            if self.log_slow_requests and duration * 1000 > self.slow_threshold_ms:
                logger.warning(
                    f"Slow request: {endpoint} took {duration * 1000:.2f}ms "
                    f"(threshold: {self.slow_threshold_ms}ms)"
                )

            return response

        except Exception as e:
            duration = time.perf_counter() - start_time
            self.monitor.record_call(endpoint, duration, 500, True)
            logger.error("Request failed: %s - %s", endpoint, e)
            raise


def get_performance_monitor() -> PerformanceMonitor:
    return PerformanceMonitor()
