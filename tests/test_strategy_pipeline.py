import numpy as np
import pandas as pd

from core.strategies import (
    BaseStrategy,
    CompositeStrategy,
    DualMAStrategy,
    MACDStrategy,
    SignalType,
    TradeSignal,
)
from core.strategy_pipeline import (
    IndicatorRequest,
    PipelineResult,
    SharedIndicators,
    StrategyPipeline,
    get_strategy_class,
    list_registered_strategies,
    strategy,
)


def _make_df(n: int = 200, seed: int = 42) -> pd.DataFrame:
    rng = np.random.RandomState(seed)
    close = 100 + np.cumsum(rng.randn(n) * 0.5)
    high = close + np.abs(rng.randn(n) * 0.3)
    low = close - np.abs(rng.randn(n) * 0.3)
    volume = np.abs(rng.randn(n) * 1e6 + 5e6)
    return pd.DataFrame({
        "date": pd.date_range("2024-01-01", periods=n),
        "open": close + rng.randn(n) * 0.2,
        "high": high,
        "low": low,
        "close": close,
        "volume": volume,
    })


class TestSharedIndicators:
    def test_compute_rsi(self):
        df = _make_df()
        shared = SharedIndicators()
        req = IndicatorRequest(rsi=True)
        result = shared.compute(df, req)
        assert "rsi" in result
        assert len(result["rsi"]) == len(df)

    def test_compute_macd(self):
        df = _make_df()
        shared = SharedIndicators()
        req = IndicatorRequest(macd=True)
        result = shared.compute(df, req)
        assert "macd_dif" in result
        assert "macd_dea" in result
        assert "macd_hist" in result

    def test_compute_boll(self):
        df = _make_df()
        shared = SharedIndicators()
        req = IndicatorRequest(boll=True)
        result = shared.compute(df, req)
        assert "boll_upper" in result
        assert "boll_lower" in result

    def test_compute_atr(self):
        df = _make_df()
        shared = SharedIndicators()
        req = IndicatorRequest(atr=True)
        result = shared.compute(df, req)
        assert "atr" in result

    def test_compute_ma(self):
        df = _make_df()
        shared = SharedIndicators()
        req = IndicatorRequest(ma=True, ma_periods=(5, 20, 60))
        result = shared.compute(df, req)
        assert "ma_5" in result
        assert "ma_20" in result
        assert "ma_60" in result

    def test_compute_multiple(self):
        df = _make_df()
        shared = SharedIndicators()
        req = IndicatorRequest(rsi=True, macd=True, atr=True, ma=True)
        result = shared.compute(df, req)
        assert "rsi" in result
        assert "macd_dif" in result
        assert "atr" in result
        assert "ma_5" in result

    def test_cache_hit(self):
        df = _make_df()
        shared = SharedIndicators()
        req = IndicatorRequest(rsi=True)
        r1 = shared.compute(df, req)
        r2 = shared.compute(df, req)
        assert r1 is r2

    def test_cache_invalidation(self):
        df = _make_df()
        shared = SharedIndicators()
        req = IndicatorRequest(rsi=True)
        r1 = shared.compute(df, req)
        shared.invalidate(df)
        r2 = shared.compute(df, req)
        assert r1 is not r2

    def test_empty_df(self):
        df = pd.DataFrame()
        shared = SharedIndicators()
        req = IndicatorRequest(rsi=True)
        result = shared.compute(df, req)
        assert result == {}

    def test_cache_max_eviction(self):
        shared = SharedIndicators()
        shared._cache_max = 3
        req = IndicatorRequest(rsi=True)
        dfs = [_make_df(seed=i) for i in range(5)]
        for df in dfs:
            shared.compute(df, req)
        assert len(shared._cache) <= 3


class TestStrategyPipeline:
    def test_pipeline_basic(self):
        df = _make_df()
        pipeline = StrategyPipeline([DualMAStrategy(), MACDStrategy()])
        result = pipeline.run(df)
        assert isinstance(result, PipelineResult)
        assert isinstance(result.final_signal, TradeSignal)
        assert result.strategies_run == 2
        assert "indicators" in result.stages_executed
        assert "signal_generation" in result.stages_executed
        assert "fusion" in result.stages_executed

    def test_pipeline_from_composite(self):
        df = _make_df()
        composite = CompositeStrategy()
        pipeline = StrategyPipeline.from_composite(composite)
        result = pipeline.run(df)
        assert result.strategies_run == len(composite.strategies)
        assert result.indicators_computed > 0

    def test_pipeline_fusion_weighted_vote(self):
        df = _make_df()
        pipeline = StrategyPipeline([DualMAStrategy(), MACDStrategy()])
        pipeline.set_fusion_method("weighted_vote")
        result = pipeline.run(df)
        assert result.final_signal.signal_type in (SignalType.BUY, SignalType.SELL, SignalType.HOLD)

    def test_pipeline_fusion_strength_weighted(self):
        df = _make_df()
        pipeline = StrategyPipeline([DualMAStrategy(), MACDStrategy()])
        pipeline.set_fusion_method("strength_weighted")
        result = pipeline.run(df)
        assert isinstance(result.final_signal, TradeSignal)

    def test_pipeline_fusion_unanimous(self):
        df = _make_df()
        pipeline = StrategyPipeline([DualMAStrategy(), MACDStrategy()])
        pipeline.set_fusion_method("unanimous")
        result = pipeline.run(df)
        assert isinstance(result.final_signal, TradeSignal)

    def test_pipeline_empty_strategies(self):
        df = _make_df()
        pipeline = StrategyPipeline([])
        result = pipeline.run(df)
        assert result.final_signal.signal_type == SignalType.HOLD
        assert result.strategies_run == 0

    def test_pipeline_none_df(self):
        pipeline = StrategyPipeline([DualMAStrategy()])
        result = pipeline.run(None)
        assert result.final_signal.signal_type == SignalType.HOLD

    def test_pipeline_short_df(self):
        df = _make_df(n=5)
        pipeline = StrategyPipeline([DualMAStrategy()])
        result = pipeline.run(df)
        assert isinstance(result, PipelineResult)

    def test_pipeline_add_remove_strategy(self):
        pipeline = StrategyPipeline([DualMAStrategy()])
        assert len(pipeline._strategies) == 1
        pipeline.add_strategy(MACDStrategy())
        assert len(pipeline._strategies) == 2
        pipeline.remove_strategy("MACDStrategy")
        assert len(pipeline._strategies) == 1

    def test_pipeline_custom_stage(self):
        df = _make_df()
        pipeline = StrategyPipeline([DualMAStrategy()])

        def custom_stage(ctx):
            ctx["custom_ran"] = True

        pipeline.add_stage("custom", custom_stage, order=25)
        result = pipeline.run(df)
        assert "custom" in result.stages_executed

    def test_pipeline_risk_filter_high_vol(self):
        rng = np.random.RandomState(42)
        n = 200
        close = 100 + np.cumsum(rng.randn(n) * 3.0)
        df = pd.DataFrame({
            "date": pd.date_range("2024-01-01", periods=n),
            "open": close,
            "high": close + 1,
            "low": close - 1,
            "close": close,
            "volume": np.ones(n) * 1e6,
        })
        pipeline = StrategyPipeline([DualMAStrategy()])
        result = pipeline.run(df)
        if result.final_signal.signal_type != SignalType.HOLD:
            assert result.final_signal.strength <= 0.5


class TestStrategyDecorator:
    def test_register_strategy(self):
        @strategy("test_strat", "ts")
        class TestStrat(BaseStrategy):
            def generate_signal(self, df):
                return TradeSignal(SignalType.HOLD)

        cls = get_strategy_class("test_strat")
        assert cls is TestStrat

        cls_alias = get_strategy_class("ts")
        assert cls_alias is TestStrat

    def test_register_no_names(self):
        @strategy()
        class AutoNamedStrategy(BaseStrategy):
            def generate_signal(self, df):
                return TradeSignal(SignalType.HOLD)

        cls = get_strategy_class("AutoNamedStrategy")
        assert cls is AutoNamedStrategy

    def test_list_registered(self):
        @strategy("list_test_strat")
        class ListTestStrat(BaseStrategy):
            def generate_signal(self, df):
                return TradeSignal(SignalType.HOLD)

        registry = list_registered_strategies()
        assert "list_test_strat" in registry

    def test_get_nonexistent(self):
        cls = get_strategy_class("nonexistent_strategy_xyz")
        assert cls is None


class TestIndicatorRequest:
    def test_default_values(self):
        req = IndicatorRequest()
        assert req.rsi is False
        assert req.macd is False
        assert req.rsi_period == 14

    def test_custom_values(self):
        req = IndicatorRequest(rsi=True, rsi_period=6, macd=True, atr=True, atr_period=20)
        assert req.rsi is True
        assert req.rsi_period == 6
        assert req.atr_period == 20
