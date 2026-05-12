from __future__ import annotations

import asyncio

import numpy as np
import pytest

from core.backtest.enhanced_metrics import (
    ComprehensiveMetrics,
    RuntimeRiskController,
    _check_guardrails,
    compute_comprehensive_metrics,
)
from core.cache import TickCache, make_cache_key, get_adaptive_ttl
from core.strategy_schema import (
    AssetClass,
    MarketType,
    StrategyDefinition,
    StrategyMeta,
    Timeframe,
)


class TestEnhancedMetricsGuardrails:
    def test_overfitting_warning_triggers_with_n_params(self):
        warnings = _check_guardrails(
            n_trades=10, years=3.0, sharpe=1.5, total_return=0.3, max_dd=0.1, n_params=5,
        )
        assert any("过拟合" in w for w in warnings)

    def test_overfitting_warning_absent_with_zero_params(self):
        warnings = _check_guardrails(
            n_trades=100, years=3.0, sharpe=1.5, total_return=0.3, max_dd=0.1, n_params=0,
        )
        assert not any("过拟合" in w for w in warnings)

    def test_low_trade_count_warning(self):
        warnings = _check_guardrails(
            n_trades=10, years=3.0, sharpe=1.5, total_return=0.3, max_dd=0.1, n_params=0,
        )
        assert any("10" in w and "CRITICAL" in w for w in warnings)

    def test_high_sharpe_warning(self):
        warnings = _check_guardrails(
            n_trades=100, years=3.0, sharpe=4.0, total_return=0.3, max_dd=0.1, n_params=0,
        )
        assert any("3.0" in w for w in warnings)

    def test_compute_comprehensive_metrics_passes_n_params(self):
        equity = [1000000 + i * 100 for i in range(100)]
        dates = [f"2024-01-{i+1:02d}" for i in range(100)]
        trades = [{"action": "sell", "pnl": 100, "hold_days": 5, "bar_index": i} for i in range(30)]
        metrics = compute_comprehensive_metrics(
            equity_curve=equity, dates=dates, trades=trades, n_params=5,
        )
        assert isinstance(metrics, ComprehensiveMetrics)
        assert any("过拟合" in w for w in metrics.guardrail_warnings)


class TestRuntimeRiskController:
    def test_daily_loss_limit_halts(self):
        controller = RuntimeRiskController(daily_loss_limit_pct=0.03)
        controller.record_pnl(-40000, 1000000)
        assert controller.is_halted

    def test_can_open_position_within_limits(self):
        controller = RuntimeRiskController(max_open_positions=5)
        can, reason = controller.can_open_position(position_risk_pct=0.02)
        assert can
        assert reason == ""

    def test_cannot_open_when_halted(self):
        controller = RuntimeRiskController(daily_loss_limit_pct=0.03)
        controller.record_pnl(-40000, 1000000)
        can, reason = controller.can_open_position(position_risk_pct=0.02)
        assert not can
        assert "暂停" in reason

    def test_max_positions_reached(self):
        controller = RuntimeRiskController(max_open_positions=2)
        controller.add_position({"symbol": "A", "risk_pct": 0.02})
        controller.add_position({"symbol": "B", "risk_pct": 0.02})
        can, reason = controller.can_open_position(position_risk_pct=0.02)
        assert not can
        assert "上限" in reason

    def test_scale_position_size(self):
        controller = RuntimeRiskController(max_portfolio_risk_pct=0.10)
        controller.add_position({"symbol": "A", "risk_pct": 0.08})
        scaled = controller.scale_position_size(100000, 0.05)
        assert scaled < 100000
        assert scaled > 0

    def test_margin_check(self):
        controller = RuntimeRiskController(leverage=3.0, maintenance_margin_pct=0.25)
        ok, ratio = controller.check_margin(300000, 200000)
        assert ok

    def test_margin_breach(self):
        controller = RuntimeRiskController(leverage=3.0, maintenance_margin_pct=0.25)
        ok, ratio = controller.check_margin(300000, 20000)
        assert not ok


class TestCacheModule:
    def test_make_cache_key_format(self):
        key = make_cache_key("realtime", "600519", "A")
        assert key == "realtime:600519:A"

    def test_make_cache_key_with_params(self):
        key = make_cache_key("history", "000001", "A", period="1y")
        assert key.startswith("history:000001:A:")

    def test_tick_cache_set_get(self):
        cache = TickCache(maxsize=100, ttl=5.0)
        cache.set("test_key", {"price": 100})
        result = cache.get("test_key")
        assert result is not None
        assert result["price"] == 100

    def test_tick_cache_miss(self):
        cache = TickCache(maxsize=100, ttl=5.0)
        result = cache.get("nonexistent")
        assert result is None

    def test_adaptive_ttl_trading_hours(self):
        ttl = get_adaptive_ttl("realtime", is_trading=True)
        assert ttl == 8

    def test_adaptive_ttl_non_trading(self):
        ttl = get_adaptive_ttl("realtime", is_trading=False)
        assert ttl == 60


class TestStrategySchema:
    def test_min_bars_required(self):
        from core.strategy_schema import IndicatorSpec, ParameterSpec
        defn = StrategyDefinition(
            strategy_meta=StrategyMeta(name="Test"),
            parameters={"period": ParameterSpec(value=20, type="int")},
            indicators=[IndicatorSpec(name="SMA", params={"window": 50})],
        )
        assert defn.min_bars_required() >= 150

    def test_summary_card(self):
        defn = StrategyDefinition(strategy_meta=StrategyMeta(name="MyStrategy"))
        card = defn.summary_card()
        assert "MyStrategy" in card
        assert "╔" in card

    def test_strategy_definition_serialization(self):
        defn = StrategyDefinition(strategy_meta=StrategyMeta(name="Test"))
        d = defn.model_dump()
        assert d["strategy_meta"]["name"] == "Test"


class TestSafeNumericConversion:
    def test_backtest_engine_handles_string_prices(self):
        import pandas as pd
        from core.backtest.engine import BacktestEngine
        from core.strategies import DualMAStrategy

        df = pd.DataFrame({
            "date": pd.date_range("2024-01-01", periods=30),
            "open": ["100"] * 15 + ["--"] * 15,
            "high": ["101"] * 15 + ["N/A"] * 15,
            "low": ["99"] * 15 + [""] * 15,
            "close": ["100.5"] * 15 + ["null"] * 15,
            "volume": ["10000"] * 30,
        })
        engine = BacktestEngine(initial_capital=100000)
        result = engine.run(DualMAStrategy(), df, "TEST")
        assert result is not None
        assert len(result.equity_curve) > 0

    def test_safe_numeric_conversion_with_mixed_types(self):
        import pandas as pd
        s = pd.Series(["1.5", "2.5", "--", "N/A", "3.5"])
        result = pd.to_numeric(s, errors="coerce").dropna().values.astype(float)
        assert len(result) == 3
        assert result[0] == 1.5
        assert result[1] == 2.5
        assert result[2] == 3.5
