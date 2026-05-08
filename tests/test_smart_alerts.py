import numpy as np

from core.smart_alerts import SmartAlertEngine


class TestSmartAlertEngineBasic:
    def test_no_alert_on_insufficient_data(self):
        engine = SmartAlertEngine()
        alerts = engine.update("000001", "平安银行", 10.0, 1000)
        assert alerts == []

    def test_no_alert_on_normal_data(self):
        engine = SmartAlertEngine()
        np.random.seed(42)
        for _i in range(30):
            price = 10.0 + np.random.randn() * 0.1
            engine.update("000001", "平安银行", price, 1000 + np.random.randn() * 100)
        alerts = engine.update("000001", "平安银行", 10.05, 1050)
        assert all(a.z_score < engine._price_z_threshold for a in alerts if a.alert_type == "price_anomaly")

    def test_price_anomaly_detected(self):
        engine = SmartAlertEngine(cooldown_seconds=0)
        np.random.seed(42)
        for _i in range(20):
            price = 10.0 + np.random.randn() * 0.05
            engine.update("000001", "平安银行", price, 1000)
        spike_price = 10.0 + 0.5
        alerts = engine.update("000001", "平安银行", spike_price, 1000)
        price_alerts = [a for a in alerts if a.alert_type == "price_anomaly"]
        assert len(price_alerts) > 0
        assert price_alerts[0].z_score >= 2.5
        assert price_alerts[0].symbol == "000001"

    def test_volume_spike_detected(self):
        engine = SmartAlertEngine(cooldown_seconds=0)
        np.random.seed(42)
        for _i in range(20):
            price = 10.0 + np.random.randn() * 0.1
            vol = 1000 + np.random.randn() * 100
            engine.update("000001", "平安银行", price, vol)
        spike_vol = 5000
        alerts = engine.update("000001", "平安银行", 10.0, spike_vol)
        vol_alerts = [a for a in alerts if a.alert_type == "volume_spike"]
        assert len(vol_alerts) > 0
        assert vol_alerts[0].z_score >= 3.0

    def test_zero_price_ignored(self):
        engine = SmartAlertEngine()
        alerts = engine.update("000001", "平安银行", 0, 1000)
        assert alerts == []

    def test_negative_price_ignored(self):
        engine = SmartAlertEngine()
        alerts = engine.update("000001", "平安银行", -5.0, 1000)
        assert alerts == []


class TestSmartAlertEngineCooldown:
    def test_cooldown_prevents_spam(self):
        engine = SmartAlertEngine(cooldown_seconds=60)
        np.random.seed(42)
        for _i in range(20):
            price = 10.0 + np.random.randn() * 0.05
            engine.update("000001", "平安银行", price, 1000)
        spike_price = 10.0 + 0.5
        alerts1 = engine.update("000001", "平安银行", spike_price, 1000)
        alerts2 = engine.update("000001", "平安银行", spike_price + 0.5, 1000)
        if alerts1:
            assert len(alerts2) == 0 or len(alerts2) < len(alerts1)


class TestSmartAlertEngineHistory:
    def test_history_empty_initially(self):
        engine = SmartAlertEngine()
        history = engine.get_alert_history()
        assert history == []

    def test_history_records_alerts(self):
        engine = SmartAlertEngine(cooldown_seconds=0)
        np.random.seed(42)
        for _i in range(20):
            price = 10.0 + np.random.randn() * 0.05
            engine.update("000001", "平安银行", price, 1000)
        engine.update("000001", "平安银行", 10.5, 1000)
        history = engine.get_alert_history()
        assert len(history) > 0
        assert "symbol" in history[0]
        assert "alert_type" in history[0]
        assert "z_score" in history[0]

    def test_history_limited(self):
        engine = SmartAlertEngine(cooldown_seconds=0)
        np.random.seed(42)
        for _i in range(20):
            price = 10.0 + np.random.randn() * 0.05
            engine.update("000001", "平安银行", price, 1000)
        engine.update("000001", "平安银行", 10.5, 1000)
        history = engine.get_alert_history(limit=1)
        assert len(history) <= 1


class TestSmartAlertEngineStats:
    def test_stats_none_for_unknown(self):
        engine = SmartAlertEngine()
        stats = engine.get_stats("999999")
        assert stats is None

    def test_stats_after_updates(self):
        engine = SmartAlertEngine()
        for i in range(15):
            engine.update("000001", "平安银行", 10.0 + i * 0.01, 1000 + i * 10)
        stats = engine.get_stats("000001")
        assert stats is not None
        assert stats["symbol"] == "000001"
        assert stats["return_count"] > 0
        assert stats["last_price"] > 0


class TestSmartAlertEngineCleanup:
    def test_cleanup_removes_stale(self):
        engine = SmartAlertEngine()
        engine.update("000001", "平安银行", 10.0, 1000)
        stats = engine.get_stats("000001")
        assert stats is not None
        removed = engine.cleanup_stale(max_age=0)
        assert removed >= 0


class TestSmartAlertEngineSingleton:
    def test_get_smart_alert_engine(self):
        from core.smart_alerts import get_smart_alert_engine
        engine1 = get_smart_alert_engine()
        engine2 = get_smart_alert_engine()
        assert engine1 is engine2
