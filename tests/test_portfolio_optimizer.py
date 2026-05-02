import numpy as np
import pandas as pd
import pytest

from core.portfolio_optimizer import (
    mean_variance_optimize,
    risk_parity_optimize,
    ic_weighted_optimize,
    PortfolioOptimizer,
)


class TestMeanVariance:
    def test_basic(self):
        np.random.seed(42)
        n = 5
        expected_returns = np.array([0.10, 0.08, 0.12, 0.06, 0.09])
        cov = np.eye(n) * 0.04
        weights = mean_variance_optimize(expected_returns, cov)
        assert len(weights) == n
        assert abs(weights.sum() - 1.0) < 0.01

    def test_max_weight(self):
        np.random.seed(42)
        n = 5
        expected_returns = np.array([0.10, 0.08, 0.12, 0.06, 0.09])
        cov = np.eye(n) * 0.04
        weights = mean_variance_optimize(expected_returns, cov, max_weight=0.30)
        assert all(w <= 0.30 + 0.01 for w in weights)

    def test_single_asset(self):
        weights = mean_variance_optimize(np.array([0.10]), np.array([[0.04]]))
        assert len(weights) == 1

    def test_empty(self):
        weights = mean_variance_optimize(np.array([]), np.array([]).reshape(0, 0))
        assert len(weights) == 0


class TestRiskParity:
    def test_basic(self):
        np.random.seed(42)
        n = 5
        cov = np.eye(n) * 0.04
        weights = risk_parity_optimize(cov)
        assert len(weights) == n
        assert abs(weights.sum() - 1.0) < 0.01

    def test_equal_risk_contribution(self):
        np.random.seed(42)
        n = 5
        cov = np.eye(n) * 0.04
        weights = risk_parity_optimize(cov)
        port_var = weights @ cov @ weights
        marginal = cov @ weights
        risk_contrib = weights * marginal / port_var
        for rc in risk_contrib:
            assert abs(rc - 1.0 / n) < 0.05

    def test_max_weight(self):
        np.random.seed(42)
        n = 5
        cov = np.eye(n) * 0.04
        weights = risk_parity_optimize(cov, max_weight=0.30)
        assert all(w <= 0.30 + 0.01 for w in weights)

    def test_single_asset(self):
        weights = risk_parity_optimize(np.array([[0.04]]))
        assert len(weights) == 1


class TestICWeighted:
    def test_basic(self):
        ics = np.array([0.05, 0.03, 0.08, 0.02, 0.06])
        vols = np.array([0.15, 0.12, 0.20, 0.10, 0.18])
        weights = ic_weighted_optimize(ics, vols)
        assert len(weights) == 5
        assert abs(weights.sum() - 1.0) < 0.01

    def test_higher_ic_gets_more_weight(self):
        ics = np.array([0.10, 0.01])
        vols = np.array([0.10, 0.20])
        weights = ic_weighted_optimize(ics, vols)
        assert weights[0] > weights[1]

    def test_empty(self):
        weights = ic_weighted_optimize(np.array([]), np.array([]))
        assert len(weights) == 0


class TestPortfolioOptimizer:
    def test_mean_variance(self):
        opt = PortfolioOptimizer()
        expected_returns = np.array([0.10, 0.08, 0.12])
        cov = np.eye(3) * 0.04
        weights = opt.optimize(expected_returns, cov, method="mean_variance")
        assert len(weights) == 3
        assert abs(weights.sum() - 1.0) < 0.01

    def test_risk_parity(self):
        opt = PortfolioOptimizer()
        cov = np.eye(3) * 0.04
        weights = opt.optimize(np.zeros(3), cov, method="risk_parity")
        assert len(weights) == 3
        assert abs(weights.sum() - 1.0) < 0.01

    def test_portfolio_report(self):
        opt = PortfolioOptimizer()
        expected_returns = np.array([0.10, 0.08])
        cov = np.eye(2) * 0.04
        weights = np.array([0.5, 0.5])
        report = opt.get_portfolio_report(weights, expected_returns, cov, ["A", "B"])
        assert "expected_return" in report
        assert "volatility" in report
        assert "sharpe_ratio" in report
        assert "weights" in report
        assert "risk_contribution" in report
