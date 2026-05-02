import numpy as np
import pandas as pd
import pytest

from core.risk_monitor import (
    EnhancedRiskMonitor,
    PositionLimit,
    RiskLevel,
    RiskMetrics,
    calc_position_size,
)


class TestEnhancedRiskMonitor:
    def test_calc_volatility(self):
        monitor = EnhancedRiskMonitor()
        monitor._equity_curve = list(np.linspace(100, 110, 60))
        vol = monitor.calc_volatility()
        assert vol >= 0

    def test_calc_max_drawdown(self):
        monitor = EnhancedRiskMonitor()
        monitor._equity_curve = [100, 110, 105, 115, 100, 120]
        dd = monitor.calc_max_drawdown()
        assert dd < 0

    def test_calc_current_drawdown(self):
        monitor = EnhancedRiskMonitor()
        monitor._equity_curve = [100, 110, 105, 115, 100]
        dd = monitor.calc_current_drawdown()
        assert dd <= 0

    def test_calc_var(self):
        np.random.seed(42)
        monitor = EnhancedRiskMonitor()
        returns = pd.Series(np.random.randn(100) * 0.02)
        var = monitor.calc_var(returns)
        assert var < 0

    def test_calc_cvar(self):
        np.random.seed(42)
        monitor = EnhancedRiskMonitor()
        returns = pd.Series(np.random.randn(100) * 0.02)
        cvar = monitor.calc_cvar(returns)
        assert cvar <= var if (var := monitor.calc_var(returns)) else True

    def test_calc_sharpe(self):
        np.random.seed(42)
        monitor = EnhancedRiskMonitor()
        returns = pd.Series(np.random.randn(100) * 0.02 + 0.001)
        sharpe = monitor.calc_sharpe(returns)
        assert isinstance(sharpe, float)

    def test_calc_sortino(self):
        np.random.seed(42)
        monitor = EnhancedRiskMonitor()
        returns = pd.Series(np.random.randn(100) * 0.02 + 0.001)
        sortino = monitor.calc_sortino(returns)
        assert isinstance(sortino, float)

    def test_calc_exposure(self):
        monitor = EnhancedRiskMonitor()
        positions = {"A": 50000, "B": 30000}
        exposure = monitor.calc_exposure(positions, 100000)
        assert 0 < exposure < 1

    def test_calc_concentration(self):
        monitor = EnhancedRiskMonitor()
        positions = {"A": 50000, "B": 50000}
        conc = monitor.calc_concentration(positions)
        assert 0 < conc <= 1

    def test_check_position_limits(self):
        monitor = EnhancedRiskMonitor(position_limit=PositionLimit(max_single_position=0.10))
        positions = {"A": 20000, "B": 30000}
        violations = monitor.check_position_limits(positions, 100000)
        assert isinstance(violations, list)

    def test_check_position_limits_violation(self):
        monitor = EnhancedRiskMonitor(position_limit=PositionLimit(max_single_position=0.10))
        positions = {"A": 50000}
        violations = monitor.check_position_limits(positions, 100000)
        assert len(violations) > 0

    def test_get_risk_metrics(self):
        np.random.seed(42)
        monitor = EnhancedRiskMonitor()
        for i in range(60):
            monitor.update_equity(100000 * (1 + np.random.randn() * 0.01))
        positions = {"A": 30000, "B": 20000}
        metrics = monitor.get_risk_metrics(positions, 100000)
        assert isinstance(metrics, RiskMetrics)
        assert isinstance(metrics.risk_level, RiskLevel)

    def test_should_force_liquidate(self):
        monitor = EnhancedRiskMonitor()
        metrics = RiskMetrics(risk_level=RiskLevel.CRITICAL, current_drawdown=-0.30)
        should, reason = monitor.should_force_liquidate(metrics)
        assert should
        assert reason

    def test_should_reduce_position(self):
        monitor = EnhancedRiskMonitor()
        metrics = RiskMetrics(risk_level=RiskLevel.HIGH, current_drawdown=-0.18)
        should, scale, reason = monitor.should_reduce_position(metrics)
        assert should
        assert 0 < scale < 1


class TestCalcPositionSize:
    def test_basic(self):
        size = calc_position_size(1000000, 10.0, 0.20, target_vol=0.15, max_position_pct=0.10)
        assert size > 0
        assert size * 10.0 <= 1000000 * 0.10

    def test_zero_price(self):
        size = calc_position_size(1000000, 0, 0.20)
        assert size == 0

    def test_zero_volatility(self):
        size = calc_position_size(1000000, 10.0, 0.0)
        assert size == 0
