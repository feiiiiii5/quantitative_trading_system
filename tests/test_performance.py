"""
性能基准测试
验证系统关键组件的性能指标
"""
import time

import numpy as np
import pandas as pd
import pytest

from core.indicators import TechnicalIndicators
from core.memory_guard import get_memory_usage
from core.strategies import (
    BollingerBreakoutStrategy,
    DualMAStrategy,
    KDJStrategy,
    MACDStrategy,
)


def generate_test_data(n_bars: int = 1000) -> pd.DataFrame:
    """生成测试用K线数据"""
    np.random.seed(42)
    dates = pd.date_range("2020-01-01", periods=n_bars, freq="D")
    base_price = 100.0
    returns = np.random.randn(n_bars) * 0.02
    prices = base_price * np.exp(np.cumsum(returns))

    high_factor = 1 + np.abs(np.random.randn(n_bars)) * 0.01
    low_factor = 1 - np.abs(np.random.randn(n_bars)) * 0.01

    return pd.DataFrame({
        "date": dates,
        "open": prices * (1 + np.random.randn(n_bars) * 0.005),
        "high": prices * high_factor,
        "low": prices * low_factor,
        "close": prices,
        "volume": np.random.randint(1000000, 10000000, n_bars),
    })


class TestStrategyPerformance:
    """策略性能测试"""

    @pytest.fixture
    def test_data(self):
        return generate_test_data(1000)

    def test_dual_ma_strategy_performance(self, test_data):
        """双均线策略性能测试"""
        strategy = DualMAStrategy(short_period=5, long_period=20)

        start = time.perf_counter()
        for _ in range(100):
            strategy.generate_signal(test_data)
        elapsed = time.perf_counter() - start

        avg_time_ms = elapsed * 10
        assert avg_time_ms < 50, f"双均线策略平均耗时 {avg_time_ms:.2f}ms 超过阈值 50ms"

    def test_macd_strategy_performance(self, test_data):
        """MACD策略性能测试"""
        strategy = MACDStrategy()

        start = time.perf_counter()
        for _ in range(100):
            strategy.generate_signal(test_data)
        elapsed = time.perf_counter() - start

        avg_time_ms = elapsed * 10
        assert avg_time_ms < 50, f"MACD策略平均耗时 {avg_time_ms:.2f}ms 超过阈值 50ms"

    def test_kdj_strategy_performance(self, test_data):
        """KDJ策略性能测试"""
        strategy = KDJStrategy()

        start = time.perf_counter()
        for _ in range(100):
            strategy.generate_signal(test_data)
        elapsed = time.perf_counter() - start

        avg_time_ms = elapsed * 10
        assert avg_time_ms < 50, f"KDJ策略平均耗时 {avg_time_ms:.2f}ms 超过阈值 50ms"

    def test_bollinger_strategy_performance(self, test_data):
        """布林带策略性能测试"""
        strategy = BollingerBreakoutStrategy()

        start = time.perf_counter()
        for _ in range(100):
            strategy.generate_signal(test_data)
        elapsed = time.perf_counter() - start

        avg_time_ms = elapsed * 10
        assert avg_time_ms < 50, f"布林带策略平均耗时 {avg_time_ms:.2f}ms 超过阈值 50ms"

    def test_precomputed_indicators_speedup(self, test_data):
        """预计算指标加速效果测试"""
        strategy = MACDStrategy()

        df_with_indicators = strategy.populate_indicators(test_data.copy())

        start = time.perf_counter()
        for _ in range(100):
            strategy.generate_signal(df_with_indicators, use_precomputed=True)
        elapsed_precomputed = time.perf_counter() - start

        start = time.perf_counter()
        for _ in range(100):
            strategy.generate_signal(test_data, use_precomputed=False)
        elapsed_full = time.perf_counter() - start

        speedup = elapsed_full / elapsed_precomputed if elapsed_precomputed > 0 else 0
        assert speedup > 0.3, f"预计算加速比 {speedup:.2f}x 应大于 0.3"


class TestIndicatorPerformance:
    """指标计算性能测试"""

    @pytest.fixture
    def test_data(self):
        return generate_test_data(1000)

    def test_compute_all_indicators_performance(self, test_data):
        """全指标计算性能测试"""
        start = time.perf_counter()
        for _ in range(10):
            TechnicalIndicators.compute_all(test_data)
        elapsed = time.perf_counter() - start

        avg_time_ms = elapsed * 100
        assert avg_time_ms < 200, f"全指标计算平均耗时 {avg_time_ms:.2f}ms 超过阈值 200ms"

    def test_indicator_caching_effectiveness(self, test_data):
        """指标缓存效果测试"""
        TechnicalIndicators.compute_all(test_data, symbol="TEST", period="daily")

        start = time.perf_counter()
        for _ in range(100):
            TechnicalIndicators.compute_all(test_data, symbol="TEST", period="daily")
        elapsed_cached = time.perf_counter() - start

        start = time.perf_counter()
        for _ in range(100):
            TechnicalIndicators.compute_all(test_data, symbol="NEW", period="daily")
        elapsed_uncached = time.perf_counter() - start

        assert elapsed_cached < elapsed_uncached, "缓存访问应快于重新计算"


class TestMemoryPerformance:
    """内存性能测试"""

    def test_memory_usage_reasonable(self):
        """内存使用合理性测试"""
        mem_info = get_memory_usage()

        assert mem_info["system_used_pct"] < 90, f"系统内存使用率 {mem_info['system_used_pct']:.1f}% 过高"

    def test_large_data_memory_control(self):
        """大数据量内存控制测试"""
        initial_mem = get_memory_usage().get("rss_mb", 0)

        large_df = generate_test_data(10000)
        TechnicalIndicators.compute_all(large_df, symbol="LARGE_TEST")

        peak_mem = get_memory_usage().get("rss_mb", 0)
        mem_increase = peak_mem - initial_mem

        assert mem_increase < 500, f"内存增长 {mem_increase:.0f}MB 超过阈值 500MB"
