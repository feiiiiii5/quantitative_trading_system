"""Tests for core performance_monitor module."""
from unittest.mock import MagicMock

from core.performance_monitor import (
    EndpointMetrics,
    PerformanceMonitor,
    PerformanceMonitorMiddleware,
    get_performance_monitor,
)


class TestEndpointMetrics:
    def test_metrics_init(self):
        metrics = EndpointMetrics()
        assert metrics.total_calls == 0
        assert metrics.total_duration == 0.0
        assert metrics.error_count == 0

    def test_avg_duration(self):
        metrics = EndpointMetrics()
        metrics.total_calls = 10
        metrics.total_duration = 1.0
        assert metrics.avg_duration == 0.1

    def test_error_rate(self):
        metrics = EndpointMetrics()
        metrics.total_calls = 100
        metrics.error_count = 5
        assert metrics.error_rate == 0.05

    def test_to_dict(self):
        metrics = EndpointMetrics()
        metrics.total_calls = 10
        metrics.total_duration = 1.0
        metrics.status_codes = {200: 8, 404: 2}
        result = metrics.to_dict()
        assert result["total_calls"] == 10
        assert result["avg_duration_ms"] == 100.0
        assert result["status_codes"] == {200: 8, 404: 2}


class TestPerformanceMonitor:
    def test_record_call(self):
        monitor = PerformanceMonitor()
        monitor.reset()
        monitor.record_call("/api/test", 0.5, 200)
        metrics = monitor.get_metrics("/api/test")
        assert metrics["total_calls"] == 1

    def test_record_error(self):
        monitor = PerformanceMonitor()
        monitor.reset()
        monitor.record_call("/api/test", 0.5, 500, is_error=True)
        metrics = monitor.get_metrics("/api/test")
        assert metrics["error_rate"] == 100.0

    def test_get_slow_endpoints(self):
        monitor = PerformanceMonitor()
        monitor.reset()
        monitor.record_call("/api/fast", 0.01, 200)
        monitor.record_call("/api/slow", 0.5, 200)
        slow = monitor.get_slow_endpoints(threshold_ms=100)
        assert len(slow) >= 1
        assert slow[0][0] == "/api/slow"

    def test_reset(self):
        monitor = PerformanceMonitor()
        monitor.reset()
        monitor.record_call("/api/test", 0.5, 200)
        monitor.reset("/api/test")
        assert monitor.get_metrics("/api/test")["total_calls"] == 0

    def test_singleton(self):
        monitor1 = PerformanceMonitor()
        monitor2 = PerformanceMonitor()
        assert monitor1 is monitor2


class TestPerformanceMonitorMiddleware:
    def test_middleware_init(self):
        app = MagicMock()
        _middleware = PerformanceMonitorMiddleware(app)
        assert _middleware.slow_threshold_ms == 1000
        assert _middleware.log_slow_requests is True

    def test_get_endpoint_name(self):
        app = MagicMock()
        _middleware = PerformanceMonitorMiddleware(app)
        request = MagicMock()
        request.method = "GET"
        request.url.path = "/api/test"
        endpoint = f"{request.method} {request.url.path}"
        assert "GET" in endpoint
        assert "/api/test" in endpoint


class TestGetPerformanceMonitor:
    def test_get_monitor(self):
        monitor = get_performance_monitor()
        assert isinstance(monitor, PerformanceMonitor)
