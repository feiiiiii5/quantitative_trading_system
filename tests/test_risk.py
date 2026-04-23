import numpy as np
import pytest

from core.risk.var_monitor import VaRMonitor, VaRResult, GreeksResult
from core.risk.position_manager import DynamicPositionManager, PositionMode, PositionConstraint
from core.risk.stop_loss import MultiDimensionStopLoss, StopLossType, CircuitBreaker
from core.risk.stress_test import RiskStressTest, StressScenario
from core.risk.risk_attribution import RiskAttribution, BrinsonResult


class TestVaRMonitor:
    def test_calculate_var(self):
        monitor = VaRMonitor()
        returns = np.random.normal(0.001, 0.02, 500)
        result = monitor.calculate_var(returns, 100000)
        assert result.historical_var > 0
        assert result.parametric_var > 0
        assert result.monte_carlo_var > 0
        assert result.cvar > 0

    def test_empty_returns(self):
        monitor = VaRMonitor()
        result = monitor.calculate_var(np.array([]), 100000)
        assert result.historical_var == 0

    def test_greeks(self):
        monitor = VaRMonitor()
        result = monitor.calculate_option_greeks("AAPL", 150, 150, 0.25, 0.03, 0.3, "call")
        assert result.delta != 0
        assert result.gamma > 0

    def test_portfolio_var(self):
        monitor = VaRMonitor()
        positions = {"A": 50000, "B": 50000}
        returns_data = {
            "A": np.random.normal(0.001, 0.02, 200),
            "B": np.random.normal(0.001, 0.015, 200),
        }
        result = monitor.calculate_portfolio_var(positions, returns_data)
        assert result.portfolio_value == 100000


class TestDynamicPositionManager:
    def test_fixed_pct_mode(self):
        mgr = DynamicPositionManager(mode=PositionMode.FIXED_PCT, risk_pct=0.1)
        result = mgr.calculate_position("TEST", 100000, 50)
        assert result.position_pct == 0.1
        assert result.shares > 0

    def test_kelly_mode(self):
        mgr = DynamicPositionManager(mode=PositionMode.KELLY)
        result = mgr.calculate_position("TEST", 100000, 50, win_rate=0.6, avg_win_loss_ratio=2.0)
        assert result.position_pct > 0

    def test_half_kelly_mode(self):
        mgr = DynamicPositionManager(mode=PositionMode.HALF_KELLY)
        result = mgr.calculate_position("TEST", 100000, 50, win_rate=0.6, avg_win_loss_ratio=2.0)
        assert result.position_pct > 0

    def test_vol_target_mode(self):
        mgr = DynamicPositionManager(mode=PositionMode.VOLATILITY_TARGET, target_volatility=0.15)
        result = mgr.calculate_position("TEST", 100000, 50, volatility=0.3)
        assert result.position_pct > 0

    def test_constraint_applied(self):
        mgr = DynamicPositionManager(
            mode=PositionMode.FIXED_PCT, risk_pct=0.5,
            constraints=PositionConstraint(max_single_pct=0.2),
        )
        result = mgr.calculate_position("TEST", 100000, 50)
        assert result.position_pct <= 0.2


class TestMultiDimensionStopLoss:
    def test_percentage_stop(self):
        mgr = MultiDimensionStopLoss(default_stop_pct=0.05)
        order = mgr.set_stop_loss("TEST", 100, "2024-01-01", StopLossType.PERCENTAGE)
        assert order.current_stop == 95.0

    def test_fixed_amount_stop(self):
        mgr = MultiDimensionStopLoss()
        order = mgr.set_stop_loss("TEST", 100, "2024-01-01", StopLossType.FIXED_AMOUNT, {"amount": 3})
        assert order.current_stop == 97.0

    def test_stop_triggered(self):
        mgr = MultiDimensionStopLoss(default_stop_pct=0.05)
        mgr.set_stop_loss("TEST", 100, "2024-01-01", StopLossType.PERCENTAGE)
        result = mgr.check_stop_loss("TEST", 94)
        assert result is not None
        assert result["action"] == "sell"

    def test_stop_not_triggered(self):
        mgr = MultiDimensionStopLoss(default_stop_pct=0.05)
        mgr.set_stop_loss("TEST", 100, "2024-01-01", StopLossType.PERCENTAGE)
        result = mgr.check_stop_loss("TEST", 96)
        assert result is None

    def test_take_profit(self):
        mgr = MultiDimensionStopLoss()
        mgr.set_take_profit("TEST", 100, 0.10)
        result = mgr.check_take_profit("TEST", 111)
        assert result is not None
        assert result["action"] == "sell"

    def test_circuit_breaker_drawdown(self):
        mgr = MultiDimensionStopLoss(circuit_breaker=CircuitBreaker(max_portfolio_drawdown=0.1))
        mgr._peak_equity = 100000
        result = mgr.check_circuit_breaker(89000)
        assert result is not None
        assert result["action"] == "halt_all"


class TestRiskStressTest:
    def test_builtin_scenarios(self):
        test = RiskStressTest()
        scenarios = test.get_scenarios()
        assert "2008_financial_crisis" in scenarios

    def test_run_scenario(self):
        test = RiskStressTest()
        positions = {"600519": {"value": 100000, "invested": 30000}}
        result = test.run_scenario("2008_financial_crisis", positions)
        assert result.portfolio_loss_pct != 0

    def test_custom_shock(self):
        test = RiskStressTest()
        positions = {"600519": {"value": 100000, "invested": 30000}}
        result = test.run_custom_shock(positions, shock_pct=-0.3)
        assert result.portfolio_loss_pct != 0

    def test_add_custom_scenario(self):
        test = RiskStressTest()
        scenario = StressScenario(name="test", description="test scenario", equity_shock=-0.2)
        test.add_scenario(scenario)
        scenarios = test.get_scenarios()
        assert "test" in scenarios


class TestRiskAttribution:
    def test_brinson_attribution(self):
        attr = RiskAttribution()
        pr = {"tech": 0.05, "finance": 0.02}
        br = {"tech": 0.03, "finance": 0.04}
        pw = {"tech": 0.6, "finance": 0.4}
        bw = {"tech": 0.5, "finance": 0.5}
        result = attr.brinson_attribution(pr, br, pw, bw)
        assert result.allocation_effect != 0 or result.selection_effect != 0

    def test_barra_exposures(self):
        attr = RiskAttribution()
        returns = np.random.normal(0.001, 0.02, 200)
        exposures = attr.calculate_barra_exposures(returns)
        assert len(exposures) > 0

    def test_risk_report(self):
        attr = RiskAttribution()
        returns = np.random.normal(0.001, 0.02, 200)
        report = attr.generate_risk_report(returns)
        assert report.total_risk > 0
        assert len(report.barra_exposures) > 0
