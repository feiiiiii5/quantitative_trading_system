import numpy as np
import pandas as pd
import pytest

from core.regime_detector import RegimeDetector, MarketRegime, RegimeResult


class TestRegimeDetector:
    def test_trending_up(self, trending_up_ohlcv):
        detector = RegimeDetector()
        result = detector.detect(trending_up_ohlcv)
        assert isinstance(result, RegimeResult)
        assert result.current_regime in [MarketRegime.TRENDING_UP, MarketRegime.TRENDING_DOWN, MarketRegime.SIDEWAYS]

    def test_trending_down(self, trending_down_ohlcv):
        detector = RegimeDetector()
        result = detector.detect(trending_down_ohlcv)
        assert isinstance(result, RegimeResult)
        assert result.current_regime in [MarketRegime.TRENDING_UP, MarketRegime.TRENDING_DOWN, MarketRegime.SIDEWAYS]

    def test_sideways(self, sideways_ohlcv):
        detector = RegimeDetector()
        result = detector.detect(sideways_ohlcv)
        assert isinstance(result, RegimeResult)
        assert isinstance(result.current_regime, MarketRegime)

    def test_normal_market(self, sample_ohlcv):
        detector = RegimeDetector()
        result = detector.detect(sample_ohlcv)
        assert isinstance(result, RegimeResult)
        assert result.confidence >= 0
        assert result.trend_strength is not None
        assert result.volatility_level >= 0

    def test_short_data(self):
        detector = RegimeDetector()
        short_df = pd.DataFrame({
            "close": [10, 11, 12],
            "high": [11, 12, 13],
            "low": [9, 10, 11],
        })
        result = detector.detect(short_df)
        assert result.current_regime == MarketRegime.UNKNOWN

    def test_none_data(self):
        detector = RegimeDetector()
        result = detector.detect(None)
        assert result.current_regime == MarketRegime.UNKNOWN

    def test_regime_history(self, sample_ohlcv):
        detector = RegimeDetector()
        detector.detect(sample_ohlcv)
        assert len(detector._regime_history) == 1

    def test_transition_probabilities(self, sample_ohlcv):
        detector = RegimeDetector()
        for _ in range(5):
            detector.detect(sample_ohlcv)
        result = detector.detect(sample_ohlcv)
        assert isinstance(result.transition_probabilities, dict)

    def test_regime_summary(self, sample_ohlcv):
        detector = RegimeDetector()
        result = detector.detect(sample_ohlcv)
        summary = detector.get_regime_summary(result)
        assert "current_regime" in summary
        assert "confidence" in summary
        assert "recommended_strategy_type" in summary

    def test_recommend_strategy(self):
        detector = RegimeDetector()
        assert detector._recommend_strategy(RegimeResult(
            current_regime=MarketRegime.TRENDING_UP,
            confidence=0.8, trend_strength=0.5,
            volatility_level=0.15, mean_reversion_score=0.1,
            regime_history=[], transition_probabilities={},
        )) == "momentum"

        assert detector._recommend_strategy(RegimeResult(
            current_regime=MarketRegime.MEAN_REVERTING,
            confidence=0.7, trend_strength=0.1,
            volatility_level=0.15, mean_reversion_score=0.5,
            regime_history=[], transition_probabilities={},
        )) == "mean_reversion"

        assert detector._recommend_strategy(RegimeResult(
            current_regime=MarketRegime.HIGH_VOLATILITY,
            confidence=0.6, trend_strength=0.2,
            volatility_level=0.40, mean_reversion_score=0.1,
            regime_history=[], transition_probabilities={},
        )) == "volatility_breakout"
