from __future__ import annotations

import asyncio

import pytest

from api.middleware import RequestDedupMiddleware, _request_fingerprint, correlation_id


class TestRequestFingerprint:
    def test_non_dedup_path_returns_none(self):
        scope = {"path": "/api/health", "method": "GET", "query_string": b"", "headers": []}
        assert _request_fingerprint(scope) is None

    def test_dedup_path_returns_fingerprint(self):
        scope = {
            "path": "/api/backtest/run",
            "method": "POST",
            "query_string": b"",
            "headers": [],
        }
        fp = _request_fingerprint(scope)
        assert fp is not None
        assert len(fp) == 24

    def test_same_path_same_fingerprint(self):
        scope1 = {"path": "/api/backtest/run", "method": "POST", "query_string": b"", "headers": []}
        scope2 = {"path": "/api/backtest/run", "method": "POST", "query_string": b"", "headers": []}
        assert _request_fingerprint(scope1) == _request_fingerprint(scope2)

    def test_different_method_different_fingerprint(self):
        scope1 = {"path": "/api/backtest/run", "method": "POST", "query_string": b"", "headers": []}
        scope2 = {"path": "/api/backtest/run", "method": "GET", "query_string": b"", "headers": []}
        assert _request_fingerprint(scope1) != _request_fingerprint(scope2)

    def test_idempotency_key_included(self):
        scope1 = {"path": "/api/backtest/run", "method": "POST", "query_string": b"", "headers": [(b"x-idempotency-key", b"abc")]}
        scope2 = {"path": "/api/backtest/run", "method": "POST", "query_string": b"", "headers": [(b"x-idempotency-key", b"xyz")]}
        assert _request_fingerprint(scope1) != _request_fingerprint(scope2)

    def test_all_dedup_paths(self):
        paths = ["/api/backtest/run", "/api/backtest/optimize", "/api/backtest/walk-forward",
                 "/api/market/realtime-batch", "/api/portfolio/risk-dashboard"]
        for path in paths:
            scope = {"path": path, "method": "POST", "query_string": b"", "headers": []}
            assert _request_fingerprint(scope) is not None, f"{path} should be dedup-eligible"


class TestRequestDedupMiddleware:
    def test_non_http_passes_through(self):
        called = False

        async def app(scope, receive, send):
            nonlocal called
            called = True

        mw = RequestDedupMiddleware(app)
        asyncio.run(mw({"type": "websocket"}, None, None))
        assert called

    def test_non_dedup_path_passes_through(self):
        called = False

        async def app(scope, receive, send):
            nonlocal called
            called = True

        mw = RequestDedupMiddleware(app)
        asyncio.run(mw({"type": "http", "path": "/api/health", "method": "GET", "query_string": b"", "headers": []}, None, None))
        assert called


class TestCorrelationId:
    def test_correlation_id_default_empty(self):
        assert correlation_id.get() == ""

    def test_correlation_id_set_and_get(self):
        correlation_id.set("test-123")
        assert correlation_id.get() == "test-123"
        correlation_id.set("")
