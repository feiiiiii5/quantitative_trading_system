import numpy as np
import pandas as pd
import pytest

from core.factor_pipeline import (
    winsorize,
    winsorize_df,
    zscore_normalize,
    zscore_normalize_df,
    rank_normalize,
    rank_normalize_df,
    industry_neutralize,
    market_cap_neutralize,
    orthogonalize,
    full_factor_pipeline,
)


class TestWinsorize:
    def test_basic(self):
        s = pd.Series([1, 2, 3, 4, 5, 100])
        result = winsorize(s, 0.1, 0.9)
        assert result.max() < 100
        assert result.min() >= 1

    def test_no_outliers(self):
        s = pd.Series([1, 2, 3, 4, 5])
        result = winsorize(s, 0.025, 0.975)
        assert len(result) == 5

    def test_with_nan(self):
        s = pd.Series([1, 2, np.nan, 4, 5, 100])
        result = winsorize(s)
        assert result.isna().sum() == 1

    def test_short_series(self):
        s = pd.Series([1, 2])
        result = winsorize(s)
        assert len(result) == 2

    def test_df_winsorize(self):
        df = pd.DataFrame({"a": [1, 2, 3, 100], "b": [4, 5, 6, 200]})
        result = winsorize_df(df)
        assert result["a"].max() < 100
        assert result["b"].max() < 200


class TestZscoreNormalize:
    def test_basic(self):
        s = pd.Series([1, 2, 3, 4, 5])
        result = zscore_normalize(s)
        assert abs(result.mean()) < 0.1
        assert abs(result.std() - 1.0) < 0.1

    def test_constant_series(self):
        s = pd.Series([5, 5, 5, 5])
        result = zscore_normalize(s)
        assert (result == 0).all()

    def test_with_nan(self):
        s = pd.Series([1, 2, np.nan, 4, 5])
        result = zscore_normalize(s)
        assert result.isna().sum() == 1


class TestRankNormalize:
    def test_basic(self):
        s = pd.Series([10, 20, 30, 40, 50])
        result = rank_normalize(s)
        assert result.iloc[0] < result.iloc[-1]
        assert result.max() <= 1.0
        assert result.min() >= 0.0

    def test_with_nan(self):
        s = pd.Series([10, np.nan, 30, 40])
        result = rank_normalize(s)
        assert result.isna().sum() == 1


class TestIndustryNeutralize:
    def test_basic(self):
        factor = pd.Series([0.1, 0.2, 0.3, 0.4, 0.5])
        industry = pd.Series(["A", "A", "B", "B", "B"])
        result = industry_neutralize(factor, industry)
        a_vals = result[industry == "A"]
        b_vals = result[industry == "B"]
        assert abs(a_vals.mean()) < 0.01
        assert abs(b_vals.mean()) < 0.01

    def test_length_mismatch(self):
        factor = pd.Series([0.1, 0.2, 0.3])
        industry = pd.Series(["A", "B"])
        result = industry_neutralize(factor, industry)
        assert len(result) == 3


class TestMarketCapNeutralize:
    def test_basic(self):
        np.random.seed(42)
        n = 50
        factor = pd.Series(np.random.randn(n))
        mcap = pd.Series(np.exp(np.random.randn(n) * 2 + 10))
        result = market_cap_neutralize(factor, mcap)
        assert len(result) == n

    def test_short_series(self):
        factor = pd.Series([0.1, 0.2])
        mcap = pd.Series([100, 200])
        result = market_cap_neutralize(factor, mcap)
        assert len(result) == 2


class TestOrthogonalize:
    def test_basic(self):
        np.random.seed(42)
        df = pd.DataFrame({
            "factor_1": np.random.randn(100),
            "factor_2": np.random.randn(100) * 0.5 + np.random.randn(100) * 0.5,
        })
        result = orthogonalize(df, "factor_1")
        assert len(result) == 100

    def test_single_column(self):
        df = pd.DataFrame({"a": [1, 2, 3]})
        result = orthogonalize(df)
        assert len(result) == 3


class TestFullPipeline:
    def test_basic(self):
        np.random.seed(42)
        df = pd.DataFrame({
            "momentum": np.random.randn(100),
            "volatility": np.random.randn(100) * 0.5,
        })
        result = full_factor_pipeline(df)
        assert len(result) == 100
        assert len(result.columns) == 2

    def test_with_industry(self):
        np.random.seed(42)
        df = pd.DataFrame({
            "momentum": np.random.randn(50),
            "volatility": np.random.randn(50),
        })
        industry = pd.Series(["A"] * 25 + ["B"] * 25)
        result = full_factor_pipeline(df, industry_labels=industry)
        assert len(result) == 50

    def test_empty_df(self):
        df = pd.DataFrame()
        result = full_factor_pipeline(df)
        assert result.empty
