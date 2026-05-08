"""Tests for ML Factor Scoring Module."""
import numpy as np
import pandas as pd

from core.ml_factor_scorer import (
    MLFactorScorer,
    MLScoringResult,
    create_ensemble_signal,
)


class TestMLScoringResult:
    def test_default_values(self):
        result = MLScoringResult(factor_name="test")
        assert result.factor_name == "test"
        assert result.ic_score == 0.0
        assert result.final_score == 0.0
        assert result.is_ml_enhanced is False


class TestMLFactorScorer:
    def test_init_defaults(self):
        scorer = MLFactorScorer()
        assert scorer._use_ml is True or scorer._use_ml is False

    def test_init_ml_disabled(self):
        scorer = MLFactorScorer(use_ml=False)
        assert scorer._use_ml is False

    def test_score_factors_empty(self):
        scorer = MLFactorScorer(use_ml=False)
        result = scorer.score_factors({}, pd.Series([1, 2, 3]))
        assert len(result) == 0

    def test_score_factors_insufficient_data(self):
        scorer = MLFactorScorer(use_ml=False)
        factor = pd.Series([1.0, 2.0, 3.0])
        returns = pd.Series([0.01, -0.01, 0.02])
        result = scorer.score_factors({"test": factor}, returns)
        assert "test" in result

    def test_score_factors_basic(self):
        scorer = MLFactorScorer(use_ml=False)
        np.random.seed(42)
        n = 100
        factor = pd.Series(np.random.randn(n))
        returns = pd.Series(factor.values * 0.5 + np.random.randn(n) * 0.1)
        result = scorer.score_factors({"test_factor": factor}, returns)
        assert "test_factor" in result
        assert isinstance(result["test_factor"], MLScoringResult)

    def test_score_factors_multiple(self):
        scorer = MLFactorScorer(use_ml=False)
        np.random.seed(42)
        n = 100
        factors = {
            "factor1": pd.Series(np.random.randn(n)),
            "factor2": pd.Series(np.random.randn(n)),
            "factor3": pd.Series(np.random.randn(n)),
        }
        returns = pd.Series(np.random.randn(n) * 0.1)
        results = scorer.score_factors(factors, returns)
        assert len(results) == 3
        assert all(name in results for name in factors)

    def test_rank_factors(self):
        scorer = MLFactorScorer(use_ml=False)
        np.random.seed(42)
        n = 100
        factor = pd.Series(np.random.randn(n))
        returns = pd.Series(factor.values * 0.5 + np.random.randn(n) * 0.1)
        results = scorer.score_factors({"f1": factor, "f2": factor * 2}, returns)
        ranked = scorer.rank_factors(results, top_n=2)
        assert len(ranked) == 2

    def test_rank_factors_empty(self):
        scorer = MLFactorScorer(use_ml=False)
        ranked = scorer.rank_factors({}, top_n=5)
        assert len(ranked) == 0

    def test_get_summary_report(self):
        scorer = MLFactorScorer(use_ml=False)
        np.random.seed(42)
        n = 100
        factor = pd.Series(np.random.randn(n))
        returns = pd.Series(np.random.randn(n) * 0.1)
        results = scorer.score_factors({"test": factor}, returns)
        report = scorer.get_summary_report(results)
        assert "total_factors" in report
        assert report["total_factors"] == 1
        assert "top_factors" in report


class TestCreateEnsembleSignal:
    def test_empty_inputs(self):
        result = create_ensemble_signal({}, {})
        assert len(result) == 0

    def test_single_factor(self):
        factor_values = {"f1": pd.Series([1.0, 2.0, 3.0])}
        weights = {"f1": 1.0}
        result = create_ensemble_signal(weights, factor_values)
        assert len(result) == 3

    def test_multiple_factors(self):
        factor_values = {
            "f1": pd.Series([1.0, 2.0, 3.0]),
            "f2": pd.Series([0.5, 1.0, 1.5]),
        }
        weights = {"f1": 1.0, "f2": 1.0}
        result = create_ensemble_signal(weights, factor_values)
        assert len(result) == 3

    def test_weighted_ensemble(self):
        factor_values = {
            "f1": pd.Series([1.0, 2.0, 3.0]),
            "f2": pd.Series([1.0, 2.0, 3.0]),
        }
        weights = {"f1": 2.0, "f2": 1.0}
        result = create_ensemble_signal(weights, factor_values)
        expected = pd.Series([3.0 / 3.0, 6.0 / 3.0, 9.0 / 3.0])
        np.testing.assert_array_almost_equal(result.values, expected.values)

    def test_with_nan_values(self):
        factor_values = {
            "f1": pd.Series([1.0, np.nan, 3.0]),
            "f2": pd.Series([0.5, 1.0, np.nan]),
        }
        weights = {"f1": 1.0, "f2": 1.0}
        result = create_ensemble_signal(weights, factor_values)
        assert len(result) >= 1
