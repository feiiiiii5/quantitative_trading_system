import numpy as np
import pandas as pd
import pytest

from core.prediction import HORIZON_MAP, PricePredictor


def _make_df(n=100, seed=42, trend=0.0):
    np.random.seed(seed)
    base = 50.0
    closes = [base]
    for _ in range(n - 1):
        base += trend + np.random.randn() * 0.3
        base = max(base, 1.0)
        closes.append(base)
    dates = pd.date_range("2024-01-01", periods=n, freq="D")
    highs = [c * (1 + abs(np.random.randn()) * 0.01) for c in closes]
    lows = [c * (1 - abs(np.random.randn()) * 0.01) for c in closes]
    vols = [10000 + i * 50 for i in range(n)]
    return pd.DataFrame({
        "date": dates,
        "open": closes,
        "high": highs,
        "low": lows,
        "close": closes,
        "volume": vols,
    })


def _mock_indicators(
    ma_cross_up=True,
    rsi_val=50.0,
    macd_hist_positive=True,
    kdj_k_over_d=True,
    supertrend_bullish=True,
    bb_position=0.5,
    atr=1.0,
):
    ma5_last = 52.0 if ma_cross_up else 48.0
    ma20_last = 50.0
    ma10_last = 53.0 if ma_cross_up else 47.0
    ma60_last = 50.0
    return {
        "ma": {
            5: [49.0, 49.5, 50.0, 51.0, ma5_last],
            10: [49.0, 49.5, 50.0, 51.0, ma10_last],
            20: [49.0, 49.5, 50.0, 50.0, ma20_last],
            60: [48.0, 48.5, 49.0, 49.5, ma60_last],
        },
        "rsi": {6: [rsi_val], 12: [rsi_val], 24: [rsi_val]},
        "macd": {
            "dif": [0.1, 0.2],
            "dea": [0.05, 0.1],
            "hist": [0.05, 0.1] if macd_hist_positive else [0.1, 0.05],
        },
        "kdj": {
            "k": [40.0, 55.0] if kdj_k_over_d else [55.0, 40.0],
            "d": [45.0, 50.0],
            "j": [50.0],
        },
        "supertrend": {
            "direction": [1 if supertrend_bullish else -1],
        },
        "boll": {
            "width": [0.5] * 20,
        },
        "bb_position": bb_position,
        "atr": atr,
        "cci": 0,
        "williams_r": -50,
    }


class TestSigmoid:
    def test_zero(self):
        assert PricePredictor._sigmoid(0) == pytest.approx(0.5, abs=1e-6)

    def test_positive(self):
        result = PricePredictor._sigmoid(5)
        assert 0.9 < result < 1.0

    def test_negative(self):
        result = PricePredictor._sigmoid(-5)
        assert 0.0 < result < 0.1

    def test_clamp_high(self):
        assert PricePredictor._sigmoid(100) == PricePredictor._sigmoid(10)

    def test_clamp_low(self):
        assert PricePredictor._sigmoid(-100) == PricePredictor._sigmoid(-10)


class TestEmptyPrediction:
    def test_returns_all_horizons(self):
        result = PricePredictor._empty_prediction()
        for horizon in HORIZON_MAP:
            assert horizon in result

    def test_fifty_fifty(self):
        result = PricePredictor._empty_prediction()
        for horizon in HORIZON_MAP:
            assert result[horizon]["up_prob"] == 50.0
            assert result[horizon]["down_prob"] == 50.0
            assert result[horizon]["expected_return"] == 0.0
            assert result[horizon]["confidence"] == 0.0
            assert result[horizon]["signals"] == []


class TestHurstExponent:
    def test_insufficient_data_returns_half(self):
        c = np.array([1.0, 2.0, 3.0])
        assert PricePredictor._hurst_exponent(c) == 0.5

    def test_random_walk_returns_value_in_range(self):
        np.random.seed(42)
        c = 100 + np.cumsum(np.random.randn(500) * 5.0)
        c = np.maximum(c, 1.0)
        h = PricePredictor._hurst_exponent(c)
        assert 0.0 <= h <= 1.0

    def test_trending_series_higher_than_random(self):
        np.random.seed(42)
        c_random = 100 + np.cumsum(np.random.randn(500) * 5.0)
        c_random = np.maximum(c_random, 1.0)
        h_random = PricePredictor._hurst_exponent(c_random)

        np.random.seed(42)
        n = 500
        returns = np.zeros(n)
        for i in range(1, n):
            returns[i] = 0.95 * returns[i - 1] + np.random.randn() * 0.02
        c_trend = 100 * np.exp(np.cumsum(returns))
        h_trend = PricePredictor._hurst_exponent(c_trend)
        assert h_trend > h_random

    def test_nan_in_prices_returns_half(self):
        c = np.array([100.0, np.nan, 102.0, 103.0, 104.0] * 20)
        h = PricePredictor._hurst_exponent(c)
        assert 0.0 <= h <= 1.0

    def test_all_zero_after_filter_returns_half(self):
        c = np.zeros(100)
        h = PricePredictor._hurst_exponent(c)
        assert h == 0.5


class TestDetectSignals:
    def test_empty_indicators(self):
        c = np.array([50.0] * 10)
        signals = PricePredictor._detect_signals(c, {})
        assert signals == []

    def test_max_six_signals(self):
        c = np.array([50.0] * 10)
        ind = _mock_indicators(
            ma_cross_up=True,
            rsi_val=25.0,
            macd_hist_positive=True,
            kdj_k_over_d=True,
            supertrend_bullish=True,
        )
        # Force MA cross by making prev_diff <= 0 and curr_diff > 0
        ind["ma"][5] = [48.0, 49.0, 50.0, 51.0, 52.0]
        ind["ma"][20] = [49.0, 49.5, 50.0, 50.5, 51.0]
        # Force MACD golden cross
        ind["macd"]["hist"] = [-0.1, 0.05]
        # Force KDJ golden cross
        ind["kdj"]["k"] = [40.0, 55.0]
        ind["kdj"]["d"] = [50.0, 50.0]
        # Force supertrend flip
        ind["supertrend"]["direction"] = [-1, 1]
        signals = PricePredictor._detect_signals(c, ind)
        assert len(signals) <= 6


class TestVolumePriceScore:
    def test_short_data_returns_zero(self):
        c = np.array([1.0, 2.0])
        v = np.array([100.0, 200.0])
        assert PricePredictor._volume_price_score(c, v) == 0


class TestPredict:
    def test_insufficient_data_returns_empty(self):
        df = _make_df(30)
        result = PricePredictor.predict(df, "TEST")
        empty = PricePredictor._empty_prediction()
        for horizon in HORIZON_MAP:
            assert result[horizon]["up_prob"] == empty[horizon]["up_prob"]

    def test_none_df_returns_empty(self):
        result = PricePredictor.predict(None, "TEST")
        empty = PricePredictor._empty_prediction()
        for horizon in HORIZON_MAP:
            assert result[horizon]["up_prob"] == empty[horizon]["up_prob"]

    def test_sufficient_data_returns_all_horizons(self):
        df = _make_df(120)
        result = PricePredictor.predict(df, "TEST")
        for horizon in HORIZON_MAP:
            assert horizon in result
            assert "up_prob" in result[horizon]
            assert "down_prob" in result[horizon]
            assert "expected_return" in result[horizon]
            assert "range" in result[horizon]
            assert "confidence" in result[horizon]
            assert "signals" in result[horizon]
            assert result[horizon]["up_prob"] + result[horizon]["down_prob"] == pytest.approx(
                100.0, abs=0.2
            )


class TestTrendMomentumScore:
    def test_empty_indicators_returns_zero(self):
        c = np.array([50.0] * 10)
        assert PricePredictor._trend_momentum_score(c, {}) == 0


class TestOverboughtOversoldScore:
    def test_empty_indicators_returns_zero(self):
        assert PricePredictor._overbought_oversold_score({}) == 0


class TestVolatilityScore:
    def test_empty_indicators_returns_zero(self):
        c = np.array([50.0] * 10)
        assert PricePredictor._volatility_score(c, {}) == 0
