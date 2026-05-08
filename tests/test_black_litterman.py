"""
Tests for black_litterman module — Black-Litterman Portfolio Model
"""
import numpy as np
import pandas as pd

from core.black_litterman import BlackLittermanModel, _ledoit_wolf_shrinkage


def _make_prices(n_assets: int = 5, n_days: int = 252, seed: int = 42) -> pd.DataFrame:
    np.random.seed(seed)
    returns = np.random.normal(0.0005, 0.02, (n_days, n_assets))
    prices = 100 * np.cumprod(1 + returns, axis=0)
    symbols = [f"SYM{i:02d}" for i in range(1, n_assets + 1)]
    return pd.DataFrame(prices, columns=symbols)


class TestLedoitWolfShrinkage:

    def test_basic_shrinkage(self):
        np.random.seed(42)
        returns = pd.DataFrame(np.random.normal(0, 1, (100, 3)), columns=["A", "B", "C"])
        cov = _ledoit_wolf_shrinkage(returns)
        assert cov.shape == (3, 3)
        np.testing.assert_array_almost_equal(cov, cov.T)

    def test_shrinkage_positive_semi_definite(self):
        np.random.seed(42)
        returns = pd.DataFrame(np.random.normal(0, 1, (200, 5)))
        cov = _ledoit_wolf_shrinkage(returns)
        eigenvalues = np.linalg.eigvalsh(cov)
        assert np.all(eigenvalues >= -1e-10)


class TestBlackLittermanModel:

    def test_no_views(self):
        prices = _make_prices()
        bl = BlackLittermanModel()
        result = bl.optimize(prices)
        assert result.is_valid
        assert len(result.weights) == 5
        assert abs(sum(result.weights.values()) - 1.0) < 1e-6
        assert result.sharpe_ratio is not None

    def test_with_views(self):
        prices = _make_prices()
        views = [
            {
                "assets": ["SYM01"],
                "signs": [1.0],
                "return": 0.15,
            },
            {
                "assets": ["SYM02", "SYM03"],
                "signs": [1.0, -1.0],
                "return": 0.05,
            },
        ]
        bl = BlackLittermanModel()
        result = bl.optimize(prices, views=views)
        assert result.is_valid
        assert len(result.weights) == 5
        assert abs(sum(result.weights.values()) - 1.0) < 1e-6

    def test_with_market_weights(self):
        prices = _make_prices()
        market_weights = {"SYM01": 0.3, "SYM02": 0.25, "SYM03": 0.2, "SYM04": 0.15, "SYM05": 0.1}
        bl = BlackLittermanModel()
        result = bl.optimize(prices, market_weights=market_weights)
        assert result.is_valid
        assert abs(sum(result.weights.values()) - 1.0) < 1e-6

    def test_with_view_confidences(self):
        prices = _make_prices()
        views = [
            {"assets": ["SYM01"], "signs": [1.0], "return": 0.10},
        ]
        confidences = [0.9]
        bl = BlackLittermanModel()
        result = bl.optimize(prices, views=views, view_confidences=confidences)
        assert result.is_valid

    def test_insufficient_data(self):
        np.random.seed(42)
        returns = np.random.normal(0, 0.02, (5, 3))
        prices = 100 * np.cumprod(1 + returns, axis=0)
        prices_df = pd.DataFrame(prices, columns=["A", "B", "C"])
        bl = BlackLittermanModel()
        result = bl.optimize(prices_df)
        assert not result.is_valid

    def test_custom_parameters(self):
        prices = _make_prices()
        bl = BlackLittermanModel(
            risk_free_rate=0.05,
            tau=0.1,
            risk_aversion=3.0,
            min_weight=0.05,
            max_weight=0.5,
        )
        result = bl.optimize(prices)
        assert result.is_valid

    def test_posterior_returns_keys_match_columns(self):
        prices = _make_prices()
        bl = BlackLittermanModel()
        result = bl.optimize(prices)
        assert set(result.posterior_returns.keys()) == set(prices.columns)

    def test_posterior_covariance_structure(self):
        prices = _make_prices()
        bl = BlackLittermanModel()
        result = bl.optimize(prices)
        assert result.is_valid
        for col in prices.columns:
            assert col in result.posterior_covariance
            for col2 in prices.columns:
                assert col2 in result.posterior_covariance[col]
