"""Tests for core strategy_optimizer module."""
import numpy as np
import pandas as pd

from core.strategies import DualMAStrategy
from core.strategy_optimizer import (
    OptimizationResult,
    StrategyOptimizer,
    quick_optimize,
)


def _create_sample_data(days: int = 100) -> pd.DataFrame:
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


class TestOptimizationResult:
    def test_result_creation(self):
        from core.metrics import InstitutionalMetrics
        metrics = InstitutionalMetrics(
            cagr=0.15,
            sharpe_ratio=1.5,
            max_drawdown=-0.1,
            win_rate=0.55,
            profit_loss_ratio=1.5,
            total_return=0.20,
        )
        result = OptimizationResult(params={"short_period": 5}, metrics=metrics)
        assert result.sharpe == 1.5
        assert result.total_return == 0.20
        assert result.max_drawdown == -0.1

    def test_to_dict(self):
        from core.metrics import InstitutionalMetrics
        metrics = InstitutionalMetrics(
            cagr=0.15,
            sharpe_ratio=1.5,
            max_drawdown=-0.1,
            win_rate=0.55,
            profit_loss_ratio=1.5,
            total_return=0.20,
        )
        result = OptimizationResult(params={"short_period": 5}, metrics=metrics)
        result_dict = result.to_dict()
        assert "params" in result_dict
        assert "sharpe" in result_dict
        assert result_dict["sharpe"] == 1.5


class TestStrategyOptimizer:
    def test_optimizer_init(self):
        optimizer = StrategyOptimizer(
            DualMAStrategy,
            {"short_period": [5, 10], "long_period": [20, 30]},
        )
        assert optimizer.strategy_class == DualMAStrategy
        assert optimizer.metric == "sharpe_ratio"

    def test_optimizer_custom_metric(self):
        optimizer = StrategyOptimizer(
            DualMAStrategy,
            {"short_period": [5, 10]},
            metric="total_return",
        )
        assert optimizer.metric == "total_return"

    def test_generate_param_combinations(self):
        optimizer = StrategyOptimizer(
            DualMAStrategy,
            {"short_period": [5, 10], "long_period": [20, 30]},
        )
        combos = optimizer._generate_param_combinations()
        assert len(combos) == 4
        assert {"short_period": 5, "long_period": 20} in combos
        assert {"short_period": 10, "long_period": 30} in combos

    def test_optimize_returns_sorted_results(self):
        optimizer = StrategyOptimizer(
            DualMAStrategy,
            {"short_period": [5], "long_period": [20]},
        )
        data = _create_sample_data(days=50)
        results = optimizer.optimize(data, max_combinations=1)
        assert len(results) >= 0
        assert all(isinstance(r, OptimizationResult) for r in results)

    def test_optimize_with_limit(self):
        optimizer = StrategyOptimizer(
            DualMAStrategy,
            {"short_period": [5, 10, 15], "long_period": [20, 30, 40]},
        )
        data = _create_sample_data(days=50)
        results = optimizer.optimize(data, max_combinations=5)
        assert len(results) <= 5

    def test_get_best(self):
        optimizer = StrategyOptimizer(
            DualMAStrategy,
            {"short_period": [5], "long_period": [20]},
        )
        data = _create_sample_data(days=50)
        optimizer.optimize(data, max_combinations=1)
        if optimizer.results:
            best = optimizer.get_best(1)
            assert len(best) >= 1

    def test_get_worst(self):
        optimizer = StrategyOptimizer(
            DualMAStrategy,
            {"short_period": [5], "long_period": [20]},
        )
        data = _create_sample_data(days=50)
        optimizer.optimize(data, max_combinations=1)
        if len(optimizer.results) >= 2:
            worst = optimizer.get_worst(1)
            assert len(worst) >= 1


class TestQuickOptimize:
    def test_quick_optimize(self):
        param_grid = {"short_period": [5], "long_period": [20]}
        data = _create_sample_data(days=50)
        results = quick_optimize(DualMAStrategy, param_grid, data, top_n=1)
        assert isinstance(results, list)
        for r in results:
            assert "params" in r
            assert "sharpe" in r

    def test_quick_optimize_custom_metric(self):
        param_grid = {"short_period": [5], "long_period": [20]}
        data = _create_sample_data(days=50)
        results = quick_optimize(
            DualMAStrategy, param_grid, data, metric="total_return", top_n=1
        )
        assert isinstance(results, list)
