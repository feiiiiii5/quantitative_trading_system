import numpy as np
import pytest

from core.chip_distribution import (
    ChipDistribution,
    ChipDistributionAnalyzer,
    _volume_profile_distribution,
    get_chip_analyzer,
)


def _make_ohlcv(n: int = 60, base_price: float = 10.0, trend: float = 0.0):
    rng = np.random.RandomState(42)
    close = base_price + np.cumsum(np.full(n, trend) + rng.randn(n) * 0.3)
    close = np.maximum(close, 1.0)
    high = close + rng.rand(n) * 0.5
    low = close - rng.rand(n) * 0.5
    low = np.maximum(low, 0.5)
    volume = rng.rand(n) * 1e6 + 1e5
    return close, high, low, volume


class TestVolumeProfileDistribution:
    def test_insufficient_data(self):
        prices, dist = _volume_profile_distribution(
            np.array([1.0]), np.array([1.5]), np.array([0.5]), np.array([100.0])
        )
        assert len(prices) == 0
        assert len(dist) == 0

    def test_flat_price_returns_empty(self):
        close = np.full(20, 10.0)
        high = np.full(20, 10.0)
        low = np.full(20, 10.0)
        volume = np.full(20, 1e6)
        prices, dist = _volume_profile_distribution(close, high, low, volume)
        assert len(prices) == 0

    def test_normal_distribution_sums_to_one(self):
        close, high, low, volume = _make_ohlcv(60)
        prices, dist = _volume_profile_distribution(close, high, low, volume)
        assert len(prices) > 0
        assert abs(dist.sum() - 1.0) < 1e-6

    def test_decay_reduces_older_weights(self):
        close, high, low, volume = _make_ohlcv(60)
        _, dist_no_decay = _volume_profile_distribution(close, high, low, volume, decay=1.0)
        _, dist_with_decay = _volume_profile_distribution(close, high, low, volume, decay=0.97)
        assert len(dist_no_decay) == len(dist_with_decay)


class TestChipDistributionAnalyzer:
    def test_insufficient_data_returns_empty(self):
        analyzer = ChipDistributionAnalyzer()
        close = np.array([10.0, 10.5, 11.0, 10.8, 10.9])
        high = close + 0.5
        low = close - 0.5
        volume = np.array([1e6] * 5)
        result = analyzer.analyze(close, high, low, volume)
        assert result.prices == []
        assert result.avg_cost == 0

    def test_normal_analysis(self):
        analyzer = ChipDistributionAnalyzer()
        close, high, low, volume = _make_ohlcv(120)
        result = analyzer.analyze(close, high, low, volume)
        assert len(result.prices) > 0
        assert len(result.distribution) == len(result.prices)
        assert result.avg_cost > 0
        assert 0 <= result.profit_ratio <= 1
        assert 0 <= result.concentration <= 1
        assert result.support_price > 0
        assert result.resistance_price > 0
        assert result.peak_price > 0
        assert len(result.chip_bands) > 0

    def test_custom_current_price(self):
        analyzer = ChipDistributionAnalyzer()
        close, high, low, volume = _make_ohlcv(60, base_price=10.0)
        result_low = analyzer.analyze(close, high, low, volume, current_price=5.0)
        result_high = analyzer.analyze(close, high, low, volume, current_price=20.0)
        assert result_low.profit_ratio < result_high.profit_ratio

    def test_chip_fire_insufficient_data(self):
        analyzer = ChipDistributionAnalyzer()
        close = np.array([10.0] * 10)
        high = close + 0.5
        low = close - 0.5
        volume = np.array([1e6] * 10)
        result = analyzer.compute_chip_fire(close, high, low, volume)
        assert result["status"] == "insufficient_data"

    def test_chip_fire_normal(self):
        analyzer = ChipDistributionAnalyzer()
        close, high, low, volume = _make_ohlcv(120)
        result = analyzer.compute_chip_fire(close, high, low, volume)
        assert "status" in result
        assert "signal" in result
        assert "short_concentration" in result


class TestGetChipAnalyzer:
    def test_singleton(self):
        a1 = get_chip_analyzer()
        a2 = get_chip_analyzer()
        assert a1 is a2
