import pytest
import pandas as pd
import numpy as np
from core.strategies import (
    BaseStrategy, DualMAStrategy, MACDStrategy, KDJStrategy,
    BollingerBreakoutStrategy, SignalType,
)


class TestBaseStrategyVectorized:
    def test_populate_indicators_default(self, sample_ohlcv):
        s = BaseStrategy()
        result = s.populate_indicators(sample_ohlcv)
        assert isinstance(result, pd.DataFrame)
        assert len(result) == len(sample_ohlcv)

    def test_populate_entry_exit_default(self, sample_ohlcv):
        s = BaseStrategy()
        result = s.populate_entry_exit(sample_ohlcv)
        assert "enter_signal" in result.columns
        assert "exit_signal" in result.columns

    def test_vectorized_fallback_to_iterative(self, sample_ohlcv):
        s = BaseStrategy()
        result = s.generate_signals_vectorized(sample_ohlcv)
        assert result.strategy_name == "BaseStrategy"


class TestDualMAStrategy:
    def test_generate_signal(self, sample_ohlcv):
        s = DualMAStrategy(short_period=5, long_period=20)
        signal = s.generate_signal(sample_ohlcv)
        assert signal.signal_type in [SignalType.BUY, SignalType.SELL, SignalType.HOLD]

    def test_populate_indicators(self, sample_ohlcv):
        s = DualMAStrategy(short_period=5, long_period=20)
        result = s.populate_indicators(sample_ohlcv)
        assert "ma_5" in result.columns
        assert "ma_20" in result.columns

    def test_populate_entry_exit(self, sample_ohlcv):
        s = DualMAStrategy(short_period=5, long_period=20)
        df = s.populate_indicators(sample_ohlcv)
        df = s.populate_entry_exit(df)
        assert "enter_signal" in df.columns
        assert "exit_signal" in df.columns
        assert df["enter_signal"].max() <= 1.0
        assert df["exit_signal"].max() <= 1.0

    def test_vectorized_signals(self, sample_ohlcv):
        s = DualMAStrategy(short_period=5, long_period=20)
        result = s.generate_signals_vectorized(sample_ohlcv)
        assert result.strategy_name == "DualMAStrategy"
        assert len(result.signals) > 0

    def test_trending_up_produces_buy(self, trending_up_ohlcv):
        s = DualMAStrategy(short_period=5, long_period=20)
        result = s.generate_signals(trending_up_ohlcv)
        buy_signals = [sig for sig in result.signals if sig.signal_type == SignalType.BUY]
        assert len(buy_signals) > 0

    def test_trending_down_produces_sell(self, trending_down_ohlcv):
        s = DualMAStrategy(short_period=5, long_period=20)
        result = s.generate_signals(trending_down_ohlcv)
        sell_signals = [sig for sig in result.signals if sig.signal_type == SignalType.SELL]
        assert len(sell_signals) > 0

    def test_insufficient_data(self):
        s = DualMAStrategy(short_period=5, long_period=20)
        small_df = pd.DataFrame({"close": [10, 11], "high": [11, 12], "low": [9, 10], "open": [10, 10.5], "volume": [1000, 1000]})
        signal = s.generate_signal(small_df)
        assert signal.signal_type == SignalType.HOLD


class TestMACDStrategy:
    def test_generate_signal(self, sample_ohlcv):
        s = MACDStrategy()
        signal = s.generate_signal(sample_ohlcv)
        assert signal.signal_type in [SignalType.BUY, SignalType.SELL, SignalType.HOLD]

    def test_populate_indicators(self, sample_ohlcv):
        s = MACDStrategy()
        result = s.populate_indicators(sample_ohlcv)
        assert "dif" in result.columns
        assert "dea" in result.columns
        assert "hist" in result.columns

    def test_vectorized_signals(self, sample_ohlcv):
        s = MACDStrategy()
        result = s.generate_signals_vectorized(sample_ohlcv)
        assert result.strategy_name == "MACDStrategy"
        assert len(result.signals) > 0


class TestKDJStrategy:
    def test_generate_signal(self, sample_ohlcv):
        s = KDJStrategy()
        signal = s.generate_signal(sample_ohlcv)
        assert signal.signal_type in [SignalType.BUY, SignalType.SELL, SignalType.HOLD]

    def test_populate_indicators(self, sample_ohlcv):
        s = KDJStrategy()
        result = s.populate_indicators(sample_ohlcv)
        assert "k" in result.columns
        assert "d" in result.columns
        assert "j" in result.columns

    def test_vectorized_signals(self, sample_ohlcv):
        s = KDJStrategy()
        result = s.generate_signals_vectorized(sample_ohlcv)
        assert result.strategy_name == "KDJStrategy"


class TestBollingerBreakoutStrategy:
    def test_generate_signal(self, sample_ohlcv):
        s = BollingerBreakoutStrategy()
        signal = s.generate_signal(sample_ohlcv)
        assert signal.signal_type in [SignalType.BUY, SignalType.SELL, SignalType.HOLD]

    def test_populate_indicators(self, sample_ohlcv):
        s = BollingerBreakoutStrategy()
        result = s.populate_indicators(sample_ohlcv)
        assert "bb_mid" in result.columns
        assert "bb_upper" in result.columns
        assert "bb_lower" in result.columns

    def test_vectorized_signals(self, sample_ohlcv):
        s = BollingerBreakoutStrategy()
        result = s.generate_signals_vectorized(sample_ohlcv)
        assert result.strategy_name == "BollingerBreakoutStrategy"
