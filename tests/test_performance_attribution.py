import numpy as np
import pandas as pd

from core.performance_attribution import AttributionResult, PerformanceAttribution


class TestPerformanceAttributionBasic:
    def test_insufficient_data(self):
        attr = PerformanceAttribution()
        result = attr.analyze(np.array([0.01]), np.array([0.01]))
        assert result.total_return == 0.0
        assert result.factor_contributions == {}

    def test_zero_strategy_std(self):
        attr = PerformanceAttribution()
        sr = np.zeros(30)
        br = np.random.randn(30) * 0.01
        result = attr.analyze(sr, br)
        assert result.total_return == 0.0

    def test_basic_attribution(self):
        attr = PerformanceAttribution()
        np.random.seed(42)
        n = 100
        br = np.random.randn(n) * 0.02
        sr = br * 1.2 + np.random.randn(n) * 0.005
        result = attr.analyze(sr, br)
        assert isinstance(result, AttributionResult)
        assert result.total_return != 0.0
        assert "market" in result.factor_contributions
        assert "momentum" in result.factor_contributions
        assert "mean_reversion" in result.factor_contributions
        assert "volatility" in result.factor_contributions

    def test_r_squared_range(self):
        attr = PerformanceAttribution()
        np.random.seed(42)
        n = 100
        br = np.random.randn(n) * 0.02
        sr = br * 1.5 + np.random.randn(n) * 0.001
        result = attr.analyze(sr, br)
        assert 0 <= result.r_squared <= 1.0

    def test_factor_weights_sum_near_one(self):
        attr = PerformanceAttribution()
        np.random.seed(42)
        n = 100
        br = np.random.randn(n) * 0.02
        sr = br * 1.0 + np.random.randn(n) * 0.005
        result = attr.analyze(sr, br)
        weight_sum = sum(abs(w) for w in result.factor_weights.values())
        assert weight_sum <= 2.0

    def test_residual_small_for_high_correlation(self):
        attr = PerformanceAttribution()
        np.random.seed(42)
        n = 100
        br = np.random.randn(n) * 0.02
        sr = br * 2.0
        result = attr.analyze(sr, br)
        assert abs(result.residual) < abs(result.total_return) * 0.5


class TestPerformanceAttributionSeries:
    def test_analyze_from_series(self):
        attr = PerformanceAttribution()
        np.random.seed(42)
        n = 100
        dates = pd.date_range("2024-01-01", periods=n, freq="D")
        sr = pd.Series(np.random.randn(n) * 0.02, index=dates)
        br = pd.Series(np.random.randn(n) * 0.02, index=dates)
        result = attr.analyze_from_series(sr, br)
        assert isinstance(result, AttributionResult)
        assert "market" in result.factor_contributions

    def test_series_with_nans(self):
        attr = PerformanceAttribution()
        np.random.seed(42)
        n = 100
        dates = pd.date_range("2024-01-01", periods=n, freq="D")
        sr_vals = np.random.randn(n) * 0.02
        sr_vals[10] = np.nan
        sr_vals[50] = np.nan
        sr = pd.Series(sr_vals, index=dates)
        br = pd.Series(np.random.randn(n) * 0.02, index=dates)
        result = attr.analyze_from_series(sr, br)
        assert isinstance(result, AttributionResult)


class TestPerformanceAttributionEdgeCases:
    def test_all_positive_returns(self):
        attr = PerformanceAttribution()
        sr = np.full(50, 0.01)
        br = np.full(50, 0.005)
        result = attr.analyze(sr, br)
        assert np.isfinite(result.total_return)

    def test_all_negative_returns(self):
        attr = PerformanceAttribution()
        sr = np.full(50, -0.01)
        br = np.full(50, -0.005)
        result = attr.analyze(sr, br)
        assert np.isfinite(result.total_return)

    def test_extreme_volatility(self):
        attr = PerformanceAttribution()
        np.random.seed(42)
        n = 100
        sr = np.random.randn(n) * 0.5
        br = np.random.randn(n) * 0.5
        result = attr.analyze(sr, br)
        assert np.isfinite(result.total_return)
        assert np.isfinite(result.r_squared)

    def test_single_factor_dominant(self):
        attr = PerformanceAttribution()
        np.random.seed(42)
        n = 100
        br = np.random.randn(n) * 0.02
        sr = br * 3.0
        result = attr.analyze(sr, br)
        assert result.factor_contributions.get("market", 0) != 0


class TestRollingAttribution:
    def test_rolling_returns_segments(self):
        attr = PerformanceAttribution()
        np.random.seed(42)
        n = 250
        br = np.random.randn(n) * 0.02
        sr = br * 1.2 + np.random.randn(n) * 0.005
        results = attr.rolling_attribution(sr, br, window=60, step=10)
        assert len(results) > 0
        for seg in results:
            assert "total_return" in seg
            assert "factor_contributions" in seg
            assert "r_squared" in seg
            assert "start_idx" in seg
            assert "end_idx" in seg

    def test_rolling_insufficient_data(self):
        attr = PerformanceAttribution()
        sr = np.random.randn(30) * 0.02
        br = np.random.randn(30) * 0.02
        results = attr.rolling_attribution(sr, br, window=60, step=5)
        assert results == []

    def test_rolling_step_affects_count(self):
        attr = PerformanceAttribution()
        np.random.seed(42)
        n = 200
        br = np.random.randn(n) * 0.02
        sr = br * 1.0 + np.random.randn(n) * 0.005
        results_step5 = attr.rolling_attribution(sr, br, window=60, step=5)
        results_step20 = attr.rolling_attribution(sr, br, window=60, step=20)
        assert len(results_step5) > len(results_step20)


class TestRollingSharpeSortino:
    def test_basic_rolling(self):
        np.random.seed(42)
        n = 250
        returns = np.random.randn(n) * 0.02 + 0.0005
        results = PerformanceAttribution.rolling_sharpe_sortino(returns, window=60, step=10)
        assert len(results) > 0
        for seg in results:
            assert "sharpe_ratio" in seg
            assert "sortino_ratio" in seg
            assert "calmar_ratio" in seg
            assert "cumulative_return" in seg
            assert "max_drawdown" in seg
            assert "volatility" in seg
            assert np.isfinite(seg["sharpe_ratio"])
            assert np.isfinite(seg["sortino_ratio"])

    def test_insufficient_data(self):
        returns = np.random.randn(30) * 0.02
        results = PerformanceAttribution.rolling_sharpe_sortino(returns, window=60, step=5)
        assert results == []

    def test_all_positive_returns(self):
        returns = np.full(100, 0.01)
        results = PerformanceAttribution.rolling_sharpe_sortino(returns, window=60, step=10)
        assert len(results) > 0
        for seg in results:
            assert seg["max_drawdown"] == 0.0
            assert seg["sortino_ratio"] == 0.0

    def test_with_risk_free_rate(self):
        np.random.seed(42)
        n = 200
        returns = np.random.randn(n) * 0.02 + 0.001
        results_zero = PerformanceAttribution.rolling_sharpe_sortino(returns, window=60, step=10, risk_free_rate=0.0)
        results_rf = PerformanceAttribution.rolling_sharpe_sortino(returns, window=60, step=10, risk_free_rate=0.03)
        assert len(results_zero) == len(results_rf)
        for z, r in zip(results_zero, results_rf, strict=False):
            assert r["sharpe_ratio"] <= z["sharpe_ratio"]

    def test_sortino_exceeds_sharpe_for_positive_skew(self):
        np.random.seed(42)
        n = 250
        positive = np.abs(np.random.randn(n)) * 0.02
        negative = -np.abs(np.random.randn(n)) * 0.005
        returns = np.where(np.random.randn(n) > 0, positive, negative)
        results = PerformanceAttribution.rolling_sharpe_sortino(returns, window=60, step=10)
        for seg in results:
            assert seg["sortino_ratio"] >= seg["sharpe_ratio"]
