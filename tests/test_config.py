import pytest
from core.config import validate_config, load_config, DEFAULT_CONFIG, get_config


class TestConfigValidation:
    def test_default_config_valid(self):
        errors = validate_config(DEFAULT_CONFIG)
        assert len(errors) == 0

    def test_invalid_port(self):
        config = {"server": {"port": 80}}
        errors = validate_config(config)
        assert any("port" in e for e in errors)

    def test_invalid_log_level(self):
        config = {"server": {"log_level": "verbose"}}
        errors = validate_config(config)
        assert any("log_level" in e for e in errors)

    def test_negative_commission(self):
        config = {"backtest": {"commission": -0.01}}
        errors = validate_config(config)
        assert any("commission" in e for e in errors)

    def test_max_concentration_range(self):
        config = {"risk": {"max_concentration": 2.0}}
        errors = validate_config(config)
        assert any("max_concentration" in e for e in errors)

    def test_valid_custom_config(self):
        config = {
            "server": {"port": 9090, "log_level": "debug"},
            "backtest": {"initial_capital": 500000, "commission": 0.0005},
            "risk": {"max_concentration": 0.2, "max_daily_loss": 0.03},
        }
        errors = validate_config(config)
        assert len(errors) == 0

    def test_load_config_returns_dict(self):
        config = load_config()
        assert isinstance(config, dict)
        assert "server" in config
        assert "backtest" in config
        assert "risk" in config

    def test_get_config_singleton(self):
        c1 = get_config()
        c2 = get_config()
        assert c1 is c2

    def test_default_values(self):
        config = DEFAULT_CONFIG
        assert config["server"]["port"] == 8080
        assert config["backtest"]["initial_capital"] == 1000000
        assert config["risk"]["max_concentration"] == 0.3
        assert config["api"]["auth_enabled"] is False
