import numpy as np
import pandas as pd

from core.indicators import TechnicalIndicators


def _make_df(n=100, seed=42):
    np.random.seed(seed)
    base = 10.0
    closes = [base]
    for _ in range(n - 1):
        base += np.random.randn() * 0.2
        base = max(base, 1.0)
        closes.append(base)
    dates = pd.date_range("2024-01-01", periods=n, freq="D")
    highs = [c * (1 + abs(np.random.randn()) * 0.01) for c in closes]
    lows = [c * (1 - abs(np.random.randn()) * 0.01) for c in closes]
    vols = [1000 + i * 10 for i in range(n)]
    return pd.DataFrame({
        "date": dates,
        "open": closes,
        "high": highs,
        "low": lows,
        "close": closes,
        "volume": vols,
    })


class TestComputeAll:
    def test_basic(self):
        df = _make_df(100)
        result = TechnicalIndicators.compute_all(df, "000001")
        assert isinstance(result, dict)
        assert "ma" in result
        assert "ema" in result
        assert "boll" in result
        assert "macd" in result
        assert "rsi" in result
        assert "kdj" in result
        assert "trend_score" in result

    def test_short_df(self):
        df = _make_df(10)
        result = TechnicalIndicators.compute_all(df, "000001")
        assert result == {}

    def test_none_df(self):
        result = TechnicalIndicators.compute_all(None, "000001")
        assert result == {}

    def test_caching(self):
        df = _make_df(100)
        r1 = TechnicalIndicators.compute_all(df, "TESTCACHE")
        r2 = TechnicalIndicators.compute_all(df, "TESTCACHE")
        assert r1 is r2


class TestMA:
    def test_basic(self):
        c = np.arange(100, dtype=float)
        result = TechnicalIndicators._ma(c)
        assert 5 in result
        assert 20 in result
        assert len(result[5]) == 100

    def test_short_data(self):
        c = np.arange(3, dtype=float)
        result = TechnicalIndicators._ma(c)
        assert 5 not in result


class TestEMA:
    def test_basic(self):
        c = np.arange(50, dtype=float)
        result = TechnicalIndicators._ema(c)
        assert 12 in result
        assert 26 in result


class TestBoll:
    def test_basic(self):
        c = np.arange(50, dtype=float) + 10
        result = TechnicalIndicators._boll(c)
        assert "upper" in result
        assert "mid" in result
        assert "lower" in result
        assert "width" in result

    def test_constant_prices(self):
        c = np.full(50, 10.0)
        result = TechnicalIndicators._boll(c)
        assert np.isfinite(result["width"][-1])


class TestMACD:
    def test_basic(self):
        c = np.arange(50, dtype=float) + 10
        result = TechnicalIndicators._macd(c)
        assert "dif" in result
        assert "dea" in result
        assert "hist" in result


class TestRSI:
    def test_basic(self):
        df = _make_df(100)
        c = df["close"].values.astype(float)
        result = TechnicalIndicators._rsi(c)
        assert isinstance(result, dict)
        for _period, vals in result.items():
            assert len(vals) == 100
            valid = np.array([v for v in vals if np.isfinite(v)])
            if len(valid) > 0:
                assert np.all(valid >= 0) and np.all(valid <= 100)

    def test_constant_prices(self):
        c = np.full(50, 10.0)
        result = TechnicalIndicators._rsi(c)
        for _period, vals in result.items():
            valid = np.array([v for v in vals if isinstance(v, (int, float)) and np.isfinite(v)])
            if len(valid) > 0:
                assert np.all(valid >= 0) and np.all(valid <= 100)


class TestKDJ:
    def test_basic(self):
        df = _make_df(100)
        h = df["high"].values.astype(float)
        low = df["low"].values.astype(float)
        c = df["close"].values.astype(float)
        result = TechnicalIndicators._kdj(h, low, c)
        assert "k" in result
        assert "d" in result
        assert "j" in result


class TestATR:
    def test_basic(self):
        df = _make_df(100)
        h = df["high"].values.astype(float)
        low = df["low"].values.astype(float)
        c = df["close"].values.astype(float)
        result = TechnicalIndicators._atr(h, low, c)
        assert len(result) > 0


class TestSupertrend:
    def test_basic(self):
        df = _make_df(100)
        h = df["high"].values.astype(float)
        low = df["low"].values.astype(float)
        c = df["close"].values.astype(float)
        result = TechnicalIndicators._supertrend(h, low, c)
        assert "value" in result
        assert "direction" in result


class TestVolumeIndicators:
    def test_obv(self):
        df = _make_df(100)
        c = df["close"].values.astype(float)
        v = df["volume"].values.astype(float)
        result = TechnicalIndicators._obv(c, v)
        assert len(result) == 100

    def test_volume_ratio(self):
        df = _make_df(100)
        v = df["volume"].values.astype(float)
        result = TechnicalIndicators._volume_ratio(v)
        assert len(result) > 0

    def test_cmf(self):
        df = _make_df(100)
        h = df["high"].values.astype(float)
        low = df["low"].values.astype(float)
        c = df["close"].values.astype(float)
        v = df["volume"].values.astype(float)
        result = TechnicalIndicators._cmf(h, low, c, v)
        assert len(result) > 0
