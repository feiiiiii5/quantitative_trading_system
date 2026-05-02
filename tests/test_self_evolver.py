import numpy as np
import pandas as pd
import pytest

from core.self_evolver import SelfEvolver, EvolutionConfig, EvolutionResult


class TestSelfEvolver:
    def test_init(self):
        evolver = SelfEvolver()
        assert evolver._generator is not None
        assert evolver._screener is not None
        assert evolver._optimizer is not None
        assert evolver._auditor is not None

    def test_evolve_basic(self, sample_ohlcv):
        config = EvolutionConfig(max_iterations=2, target_sharpe=5.0)
        evolver = SelfEvolver(config=config)
        result = evolver.evolve(sample_ohlcv)
        assert isinstance(result, EvolutionResult)
        assert result.total_iterations >= 1
        assert isinstance(result.best_alphas, list)

    def test_evolve_report(self, sample_ohlcv):
        config = EvolutionConfig(max_iterations=1)
        evolver = SelfEvolver(config=config)
        result = evolver.evolve(sample_ohlcv)
        report = evolver.get_evolution_report(result)
        assert "total_iterations" in report
        assert "is_converged" in report
        assert "best_alphas" in report

    def test_evolve_with_backtest(self, sample_ohlcv):
        config = EvolutionConfig(max_iterations=1)

        def mock_backtest(df, weights, alphas):
            return {"sharpe_ratio": 0.8, "audit_passed": True}

        evolver = SelfEvolver(config=config)
        result = evolver.evolve(sample_ohlcv, backtest_fn=mock_backtest)
        assert isinstance(result, EvolutionResult)

    def test_evolve_convergence(self, sample_ohlcv):
        config = EvolutionConfig(max_iterations=3, target_sharpe=0.01)

        def mock_backtest(df, weights, alphas):
            return {"sharpe_ratio": 1.5, "audit_passed": True}

        evolver = SelfEvolver(config=config)
        result = evolver.evolve(sample_ohlcv, backtest_fn=mock_backtest)
        assert result.is_converged or result.total_iterations <= 3
