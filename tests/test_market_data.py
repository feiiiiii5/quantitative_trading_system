import asyncio


class TestGetAllAStocksSync:
    def test_returns_list_when_cache_empty_and_no_loop(self):
        from core.market_data import get_all_a_stocks_sync
        result = get_all_a_stocks_sync()
        assert isinstance(result, list)

    def test_returns_cached_data_when_loop_running(self):
        from core.market_data import _all_a_stocks_cache

        cached = [{"symbol": "000001", "name": "Test"}]
        _all_a_stocks_cache[:] = cached

        from core.market_data import get_all_a_stocks_sync
        result = get_all_a_stocks_sync()
        assert result == cached

        _all_a_stocks_cache.clear()

    def test_no_runtime_error_in_running_loop(self):
        from core.market_data import get_all_a_stocks_sync

        async def inner():
            return get_all_a_stocks_sync()

        loop = asyncio.new_event_loop()
        try:
            result = loop.run_until_complete(inner())
            assert isinstance(result, list)
        finally:
            loop.close()
