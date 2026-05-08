"""
Tests for monte_carlo_var module — Monte Carlo VaR Simulation
"""
import numpy as np
import pandas as pd

from core.monte_carlo_var import MonteCarloVaR


def _make_prices(n_assets: int = 5, n_days: int = 252, seed: int = 42) -> pd.DataFrame:
    np.random.seed(seed)
    returns = np.random.normal(0.0005, 0.02, (n_days, n_assets))
    prices = 100 * np.cumprod(1 + returns, axis=0)
    symbols = [f"SYM{i:02d}" for i in range(1, n_assets + 1)]
    return pd.DataFrame(prices, columns=symbols)


class TestMonteCarloVaR:

    def test_basic_simulation(self):
        prices = _make_prices()
        mc = MonteCarloVaR(n_simulations=5000, random_seed=42)
        result = mc.simulate(prices)
        assert result.is_valid
        assert result.n_simulations == 5000
        assert isinstance(result.var_95, float)
        assert isinstance(result.var_99, float)

    def test_var_ordering(self):
        prices = _make_prices()
        mc = MonteCarloVaR(n_simulations=10000, random_seed=42)
        result = mc.simulate(prices)
        assert result.is_valid
        assert result.var_99 <= result.var_95

    def test_cvar_worse_than_var(self):
        prices = _make_prices()
        mc = MonteCarloVaR(n_simulations=10000, random_seed=42)
        result = mc.simulate(prices)
        assert result.is_valid
        assert result.cvar_95 <= result.var_95
        assert result.cvar_99 <= result.var_99

    def test_with_custom_weights(self):
        prices = _make_prices()
        weights = {"SYM01": 0.4, "SYM02": 0.3, "SYM03": 0.2, "SYM04": 0.1, "SYM05": 0.0}
        mc = MonteCarloVaR(n_simulations=5000, random_seed=42)
        result = mc.simulate(prices, weights=weights)
        assert result.is_valid

    def test_reproducibility_with_seed(self):
        prices = _make_prices()
        mc1 = MonteCarloVaR(n_simulations=5000, random_seed=42)
        mc2 = MonteCarloVaR(n_simulations=5000, random_seed=42)
        r1 = mc1.simulate(prices)
        r2 = mc2.simulate(prices)
        assert r1.var_95 == r2.var_95
        assert r1.var_99 == r2.var_99

    def test_historical_simulation(self):
        prices = _make_prices()
        mc = MonteCarloVaR(n_simulations=5000, random_seed=42)
        result = mc.simulate_historical(prices)
        assert result.is_valid
        assert result.n_simulations == 5000

    def test_historical_var_ordering(self):
        prices = _make_prices()
        mc = MonteCarloVaR(n_simulations=10000, random_seed=42)
        result = mc.simulate_historical(prices)
        assert result.is_valid
        assert result.var_99 <= result.var_95

    def test_insufficient_data(self):
        np.random.seed(42)
        returns = np.random.normal(0, 0.02, (20, 3))
        prices = 100 * np.cumprod(1 + returns, axis=0)
        prices_df = pd.DataFrame(prices, columns=["A", "B", "C"])
        mc = MonteCarloVaR(n_simulations=1000, random_seed=42)
        result = mc.simulate(prices_df)
        assert not result.is_valid

    def test_historical_insufficient_data(self):
        np.random.seed(42)
        returns = np.random.normal(0, 0.02, (20, 3))
        prices = 100 * np.cumprod(1 + returns, axis=0)
        prices_df = pd.DataFrame(prices, columns=["A", "B", "C"])
        mc = MonteCarloVaR(n_simulations=1000, random_seed=42)
        result = mc.simulate_historical(prices_df)
        assert not result.is_valid

    def test_confidence_levels_present(self):
        prices = _make_prices()
        mc = MonteCarloVaR(n_simulations=5000, random_seed=42)
        result = mc.simulate(prices)
        assert result.is_valid
        assert "95%" in result.confidence_levels
        assert "99%" in result.confidence_levels

    def test_time_horizon(self):
        prices = _make_prices()
        mc = MonteCarloVaR(n_simulations=5000, time_horizon=10, random_seed=42)
        result = mc.simulate(prices)
        assert result.is_valid

    def test_mean_and_std_positive(self):
        prices = _make_prices()
        mc = MonteCarloVaR(n_simulations=5000, random_seed=42)
        result = mc.simulate(prices)
        assert result.is_valid
        assert result.std_portfolio_return > 0
