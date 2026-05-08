"""
Tests for factor_model module — Factor Exposure Analysis
"""
import numpy as np
import pandas as pd

from core.factor_model import FactorModel


def _make_asset_returns(n_days: int = 252, seed: int = 42) -> pd.Series:
    np.random.seed(seed)
    returns = np.random.normal(0.0005, 0.02, n_days)
    dates = pd.date_range("2023-01-01", periods=n_days, freq="B")
    return pd.Series(returns, index=dates)


def _make_factor_returns(n_days: int = 252, n_factors: int = 3, seed: int = 42) -> pd.DataFrame:
    np.random.seed(seed + 1)
    factor_names = ["MKT", "SMB", "HML"][:n_factors]
    data = {}
    data["MKT"] = np.random.normal(0.0004, 0.015, n_days)
    data["SMB"] = np.random.normal(0.0002, 0.01, n_days)
    data["HML"] = np.random.normal(0.0001, 0.008, n_days)
    dates = pd.date_range("2023-01-01", periods=n_days, freq="B")
    return pd.DataFrame(data, index=dates)[factor_names]


class TestFactorModel:

    def test_estimate_factor_exposures_basic(self):
        asset_returns = _make_asset_returns()
        factor_returns = _make_factor_returns()
        fm = FactorModel()
        result = fm.estimate_factor_exposures(asset_returns, factor_returns)
        assert result.is_valid
        assert result.factor_count == 3
        assert "MKT" in result.betas
        assert "SMB" in result.betas
        assert "HML" in result.betas

    def test_exposure_r_squared_range(self):
        asset_returns = _make_asset_returns()
        factor_returns = _make_factor_returns()
        fm = FactorModel()
        result = fm.estimate_factor_exposures(asset_returns, factor_returns)
        assert result.is_valid
        assert 0.0 <= result.r_squared <= 1.0
        assert result.adjusted_r_squared <= result.r_squared or result.r_squared < 0.01

    def test_exposure_alpha_and_tstats(self):
        asset_returns = _make_asset_returns()
        factor_returns = _make_factor_returns()
        fm = FactorModel()
        result = fm.estimate_factor_exposures(asset_returns, factor_returns)
        assert result.is_valid
        assert isinstance(result.alpha, float)
        assert isinstance(result.alpha_tstat, float)
        assert isinstance(result.alpha_pvalue, float)
        assert 0.0 <= result.alpha_pvalue <= 1.0

    def test_exposure_single_factor(self):
        asset_returns = _make_asset_returns()
        factor_returns = _make_factor_returns(n_factors=1)
        fm = FactorModel()
        result = fm.estimate_factor_exposures(asset_returns, factor_returns)
        assert result.is_valid
        assert result.factor_count == 1
        assert "MKT" in result.betas

    def test_exposure_insufficient_data(self):
        dates = pd.date_range("2023-01-01", periods=20, freq="B")
        asset_returns = pd.Series(np.random.normal(0, 0.02, 20), index=dates)
        factor_returns = pd.DataFrame({"MKT": np.random.normal(0, 0.015, 20)}, index=dates)
        fm = FactorModel()
        result = fm.estimate_factor_exposures(asset_returns, factor_returns)
        assert not result.is_valid

    def test_attribute_returns_basic(self):
        asset_returns = _make_asset_returns()
        factor_returns = _make_factor_returns()
        betas = {"MKT": 1.1, "SMB": 0.3, "HML": -0.2}
        fm = FactorModel()
        result = fm.attribute_returns(asset_returns, factor_returns, betas)
        assert result.is_valid
        assert isinstance(result.total_return, float)
        assert isinstance(result.specific_return, float)
        assert "MKT" in result.factor_contributions

    def test_attribute_returns_conservation(self):
        asset_returns = _make_asset_returns()
        factor_returns = _make_factor_returns()
        betas = {"MKT": 1.0, "SMB": 0.5, "HML": -0.3}
        fm = FactorModel()
        result = fm.attribute_returns(asset_returns, factor_returns, betas)
        assert result.is_valid
        total_factor = sum(result.factor_contributions.values())
        reconstructed = total_factor + result.specific_return
        assert abs(reconstructed - result.total_return) < 1e-6

    def test_attribute_empty_returns(self):
        asset_returns = pd.Series(dtype=float)
        factor_returns = pd.DataFrame({"MKT": []})
        betas = {"MKT": 1.0}
        fm = FactorModel()
        result = fm.attribute_returns(asset_returns, factor_returns, betas)
        assert not result.is_valid

    def test_construct_factor_portfolios(self):
        np.random.seed(42)
        n_assets = 20
        n_days = 100
        returns = pd.DataFrame(
            np.random.normal(0.001, 0.02, (n_days, n_assets)),
            columns=[f"STK{i:02d}" for i in range(n_assets)],
        )
        sort_var = pd.Series(
            np.random.randn(n_assets),
            index=returns.columns,
        )
        fm = FactorModel()
        portfolios = fm.construct_factor_mimicking_portfolios(returns, sort_var, n_portfolios=5)
        assert isinstance(portfolios, dict)
        assert "P1" in portfolios
        assert "P5" in portfolios
        assert "SMB_like" in portfolios

    def test_construct_factor_portfolios_insufficient_assets(self):
        np.random.seed(42)
        returns = pd.DataFrame(
            np.random.normal(0.001, 0.02, (100, 3)),
            columns=["A", "B", "C"],
        )
        sort_var = pd.Series([1.0, 2.0, 3.0], index=returns.columns)
        fm = FactorModel()
        portfolios = fm.construct_factor_mimicking_portfolios(returns, sort_var, n_portfolios=5)
        assert portfolios == {}

    def test_custom_risk_free_rate(self):
        asset_returns = _make_asset_returns()
        factor_returns = _make_factor_returns()
        fm = FactorModel(risk_free_rate=0.05)
        result = fm.estimate_factor_exposures(asset_returns, factor_returns)
        assert result.is_valid
