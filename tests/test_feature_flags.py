"""Tests for feature flags module"""
import pytest

from core.feature_flags import (
    FeatureFlag,
    FeatureFlagManager,
    feature_enabled,
    get_feature_flag_manager,
    require_feature,
    require_feature_async,
)


class TestFeatureFlag:
    """Test FeatureFlag dataclass"""

    def test_feature_flag_creation(self):
        flag = FeatureFlag(
            name="test_feature",
            description="Test feature",
            enabled=True,
            rollout_percentage=50.0,
            tags=["test", "beta"]
        )
        assert flag.name == "test_feature"
        assert flag.description == "Test feature"
        assert flag.enabled is True
        assert flag.rollout_percentage == 50.0
        assert "test" in flag.tags
        assert "beta" in flag.tags

    def test_feature_flag_defaults(self):
        flag = FeatureFlag(name="default", description="Default")
        assert flag.enabled is True
        assert flag.rollout_percentage == 100.0
        assert flag.tags == []
        assert flag.metadata == {}


class TestFeatureFlagManager:
    """Test FeatureFlagManager singleton"""

    def test_singleton(self):
        mgr1 = FeatureFlagManager()
        mgr2 = FeatureFlagManager()
        assert mgr1 is mgr2

    def test_default_flags_loaded(self):
        mgr = get_feature_flag_manager()
        flags = mgr.list_flags()
        assert len(flags) > 0
        flag_names = [f.name for f in flags]
        assert "vectorized_backtest" in flag_names
        assert "real_time_data" in flag_names
        assert "ml_factor_scoring" in flag_names

    def test_is_enabled(self):
        mgr = get_feature_flag_manager()
        assert mgr.is_enabled("vectorized_backtest") is True
        assert mgr.is_enabled("nonexistent") is False

    def test_set_enabled(self):
        mgr = get_feature_flag_manager()
        original = mgr.is_enabled("auto_risk_management")
        mgr.set_enabled("auto_risk_management", False)
        assert mgr.is_enabled("auto_risk_management") is False
        mgr.set_enabled("auto_risk_management", original)

    def test_toggle(self):
        mgr = get_feature_flag_manager()
        original = mgr.is_enabled("advanced_analytics")
        result = mgr.toggle("advanced_analytics")
        assert result != original
        result = mgr.toggle("advanced_analytics")
        assert result == original

    def test_register_new_flag(self):
        mgr = get_feature_flag_manager()
        mgr.register_flag("new_feature", "New test feature", enabled=False)
        assert mgr.is_enabled("new_feature") is False
        mgr.set_enabled("new_feature", True)
        assert mgr.is_enabled("new_feature") is True

    def test_get_flag(self):
        mgr = get_feature_flag_manager()
        flag = mgr.get_flag("vectorized_backtest")
        assert flag is not None
        assert flag.name == "vectorized_backtest"
        assert mgr.get_flag("nonexistent") is None

    def test_list_flags_with_tags(self):
        mgr = get_feature_flag_manager()
        risk_flags = mgr.list_flags(tags=["risk"])
        assert len(risk_flags) > 0
        for flag in risk_flags:
            assert "risk" in flag.tags

    def test_callback(self):
        mgr = get_feature_flag_manager()
        callback_events = []

        def callback(name, enabled):
            callback_events.append((name, enabled))

        mgr.register_callback(callback)
        try:
            mgr.set_enabled("news_sentiment", False)
            mgr.set_enabled("news_sentiment", True)
            assert len(callback_events) == 2
            assert callback_events[0] == ("news_sentiment", False)
            assert callback_events[1] == ("news_sentiment", True)
        finally:
            mgr.unregister_callback(callback)

    def test_export_import_flags(self):
        mgr = get_feature_flag_manager()
        original = mgr.export_flags()
        mgr.set_enabled("walk_forward_optimization", False)
        exported = mgr.export_flags()
        assert exported["walk_forward_optimization"]["enabled"] is False
        mgr.import_flags(original)
        assert mgr.is_enabled("walk_forward_optimization") is True

    def test_reset_all(self):
        mgr = get_feature_flag_manager()
        mgr.set_enabled("monte_carlo_var", False)
        mgr.reset_all()
        assert mgr.is_enabled("monte_carlo_var") is True


class TestFeatureFlagConvenienceFunctions:
    """Test convenience functions"""

    def test_feature_enabled(self):
        assert feature_enabled("vectorized_backtest") is True
        assert feature_enabled("nonexistent_feature") is False

    def test_require_feature_decorator(self):
        @require_feature("vectorized_backtest")
        def enabled_func():
            return "success"

        @require_feature("disabled_feature")
        def disabled_func():
            return "should not reach"

        result = enabled_func()
        assert result == "success"

        with pytest.raises(RuntimeError, match="disabled_feature"):
            disabled_func()

    @pytest.mark.asyncio
    async def test_require_feature_async_decorator(self):
        @require_feature_async("vectorized_backtest")
        async def enabled_async_func():
            return "success"

        @require_feature_async("disabled_feature")
        async def disabled_async_func():
            return "should not reach"

        result = await enabled_async_func()
        assert result == "success"

        with pytest.raises(RuntimeError, match="disabled_feature"):
            await disabled_async_func()
