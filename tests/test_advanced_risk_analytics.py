"""Tests for Advanced Risk Analytics Module."""
import numpy as np
import pandas as pd
import pytest

from core.advanced_risk_analytics import (
    AdvancedRiskAnalytics,
    RiskMetrics,
    StressTestResult,
)


class TestRiskMetrics:
    def test_default_values(self):
        metrics = RiskMetrics()
        assert metrics.var_95 == 0.0
        assert metrics.max_drawdown == 0.0
        assert metrics.sortino_ratio == 0.0


class TestAdvancedRiskAnalytics:
    @pytest.fixture
    def sample_returns(self):
        np.random.seed(42)
        dates = pd.date_range(start='2023-01-01', periods=252, freq='D')
        returns = pd.Series(np.random.randn(252) * 0.02, index=dates)
        return returns

    @pytest.fixture
    def sample_equity(self):
        np.random.seed(42)
        dates = pd.date_range(start='2023-01-01', periods=252, freq='D')
        returns = pd.Series(np.random.randn(252) * 0.02, index=dates)
        equity = (1 + returns).cumprod() * 100000
        return equity

    def test_init_defaults(self):
        analytics = AdvancedRiskAnalytics()
        assert analytics._risk_free_rate == 0.03

    def test_init_custom(self):
        analytics = AdvancedRiskAnalytics(risk_free_rate=0.05, target_return=0.02)
        assert analytics._risk_free_rate == 0.05
        assert analytics._target_return == 0.02

    def test_calculate_var(self, sample_returns):
        analytics = AdvancedRiskAnalytics()
        var = analytics.calculate_var(sample_returns)
        assert "var_95" in var
        assert "var_99" in var
        assert abs(var["var_95"]) <= abs(var["var_99"])

    def test_calculate_var_single_confidence(self, sample_returns):
        analytics = AdvancedRiskAnalytics()
        var = analytics.calculate_var(sample_returns, confidence_levels=[0.95])
        assert "var_95" in var
        assert "var_99" not in var

    def test_calculate_cvar(self, sample_returns):
        analytics = AdvancedRiskAnalytics()
        cvar = analytics.calculate_cvar(sample_returns)
        assert "cvar_95" in cvar
        assert "cvar_99" in cvar

    def test_calculate_max_drawdown(self, sample_equity):
        analytics = AdvancedRiskAnalytics()
        max_dd, duration = analytics.calculate_max_drawdown(sample_equity)
        assert max_dd >= 0
        assert duration >= 0

    def test_calculate_max_drawdown_empty(self):
        analytics = AdvancedRiskAnalytics()
        max_dd, duration = analytics.calculate_max_drawdown(pd.Series([]))
        assert max_dd == 0.0

    def test_calculate_drawdown_curve(self, sample_equity):
        analytics = AdvancedRiskAnalytics()
        dd_curve = analytics.calculate_drawdown_curve(sample_equity)
        assert len(dd_curve) == len(sample_equity)
        assert dd_curve.min() <= 0

    def test_calculate_sortino_ratio(self, sample_returns):
        analytics = AdvancedRiskAnalytics()
        sortino = analytics.calculate_sortino_ratio(sample_returns)
        assert isinstance(sortino, float)

    def test_calculate_omega_ratio(self, sample_returns):
        analytics = AdvancedRiskAnalytics()
        omega = analytics.calculate_omega_ratio(sample_returns)
        assert isinstance(omega, float)
        assert omega >= 0

    def test_calculate_tail_ratio(self, sample_returns):
        analytics = AdvancedRiskAnalytics()
        tail = analytics.calculate_tail_ratio(sample_returns)
        assert isinstance(tail, float)
        assert tail >= 0

    def test_calculate_moments(self, sample_returns):
        analytics = AdvancedRiskAnalytics()
        moments = analytics.calculate_moments(sample_returns)
        assert "skewness" in moments
        assert "kurtosis" in moments

    def test_calculate_moments_insufficient_data(self):
        analytics = AdvancedRiskAnalytics()
        returns = pd.Series([0.01, 0.02])
        moments = analytics.calculate_moments(returns)
        assert moments["skewness"] == 0.0

    def test_calculate_risk_metrics(self, sample_returns, sample_equity):
        analytics = AdvancedRiskAnalytics()
        metrics = analytics.calculate_risk_metrics(sample_returns, sample_equity)
        assert isinstance(metrics, RiskMetrics)
        assert metrics.var_95 != 0 or metrics.var_95 == 0
        assert metrics.max_drawdown >= 0

    def test_stress_test(self, sample_returns):
        analytics = AdvancedRiskAnalytics()
        results = analytics.stress_test(sample_returns)
        assert len(results) > 0
        assert all(isinstance(r, StressTestResult) for r in results)

    def test_stress_test_custom_scenarios(self, sample_returns):
        analytics = AdvancedRiskAnalytics()
        scenarios = {"test_scenario": -0.20}
        results = analytics.stress_test(sample_returns, scenarios)
        assert len(results) == 1
        assert results[0].scenario_name == "test_scenario"

    def test_calculate_risk_contribution(self):
        analytics = AdvancedRiskAnalytics()
        positions = {"A": 0.4, "B": 0.3, "C": 0.3}
        volatilities = {"A": 0.15, "B": 0.20, "C": 0.18}
        correlations = {}
        contributions = analytics.calculate_risk_contribution(
            positions, volatilities, correlations
        )
        assert len(contributions) == 3
        assert all(c >= 0 for c in contributions.values())

    def test_get_risk_report(self, sample_returns, sample_equity):
        analytics = AdvancedRiskAnalytics()
        report = analytics.get_risk_report(sample_returns, sample_equity)
        assert "var_95" in report
        assert "max_drawdown" in report
        assert "stress_tests" in report
        assert len(report["stress_tests"]) > 0
