import os

import pytest
from pydantic import ValidationError

from core.settings import (
    ApiSettings,
    AppSettings,
    BacktestSettings,
    DataSettings,
    RiskSettings,
    ServerSettings,
    get_settings,
)


class TestServerSettings:
    def test_defaults(self):
        s = ServerSettings()
        assert s.host == "0.0.0.0"
        assert s.port == 8080
        assert s.workers == 1
        assert s.log_level == "info"

    def test_invalid_port(self):
        with pytest.raises(ValidationError):
            ServerSettings(port=80)

    def test_invalid_log_level(self):
        with pytest.raises(ValidationError):
            ServerSettings(log_level="verbose")


class TestBacktestSettings:
    def test_defaults(self):
        s = BacktestSettings()
        assert s.initial_capital == 1000000
        assert s.commission == pytest.approx(0.0003)
        assert s.use_vectorized is True

    def test_invalid_capital(self):
        with pytest.raises(ValidationError):
            BacktestSettings(initial_capital=100)


class TestRiskSettings:
    def test_defaults(self):
        s = RiskSettings()
        assert s.max_concentration == pytest.approx(0.3)
        assert s.max_daily_loss == pytest.approx(0.05)
        assert s.max_open_trades == 10

    def test_invalid_concentration(self):
        with pytest.raises(ValidationError):
            RiskSettings(max_concentration=0.01)


class TestApiSettings:
    def test_defaults(self):
        s = ApiSettings()
        assert s.auth_enabled is False
        assert s.rate_limit_per_minute == 120


class TestDataSettings:
    def test_defaults(self):
        s = DataSettings()
        assert s.cache_ttl_realtime == 8
        assert s.cache_ttl_history == 120
        assert s.max_concurrent_requests == 5


class TestAppSettings:
    def test_defaults(self):
        s = AppSettings()
        assert isinstance(s.server, ServerSettings)
        assert isinstance(s.backtest, BacktestSettings)
        assert isinstance(s.risk, RiskSettings)
        assert isinstance(s.api, ApiSettings)
        assert isinstance(s.data, DataSettings)

    def test_get_settings_singleton(self):
        s1 = get_settings()
        s2 = get_settings()
        assert s1 is s2

    def test_env_override(self):
        os.environ["QUANTCORE_SERVER_PORT"] = "9090"
        try:
            s = ServerSettings()
            assert s.port == 9090
        finally:
            del os.environ["QUANTCORE_SERVER_PORT"]
