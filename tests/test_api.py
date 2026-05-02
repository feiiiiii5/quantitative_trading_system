import pytest

API_TESTS_AVAILABLE = False
try:
    from main import app
    from starlette.testclient import TestClient
    API_TESTS_AVAILABLE = True
except Exception:
    pass


@pytest.mark.skipif(not API_TESTS_AVAILABLE, reason="API tests require full server dependencies")
class TestHealthEndpoint:
    def test_health_returns_200(self):
        with TestClient(app, raise_server_exceptions=False) as client:
            resp = client.get("/health")
            assert resp.status_code == 200

    def test_health_has_status(self):
        with TestClient(app, raise_server_exceptions=False) as client:
            resp = client.get("/health")
            data = resp.json()
            assert "status" in data

    def test_health_has_version(self):
        with TestClient(app, raise_server_exceptions=False) as client:
            resp = client.get("/health")
            data = resp.json()
            assert "version" in data


@pytest.mark.skipif(not API_TESTS_AVAILABLE, reason="API tests require full server dependencies")
class TestMarketEndpoints:
    def test_market_status(self):
        with TestClient(app, raise_server_exceptions=False) as client:
            resp = client.get("/api/market/status")
            assert resp.status_code == 200

    def test_market_overview(self):
        with TestClient(app, raise_server_exceptions=False) as client:
            resp = client.get("/api/market/overview")
            assert resp.status_code == 200


@pytest.mark.skipif(not API_TESTS_AVAILABLE, reason="API tests require full server dependencies")
class TestStockEndpoints:
    def test_search(self):
        with TestClient(app, raise_server_exceptions=False) as client:
            resp = client.get("/api/search", params={"q": "平安银行"})
            assert resp.status_code == 200

    def test_realtime(self):
        with TestClient(app, raise_server_exceptions=False) as client:
            resp = client.get("/api/stock/realtime/000001")
            assert resp.status_code == 200

    def test_history(self):
        with TestClient(app, raise_server_exceptions=False) as client:
            resp = client.get("/api/stock/history/000001", params={"period": "1m"})
            assert resp.status_code == 200


@pytest.mark.skipif(not API_TESTS_AVAILABLE, reason="API tests require full server dependencies")
class TestBacktestEndpoints:
    def test_strategies_list(self):
        with TestClient(app, raise_server_exceptions=False) as client:
            resp = client.get("/api/backtest/strategies")
            assert resp.status_code == 200


@pytest.mark.skipif(not API_TESTS_AVAILABLE, reason="API tests require full server dependencies")
class TestSystemEndpoints:
    def test_system_metrics(self):
        with TestClient(app, raise_server_exceptions=False) as client:
            resp = client.get("/api/system/metrics")
            assert resp.status_code == 200
