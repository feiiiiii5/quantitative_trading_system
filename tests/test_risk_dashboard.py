import numpy as np
import pytest

from core.orders import Order, OrderSide
from core.portfolio_risk_engine import (
    Portfolio,
    PositionInfo,
    PreTradeRiskEngine,
    StressScenario,
    historical_cvar,
    historical_var,
    monte_carlo_var,
    parametric_var,
    run_all_stress_tests,
    run_stress_test,
)


class TestHistoricalVar:
    def test_basic(self):
        returns = np.array([-0.05, -0.03, -0.01, 0.0, 0.01, 0.02, 0.03, 0.04])
        var = historical_var(returns, confidence=0.95)
        assert var > 0

    def test_short_returns(self):
        assert historical_var(np.array([0.01]), confidence=0.95) == 0.0

    def test_empty_returns(self):
        assert historical_var(np.array([]), confidence=0.95) == 0.0


class TestHistoricalCvar:
    def test_basic(self):
        returns = np.array([-0.05, -0.03, -0.01, 0.0, 0.01, 0.02, 0.03, 0.04])
        cvar = historical_cvar(returns, confidence=0.95)
        assert cvar > 0

    def test_cvar_exceeds_var(self):
        returns = np.random.default_rng(42).normal(0, 0.02, 1000)
        var = historical_var(returns, confidence=0.95)
        cvar = historical_cvar(returns, confidence=0.95)
        assert cvar >= var


class TestParametricVar:
    def test_basic(self):
        returns = np.random.default_rng(42).normal(0.001, 0.02, 100)
        var = parametric_var(returns, confidence=0.95)
        assert var > 0

    def test_zero_vol(self):
        returns = np.zeros(100)
        assert parametric_var(returns, confidence=0.95) == 0.0


class TestMonteCarloVar:
    def test_basic(self):
        returns = np.random.default_rng(42).normal(0.001, 0.02, 100)
        var = monte_carlo_var(returns, confidence=0.95)
        assert var > 0


class TestStressTest:
    def test_run_stress_test(self):
        portfolio = Portfolio(
            cash=500000,
            total_value=1000000,
            peak_value=1050000,
            positions={
                "AAPL": PositionInfo(symbol="AAPL", quantity=100, avg_cost=150, market_value=500000, sector="Tech"),
            },
        )
        scenario = StressScenario(
            name="test_crash",
            date_range=("2020-01-01", "2020-03-01"),
            description="Test crash",
            market_shock=-0.30,
        )
        result = run_stress_test(portfolio, scenario)
        assert result.projected_loss_pct < 0
        assert result.projected_loss < 0

    def test_run_all_stress_tests(self):
        portfolio = Portfolio(
            cash=500000,
            total_value=1000000,
            positions={
                "AAPL": PositionInfo(symbol="AAPL", quantity=100, avg_cost=150, market_value=16000, sector="Tech"),
            },
        )
        results = run_all_stress_tests(portfolio)
        assert len(results) > 0
        for r in results:
            assert r.projected_loss_pct < 0


class TestPreTradeRiskEngine:
    def _make_portfolio(self) -> Portfolio:
        return Portfolio(
            cash=500000,
            total_value=1000000,
            peak_value=1050000,
            positions={
                "AAPL": PositionInfo(symbol="AAPL", quantity=100, avg_cost=150, market_value=16000, sector="Tech"),
            },
        )

    def _make_buy_order(self, symbol: str = "MSFT", quantity: int = 100, price: float = 300.0) -> Order:
        return Order(
            order_id="test-001",
            symbol=symbol,
            side=OrderSide.BUY,
            order_type="limit",
            quantity=quantity,
            price=price,
        )

    def test_approved_order(self):
        portfolio = self._make_portfolio()
        order = self._make_buy_order(quantity=10, price=100)
        engine = PreTradeRiskEngine()
        result = engine.check(order, portfolio)
        assert result.approved

    def test_concentration_violation(self):
        portfolio = self._make_portfolio()
        order = self._make_buy_order(quantity=10000, price=300)
        engine = PreTradeRiskEngine()
        result = engine.check(order, portfolio)
        assert not result.approved

    def test_drawdown_circuit_breaker(self):
        portfolio = Portfolio(
            cash=500000,
            total_value=800000,
            peak_value=1000000,
            positions={},
        )
        order = self._make_buy_order(quantity=1, price=1)
        engine = PreTradeRiskEngine()
        result = engine.check(order, portfolio)
        assert not result.approved
        assert any(v.rule_name == "DrawdownCircuitBreaker" for v in result.violations)


class TestConcentrationAnalysis:
    def test_empty_positions(self):
        portfolio = Portfolio(cash=1000000, total_value=1000000, positions={})
        assert portfolio.position_count == 0
        assert portfolio.position_weight("AAPL") == 0.0

    def test_single_position_weight(self):
        portfolio = Portfolio(
            cash=500000,
            total_value=1000000,
            positions={
                "AAPL": PositionInfo(symbol="AAPL", quantity=100, avg_cost=150, market_value=500000, sector="Tech"),
            },
        )
        assert portfolio.position_weight("AAPL") == pytest.approx(0.5)

    def test_sector_exposure(self):
        portfolio = Portfolio(
            cash=500000,
            total_value=1000000,
            positions={
                "AAPL": PositionInfo(symbol="AAPL", quantity=100, avg_cost=150, market_value=300000, sector="Tech"),
                "MSFT": PositionInfo(symbol="MSFT", quantity=50, avg_cost=300, market_value=200000, sector="Tech"),
            },
        )
        assert portfolio.sector_exposure("Tech") == pytest.approx(0.5)
