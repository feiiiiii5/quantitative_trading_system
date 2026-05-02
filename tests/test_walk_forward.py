import numpy as np
import pandas as pd
import pytest

from core.walk_forward import (
    WalkForwardConfig,
    WalkForwardSplit,
    WalkForwardResult,
    generate_walk_forward_splits,
    calc_overfitting_score,
    calc_strategy_metrics,
    WalkForwardValidator,
)


class TestGenerateSplits:
    def test_basic(self):
        splits = generate_walk_forward_splits(500)
        assert len(splits) >= 1
        for split in splits:
            assert split.train_end > split.train_start
            assert split.val_end > split.val_start
            assert split.test_end > split.test_start

    def test_expanding_window(self):
        config = WalkForwardConfig(expanding_window=True)
        splits = generate_walk_forward_splits(500, config)
        assert len(splits) >= 1
        for split in splits:
            assert split.train_start == 0

    def test_min_train_size(self):
        config = WalkForwardConfig(min_train_size=200)
        splits = generate_walk_forward_splits(500, config)
        for split in splits:
            assert split.train_end - split.train_start >= 200

    def test_short_data(self):
        splits = generate_walk_forward_splits(50)
        assert isinstance(splits, list)


class TestCalcOverfittingScore:
    def test_no_overfitting(self):
        train = {"sharpe_ratio": 1.0}
        val = {"sharpe_ratio": 0.9}
        test = {"sharpe_ratio": 0.85}
        score = calc_overfitting_score(train, val, test)
        assert score < 0.5

    def test_overfitting(self):
        train = {"sharpe_ratio": 3.0}
        val = {"sharpe_ratio": 0.5}
        test = {"sharpe_ratio": 0.3}
        score = calc_overfitting_score(train, val, test)
        assert score > 0.3


class TestCalcStrategyMetrics:
    def test_basic(self):
        np.random.seed(42)
        equity = list(np.cumprod(1 + np.random.randn(100) * 0.01) * 100000)
        metrics = calc_strategy_metrics(equity)
        assert "sharpe_ratio" in metrics
        assert "max_drawdown" in metrics
        assert "cagr" in metrics
        assert "total_return" in metrics

    def test_short_equity(self):
        metrics = calc_strategy_metrics([100000])
        assert metrics["sharpe_ratio"] == 0.0


class TestWalkForwardValidator:
    def test_init(self):
        validator = WalkForwardValidator()
        assert validator._config is not None

    def test_custom_config(self):
        config = WalkForwardConfig(n_splits=3)
        validator = WalkForwardValidator(config)
        assert validator._config.n_splits == 3
