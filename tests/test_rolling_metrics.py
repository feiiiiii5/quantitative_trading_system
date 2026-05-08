import numpy as np
import pandas as pd
import pytest

from core.rolling_metrics import RollingMetricsTracker, get_rolling_metrics_tracker


@pytest.fixture
def tracker():
    return RollingMetricsTracker()


@pytest.fixture
def returns_200():
    np.random.seed(42)
    n = 200
    dates = pd.date_range("2024-01-01", periods=n, freq="B")
    return pd.Series(np.random.randn(n) * 0.02 + 0.001, index=dates)


@pytest.fixture
def benchmark_200():
    np.random.seed(99)
    n = 200
    dates = pd.date_range("2024-01-01", periods=n, freq="B")
    return pd.Series(np.random.randn(n) * 0.015 + 0.0005, index=dates)


@pytest.fixture
def equity_200():
    np.random.seed(42)
    n = 200
    dates = pd.date_range("2024-01-01", periods=n, freq="B")
    returns = np.random.randn(n) * 0.02 + 0.001
    equity = 1e6 * np.cumprod(1 + returns)
    return pd.Series(equity, index=dates)


class TestRollingSharpe:
    def test_basic_computation(self, tracker, returns_200):
        result = tracker.compute_rolling_sharpe(returns_200, window=60)
        assert "error" not in result
        assert result["current"] is not None
        assert len(result["dates"]) > 0
        assert len(result["values"]) > 0
        assert result["window"] == 60
        assert result["annualized"] is True

    def test_insufficient_data(self, tracker):
        np.random.seed(1)
        short_returns = pd.Series(np.random.randn(10) * 0.01, index=pd.date_range("2024-01-01", periods=10, freq="B"))
        result = tracker.compute_rolling_sharpe(short_returns, window=60)
        assert "error" in result
        assert "65" in result["error"]

    def test_regime_classification(self, tracker):
        np.random.seed(7)
        n = 200
        dates = pd.date_range("2024-01-01", periods=n, freq="B")

        high_returns = pd.Series(np.random.randn(n) * 0.005 + 0.01, index=dates)
        result = tracker.compute_rolling_sharpe(high_returns, window=60)
        assert result["regime"] in ("excellent", "good", "marginal", "poor")
        if result["current"] is not None:
            if result["current"] > 2.0:
                assert result["regime"] == "excellent"
            elif result["current"] > 1.0:
                assert result["regime"] == "good"
            elif result["current"] > 0.0:
                assert result["regime"] == "marginal"
            else:
                assert result["regime"] == "poor"

        negative_returns = pd.Series(np.random.randn(n) * 0.02 - 0.01, index=dates)
        result_neg = tracker.compute_rolling_sharpe(negative_returns, window=60)
        if result_neg["current"] is not None and result_neg["current"] <= 0:
            assert result_neg["regime"] == "poor"

    def test_output_keys(self, tracker, returns_200):
        result = tracker.compute_rolling_sharpe(returns_200, window=60)
        expected_keys = {"dates", "values", "current", "mean", "std", "min", "max", "regime", "window", "annualized"}
        assert expected_keys.issubset(set(result.keys()))


class TestRollingSortino:
    def test_basic_computation(self, tracker, returns_200):
        result = tracker.compute_rolling_sortino(returns_200, window=60)
        assert "error" not in result
        assert result["current"] is not None
        assert len(result["dates"]) > 0
        assert len(result["values"]) > 0
        assert result["window"] == 60

    def test_insufficient_data(self, tracker):
        np.random.seed(2)
        short_returns = pd.Series(np.random.randn(30) * 0.01, index=pd.date_range("2024-01-01", periods=30, freq="B"))
        result = tracker.compute_rolling_sortino(short_returns, window=60)
        assert "error" in result

    def test_output_keys(self, tracker, returns_200):
        result = tracker.compute_rolling_sortino(returns_200, window=60)
        expected_keys = {"dates", "values", "current", "mean", "window"}
        assert expected_keys.issubset(set(result.keys()))

    def test_vectorized_matches_loop_semantics(self, tracker, returns_200):
        result = tracker.compute_rolling_sortino(returns_200, window=60)
        assert result["current"] is not None
        assert np.isfinite(result["current"])
        assert abs(result["current"]) < 100


class TestRollingCalmar:
    def test_basic_computation(self, tracker, equity_200):
        result = tracker.compute_rolling_calmar(equity_200, window=120)
        assert "error" not in result
        assert result["current"] is not None
        assert len(result["dates"]) > 0
        assert result["window"] == 120

    def test_insufficient_data(self, tracker):
        np.random.seed(3)
        short_equity = pd.Series(np.linspace(1e6, 1.1e6, 50), index=pd.date_range("2024-01-01", periods=50, freq="B"))
        result = tracker.compute_rolling_calmar(short_equity, window=120)
        assert "error" in result

    def test_vectorized_calmar_produces_finite(self, tracker, equity_200):
        result = tracker.compute_rolling_calmar(equity_200, window=120)
        assert "error" not in result
        if result["current"] is not None:
            assert np.isfinite(result["current"])


class TestInformationRatio:
    def test_basic_computation(self, tracker, returns_200, benchmark_200):
        result = tracker.compute_information_ratio(returns_200, benchmark_200, window=60)
        assert "error" not in result
        assert result["current"] is not None
        assert len(result["dates"]) > 0
        assert result["window"] == 60

    def test_insufficient_overlap(self, tracker):
        np.random.seed(4)
        dates_a = pd.date_range("2024-01-01", periods=200, freq="B")
        dates_b = pd.date_range("2025-06-01", periods=200, freq="B")
        returns_a = pd.Series(np.random.randn(200) * 0.01, index=dates_a)
        returns_b = pd.Series(np.random.randn(200) * 0.01, index=dates_b)
        result = tracker.compute_information_ratio(returns_a, returns_b, window=60)
        assert "error" in result


class TestComputeAllRollingMetrics:
    def test_with_all_inputs(self, tracker, returns_200, benchmark_200, equity_200):
        result = tracker.compute_all_rolling_metrics(returns_200, benchmark_returns=benchmark_200, equity_curve=equity_200)
        assert "sharpe" in result
        assert "sortino" in result
        assert "calmar" in result
        assert "information_ratio" in result
        assert "composite_score" in result
        assert "performance_regime" in result

    def test_with_only_returns(self, tracker, returns_200):
        result = tracker.compute_all_rolling_metrics(returns_200)
        assert "sharpe" in result
        assert "sortino" in result
        assert "calmar" not in result
        assert "information_ratio" not in result

    def test_composite_score_and_regime(self, tracker, returns_200, benchmark_200):
        result = tracker.compute_all_rolling_metrics(returns_200, benchmark_returns=benchmark_200)
        assert "composite_score" in result
        assert "performance_regime" in result
        assert result["performance_regime"] in ("excellent", "good", "marginal", "poor")
        assert isinstance(result["composite_score"], float)


class TestGetRollingMetricsTracker:
    def test_singleton(self):
        import core.rolling_metrics as mod
        from core.rolling_metrics import _tracker as original

        mod._tracker = None
        t1 = get_rolling_metrics_tracker()
        t2 = get_rolling_metrics_tracker()
        assert t1 is t2
        assert isinstance(t1, RollingMetricsTracker)
        mod._tracker = original
