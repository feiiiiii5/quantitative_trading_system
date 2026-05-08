import asyncio

import pytest

from core.async_batch import BatchFetcher, PollingThrottle, request_id_var


class TestPollingThrottle:
    def test_basic_throttle(self):
        throttle = PollingThrottle(requests_per_second=10, burst_size=5)
        assert throttle._rps == 10
        assert throttle._burst == 5

    def test_record_success(self):
        throttle = PollingThrottle(requests_per_second=10, burst_size=5)
        throttle.record_success()
        assert throttle._consecutive_errors == 0

    def test_record_rate_limit(self):
        throttle = PollingThrottle(requests_per_second=10, burst_size=5)
        throttle.record_rate_limit()
        assert throttle._consecutive_errors == 1
        assert throttle._tokens == 0.0
        assert throttle._backoff_until > 0

    def test_record_error(self):
        throttle = PollingThrottle(requests_per_second=10, burst_size=5)
        throttle.record_error()
        assert throttle._consecutive_errors == 1

    def test_reset(self):
        throttle = PollingThrottle(requests_per_second=10, burst_size=5)
        throttle.reset()
        assert throttle._tokens == 5.0
        assert throttle._backoff_until == 0.0
        assert throttle._consecutive_errors == 0


class TestBatchFetcher:
    @pytest.mark.asyncio
    async def test_fetch_one_success(self):
        fetcher = BatchFetcher(max_concurrent=5)
        result = await fetcher.fetch_one(asyncio.sleep(0.001, result=42))
        assert result == 42

    @pytest.mark.asyncio
    async def test_fetch_batch_all_success(self):
        fetcher = BatchFetcher(max_concurrent=5)
        coros = [asyncio.sleep(0.001, result=i) for i in range(5)]
        results = await fetcher.fetch_batch(coros)
        assert sorted(r for r in results if not isinstance(r, Exception)) == [0, 1, 2, 3, 4]

    @pytest.mark.asyncio
    async def test_fetch_batch_with_error(self):
        fetcher = BatchFetcher(max_concurrent=5)

        async def fail():
            raise ValueError("test error")

        coros = [asyncio.sleep(0.001, result=i) for i in range(3)] + [fail()]
        results = await fetcher.fetch_batch(coros)
        assert len(results) == 4
        exceptions = [r for r in results if isinstance(r, Exception)]
        assert len(exceptions) == 1
        assert str(exceptions[0]) == "test error"

    @pytest.mark.asyncio
    async def test_fetch_batch_with_retry_success(self):
        fetcher = BatchFetcher(max_concurrent=5)

        async def succeed():
            return 99

        results = await fetcher.fetch_batch_with_retry(
            items=[1, 2, 3],
            fetch_fn=lambda x: succeed(),
            max_retries=3,
        )
        assert len(results) == 3
        assert all(result == 99 for _, result in results)
        assert [r[0] for r in results] == [1, 2, 3]

    @pytest.mark.asyncio
    async def test_fetch_batch_with_retry_failure(self):
        fetcher = BatchFetcher(max_concurrent=5)

        async def fail():
            raise ValueError("persistent failure")

        results = await fetcher.fetch_batch_with_retry(
            items=["a"],
            fetch_fn=lambda x: fail(),
            max_retries=2,
        )
        assert len(results) == 1
        item, error = results[0]
        assert item == "a"
        assert isinstance(error, ValueError)
        assert str(error) == "persistent failure"

    @pytest.mark.asyncio
    async def test_context_variable_exposed(self):
        token = request_id_var.set("test-req-123")
        try:
            assert request_id_var.get() == "test-req-123"
        finally:
            request_id_var.reset(token)
        assert request_id_var.get() == ""
