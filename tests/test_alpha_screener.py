import numpy as np
import pandas as pd
import pytest

from core.alpha_screener import (
    AlphaScreeningConfig,
    AlphaScreener,
    calc_ic,
    calc_rolling_ic,
    calc_turnover,
    calc_decay,
)
from core.alpha_engine import AlphaResult


class TestCalcIC:
    def test_positive_correlation(self):
        np.random.seed(42)
        factor = pd.Series(np.random.randn(100))
        returns = factor * 0.5 + np.random.randn(100) * 0.5
        ic = calc_ic(factor, returns)
        assert ic > 0.1

    def test_negative_correlation(self):
        np.random.seed(42)
        factor = pd.Series(np.random.randn(100))
        returns = -factor * 0.5 + np.random.randn(100) * 0.5
        ic = calc_ic(factor, returns)
        assert ic < -0.1

    def test_no_correlation(self):
        np.random.seed(42)
        factor = pd.Series(np.random.randn(100))
        returns = pd.Series(np.random.randn(100))
        ic = calc_ic(factor, returns)
        assert abs(ic) < 0.5

    def test_short_series(self):
        factor = pd.Series([1, 2])
        returns = pd.Series([3, 4])
        ic = calc_ic(factor, returns)
        assert isinstance(ic, float)

    def test_with_nan(self):
        factor = pd.Series([1, np.nan, 3, 4, 5])
        returns = pd.Series([2, 3, np.nan, 5, 6])
        ic = calc_ic(factor, returns)
        assert isinstance(ic, float)


class TestCalcRollingIC:
    def test_basic(self):
        np.random.seed(42)
        n = 200
        factor = pd.Series(np.random.randn(n))
        returns = factor * 0.3 + np.random.randn(n) * 0.7
        ic, ic_ir = calc_rolling_ic(factor, returns, window=20)
        assert isinstance(ic, float)
        assert isinstance(ic_ir, float)

    def test_short_series(self):
        factor = pd.Series([1, 2, 3])
        returns = pd.Series([4, 5, 6])
        ic, ic_ir = calc_rolling_ic(factor, returns, window=20)
        assert isinstance(ic, float)


class TestCalcTurnover:
    def test_stable_factor(self):
        factor = pd.Series(np.arange(100, dtype=float))
        turnover = calc_turnover(factor)
        assert 0 <= turnover <= 1

    def test_volatile_factor(self):
        np.random.seed(42)
        factor = pd.Series(np.random.randn(100))
        turnover = calc_turnover(factor)
        assert turnover > 0


class TestCalcDecay:
    def test_basic(self):
        np.random.seed(42)
        n = 100
        factor = pd.Series(np.random.randn(n))
        returns = factor.shift(-1) * 0.3 + np.random.randn(n) * 0.7
        decay = calc_decay(factor, returns)
        assert isinstance(decay, float)
        assert decay >= 0

    def test_short_series(self):
        factor = pd.Series([1, 2, 3])
        returns = pd.Series([4, 5, 6])
        decay = calc_decay(factor, returns)
        assert isinstance(decay, float)


class TestAlphaScreener:
    def test_screen_alpha(self, sample_ohlcv):
        screener = AlphaScreener()
        factor = sample_ohlcv["close"].pct_change(20)
        result = screener.screen_alpha(
            name="test_alpha",
            factor_values=factor,
            close=sample_ohlcv["close"],
            category="test",
        )
        assert result.name == "test_alpha"
        assert isinstance(result.ic, float)
        assert isinstance(result.ic_ir, float)
        assert isinstance(result.turnover, float)
        assert isinstance(result.decay, float)

    def test_screen_all(self, sample_ohlcv):
        screener = AlphaScreener()
        alpha_values = {
            "alpha_1": sample_ohlcv["close"].pct_change(20),
            "alpha_2": sample_ohlcv["close"].pct_change(60),
        }
        results = screener.screen_all(alpha_values, sample_ohlcv["close"])
        assert len(results) == 2

    def test_filter_passed(self, sample_ohlcv):
        screener = AlphaScreener(AlphaScreeningConfig(ic_threshold=0.001, ic_ir_threshold=0.01))
        alpha_values = {
            "alpha_1": sample_ohlcv["close"].pct_change(20),
        }
        results = screener.screen_all(alpha_values, sample_ohlcv["close"])
        passed = screener.filter_passed(results)
        assert isinstance(passed, dict)

    def test_rank_by_ic_ir(self, sample_ohlcv):
        screener = AlphaScreener()
        alpha_values = {
            "alpha_1": sample_ohlcv["close"].pct_change(10),
            "alpha_2": sample_ohlcv["close"].pct_change(60),
        }
        results = screener.screen_all(alpha_values, sample_ohlcv["close"])
        ranked = screener.rank_by_ic_ir(results)
        assert len(ranked) == 2

    def test_screening_report(self, sample_ohlcv):
        screener = AlphaScreener()
        alpha_values = {
            "alpha_1": sample_ohlcv["close"].pct_change(20),
            "alpha_2": sample_ohlcv["close"].pct_change(60),
        }
        results = screener.screen_all(alpha_values, sample_ohlcv["close"])
        report = screener.get_screening_report(results)
        assert "total_alphas" in report
        assert "passed_alphas" in report
        assert "top_alphas" in report
