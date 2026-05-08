import numpy as np
import pytest

from core.risk_analytics import (
    calc_all_risk_metrics,
    calc_cvar,
    calc_historic_var,
    calc_max_drawdown,
    calc_monte_carlo_var,
    calc_omega_ratio,
    calc_sortino_ratio,
    generate_risk_report,
)


class TestRiskAnalytics:
    def test_calc_max_drawdown_basic(self):
        equity = [100.0, 110.0, 105.0, 120.0, 115.0, 95.0, 100.0, 110.0]
        dd_value, dd_pct, info = calc_max_drawdown(equity)
        assert dd_pct == pytest.approx(0.2083, rel=0.01)
        assert info.trough_date_idx == 5
        assert info.peak_date_idx == 3
        assert info.recovery_date_idx is None

    def test_calc_max_drawdown_empty(self):
        dd_value, dd_pct, info = calc_max_drawdown([])
        assert dd_value == 0.0
        assert dd_pct == 0.0
        assert info is None

    def test_calc_max_drawdown_single(self):
        dd_value, dd_pct, info = calc_max_drawdown([100.0])
        assert dd_value == 0.0
        assert dd_pct == 0.0

    def test_calc_max_drawdown_no_recovery(self):
        equity = [100.0, 120.0, 80.0, 70.0]
        _, dd_pct, info = calc_max_drawdown(equity)
        assert info.recovery_date_idx is None
        assert info.duration_days is None

    def test_calc_sortino_ratio_basic(self):
        returns = np.array([0.01, -0.02, 0.03, -0.01, 0.02, 0.015, -0.025, 0.01])
        ratio = calc_sortino_ratio(returns)
        assert ratio > 0

    def test_calc_sortino_ratio_no_downside(self):
        returns = np.array([0.01, 0.02, 0.03, 0.01])
        ratio = calc_sortino_ratio(returns)
        assert ratio == 0.0

    def test_calc_omega_ratio_basic(self):
        returns = np.array([0.01, -0.02, 0.03, -0.01, 0.02])
        ratio = calc_omega_ratio(returns)
        assert ratio > 0

    def test_calc_omega_ratio_no_losses(self):
        returns = np.array([0.01, 0.02, 0.03])
        ratio = calc_omega_ratio(returns)
        assert ratio == float("inf")

    def test_calc_historic_var_95(self):
        np.random.seed(42)
        returns = np.random.normal(0.001, 0.02, 252)
        var = calc_historic_var(returns, 1_000_000, 0.95)
        assert var > 0
        assert var < 200_000

    def test_calc_historic_var_insufficient_data(self):
        returns = np.array([0.01, 0.02])
        var = calc_historic_var(returns, 1_000_000, 0.95)
        assert var == 0.0

    def test_calc_monte_carlo_var(self):
        np.random.seed(42)
        returns = np.random.normal(0.001, 0.02, 100)
        var = calc_monte_carlo_var(returns, 1_000_000, 0.95, n_simulations=5000)
        assert var > 0

    def test_calc_cvar(self):
        np.random.seed(42)
        returns = np.random.normal(0.001, 0.02, 252)
        cvar = calc_cvar(returns, 1_000_000, 0.95)
        var = calc_historic_var(returns, 1_000_000, 0.95)
        assert cvar >= var

    def test_calc_all_risk_metrics(self):
        np.random.seed(42)
        equity = np.array([100.0 + i * 0.5 + np.random.normal(0, 1) for i in range(100)])
        returns = np.diff(equity) / equity[:-1]
        portfolio_value = 100_000.0
        annual_return = 0.15
        risk_free_rate = 0.03

        metrics = calc_all_risk_metrics(
            returns, equity, portfolio_value, annual_return, risk_free_rate
        )
        assert metrics.sharpe_ratio > 0
        assert metrics.max_drawdown_pct >= 0
        assert metrics.annual_volatility > 0

    def test_generate_risk_report(self):
        from core.risk_analytics import RiskMetrics

        metrics = RiskMetrics(
            var_historic_95=10000,
            var_historic_99=15000,
            var_monte_carlo_95=10500,
            var_monte_carlo_99=16000,
            cvar_95=12000,
            cvar_99=18000,
            max_drawdown=5000,
            max_drawdown_pct=5.0,
            calmar_ratio=1.5,
            sortino_ratio=1.2,
            omega_ratio=1.3,
            annual_volatility=15.0,
            sharpe_ratio=1.0,
            skewness=-0.5,
            kurtosis=2.0,
        )

        report = generate_risk_report(metrics, 100_000)
        assert report["portfolio_value"] == 100_000
        assert report["value_at_risk"]["historic_95"] == 10000
        assert report["risk_adjusted_returns"]["sharpe_ratio"] == 1.0
        assert report["drawdown"]["max_drawdown_pct"] == 5.0
