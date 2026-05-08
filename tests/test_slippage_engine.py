import pandas as pd
import pytest

from core.slippage_engine import (
    SlippageEngine,
    SlippageModel,
    SlippageResult,
    get_slippage_engine,
)


class TestSlippageEngineFixed:
    def test_fixed_model_returns_result(self):
        config = pytest.importorskip("core.slippage_engine").SlippageConfig(
            model=SlippageModel.FIXED, fixed_bps=5.0
        )
        engine = SlippageEngine(config)
        result = engine.estimate("buy", 100.0, 1000, 100000)
        assert isinstance(result, SlippageResult)
        assert result.total_cost_bps == 5.0

    def test_fixed_buy_effective_price_higher(self):
        config = pytest.importorskip("core.slippage_engine").SlippageConfig(
            model=SlippageModel.FIXED, fixed_bps=10.0
        )
        engine = SlippageEngine(config)
        result = engine.estimate("buy", 100.0, 1000, 100000)
        assert result.effective_price > 100.0

    def test_fixed_sell_effective_price_lower(self):
        config = pytest.importorskip("core.slippage_engine").SlippageConfig(
            model=SlippageModel.FIXED, fixed_bps=10.0
        )
        engine = SlippageEngine(config)
        result = engine.estimate("sell", 100.0, 1000, 100000)
        assert result.effective_price < 100.0


class TestSlippageEngineVolumeBased:
    def test_volume_based_returns_result(self):
        engine = SlippageEngine()
        result = engine.estimate("buy", 100.0, 1000, 100000, 0.02)
        assert isinstance(result, SlippageResult)
        assert 0 <= result.total_cost_bps <= 100

    def test_higher_volume_increases_slippage(self):
        engine = SlippageEngine()
        r_small = engine.estimate("buy", 100.0, 100, 100000, 0.02)
        r_large = engine.estimate("buy", 100.0, 50000, 100000, 0.02)
        assert r_large.total_cost_bps >= r_small.total_cost_bps

    def test_zero_avg_volume_uses_default(self):
        engine = SlippageEngine()
        result = engine.estimate("buy", 100.0, 1000, 0, 0.02)
        assert isinstance(result, SlippageResult)
        assert result.total_cost_bps > 0

    def test_all_models_produce_valid_results(self):
        for model in SlippageModel:
            cfg = pytest.importorskip("core.slippage_engine").SlippageConfig(model=model)
            eng = SlippageEngine(cfg)
            result = eng.estimate("buy", 100.0, 1000, 100000, 0.02)
            assert isinstance(result, SlippageResult)
            assert result.total_cost_bps >= 0
            assert result.effective_price > 0


class TestSlippageEngineEdgeCases:
    def test_negative_price_returns_valid(self):
        engine = SlippageEngine()
        result = engine.estimate("buy", 0, 1000, 100000, 0.02)
        assert isinstance(result, SlippageResult)
        assert result.effective_price >= 0

    def test_delay_cost_positive(self):
        engine = SlippageEngine()
        result = engine.estimate("buy", 100.0, 1000, 100000, 0.02, delay_ms=1000)
        assert result.delay_cost_bps >= 0


class TestSlippageEngineEstimateTradeSeries:
    def test_estimate_trade_series(self):
        engine = SlippageEngine()
        trades = [
            {"date": "2023-01-01", "direction": "buy", "price": 100.0, "volume": 1000},
            {"date": "2023-01-02", "direction": "sell", "price": 102.0, "volume": 500},
            {"date": "2023-01-03", "direction": "buy", "price": 101.0, "volume": 2000},
        ]
        results = engine.estimate_trade_series(trades)
        assert len(results) == 3
        assert all(isinstance(r, SlippageResult) for r in results)

    def test_with_daily_volumes(self):
        engine = SlippageEngine()
        trades = [
            {"date": "2023-01-01", "direction": "buy", "price": 100.0, "volume": 5000},
        ]
        daily_vols = pd.Series({"2023-01-01": 100000.0})
        results = engine.estimate_trade_series(trades, daily_volumes=daily_vols)
        assert len(results) == 1


class TestSlippageEngineApplyToBacktest:
    def test_apply_adjusts_returns(self):
        engine = SlippageEngine()
        df = pd.DataFrame({
            "date": pd.date_range("2023-01-01", periods=5),
            "close": [100, 101, 102, 103, 104],
            "returns": [0.01, 0.01, 0.01, 0.01, 0.01],
        })
        orders = [
            {"date": "2023-01-02", "direction": "buy", "price": 101.0, "volume": 5000},
        ]
        result_df = engine.apply_to_backtest(df, orders)
        assert "returns_adjusted" in result_df.columns
        assert "slippage_cost_bps" in result_df.columns


class TestSlippageEngineCostSummary:
    def test_cost_summary_zero_trades(self):
        engine = SlippageEngine()
        summary = engine.get_cost_summary([])
        assert summary["total_slippage_bps"] == 0.0
        assert summary["avg_slippage_bps"] == 0.0

    def test_cost_summary_multiple_trades(self):
        engine = SlippageEngine()
        results = [
            SlippageResult(5.0, 3.0, 1.0, 1.0, 5.0, 100.05, SlippageModel.VOLUME_BASED),
            SlippageResult(8.0, 5.0, 2.0, 1.0, 8.0, 100.08, SlippageModel.VOLUME_BASED),
        ]
        summary = engine.get_cost_summary(results, initial_capital=1_000_000)
        assert summary["n_trades"] == 2
        assert summary["total_slippage_bps"] == 13.0
        assert summary["avg_slippage_bps"] == 6.5
        assert summary["max_slippage_bps"] == 8.0
        assert summary["model_used"] == "volume_based"


class TestSlippageEngineSingleton:
    def test_singleton(self):
        e1 = get_slippage_engine()
        e2 = get_slippage_engine()
        assert e1 is e2
