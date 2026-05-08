import numpy as np
import pandas as pd
import pytest

from core.correlation import CorrelationAnalyzer


@pytest.fixture
def price_data():
    np.random.seed(42)
    n = 100
    dates = pd.date_range("2024-01-01", periods=n)
    base = np.cumsum(np.random.randn(n) * 0.02) + 100
    return {
        "A": pd.Series(base, index=dates),
        "B": pd.Series(base + np.random.randn(n) * 0.5, index=dates),
        "C": pd.Series(np.cumsum(np.random.randn(n) * 0.02) + 100, index=dates),
    }


class TestCorrelationAnalyzer:
    def test_correlation_matrix(self, price_data):
        analyzer = CorrelationAnalyzer()
        result = analyzer.compute_correlation_matrix(price_data)
        assert "matrix" in result
        assert "heatmap" in result
        assert "summary" in result
        assert result["summary"]["avg_correlation"] is not None

    def test_correlation_matrix_too_few(self):
        analyzer = CorrelationAnalyzer()
        result = analyzer.compute_correlation_matrix({"A": pd.Series([1, 2, 3])})
        assert "error" in result

    def test_rolling_correlation(self, price_data):
        analyzer = CorrelationAnalyzer()
        result = analyzer.compute_rolling_correlation(
            price_data["A"], price_data["B"], window=20
        )
        assert "dates" in result
        assert "values" in result

    def test_beta_matrix(self, price_data):
        analyzer = CorrelationAnalyzer()
        bench = price_data["A"]
        stock_data = {k: v for k, v in price_data.items() if k != "A"}
        result = analyzer.compute_beta_matrix(stock_data, bench)
        assert "betas" in result
        assert "B" in result["betas"]

    def test_diversification_score(self, price_data):
        analyzer = CorrelationAnalyzer()
        result = analyzer.compute_diversification_score(price_data)
        assert "effective_number_of_bets" in result
        assert "composite_diversification_score" in result
        assert "rating" in result
        assert result["n_assets"] == 3
        assert result["effective_number_of_bets"] > 0
        assert 0 <= result["composite_diversification_score"] <= 100

    def test_diversification_score_too_few(self):
        analyzer = CorrelationAnalyzer()
        result = analyzer.compute_diversification_score({"A": pd.Series([1, 2, 3])})
        assert "error" in result

    def test_diversification_uncorrelated(self):
        np.random.seed(42)
        n = 200
        dates = pd.date_range("2024-01-01", periods=n)
        data = {
            f"S{i}": pd.Series(np.cumsum(np.random.randn(n) * 0.02) + 100, index=dates)
            for i in range(5)
        }
        analyzer = CorrelationAnalyzer()
        result = analyzer.compute_diversification_score(data)
        assert result["effective_number_of_bets"] > 2
        assert result["rating"] in ("excellent", "good", "moderate", "poor")
