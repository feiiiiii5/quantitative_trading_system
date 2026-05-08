"""
Tests for Multi-Symbol Backtest Engine
"""
import numpy as np
import pandas as pd
import pytest

from core.multi_symbol_backtest import (
    MultiSymbolBacktest,
    MultiSymbolConfig,
    run_multi_symbol,
)


class TestMultiSymbolConfig:
    def test_default_config(self):
        config = MultiSymbolConfig(
            strategy_name="DualMAStrategy",
            symbols=["AAPL", "MSFT"],
        )
        assert config.max_positions == 5
        assert config.correlation_threshold == 0.7
        assert config.position_method == "equal_weight"

    def test_custom_config(self):
        config = MultiSymbolConfig(
            strategy_name="MACDStrategy",
            symbols=["AAPL", "MSFT", "GOOGL"],
            initial_capital=500_000.0,
            max_positions=3,
            correlation_threshold=0.5,
            position_method="sharpe_weighted",
            parallel=False,
        )
        assert config.initial_capital == 500_000.0
        assert config.max_positions == 3
        assert config.correlation_threshold == 0.5
        assert config.position_method == "sharpe_weighted"


class TestMultiSymbolBacktest:
    def _make_klines(self, n: int = 100, trend: float = 0.001) -> pd.DataFrame:
        dates = pd.bdate_range("2024-01-01", periods=n)
        closes = [100.0]
        for _ in range(n - 1):
            closes.append(closes[-1] * (1 + np.random.randn() * 0.01 + trend))
        return pd.DataFrame({"date": dates, "close": closes})

    def test_empty_data_rejected(self):
        config = MultiSymbolConfig(strategy_name="DualMAStrategy", symbols=["A"])
        engine = MultiSymbolBacktest(config)
        with pytest.raises(ValueError, match="No valid symbol data"):
            engine.run({})

    def test_invalid_data_rejected(self):
        config = MultiSymbolConfig(strategy_name="DualMAStrategy", symbols=["A"])
        engine = MultiSymbolBacktest(config)
        with pytest.raises(ValueError, match="No valid symbol data"):
            engine.run({"A": pd.DataFrame({"close": [1.0]})})

    def test_single_symbol_run(self):
        config = MultiSymbolConfig(
            strategy_name="DualMAStrategy",
            symbols=["AAPL"],
            parallel=False,
        )
        engine = MultiSymbolBacktest(config)
        data = {"AAPL": self._make_klines(60)}
        report = engine.run(data)
        assert "AAPL" in report.symbol_results
        assert report.config.strategy_name == "DualMAStrategy"
        assert isinstance(report.total_return, float)

    def test_multi_symbol_run(self):
        config = MultiSymbolConfig(
            strategy_name="DualMAStrategy",
            symbols=["AAPL", "MSFT"],
            parallel=False,
        )
        engine = MultiSymbolBacktest(config)
        data = {
            "AAPL": self._make_klines(60),
            "MSFT": self._make_klines(60),
        }
        report = engine.run(data)
        assert set(report.symbol_results.keys()) == {"AAPL", "MSFT"}
        assert len(report.weights) == 2
        assert abs(sum(report.weights.values()) - 1.0) < 0.001

    def test_equal_weight_method(self):
        config = MultiSymbolConfig(
            strategy_name="DualMAStrategy",
            symbols=["A", "B", "C"],
            position_method="equal_weight",
            parallel=False,
        )
        engine = MultiSymbolBacktest(config)
        data = {s: self._make_klines(60) for s in ["A", "B", "C"]}
        report = engine.run(data)
        for sym in ["A", "B", "C"]:
            assert abs(report.weights.get(sym, 0) - 1/3) < 0.01

    def test_correlation_matrix_computed(self):
        config = MultiSymbolConfig(
            strategy_name="DualMAStrategy",
            symbols=["A", "B"],
            parallel=False,
        )
        engine = MultiSymbolBacktest(config)
        data = {
            "A": self._make_klines(60),
            "B": self._make_klines(60),
        }
        report = engine.run(data)
        assert "A" in report.correlation_matrix or "B" in report.correlation_matrix

    def test_to_dict_serialization(self):
        config = MultiSymbolConfig(strategy_name="DualMAStrategy", symbols=["A"], parallel=False)
        engine = MultiSymbolBacktest(config)
        data = {"A": self._make_klines(60)}
        report = engine.run(data)
        d = report.to_dict()
        assert "config" in d
        assert "portfolio" in d
        assert "symbols" in d
        assert d["portfolio"]["total_trades"] >= 0


class TestRunMultiSymbol:
    def test_run_multi_symbol_convenience(self):
        dates = pd.bdate_range("2024-01-01", periods=60)
        closes = 100 + np.cumsum(np.random.randn(60) * 0.5)
        df = pd.DataFrame({"date": dates, "close": closes})

        report = run_multi_symbol(
            {"AAPL": df, "MSFT": df},
            strategy_name="DualMAStrategy",
            initial_capital=100_000.0,
            position_method="equal_weight",
            parallel=False,
        )
        assert report.config.initial_capital == 100_000.0
        assert len(report.symbol_results) == 2
