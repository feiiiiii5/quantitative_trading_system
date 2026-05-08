"""Tests for core data_fetcher module."""

import pandas as pd

from core.data_fetcher import (
    CircuitBreaker,
    DataSourceHealthMonitor,
    SmartDataFetcher,
    get_fetcher,
    validate_kline_data,
    validate_realtime_data,
)


class TestCircuitBreaker:
    def test_circuit_breaker_init(self):
        breaker = CircuitBreaker(failure_threshold=3, timeout=60)
        assert breaker.failure_count == 0
        assert breaker.state == "CLOSED"

    def test_is_valid_result_none(self):
        assert CircuitBreaker._is_valid_result(None) is False

    def test_is_valid_result_empty_dataframe(self):
        assert CircuitBreaker._is_valid_result(pd.DataFrame()) is False

    def test_is_valid_result_valid_dataframe(self):
        df = pd.DataFrame({"a": [1, 2, 3]})
        assert CircuitBreaker._is_valid_result(df) is True

    def test_is_valid_result_empty_dict(self):
        assert CircuitBreaker._is_valid_result({}) is False

    def test_is_valid_result_valid_dict(self):
        assert CircuitBreaker._is_valid_result({"key": "value"}) is True


class TestDataSourceHealthMonitor:
    def test_monitor_init(self):
        monitor = DataSourceHealthMonitor()
        assert monitor is not None
        assert hasattr(monitor, "_memory_stats")

    def test_record_request_success(self):
        monitor = DataSourceHealthMonitor()
        monitor.record_request("akshare", "kline", success=True, latency=0.5)
        assert ("akshare", "kline") in monitor._memory_stats

    def test_record_request_failure(self):
        monitor = DataSourceHealthMonitor()
        monitor.record_request("akshare", "kline", success=False, latency=0.0)
        assert ("akshare", "kline") in monitor._memory_stats

    def test_record_request_updates_stats(self):
        monitor = DataSourceHealthMonitor()
        monitor.record_request("akshare", "kline", success=True, latency=0.5)
        stats = monitor._memory_stats.get(("akshare", "kline"))
        assert stats is not None
        assert stats["success_count"] == 1
        assert stats["latency_sum"] == 0.5


class TestValidateRealtimeData:
    def test_valid_realtime_data(self):
        import time
        data = {
            "symbol": "000001",
            "price": 10.5,
            "change_pct": 2.5,
            "volume": 1000000,
            "timestamp": time.time(),
        }
        assert validate_realtime_data(data, "000001") is True

    def test_missing_price(self):
        import time
        data = {
            "symbol": "000001",
            "change_pct": 2.5,
            "volume": 1000000,
            "timestamp": time.time(),
        }
        assert validate_realtime_data(data, "000001") is False

    def test_negative_price(self):
        import time
        data = {
            "symbol": "000001",
            "price": -10.5,
            "change_pct": 2.5,
            "volume": 1000000,
            "timestamp": time.time(),
        }
        assert validate_realtime_data(data, "000001") is False

    def test_empty_data(self):
        assert validate_realtime_data({}, "000001") is False
        assert validate_realtime_data(None, "000001") is False


class TestValidateKlineData:
    def test_valid_kline_data(self):
        df = pd.DataFrame({
            "date": pd.date_range("2024-01-01", periods=10),
            "open": [10.0] * 10,
            "high": [11.0] * 10,
            "low": [9.0] * 10,
            "close": [10.5] * 10,
            "volume": [1000000] * 10,
        })
        assert validate_kline_data(df, "000001") is True

    def test_empty_dataframe(self):
        df = pd.DataFrame()
        assert validate_kline_data(df, "000001") is False

    def test_missing_date_column(self):
        df = pd.DataFrame({
            "close": [10.5] * 10,
        })
        assert validate_kline_data(df, "000001") is False

    def test_insufficient_rows(self):
        df = pd.DataFrame({
            "date": pd.date_range("2024-01-01", periods=5),
            "close": [10.5] * 5,
            "open": [10.0] * 5,
            "high": [11.0] * 5,
            "low": [9.0] * 5,
        })
        assert validate_kline_data(df, "000001") is False


class TestSmartDataFetcher:
    def test_get_fetcher(self):
        fetcher = get_fetcher()
        assert isinstance(fetcher, SmartDataFetcher)

    def test_fetcher_has_sources(self):
        fetcher = SmartDataFetcher()
        assert hasattr(fetcher, "_sources")
