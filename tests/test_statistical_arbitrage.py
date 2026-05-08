from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from core.statistical_arbitrage import (
    CointegrationTestResult,
    KalmanHedgeRatio,
    PairMiningEngine,
    SpreadMonitor,
    SpreadState,
    _compute_half_life,
    compute_hurst,
    engle_granger_test,
    estimate_pair_capacity,
    johansen_test,
)


def _make_cointegrated_pair(
    n: int = 500,
    hedge_ratio: float = 1.5,
    seed: int = 42,
) -> tuple[pd.Series, pd.Series]:
    rng = np.random.default_rng(seed)
    x_walk = np.cumsum(rng.standard_normal(n)) + 100.0
    noise = rng.standard_normal(n) * 0.5
    y_walk = hedge_ratio * x_walk + noise
    dates = pd.date_range("2023-01-01", periods=n, freq="D")
    x_series = pd.Series(x_walk, index=dates, name="X")
    y_series = pd.Series(y_walk, index=dates, name="Y")
    return y_series, x_series


class TestCointegrationTestResult:
    def test_cointegration_result_to_dict(self) -> None:
        result = CointegrationTestResult(
            symbol_y="AAPL",
            symbol_x="MSFT",
            p_value=0.03,
            hedge_ratio=1.2,
            half_life=5.0,
            hurst_exponent=0.4,
            test_method="engle_granger",
            is_cointegrated=True,
        )
        d = result.to_dict()
        expected_keys = {
            "symbol_y", "symbol_x", "p_value", "hedge_ratio",
            "half_life", "hurst_exponent", "test_method", "is_cointegrated",
        }
        assert set(d.keys()) == expected_keys
        assert d["symbol_y"] == "AAPL"
        assert d["symbol_x"] == "MSFT"
        assert d["p_value"] == 0.03
        assert d["hedge_ratio"] == 1.2
        assert d["half_life"] == 5.0
        assert d["hurst_exponent"] == 0.4
        assert d["test_method"] == "engle_granger"
        assert d["is_cointegrated"] is True


class TestSpreadState:
    def test_spread_state_to_dict(self) -> None:
        state = SpreadState(
            z_score=2.5,
            mean=0.0,
            std=1.0,
            half_life=3.0,
            is_entry_signal=True,
            is_exit_signal=False,
        )
        d = state.to_dict()
        expected_keys = {
            "z_score", "mean", "std", "half_life",
            "is_entry_signal", "is_exit_signal",
        }
        assert set(d.keys()) == expected_keys
        assert d["z_score"] == 2.5
        assert d["mean"] == 0.0
        assert d["std"] == 1.0
        assert d["half_life"] == 3.0
        assert d["is_entry_signal"] is True
        assert d["is_exit_signal"] is False


class TestComputeHalfLife:
    def test_compute_half_life_mean_reverting(self) -> None:
        rng = np.random.default_rng(42)
        spread = np.zeros(200)
        for i in range(1, 200):
            spread[i] = spread[i - 1] * 0.9 + rng.standard_normal() * 0.5
        hl = _compute_half_life(spread)
        assert 0.0 < hl < float("inf")

    def test_compute_half_life_single_element(self) -> None:
        hl = _compute_half_life(np.array([1.0]))
        assert hl == float("inf")


class TestComputeHurst:
    def test_compute_hurst_random_walk(self) -> None:
        rng = np.random.default_rng(42)
        series = pd.Series(np.cumsum(rng.standard_normal(5000)))
        hurst = compute_hurst(series, max_lag=200)
        assert 0.35 < hurst < 0.7

    def test_compute_hurst_trending(self) -> None:
        rng = np.random.default_rng(7)
        returns = rng.standard_normal(2000) * 0.01 + 0.005
        series = pd.Series(np.cumprod(1 + returns))
        hurst = compute_hurst(series, max_lag=200)
        assert hurst > 0.5

    def test_compute_hurst_short_series(self) -> None:
        series = pd.Series([1.0, 2.0, 3.0])
        hurst = compute_hurst(series)
        assert hurst == 0.5


class TestKalmanHedgeRatio:
    def test_kalman_hedge_ratio_initial_state(self) -> None:
        kf = KalmanHedgeRatio()
        assert kf.beta == 0.0
        assert kf.covariance == 1.0

    def test_kalman_hedge_ratio_update(self) -> None:
        kf = KalmanHedgeRatio()
        true_beta = 2.0
        rng = np.random.default_rng(42)
        for _ in range(200):
            x = rng.standard_normal()
            y = true_beta * x + rng.standard_normal() * 0.01
            kf.update(y, x)
        assert abs(kf.beta - true_beta) < 0.5

    def test_kalman_hedge_ratio_get_spread(self) -> None:
        kf = KalmanHedgeRatio(initial_beta=1.5)
        y, x = 10.0, 4.0
        spread = kf.get_spread(y, x)
        assert spread == pytest.approx(y - 1.5 * x)


class TestSpreadMonitor:
    def test_spread_monitor_update_returns_spread_state(self) -> None:
        monitor = SpreadMonitor()
        state = monitor.update(1.0)
        assert isinstance(state, SpreadState)

    def test_spread_monitor_entry_signal(self) -> None:
        monitor = SpreadMonitor(window=20, entry_threshold=2.0)
        for _ in range(20):
            monitor.update(0.0)
        state = monitor.update(10.0)
        assert state.is_entry_signal is True

    def test_spread_monitor_exit_signal(self) -> None:
        monitor = SpreadMonitor(window=20, exit_threshold=0.5)
        rng = np.random.default_rng(42)
        for _ in range(20):
            monitor.update(rng.normal(0.0, 1.0))
        state = monitor.update(0.01)
        assert state.is_exit_signal is True

    def test_spread_monitor_reset(self) -> None:
        monitor = SpreadMonitor()
        for _ in range(10):
            monitor.update(1.0)
        monitor.reset()
        assert monitor.history == []

    def test_spread_monitor_history_property(self) -> None:
        monitor = SpreadMonitor()
        monitor.update(1.0)
        monitor.update(2.0)
        h = monitor.history
        assert h == [1.0, 2.0]
        h.append(99.0)
        assert monitor.history == [1.0, 2.0]


class TestEstimatePairCapacity:
    def test_estimate_pair_capacity_normal(self) -> None:
        pair = CointegrationTestResult(
            symbol_y="A", symbol_x="B", p_value=0.03,
            hedge_ratio=1.0, half_life=5.0, hurst_exponent=0.4,
            test_method="engle_granger", is_cointegrated=True,
        )
        result = estimate_pair_capacity(pair, adv_y=1_000_000, adv_x=800_000)
        assert result == pytest.approx(800_000 * 0.05)

    def test_estimate_pair_capacity_zero_adv(self) -> None:
        pair = CointegrationTestResult(
            symbol_y="A", symbol_x="B", p_value=0.03,
            hedge_ratio=1.0, half_life=5.0, hurst_exponent=0.4,
            test_method="engle_granger", is_cointegrated=True,
        )
        assert estimate_pair_capacity(pair, adv_y=0.0, adv_x=800_000) == 0.0
        assert estimate_pair_capacity(pair, adv_y=1_000_000, adv_x=0.0) == 0.0


class TestEngleGrangerTest:
    def test_engle_granger_test_short_data(self) -> None:
        dates = pd.date_range("2023-01-01", periods=20, freq="D")
        y = pd.Series(np.random.randn(20), index=dates, name="Y")
        x = pd.Series(np.random.randn(20), index=dates, name="X")
        result = engle_granger_test(y, x)
        assert result.is_cointegrated is False
        assert result.p_value == 1.0

    def test_engle_granger_test_cointegrated_series(self) -> None:
        y, x = _make_cointegrated_pair(n=500, hedge_ratio=1.5)
        result = engle_granger_test(y, x)
        assert result.is_cointegrated is True
        assert result.p_value < 0.05
        assert result.test_method == "engle_granger"


class TestPairMiningEngine:
    def test_pair_mining_engine_insufficient_symbols(self) -> None:
        engine = PairMiningEngine()
        dates = pd.date_range("2023-01-01", periods=100, freq="D")
        prices_df = pd.DataFrame(
            {"A": np.cumsum(np.random.randn(100)) + 100},
            index=dates,
        )
        result = engine.find_cointegrated_pairs(prices_df, universe=["A"])
        assert result == []


class TestJohansenTest:
    def test_johansen_test_insufficient_columns(self) -> None:
        dates = pd.date_range("2023-01-01", periods=100, freq="D")
        df = pd.DataFrame({"A": np.random.randn(100)}, index=dates)
        result = johansen_test(df)
        assert result == []
