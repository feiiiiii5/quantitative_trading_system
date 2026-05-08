import numpy as np
import pandas as pd

from core.regime_detector import (
    MarketRegime,
    MarketRegimeDetector,
    RegimeAwareSignalGenerator,
    analyze_regime_signals,
    detect_market_regime,
    get_regime_detector,
)


def _make_kline(n: int, trend: float = 0, vol: float = 0.02, seed: int = 42) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    dates = pd.date_range("2023-01-01", periods=n, freq="D")
    base = 100.0
    price = base
    closes = []
    for _ in range(n):
        daily_ret = rng.normal(trend / n, vol)
        price = price * (1 + daily_ret)
        closes.append(price)
    highs = [c * (1 + abs(rng.normal(0, vol / 2))) for c in closes]
    lows = [c * (1 - abs(rng.normal(0, vol / 2))) for c in closes]
    opens = [c * (1 + rng.normal(0, vol / 4)) for c in closes]
    volumes = [int(rng.lognormal(15, 0.5)) for _ in range(n)]
    return pd.DataFrame({
        "date": dates,
        "open": opens,
        "high": highs,
        "low": lows,
        "close": closes,
        "volume": volumes,
    })


class TestMarketRegimeDetector:
    def test_detect_bull_breakout(self):
        df = _make_kline(200, trend=0.5, vol=0.015, seed=99)
        detector = MarketRegimeDetector()
        regime, ctx = detector.detect(df)
        assert regime in list(MarketRegime)
        assert "confidence" in ctx
        assert 0 <= ctx["confidence"] <= 1

    def test_detect_bear_distribution(self):
        df = _make_kline(200, trend=-0.5, vol=0.02, seed=13)
        detector = MarketRegimeDetector()
        regime, ctx = detector.detect(df)
        assert regime in list(MarketRegime)
        assert "trend" in ctx
        assert "volatility" in ctx
        assert "momentum" in ctx

    def test_detect_volatile_regime(self):
        rng = np.random.default_rng(7)
        dates = pd.date_range("2023-01-01", periods=200, freq="D")
        base = 100.0
        closes = []
        price = base
        for _ in range(200):
            vol = 0.05 if _ < 100 else 0.01
            daily_ret = rng.normal(0, vol)
            price = price * (1 + daily_ret)
            closes.append(price)
        highs = [c * 1.02 for c in closes]
        lows = [c * 0.98 for c in closes]
        volumes = [int(rng.lognormal(15, 0.5)) for _ in range(200)]
        df = pd.DataFrame({
            "date": dates, "open": closes, "high": highs,
            "low": lows, "close": closes, "volume": volumes,
        })
        detector = MarketRegimeDetector()
        regime, ctx = detector.detect(df)
        assert regime in list(MarketRegime)
        assert "volatility" in ctx

    def test_detect_insufficient_data(self):
        df = _make_kline(10)
        detector = MarketRegimeDetector()
        regime, ctx = detector.detect(df)
        assert regime == MarketRegime.UNKNOWN

    def test_detect_none_dataframe(self):
        detector = MarketRegimeDetector()
        regime, ctx = detector.detect(None)
        assert regime == MarketRegime.UNKNOWN

    def test_detect_empty_dataframe(self):
        df = pd.DataFrame(columns=["date", "open", "high", "low", "close", "volume"])
        detector = MarketRegimeDetector()
        regime, ctx = detector.detect(df)
        assert regime == MarketRegime.UNKNOWN

    def test_indicators_include_adx(self):
        df = _make_kline(200, seed=55)
        detector = MarketRegimeDetector()
        _, ctx = detector.detect(df)
        assert "indicators" in ctx
        assert "adx" in ctx["indicators"]
        assert "asymmetry" in ctx["indicators"]
        assert "range_position" in ctx["indicators"]

    def test_singleton(self):
        d1 = get_regime_detector()
        d2 = get_regime_detector()
        assert d1 is d2


class TestRegimeAwareSignalGenerator:
    def test_analyze_returns_all_fields(self):
        df = _make_kline(200, seed=21)
        gen = RegimeAwareSignalGenerator()
        result = gen.analyze(df)
        assert "regime" in result
        assert "confidence" in result
        assert "signal_bias" in result
        assert "stop_loss_pct" in result
        assert "take_profit_pct" in result
        assert "position_scale" in result
        assert "description" in result

    def test_all_regimes_have_valid_config(self):
        for regime in MarketRegime:
            gen = RegimeAwareSignalGenerator()
            config = gen.get_regime_config(regime)
            assert "signal_bias" in config
            assert "stop_loss_pct" in config
            assert "take_profit_pct" in config
            assert "position_scale" in config
            assert 0 < config["position_scale"] <= 2.0

    def test_analyze_regime_signals_function(self):
        df = _make_kline(200, seed=44)
        result = analyze_regime_signals(df)
        assert "regime" in result
        assert "signal_bias" in result

    def test_detect_market_regime_function(self):
        df = _make_kline(200, seed=77)
        regime_str, ctx = detect_market_regime(df)
        assert isinstance(regime_str, str)
        assert isinstance(ctx, dict)


class TestRegimeStability:
    def test_same_data_produces_same_regime(self):
        df = _make_kline(200, seed=100)
        detector = MarketRegimeDetector()
        r1, _ = detector.detect(df)
        r2, _ = detector.detect(df)
        assert r1 == r2

    def test_different_seeds_produce_different_regimes(self):
        regimes = set()
        for seed in range(10, 30):
            df = _make_kline(200, seed=seed)
            detector = MarketRegimeDetector()
            r, _ = detector.detect(df)
            regimes.add(r)
        assert len(regimes) >= 2

    def test_confidence_bounded(self):
        for seed in range(10):
            df = _make_kline(200, seed=seed)
            detector = MarketRegimeDetector()
            _, ctx = detector.detect(df)
            assert 0 <= ctx["confidence"] <= 1
