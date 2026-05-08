"""
FeatureEngineer 测试套件
测试特征工程管道 - 6大类别40+特征
"""
from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from core.feature_engineer import (
    FeatureCategory,
    FeatureConfig,
    FeatureEngineer,
    FeatureResult,
    build_ml_features,
    get_feature_engineer,
)


@pytest.fixture
def sample_klines() -> pd.DataFrame:
    np.random.seed(42)
    n = 100
    dates = pd.date_range("2024-01-01", periods=n, freq="1h")
    close = 100 + np.cumsum(np.random.randn(n) * 0.5)
    open_prices = close + np.random.randn(n) * 0.2
    high = np.maximum(close, open_prices) + np.abs(np.random.randn(n) * 0.3)
    low = np.minimum(close, open_prices) - np.abs(np.random.randn(n) * 0.3)
    volume = np.random.randint(1000, 10000, n).astype(float)

    return pd.DataFrame(
        {
            "open": open_prices,
            "high": high,
            "low": low,
            "close": close,
            "volume": volume,
        },
        index=dates,
    )


@pytest.fixture
def minimal_klines() -> pd.DataFrame:
    dates = pd.date_range("2024-01-01", periods=6, freq="1h")
    return pd.DataFrame(
        {
            "open": [100.0] * 6,
            "high": [101.0] * 6,
            "low": [99.0] * 6,
            "close": [100.0, 101.0, 100.5, 100.8, 99.5, 100.2],
            "volume": [1000.0] * 6,
        },
        index=dates,
    )


class TestFeatureEngineerInit:
    def test_default_config(self):
        fe = FeatureEngineer()
        assert fe._config is not None
        assert fe._config.fill_na_method == "zero"

    def test_custom_config(self):
        config = FeatureConfig(
            include_categories=[FeatureCategory.PRICE, FeatureCategory.TECHNICAL],
            lookback_periods=[5, 10],
            normalize=True,
            fill_na_method="mean",
        )
        fe = FeatureEngineer(config)
        assert fe._config.include_categories == [FeatureCategory.PRICE, FeatureCategory.TECHNICAL]
        assert fe._config.lookback_periods == [5, 10]
        assert fe._config.normalize is True
        assert fe._config.fill_na_method == "mean"


class TestBuildFeatures:
    def test_build_all_categories(self, sample_klines):
        fe = FeatureEngineer()
        result = fe.build_features(sample_klines)

        assert isinstance(result, FeatureResult)
        assert len(result.features) == len(sample_klines)
        assert result.n_samples == len(sample_klines)
        assert result.target is not None
        assert len(result.features.columns) > 30

    def test_empty_dataframe_returns_empty(self):
        fe = FeatureEngineer()
        result = fe.build_features(pd.DataFrame())
        assert result.features.empty
        assert result.n_samples == 0

    def test_too_few_rows_returns_empty(self):
        fe = FeatureEngineer()
        df = pd.DataFrame({"close": [1, 2, 3, 4]})
        result = fe.build_features(df)
        assert result.features.empty
        assert result.n_samples == 0

    def test_none_input_returns_empty(self):
        fe = FeatureEngineer()
        result = fe.build_features(None)
        assert result.features.empty

    def test_selected_categories_only(self, sample_klines):
        config = FeatureConfig(include_categories=[FeatureCategory.PRICE])
        fe = FeatureEngineer(config)
        result = fe.build_features(sample_klines)

        assert len(result.features.columns) > 0
        for col in result.features.columns:
            assert col.startswith("returns_") or col.startswith("volatility_") or col.startswith("bb_") or col in ("high_low_ratio", "close_open_ratio")

    def test_feature_names_populated(self, sample_klines):
        fe = FeatureEngineer()
        result = fe.build_features(sample_klines)
        assert len(result.feature_names) > 0
        assert len(result.feature_names) <= len(result.features.columns)

    def test_feature_categories_mapping(self, sample_klines):
        fe = FeatureEngineer()
        result = fe.build_features(sample_klines)
        assert len(result.feature_categories) > 0
        for _, category in result.feature_categories.items():
            assert isinstance(category, FeatureCategory)


class TestPriceFeatures:
    def test_returns_features_exist(self, sample_klines):
        fe = FeatureEngineer(FeatureConfig(include_categories=[FeatureCategory.PRICE]))
        result = fe.build_features(sample_klines)

        for period in [1, 5, 10, 20]:
            assert f"returns_{period}d" in result.features.columns

    def test_volatility_features_exist(self, sample_klines):
        fe = FeatureEngineer(FeatureConfig(include_categories=[FeatureCategory.PRICE]))
        result = fe.build_features(sample_klines)

        for period in [5, 10, 20, 60]:
            assert f"volatility_{period}d" in result.features.columns

    def test_bb_features_exist(self, sample_klines):
        fe = FeatureEngineer(FeatureConfig(include_categories=[FeatureCategory.PRICE]))
        result = fe.build_features(sample_klines)

        for period in [20]:
            assert f"bb_position_{period}d" in result.features.columns
            assert f"bb_upper_{period}d" in result.features.columns
            assert f"bb_lower_{period}d" in result.features.columns

    def test_ratio_features_exist(self, sample_klines):
        fe = FeatureEngineer(FeatureConfig(include_categories=[FeatureCategory.PRICE]))
        result = fe.build_features(sample_klines)

        assert "high_low_ratio" in result.features.columns
        assert "close_open_ratio" in result.features.columns


class TestTechnicalFeatures:
    def test_rsi_features_exist(self, sample_klines):
        fe = FeatureEngineer(FeatureConfig(include_categories=[FeatureCategory.TECHNICAL]))
        result = fe.build_features(sample_klines)

        for period in [7, 14, 28]:
            assert f"rsi_{period}" in result.features.columns

    def test_macd_features_exist(self, sample_klines):
        fe = FeatureEngineer(FeatureConfig(include_categories=[FeatureCategory.TECHNICAL]))
        result = fe.build_features(sample_klines)

        assert "macd" in result.features.columns
        assert "macd_signal" in result.features.columns
        assert "macd_histogram" in result.features.columns

    def test_kdj_features_exist(self, sample_klines):
        fe = FeatureEngineer(FeatureConfig(include_categories=[FeatureCategory.TECHNICAL]))
        result = fe.build_features(sample_klines)

        assert "kdj_k" in result.features.columns
        assert "kdj_d" in result.features.columns
        assert "kdj_j" in result.features.columns

    def test_cci_features_exist(self, sample_klines):
        fe = FeatureEngineer(FeatureConfig(include_categories=[FeatureCategory.TECHNICAL]))
        result = fe.build_features(sample_klines)

        assert "cci_14" in result.features.columns
        assert "cci_20" in result.features.columns

    def test_atr_features_exist(self, sample_klines):
        fe = FeatureEngineer(FeatureConfig(include_categories=[FeatureCategory.TECHNICAL]))
        result = fe.build_features(sample_klines)

        assert "atr_14" in result.features.columns
        assert "atr_ratio" in result.features.columns

    def test_stochastic_features_exist(self, sample_klines):
        fe = FeatureEngineer(FeatureConfig(include_categories=[FeatureCategory.TECHNICAL]))
        result = fe.build_features(sample_klines)

        assert "stoch_k" in result.features.columns
        assert "stoch_d" in result.features.columns

    def test_rsi_range(self, sample_klines):
        fe = FeatureEngineer(FeatureConfig(include_categories=[FeatureCategory.TECHNICAL]))
        result = fe.build_features(sample_klines)
        rsi = result.features["rsi_14"].dropna()
        assert rsi.between(0, 100).all()


class TestVolumeFeatures:
    def test_volume_ratio_features_exist(self, sample_klines):
        fe = FeatureEngineer(FeatureConfig(include_categories=[FeatureCategory.VOLUME]))
        result = fe.build_features(sample_klines)

        assert "volume_ratio_5d" in result.features.columns
        assert "volume_ratio_20d" in result.features.columns
        assert "volume_change" in result.features.columns

    def test_obv_feature_exists(self, sample_klines):
        fe = FeatureEngineer(FeatureConfig(include_categories=[FeatureCategory.VOLUME]))
        result = fe.build_features(sample_klines)

        assert "obv" in result.features.columns
        assert "obv_ma_ratio" in result.features.columns

    def test_price_volume_correlation_exists(self, sample_klines):
        fe = FeatureEngineer(FeatureConfig(include_categories=[FeatureCategory.VOLUME]))
        result = fe.build_features(sample_klines)

        assert "price_volume_corr" in result.features.columns

    def test_volume_std_features_exist(self, sample_klines):
        fe = FeatureEngineer(FeatureConfig(include_categories=[FeatureCategory.VOLUME]))
        result = fe.build_features(sample_klines)

        for period in [5, 10, 20]:
            assert f"volume_std_{period}d" in result.features.columns


class TestTrendFeatures:
    def test_ma_ratio_features_exist(self, sample_klines):
        fe = FeatureEngineer(FeatureConfig(include_categories=[FeatureCategory.TREND]))
        result = fe.build_features(sample_klines)

        for period in [10, 20, 60]:
            assert f"ma_ratio_{period}d" in result.features.columns

    def test_adx_feature_exists(self, sample_klines):
        fe = FeatureEngineer(FeatureConfig(include_categories=[FeatureCategory.TREND]))
        result = fe.build_features(sample_klines)

        assert "adx" in result.features.columns

    def test_swing_features_exist(self, sample_klines):
        fe = FeatureEngineer(FeatureConfig(include_categories=[FeatureCategory.TREND]))
        result = fe.build_features(sample_klines)

        for period in [10, 20]:
            assert f"swing_highs_{period}d" in result.features.columns
            assert f"swing_lows_{period}d" in result.features.columns


class TestStatisticalFeatures:
    def test_skewness_features_exist(self, sample_klines):
        fe = FeatureEngineer(FeatureConfig(include_categories=[FeatureCategory.STATISTICAL]))
        result = fe.build_features(sample_klines)

        for period in [10, 20, 60]:
            assert f"skewness_{period}d" in result.features.columns

    def test_kurtosis_features_exist(self, sample_klines):
        fe = FeatureEngineer(FeatureConfig(include_categories=[FeatureCategory.STATISTICAL]))
        result = fe.build_features(sample_klines)

        for period in [10, 20, 60]:
            assert f"kurtosis_{period}d" in result.features.columns

    def test_returns_stats_features_exist(self, sample_klines):
        fe = FeatureEngineer(FeatureConfig(include_categories=[FeatureCategory.STATISTICAL]))
        result = fe.build_features(sample_klines)

        for stat in ["mean", "std", "min", "max"]:
            for period in [5, 10, 20]:
                assert f"returns_{stat}_{period}d" in result.features.columns


class TestCrossPeriodFeatures:
    def test_ma_crossover_feature_exists(self, sample_klines):
        fe = FeatureEngineer(FeatureConfig(include_categories=[FeatureCategory.CROSS_PERIOD]))
        result = fe.build_features(sample_klines)

        assert "ma_crossover" in result.features.columns

    def test_vol_regime_feature_exists(self, sample_klines):
        fe = FeatureEngineer(FeatureConfig(include_categories=[FeatureCategory.CROSS_PERIOD]))
        result = fe.build_features(sample_klines)

        assert "vol_regime" in result.features.columns


class TestFillNA:
    def test_fill_na_zero(self, minimal_klines):
        config = FeatureConfig(fill_na_method="zero")
        fe = FeatureEngineer(config)
        result = fe.build_features(minimal_klines)
        assert result.features.isna().sum().sum() == 0

    def test_fill_na_ffill(self, minimal_klines):
        config = FeatureConfig(fill_na_method="ffill")
        fe = FeatureEngineer(config)
        result = fe.build_features(minimal_klines)
        assert result.features.notna().sum().sum() > 0

    def test_fill_na_bfill(self, minimal_klines):
        config = FeatureConfig(fill_na_method="bfill")
        fe = FeatureEngineer(config)
        result = fe.build_features(minimal_klines)
        assert result.features.notna().sum().sum() > 0

    def test_fill_na_mean(self, minimal_klines):
        config = FeatureConfig(fill_na_method="mean")
        fe = FeatureEngineer(config)
        result = fe.build_features(minimal_klines)
        assert result.features.notna().sum().sum() > 0


class TestTarget:
    def test_target_generated_by_default(self, sample_klines):
        fe = FeatureEngineer()
        result = fe.build_features(sample_klines)
        assert result.target is not None
        assert len(result.target) == len(sample_klines)

    def test_target_with_horizon(self, sample_klines):
        config = FeatureConfig(prediction_horizon=5)
        fe = FeatureEngineer(config)
        result = fe.build_features(sample_klines)
        assert result.target is not None
        assert result.target.iloc[-5:].isna().all()


class TestFeatureImportance:
    def test_importance_with_sufficient_data(self, sample_klines):
        fe = FeatureEngineer()
        result = fe.build_features(sample_klines)
        importance = fe.get_feature_importance(result.features, result.target)
        assert isinstance(importance, list)
        assert len(importance) <= 20
        for name, score in importance:
            assert isinstance(name, str)
            assert isinstance(score, (int, float))
            assert score >= 0

    def test_importance_insufficient_data(self):
        fe = FeatureEngineer()
        df = pd.DataFrame({
            "open": [100.0] * 5,
            "high": [101.0] * 5,
            "low": [99.0] * 5,
            "close": [100.0, 101.0, 100.5, 100.8, 99.5],
            "volume": [1000.0] * 5,
        })
        result = fe.build_features(df)
        importance = fe.get_feature_importance(result.features, result.target)
        assert importance == []

    def test_importance_sorted_by_score(self, sample_klines):
        fe = FeatureEngineer()
        result = fe.build_features(sample_klines)
        importance = fe.get_feature_importance(result.features, result.target)
        if len(importance) > 1:
            scores = [score for _, score in importance]
            assert scores == sorted(scores, reverse=True)


class TestSingleton:
    def test_singleton_returns_same_instance(self):
        fe1 = get_feature_engineer()
        fe2 = get_feature_engineer()
        assert fe1 is fe2

    def test_singleton_resets_with_config(self):
        fe1 = get_feature_engineer(FeatureConfig(lookback_periods=[5]))
        fe2 = get_feature_engineer(FeatureConfig(lookback_periods=[10]))
        assert fe1 is not fe2


class TestBuildMLFeatures:
    def test_build_ml_features_convenience(self, sample_klines):
        result = build_ml_features(sample_klines)
        assert isinstance(result, FeatureResult)
        assert result.n_samples == len(sample_klines)
        assert len(result.features.columns) > 20
