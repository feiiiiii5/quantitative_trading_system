import time

import pytest

from core.alert_system import (
    AlertManager,
    AlertRule,
    AlertSeverity,
    AlertType,
    get_alert_manager,
)


class TestAlertManager:
    def test_creation(self):
        m = AlertManager()
        assert m._config.enabled

    def test_trigger_returns_alert(self):
        m = AlertManager()
        alert = m.trigger(
            AlertType.PRICE_ABOVE,
            AlertSeverity.WARNING,
            "AAPL",
            "Price above 150",
            151.5,
            150.0,
        )
        assert alert is not None
        assert alert.alert_type == AlertType.PRICE_ABOVE
        assert alert.symbol == "AAPL"
        assert alert.value == 151.5

    def test_trigger_stores_in_history(self):
        m = AlertManager()
        m.trigger(AlertType.PRICE_ABOVE, AlertSeverity.WARNING, "AAPL", "test", 151.5, 150.0)
        history = m.get_history()
        assert len(history) == 1

    def test_trigger_filters_by_type(self):
        m = AlertManager()
        m.trigger(AlertType.PRICE_ABOVE, AlertSeverity.WARNING, "AAPL", "test", 151.5, 150.0)
        m.trigger(AlertType.DRAWDOWN, AlertSeverity.CRITICAL, "AAPL", "test", 0.15, 0.10)
        history = m.get_history(alert_type=AlertType.PRICE_ABOVE)
        assert len(history) == 1
        assert history[0].alert_type == AlertType.PRICE_ABOVE

    def test_trigger_filters_by_symbol(self):
        m = AlertManager()
        m.trigger(AlertType.PRICE_ABOVE, AlertSeverity.WARNING, "AAPL", "test", 151.5, 150.0)
        m.trigger(AlertType.PRICE_ABOVE, AlertSeverity.WARNING, "GOOGL", "test", 141.5, 140.0)
        history = m.get_history(symbol="AAPL")
        assert len(history) == 1

    def test_cooldown(self):
        m = AlertManager()
        alert1 = m.trigger(
            AlertType.PRICE_ABOVE, AlertSeverity.WARNING, "AAPL", "test", 151.5, 150.0
        )
        time.sleep(0.05)
        alert2 = m.trigger(
            AlertType.PRICE_ABOVE, AlertSeverity.WARNING, "AAPL", "test", 152.0, 150.0
        )
        assert alert1 is not None
        assert alert2 is None

    def test_throttle(self):
        config = pytest.importorskip("core.alert_system").AlertConfig(
            max_alerts_per_minute=2
        )
        m = AlertManager(config)
        for i in range(5):
            m.trigger(AlertType.PRICE_ABOVE, AlertSeverity.WARNING, f"SYM{i}", f"test{i}", 100 + i, 99)
        history = m.get_history()
        assert len(history) == 2

    def test_disabled_config(self):
        config = pytest.importorskip("core.alert_system").AlertConfig(enabled=False)
        m = AlertManager(config)
        alert = m.trigger(
            AlertType.PRICE_ABOVE, AlertSeverity.WARNING, "AAPL", "test", 151.5, 150.0
        )
        assert alert is None


class TestAlertRules:
    def test_add_rule(self):
        m = AlertManager()
        rule = AlertRule(
            name="test_rule",
            alert_type=AlertType.PRICE_ABOVE,
            symbol="AAPL",
            threshold=150.0,
            severity=AlertSeverity.WARNING,
        )
        rule_id = m.add_rule(rule)
        assert rule_id
        rules = m.get_active_rules()
        assert len(rules) == 1

    def test_disable_rule(self):
        m = AlertManager()
        rule = AlertRule(
            name="test_rule",
            alert_type=AlertType.PRICE_ABOVE,
            symbol="AAPL",
            threshold=150.0,
            severity=AlertSeverity.WARNING,
        )
        rule_id = m.add_rule(rule)
        m.disable_rule(rule_id)
        assert len(m.get_active_rules()) == 0

    def test_enable_rule(self):
        m = AlertManager()
        rule = AlertRule(
            name="test_rule",
            alert_type=AlertType.PRICE_ABOVE,
            symbol="AAPL",
            threshold=150.0,
            severity=AlertSeverity.WARNING,
        )
        rule_id = m.add_rule(rule)
        m.disable_rule(rule_id)
        m.enable_rule(rule_id)
        assert len(m.get_active_rules()) == 1


class TestAlertManagerSubscribe:
    def test_subscribe(self):
        m = AlertManager()
        received = []
        def callback(alert):
            received.append(alert)
        m.subscribe(callback)
        m.trigger(AlertType.PRICE_ABOVE, AlertSeverity.WARNING, "AAPL", "test", 151.5, 150.0)
        assert len(received) == 1

    def test_unsubscribe(self):
        m = AlertManager()
        def callback(alert):
            pass
        m.subscribe(callback)
        m.unsubscribe(callback)
        m.trigger(AlertType.PRICE_ABOVE, AlertSeverity.WARNING, "AAPL", "test", 151.5, 150.0)


class TestAlertCheckMethods:
    def test_check_price_alert_above(self):
        m = AlertManager()
        alert = m.check_price_alert("AAPL", 151.0, upper_threshold=150.0)
        assert alert is not None
        assert alert.alert_type == AlertType.PRICE_ABOVE

    def test_check_price_alert_below(self):
        m = AlertManager()
        alert = m.check_price_alert("AAPL", 149.0, lower_threshold=150.0)
        assert alert is not None
        assert alert.alert_type == AlertType.PRICE_BELOW

    def test_check_pnl_target_reached(self):
        m = AlertManager()
        alert = m.check_pnl_alert("AAPL", pnl=10000, target=5000)
        assert alert is not None
        assert alert.alert_type == AlertType.PNL_TARGET

    def test_check_pnl_stop_loss(self):
        m = AlertManager()
        alert = m.check_pnl_alert("AAPL", pnl=-5000, target=10000, stop_loss=-3000)
        assert alert is not None
        assert alert.alert_type == AlertType.PNL_STOP_LOSS

    def test_check_drawdown(self):
        m = AlertManager()
        alert = m.check_drawdown_alert("AAPL", current_drawdown=0.15, threshold=0.10)
        assert alert is not None
        assert alert.alert_type == AlertType.DRAWDOWN

    def test_check_regime_change(self):
        m = AlertManager()
        alert = m.check_regime_change("AAPL", "bull_base", "bear_distribution")
        assert alert is not None
        assert alert.severity == AlertSeverity.CRITICAL
        assert alert.metadata["new_regime"] == "bear_distribution"

    def test_check_volume_spike(self):
        m = AlertManager()
        alert = m.check_volume_spike("AAPL", current_volume=500000, avg_volume=100000, spike_threshold=3.0)
        assert alert is not None
        assert alert.alert_type == AlertType.VOLUME_SPIKE


class TestAlertSummary:
    def test_summary(self):
        m = AlertManager()
        m.trigger(AlertType.PRICE_ABOVE, AlertSeverity.WARNING, "AAPL", "test", 151.5, 150.0)
        m.trigger(AlertType.PRICE_BELOW, AlertSeverity.WARNING, "GOOGL", "test", 139.0, 140.0)
        summary = m.get_alert_summary()
        assert summary["total_alerts"] == 2
        assert summary["by_type"]["price_above"] == 1


class TestAlertSingleton:
    def test_singleton(self):
        m1 = get_alert_manager()
        m2 = get_alert_manager()
        assert m1 is m2
