"""
Tests for correlation_analysis module
"""
import numpy as np
import pandas as pd

from core.correlation_analysis import CorrelationAnalyzer


def _make_prices(n_assets: int = 5, n_days: int = 252, seed: int = 42) -> pd.DataFrame:
    np.random.seed(seed)
    returns = np.random.normal(0.0005, 0.02, (n_days, n_assets))
    prices = 100 * np.cumprod(1 + returns, axis=0)
    symbols = [f"SYM{i:02d}" for i in range(1, n_assets + 1)]
    return pd.DataFrame(prices, columns=symbols)


def _make_correlated_prices(seed: int = 42) -> pd.DataFrame:
    np.random.seed(seed)
    n_days = 252
    base = np.random.normal(0.0005, 0.02, n_days)
    noise1 = np.random.normal(0, 0.005, n_days)
    noise2 = np.random.normal(0, 0.02, n_days)
    p1 = 100 * np.cumprod(1 + base + noise1)
    p2 = 100 * np.cumprod(1 + base + noise1)
    p3 = 100 * np.cumprod(1 + noise2)
    return pd.DataFrame({"HIGH1": p1, "HIGH2": p2, "LOW1": p3})


class TestCorrelationAnalyzer:

    def test_basic_analysis(self):
        prices = _make_prices()
        analyzer = CorrelationAnalyzer()
        result = analyzer.analyze(prices)
        assert result.is_valid
        assert result.n_assets == 5
        assert len(result.correlation_matrix) == 5

    def test_correlation_matrix_symmetric(self):
        prices = _make_prices()
        analyzer = CorrelationAnalyzer()
        result = analyzer.analyze(prices)
        assert result.is_valid
        for col in result.correlation_matrix:
            for col2 in result.correlation_matrix:
                assert abs(result.correlation_matrix[col][col2] - result.correlation_matrix[col2][col]) < 1e-10

    def test_diagonal_is_one(self):
        prices = _make_prices()
        analyzer = CorrelationAnalyzer()
        result = analyzer.analyze(prices)
        assert result.is_valid
        for col in result.correlation_matrix:
            assert abs(result.correlation_matrix[col][col] - 1.0) < 1e-10

    def test_highly_correlated_detection(self):
        prices = _make_correlated_prices()
        analyzer = CorrelationAnalyzer(high_correlation_threshold=0.7)
        result = analyzer.analyze(prices)
        assert result.is_valid
        high_names = {(a, b) for a, b, _ in result.highly_correlated_pairs}
        assert ("HIGH1", "HIGH2") in high_names or ("HIGH2", "HIGH1") in high_names

    def test_spearman_method(self):
        prices = _make_prices()
        analyzer = CorrelationAnalyzer()
        result = analyzer.analyze(prices, method="spearman")
        assert result.is_valid

    def test_average_correlation_range(self):
        prices = _make_prices()
        analyzer = CorrelationAnalyzer()
        result = analyzer.analyze(prices)
        assert result.is_valid
        assert -1.0 <= result.average_correlation <= 1.0

    def test_diversification_score_range(self):
        prices = _make_prices()
        analyzer = CorrelationAnalyzer()
        result = analyzer.analyze(prices)
        assert result.is_valid
        assert 0.0 <= result.diversification_score <= 2.0

    def test_insufficient_data(self):
        np.random.seed(42)
        returns = np.random.normal(0, 0.02, (10, 3))
        prices = 100 * np.cumprod(1 + returns, axis=0)
        prices_df = pd.DataFrame(prices, columns=["A", "B", "C"])
        analyzer = CorrelationAnalyzer()
        result = analyzer.analyze(prices_df)
        assert not result.is_valid

    def test_rolling_correlation(self):
        prices = _make_prices(n_days=120)
        analyzer = CorrelationAnalyzer()
        result = analyzer.rolling_correlation(prices, window=30)
        assert result.is_valid
        assert result.window_size == 30

    def test_rolling_insufficient_data(self):
        prices = _make_prices(n_days=20)
        analyzer = CorrelationAnalyzer()
        result = analyzer.rolling_correlation(prices, window=60)
        assert not result.is_valid

    def test_find_optimal_pairs(self):
        prices = _make_prices()
        analyzer = CorrelationAnalyzer()
        pairs = analyzer.find_optimal_pairs(prices, target_corr=0.0)
        assert isinstance(pairs, list)
        assert len(pairs) <= 10
        if len(pairs) > 0:
            assert len(pairs[0]) == 3

    def test_custom_thresholds(self):
        prices = _make_prices()
        analyzer = CorrelationAnalyzer(
            high_correlation_threshold=0.5,
            low_correlation_threshold=0.1,
        )
        result = analyzer.analyze(prices)
        assert result.is_valid
