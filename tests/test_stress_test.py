"""组合压力测试模块测试"""
import numpy as np
import pytest

from core.stress_test import (
    PREDEFINED_SCENARIOS,
    MonteCarloResult,
    PortfolioStressTester,
    ScenarioResult,
    StressScenario,
    get_stress_tester,
)


@pytest.fixture
def tester():
    return PortfolioStressTester(seed=42)


@pytest.fixture
def sample_positions():
    return [
        {"symbol": "600519", "value": 100000, "type": "equity"},
        {"symbol": "000858", "value": 80000, "type": "equity"},
        {"symbol": "BOND01", "value": 50000, "type": "bond"},
        {"symbol": "GOLD01", "value": 30000, "type": "commodity"},
    ]


@pytest.fixture
def sample_returns():
    rng = np.random.default_rng(42)
    n_days = 120
    n_assets = 3
    mean = np.array([0.0005, 0.0003, 0.0002])
    cov = np.array([[0.002, 0.001, 0.0005],
                    [0.001, 0.001, 0.0003],
                    [0.0005, 0.0003, 0.0008]])
    chol_factor = np.linalg.cholesky(cov)
    z = rng.standard_normal((n_days, n_assets))
    returns = mean + z @ chol_factor.T
    return returns


class TestStressScenario:
    def test_creation(self):
        s = StressScenario(name="test", description="desc", equity_shock=-0.2)
        assert s.name == "test"
        assert s.equity_shock == -0.2

    def test_defaults(self):
        s = StressScenario(name="test", description="desc")
        assert s.bond_shock == 0.0
        assert s.volatility_mult == 1.0


class TestPredefinedScenarios:
    def test_count(self):
        assert len(PREDEFINED_SCENARIOS) >= 5

    def test_all_have_negative_equity_shock(self):
        for s in PREDEFINED_SCENARIOS:
            assert s.equity_shock < 0

    def test_all_have_names(self):
        for s in PREDEFINED_SCENARIOS:
            assert len(s.name) > 0
            assert len(s.description) > 0


class TestRunScenario:
    def test_basic_scenario(self, tester, sample_positions):
        scenario = StressScenario(name="test", description="test", equity_shock=-0.2, bond_shock=-0.05, commodity_shock=-0.1)
        result = tester.run_scenario(sample_positions, scenario)
        assert isinstance(result, ScenarioResult)
        assert result.scenario_name == "test"
        assert result.portfolio_impact_pct < 0

    def test_positive_shock(self, tester, sample_positions):
        scenario = StressScenario(name="bull", description="bull", equity_shock=0.2, bond_shock=0.05, commodity_shock=0.1)
        result = tester.run_scenario(sample_positions, scenario)
        assert result.portfolio_impact_pct > 0

    def test_zero_shock(self, tester, sample_positions):
        scenario = StressScenario(name="flat", description="flat")
        result = tester.run_scenario(sample_positions, scenario)
        assert result.portfolio_impact_pct == 0

    def test_position_impacts(self, tester, sample_positions):
        scenario = StressScenario(name="test", description="test", equity_shock=-0.1)
        result = tester.run_scenario(sample_positions, scenario)
        assert "600519" in result.position_impacts
        assert result.position_impacts["600519"] == -10.0

    def test_empty_positions(self, tester):
        scenario = StressScenario(name="test", description="test", equity_shock=-0.2)
        result = tester.run_scenario([], scenario)
        assert result.portfolio_impact_pct == 0


class TestRunAllScenarios:
    def test_returns_all_results(self, tester, sample_positions):
        results = tester.run_all_scenarios(sample_positions)
        assert len(results) == len(PREDEFINED_SCENARIOS)
        for r in results:
            assert "scenario_name" in r
            assert "portfolio_impact_pct" in r

    def test_custom_scenarios(self, tester, sample_positions):
        custom = [StressScenario(name="c1", description="c1", equity_shock=-0.5)]
        results = tester.run_all_scenarios(sample_positions, scenarios=custom)
        assert len(results) == 1
        assert results[0]["scenario_name"] == "c1"


class TestCustomScenario:
    def test_custom(self, tester, sample_positions):
        result = tester.custom_scenario(sample_positions, equity_shock=-0.3, bond_shock=-0.1, name="my_scenario")
        assert result.scenario_name == "my_scenario"
        assert result.portfolio_impact_pct < 0


class TestMonteCarlo:
    def test_basic(self, tester, sample_returns):
        weights = np.array([0.5, 0.3, 0.2])
        result = tester.monte_carlo(sample_returns, weights, 1000000, horizon_days=20, n_simulations=1000)
        assert isinstance(result, MonteCarloResult)
        assert result.n_simulations == 1000
        assert result.var_95 > 0
        assert result.var_99 > 0
        assert result.var_99 >= result.var_95
        assert result.cvar_95 >= result.var_95
        assert 0 <= result.prob_loss <= 1

    def test_summary(self, tester, sample_returns):
        weights = np.array([0.5, 0.3, 0.2])
        result = tester.monte_carlo(sample_returns, weights, 1000000, horizon_days=20, n_simulations=1000)
        summary = result.summary()
        assert "var_95" in summary
        assert "prob_loss_pct" in summary
        assert summary["n_simulations"] == 1000

    def test_insufficient_data(self, tester):
        short_returns = np.array([[0.01], [-0.01]])
        weights = np.array([1.0])
        result = tester.monte_carlo(short_returns, weights, 100000)
        assert result.n_simulations == 0

    def test_empty_weights(self, tester, sample_returns):
        result = tester.monte_carlo(sample_returns, np.array([]), 100000)
        assert result.n_simulations == 0

    def test_mismatched_dimensions(self, tester):
        returns = np.random.randn(100, 3)
        weights = np.array([0.5, 0.5])
        result = tester.monte_carlo(returns, weights, 100000, n_simulations=100)
        assert result.n_simulations == 0

    def test_reproducible_with_seed(self):
        returns = np.random.default_rng(42).standard_normal((100, 2)) * 0.02
        weights = np.array([0.6, 0.4])
        t1 = PortfolioStressTester(seed=123)
        t2 = PortfolioStressTester(seed=123)
        r1 = t1.monte_carlo(returns, weights, 100000, n_simulations=500)
        r2 = t2.monte_carlo(returns, weights, 100000, n_simulations=500)
        assert abs(r1.var_95 - r2.var_95) < 1e-6


class TestGetStressTester:
    def test_singleton(self):
        import core.stress_test as mod
        original = mod._stress_tester
        mod._stress_tester = None
        t1 = get_stress_tester()
        t2 = get_stress_tester()
        assert t1 is t2
        mod._stress_tester = original
