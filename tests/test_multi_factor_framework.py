import numpy as np
import pandas as pd
import pytest

from core.multi_factor_framework import (
    FactorCategory,
    FactorDefinition,
    FactorRotationDetector,
    FactorTestResult,
    _compute_factor_turnover,
    _compute_monotonicity,
    barra_neutralize,
    factor_ic_analysis,
    optimize_with_factor_exposure,
    quintile_return_test,
)


class TestFactorCategory:
    def test_all_categories_exist(self):
        expected = {"value", "growth", "quality", "momentum", "low_volatility", "liquidity", "technical"}
        actual = {c.value for c in FactorCategory}
        assert expected == actual


class TestFactorDefinition:
    def test_creation(self):
        fd = FactorDefinition(
            name="pe_ratio",
            category=FactorCategory.VALUE,
            description="Price-to-Earnings ratio",
            compute_fn=lambda df: df.get("pe", pd.Series(dtype=float)),
        )
        assert fd.name == "pe_ratio"
        assert fd.category == FactorCategory.VALUE


class TestQuintileReturnTest:
    def test_basic_quintile(self):
        np.random.seed(42)
        n = 100
        fv = pd.Series(np.random.randn(n))
        fr = pd.Series(np.random.randn(n) * 0.02)
        result = quintile_return_test(fv, fr, n_quintiles=5)
        assert len(result) == 5
        assert all(isinstance(v, float) for v in result.values())

    def test_monotonic_factor(self):
        n = 100
        fv = pd.Series(np.arange(n, dtype=float))
        fr = pd.Series(np.arange(n, dtype=float) * 0.001)
        result = quintile_return_test(fv, fr, n_quintiles=5)
        assert result[4] > result[0]

    def test_insufficient_data(self):
        fv = pd.Series([1.0, 2.0])
        fr = pd.Series([0.01, 0.02])
        result = quintile_return_test(fv, fr, n_quintiles=5)
        assert all(v == 0.0 for v in result.values())

    def test_custom_quintiles(self):
        np.random.seed(42)
        n = 60
        fv = pd.Series(np.random.randn(n))
        fr = pd.Series(np.random.randn(n) * 0.02)
        result = quintile_return_test(fv, fr, n_quintiles=3)
        assert len(result) == 3


class TestFactorICAnalysis:
    def test_basic_ic_analysis(self):
        np.random.seed(42)
        n = 100
        fv = pd.Series(np.random.randn(n))
        fr = pd.Series(np.random.randn(n) * 0.02)
        result = factor_ic_analysis(fv, fr)
        assert isinstance(result, FactorTestResult)
        assert isinstance(result.mean_ic, float)
        assert isinstance(result.icir, float)
        assert isinstance(result.ic_decay, list)
        assert isinstance(result.turnover, float)
        assert isinstance(result.long_short_return, float)
        assert isinstance(result.monotonicity, float)

    def test_insufficient_data_returns_zeros(self):
        fv = pd.Series([1.0, 2.0, 3.0])
        fr = pd.Series([0.01, 0.02, 0.03])
        result = factor_ic_analysis(fv, fr)
        assert result.mean_ic == 0.0
        assert result.icir == 0.0

    def test_perfect_positive_factor(self):
        n = 200
        fv = pd.Series(np.arange(n, dtype=float))
        fr = pd.Series(np.arange(n, dtype=float) * 0.001 + np.random.randn(n) * 0.0001)
        result = factor_ic_analysis(fv, fr)
        assert result.mean_ic > 0.5

    def test_named_series(self):
        np.random.seed(42)
        n = 50
        fv = pd.Series(np.random.randn(n), name="test_factor")
        fr = pd.Series(np.random.randn(n) * 0.02)
        result = factor_ic_analysis(fv, fr)
        assert result.factor_name == "test_factor"


class TestComputeMonotonicity:
    def test_perfectly_monotone(self):
        quintile_returns = {0: -0.02, 1: -0.01, 2: 0.0, 3: 0.01, 4: 0.02}
        result = _compute_monotonicity(quintile_returns)
        assert result == 1.0

    def test_perfectly_reverse(self):
        quintile_returns = {0: 0.02, 1: 0.01, 2: 0.0, 3: -0.01, 4: -0.02}
        result = _compute_monotonicity(quintile_returns)
        assert result == -1.0

    def test_flat_returns(self):
        quintile_returns = {0: 0.01, 1: 0.01, 2: 0.01, 3: 0.01, 4: 0.01}
        result = _compute_monotonicity(quintile_returns)
        assert result == 0.0

    def test_single_quintile(self):
        result = _compute_monotonicity({0: 0.01})
        assert result == 0.0


class TestComputeFactorTurnover:
    def test_basic(self):
        fv = pd.Series(np.random.randn(100))
        result = _compute_factor_turnover(fv)
        assert isinstance(result, float)
        assert 0.0 <= result <= 1.0

    def test_short_series(self):
        fv = pd.Series([1.0, 2.0])
        result = _compute_factor_turnover(fv)
        assert result == 1.0


class TestBarraNeutralize:
    def test_basic_neutralization(self):
        np.random.seed(42)
        n = 50
        fv = pd.Series(np.random.randn(n))
        ind = pd.Series(["tech"] * 25 + ["fin"] * 25)
        mc = pd.Series(np.random.uniform(1e9, 1e11, n))
        result = barra_neutralize(fv, ind, mc)
        assert len(result) == n
        assert isinstance(result, pd.Series)

    def test_too_few_observations(self):
        fv = pd.Series([1.0, 2.0, 3.0])
        ind = pd.Series(["a", "b", "c"])
        mc = pd.Series([100.0, 200.0, 300.0])
        result = barra_neutralize(fv, ind, mc)
        pd.testing.assert_series_equal(result, fv)

    def test_with_style_factors(self):
        np.random.seed(42)
        n = 50
        fv = pd.Series(np.random.randn(n))
        ind = pd.Series(["tech"] * 25 + ["fin"] * 25)
        mc = pd.Series(np.random.uniform(1e9, 1e11, n))
        style = pd.DataFrame({
            "momentum": np.random.randn(n),
            "size": np.random.randn(n),
        })
        result = barra_neutralize(fv, ind, mc, style_factors=style)
        assert len(result) == n


class TestOptimizeWithFactorExposure:
    def test_basic_optimization(self):
        n = 10
        expected_returns = np.array([0.05 + i * 0.01 for i in range(n)])
        cov = np.eye(n) * 0.04
        factor_exp = np.ones((1, n)) / n
        factor_constr = np.array([0.5])
        weights = optimize_with_factor_exposure(
            expected_returns, cov, factor_exp, factor_constr,
            max_weight=0.15,
        )
        assert len(weights) == n
        assert abs(weights.sum() - 1.0) < 0.01
        assert all(w >= -0.001 for w in weights)

    def test_empty_returns(self):
        result = optimize_with_factor_exposure(
            np.array([]), np.array([[]]),
            np.array([[]]), np.array([]),
        )
        assert len(result) == 0

    def test_single_asset(self):
        result = optimize_with_factor_exposure(
            np.array([0.05]), np.array([[0.04]]),
            np.array([[1.0]]), np.array([0.5]),
        )
        assert len(result) == 1
        assert result[0] <= 0.06

    def test_mismatched_cov_shape_falls_back(self):
        n = 5
        expected_returns = np.array([0.05] * n)
        cov = np.eye(3) * 0.04
        factor_exp = np.ones((1, n)) / n
        factor_constr = np.array([0.5])
        weights = optimize_with_factor_exposure(
            expected_returns, cov, factor_exp, factor_constr,
        )
        assert len(weights) == n


class TestFactorRotationDetector:
    def test_detect_rotation(self):
        np.random.seed(42)
        n = 100
        factor_names = ["momentum"]
        fv_ts = pd.DataFrame({"momentum": np.random.randn(n)})
        fr_ts = pd.DataFrame({"returns": np.random.randn(n) * 0.02})
        detector = FactorRotationDetector(recent_window=20, long_term_window=80)
        signals = detector.detect_rotation_multi(factor_names, fv_ts, fr_ts)
        assert len(signals) >= 1
        assert signals[0].factor_name == "momentum"
        assert isinstance(signals[0].recommendation, str)

    def test_no_rotation_stable_ic(self):
        np.random.seed(42)
        n = 200
        fv = pd.Series(np.random.randn(n))
        fr = fv * 0.01 + np.random.randn(n) * 0.001
        fv_ts = pd.DataFrame({"stable_factor": fv.values})
        fr_ts = pd.DataFrame({"returns": fr.values})
        detector = FactorRotationDetector(recent_window=60, long_term_window=180, ic_threshold=0.5)
        signals = detector.detect_rotation_multi(["stable_factor"], fv_ts, fr_ts)
        assert len(signals) >= 1
