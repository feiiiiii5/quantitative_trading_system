import pytest
import pandas as pd
import numpy as np
from core.backtest import BacktestEngine
from core.strategies import DualMAStrategy, MACDStrategy


class TestBacktestEngine:
    def test_basic_backtest(self, sample_ohlcv):
        engine = BacktestEngine(initial_capital=1000000)
        strategy = DualMAStrategy(short_period=5, long_period=20)
        result = engine.run(strategy, sample_ohlcv)
        assert result.strategy_name == "DualMAStrategy"
        assert result.total_return is not None

    def test_vectorized_backtest(self, sample_ohlcv):
        engine = BacktestEngine(initial_capital=1000000, use_vectorized=True)
        strategy = DualMAStrategy(short_period=5, long_period=20)
        result = engine.run(strategy, sample_ohlcv)
        assert result.strategy_name == "DualMAStrategy"

    def test_non_vectorized_backtest(self, sample_ohlcv):
        engine = BacktestEngine(initial_capital=1000000, use_vectorized=False)
        strategy = DualMAStrategy(short_period=5, long_period=20)
        result = engine.run(strategy, sample_ohlcv)
        assert result.strategy_name == "DualMAStrategy"

    def test_insufficient_data(self):
        engine = BacktestEngine()
        strategy = DualMAStrategy()
        small_df = pd.DataFrame({"close": [10], "high": [11], "low": [9], "open": [10], "volume": [1000]})
        result = engine.run(strategy, small_df)
        assert result.strategy_name == "DualMAStrategy"

    def test_none_data(self):
        engine = BacktestEngine()
        strategy = DualMAStrategy()
        result = engine.run(strategy, None)
        assert result.strategy_name == "DualMAStrategy"

    def test_macd_backtest(self, sample_ohlcv):
        engine = BacktestEngine(initial_capital=1000000)
        strategy = MACDStrategy()
        result = engine.run(strategy, sample_ohlcv)
        assert result.strategy_name == "MACDStrategy"

    def test_trending_market(self, trending_up_ohlcv):
        engine = BacktestEngine(initial_capital=1000000)
        strategy = DualMAStrategy(short_period=5, long_period=20)
        result = engine.run(strategy, trending_up_ohlcv)
        assert result is not None

    def test_backtest_result_fields(self, sample_ohlcv):
        engine = BacktestEngine(initial_capital=1000000)
        strategy = DualMAStrategy(short_period=5, long_period=20)
        result = engine.run(strategy, sample_ohlcv)
        assert hasattr(result, "strategy_name")
        assert hasattr(result, "total_return")
        assert hasattr(result, "max_drawdown")
        assert hasattr(result, "sharpe_ratio")
