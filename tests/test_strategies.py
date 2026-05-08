"""Tests for core strategies module."""
import numpy as np
import pandas as pd

from core.strategies import (
    DualMAStrategy,
    MACDStrategy,
    SignalType,
    StrategyResult,
    TradeSignal,
    _safe_divide,
)


def _create_sample_data(days: int = 60) -> pd.DataFrame:
    np.random.seed(42)
    dates = pd.date_range("2024-01-01", periods=days, freq="D")
    prices = 100 + np.cumsum(np.random.randn(days) * 2)
    return pd.DataFrame({
        "date": dates,
        "open": prices * 0.99,
        "high": prices * 1.02,
        "low": prices * 0.98,
        "close": prices,
        "volume": np.random.randint(1000000, 5000000, days),
    })


class TestSafeDivide:
    def test_basic_division(self):
        result = _safe_divide(10.0, 2.0)
        assert result == 5.0

    def test_zero_denominator(self):
        result = _safe_divide(10.0, 0.0)
        assert result == 0.0

    def test_array_division(self):
        num = np.array([10.0, 20.0, 30.0])
        den = np.array([2.0, 4.0, 5.0])
        result = _safe_divide(num, den)
        assert np.allclose(result, [5.0, 5.0, 6.0])

    def test_array_zero_denominator(self):
        num = np.array([10.0, 20.0, 30.0])
        den = np.array([2.0, 0.0, 5.0])
        result = _safe_divide(num, den, default=-1.0)
        assert result[0] == 5.0
        assert result[1] == -1.0
        assert result[2] == 6.0


class TestSignalType:
    def test_signal_types(self):
        assert SignalType.BUY.value == "buy"
        assert SignalType.SELL.value == "sell"
        assert SignalType.HOLD.value == "hold"


class TestTradeSignal:
    def test_signal_creation(self):
        signal = TradeSignal(
            signal_type=SignalType.BUY,
            strength=0.8,
            reason="Test signal",
            bar_index=5,
            position_pct=0.5,
        )
        assert signal.signal_type == SignalType.BUY
        assert signal.strength == 0.8
        assert signal.bar_index == 5


class TestStrategyResult:
    def test_result_creation(self):
        result = StrategyResult(
            strategy_name="TestStrategy",
            total_return=0.15,
            sharpe_ratio=1.5,
            max_drawdown=-0.1,
        )
        assert result.strategy_name == "TestStrategy"
        assert result.total_return == 0.15
        assert result.sharpe_ratio == 1.5


class TestDualMAStrategy:
    def test_strategy_creation(self):
        strategy = DualMAStrategy(short_period=5, long_period=20)
        assert strategy.name == "DualMAStrategy"

    def test_generate_signal(self):
        strategy = DualMAStrategy(short_period=5, long_period=20)
        df = _create_sample_data(days=30)
        signal = strategy.generate_signal(df)
        assert isinstance(signal, TradeSignal)
        assert signal.signal_type in SignalType

    def test_insufficient_data(self):
        strategy = DualMAStrategy(short_period=5, long_period=20)
        df = _create_sample_data(days=3)
        signal = strategy.generate_signal(df)
        assert signal.signal_type == SignalType.HOLD

    def test_generate_signals(self):
        strategy = DualMAStrategy(short_period=5, long_period=20)
        df = _create_sample_data(days=60)
        result = strategy.generate_signals(df)
        assert isinstance(result, StrategyResult)
        assert result.strategy_name == "DualMAStrategy"


class TestMACDStrategy:
    def test_strategy_creation(self):
        strategy = MACDStrategy()
        assert strategy.name == "MACDStrategy"

    def test_generate_signal(self):
        strategy = MACDStrategy()
        df = _create_sample_data(days=60)
        signal = strategy.generate_signal(df)
        assert isinstance(signal, TradeSignal)


class TestStrategyValidation:
    def test_param_constraints(self):
        strategy = DualMAStrategy(short_period=5, long_period=20)
        assert hasattr(strategy, "_PARAM_CONSTRAINTS")

    def test_get_params(self):
        strategy = DualMAStrategy(short_period=5, long_period=20)
        params = strategy.get_params()
        assert isinstance(params, dict)
        assert "short_period" in params

    def test_set_params(self):
        strategy = DualMAStrategy(short_period=5, long_period=20)
        strategy.set_params(short_period=10)
        assert strategy.short_period == 10
