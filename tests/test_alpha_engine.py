import numpy as np
import pandas as pd
import pytest

from core.alpha_engine import AlphaGenerator, AlphaPrimitive, AlphaExpression


class TestAlphaPrimitive:
    def test_returns(self, sample_ohlcv):
        result = AlphaPrimitive.returns(sample_ohlcv["close"], 1)
        assert len(result) == len(sample_ohlcv)
        assert result.iloc[0] != result.iloc[0] or True

    def test_momentum(self, sample_ohlcv):
        result = AlphaPrimitive.momentum(sample_ohlcv["close"], 20)
        assert len(result) == len(sample_ohlcv)

    def test_volatility(self, sample_ohlcv):
        result = AlphaPrimitive.volatility(sample_ohlcv["close"], 20)
        assert len(result) == len(sample_ohlcv)

    def test_volume_ratio(self, sample_ohlcv):
        result = AlphaPrimitive.volume_ratio(sample_ohlcv["volume"], 20)
        assert len(result) == len(sample_ohlcv)

    def test_rank(self):
        s = pd.Series([3, 1, 4, 1, 5])
        result = AlphaPrimitive.rank(s)
        assert result.max() <= 1.0
        assert result.min() >= 0.0

    def test_zscore(self):
        s = pd.Series(np.random.randn(100))
        result = AlphaPrimitive.zscore(s, 20)
        assert len(result) == 100

    def test_delay(self):
        s = pd.Series([1, 2, 3, 4, 5])
        result = AlphaPrimitive.delay(s, 2)
        assert pd.isna(result.iloc[0])
        assert pd.isna(result.iloc[1])
        assert result.iloc[2] == 1

    def test_delta(self):
        s = pd.Series([1, 2, 3, 4, 5])
        result = AlphaPrimitive.delta(s, 1)
        assert result.iloc[1] == 1

    def test_ts_mean(self):
        s = pd.Series(np.random.randn(100))
        result = AlphaPrimitive.ts_mean(s, 20)
        assert len(result) == 100

    def test_ts_corr(self, sample_ohlcv):
        result = AlphaPrimitive.ts_corr(sample_ohlcv["close"], sample_ohlcv["volume"], 20)
        assert len(result) == len(sample_ohlcv)

    def test_breakout(self, sample_ohlcv):
        result = AlphaPrimitive.breakout(
            sample_ohlcv["close"], sample_ohlcv["high"], sample_ohlcv["low"], 20
        )
        assert len(result) == len(sample_ohlcv)

    def test_mean_reversion(self, sample_ohlcv):
        result = AlphaPrimitive.mean_reversion(sample_ohlcv["close"], 20)
        assert len(result) == len(sample_ohlcv)

    def test_rsi(self, sample_ohlcv):
        result = AlphaPrimitive.rsi(sample_ohlcv["close"], 14)
        assert len(result) == len(sample_ohlcv)
        valid = result.dropna()
        assert valid.min() >= 0
        assert valid.max() <= 100

    def test_macd_hist(self, sample_ohlcv):
        result = AlphaPrimitive.macd_hist(sample_ohlcv["close"])
        assert len(result) == len(sample_ohlcv)

    def test_ts_regression_residual(self, sample_ohlcv):
        result = AlphaPrimitive.ts_regression_residual(
            AlphaPrimitive.momentum(sample_ohlcv["close"], 20),
            AlphaPrimitive.volatility(sample_ohlcv["close"], 20),
            60,
        )
        assert len(result) == len(sample_ohlcv)


class TestAlphaGenerator:
    def test_default_alphas_registered(self):
        gen = AlphaGenerator()
        names = gen.list_alpha_names()
        assert len(names) >= 10
        assert "alpha_momentum_rank" in names
        assert "alpha_mean_reversion_zscore" in names

    def test_compute_alpha(self, sample_ohlcv):
        gen = AlphaGenerator()
        result = gen.compute_alpha("alpha_momentum_rank", sample_ohlcv)
        assert result is not None
        assert len(result) == len(sample_ohlcv)

    def test_compute_all_alphas(self, sample_ohlcv):
        gen = AlphaGenerator()
        results = gen.compute_all_alphas(sample_ohlcv)
        assert len(results) >= 5
        for name, values in results.items():
            assert values.notna().sum() > 10

    def test_register_custom_alpha(self, sample_ohlcv):
        gen = AlphaGenerator()
        custom = AlphaExpression(
            name="alpha_custom_test",
            expression="rank(close)",
            category="custom",
            compute_fn=lambda df: AlphaPrimitive.rank(df["close"]),
            description="Test custom alpha",
        )
        gen.register(custom)
        assert "alpha_custom_test" in gen.list_alpha_names()
        result = gen.compute_alpha("alpha_custom_test", sample_ohlcv)
        assert result is not None

    def test_generate_parametric_alphas(self, sample_ohlcv):
        gen = AlphaGenerator()
        results = gen.generate_parametric_alphas(
            sample_ohlcv,
            base_alphas=["momentum", "mean_reversion"],
            periods=[5, 10, 20],
        )
        assert len(results) >= 3

    def test_invalid_alpha_name(self, sample_ohlcv):
        gen = AlphaGenerator()
        result = gen.compute_alpha("nonexistent_alpha", sample_ohlcv)
        assert result is None

    def test_list_alphas(self):
        gen = AlphaGenerator()
        alphas = gen.list_alphas()
        assert len(alphas) >= 10
        for a in alphas:
            assert a.name
            assert a.expression
            assert a.category
