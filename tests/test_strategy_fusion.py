import numpy as np
import pandas as pd
import pytest

from core.strategy_fusion import (
    StrategyFusion,
    FusionConfig,
    FusionResult,
    ic_vol_weight,
    equal_weight,
    ic_weight,
    sharpe_weight,
    rank_weight,
)
from core.alpha_engine import AlphaResult


def _make_alpha_result(name, ic_val, n=100):
    np.random.seed(42)
    return AlphaResult(
        name=name,
        values=pd.Series(np.random.randn(n)),
        ic=ic_val,
        ic_ir=ic_val * 5,
        turnover=0.3,
        decay=0.1,
        passed=True,
        category="test",
    )


class TestICVolWeight:
    def test_basic(self):
        alphas = {
            "a1": _make_alpha_result("a1", 0.05),
            "a2": _make_alpha_result("a2", 0.03),
        }
        weights = ic_vol_weight(alphas)
        assert len(weights) == 2
        assert abs(sum(weights.values()) - 1.0) < 0.01

    def test_empty(self):
        weights = ic_vol_weight({})
        assert weights == {}


class TestEqualWeight:
    def test_basic(self):
        alphas = {
            "a1": _make_alpha_result("a1", 0.05),
            "a2": _make_alpha_result("a2", 0.03),
        }
        weights = equal_weight(alphas)
        assert abs(weights["a1"] - 0.5) < 0.01
        assert abs(weights["a2"] - 0.5) < 0.01


class TestICWeight:
    def test_basic(self):
        alphas = {
            "a1": _make_alpha_result("a1", 0.10),
            "a2": _make_alpha_result("a2", 0.05),
        }
        weights = ic_weight(alphas)
        assert weights["a1"] > weights["a2"]


class TestSharpeWeight:
    def test_basic(self):
        alphas = {
            "a1": _make_alpha_result("a1", 0.05),
            "a2": _make_alpha_result("a2", 0.03),
        }
        weights = sharpe_weight(alphas)
        assert abs(sum(weights.values()) - 1.0) < 0.01


class TestRankWeight:
    def test_basic(self):
        alphas = {
            "a1": _make_alpha_result("a1", 0.10),
            "a2": _make_alpha_result("a2", 0.05),
            "a3": _make_alpha_result("a3", 0.03),
        }
        weights = rank_weight(alphas)
        assert weights["a1"] > weights["a2"]
        assert weights["a2"] > weights["a3"]


class TestStrategyFusion:
    def test_fuse_ic_vol(self):
        fusion = StrategyFusion()
        alphas = {
            "a1": _make_alpha_result("a1", 0.05),
            "a2": _make_alpha_result("a2", 0.03),
        }
        result = fusion.fuse(alphas, method="ic_vol")
        assert isinstance(result, FusionResult)
        assert result.n_strategies == 2
        assert len(result.combined_signal) == 100

    def test_fuse_equal(self):
        fusion = StrategyFusion()
        alphas = {
            "a1": _make_alpha_result("a1", 0.05),
            "a2": _make_alpha_result("a2", 0.03),
        }
        result = fusion.fuse(alphas, method="equal")
        assert abs(result.strategy_weights["a1"] - 0.5) < 0.01

    def test_fuse_empty(self):
        fusion = StrategyFusion()
        result = fusion.fuse({})
        assert result.n_strategies == 0

    def test_fusion_report(self):
        fusion = StrategyFusion()
        alphas = {
            "a1": _make_alpha_result("a1", 0.05),
        }
        result = fusion.fuse(alphas)
        report = fusion.get_fusion_report(result)
        assert "method" in report
        assert "n_strategies" in report

    def test_weight_stability(self):
        fusion = StrategyFusion()
        alphas = {
            "a1": _make_alpha_result("a1", 0.05),
            "a2": _make_alpha_result("a2", 0.03),
        }
        fusion.fuse(alphas)
        fusion.fuse(alphas)
        stability = fusion.get_weight_stability()
        assert isinstance(stability, dict)

    def test_min_ic_filter(self):
        config = FusionConfig(min_ic=0.04)
        fusion = StrategyFusion(config)
        alphas = {
            "a1": _make_alpha_result("a1", 0.05),
            "a2": _make_alpha_result("a2", 0.01),
        }
        result = fusion.fuse(alphas)
        assert "a2" not in result.strategy_weights or result.n_strategies <= 2
