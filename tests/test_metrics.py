"""Tests for core metrics module."""
import numpy as np
import pandas as pd

from core.metrics import (
    InstitutionalMetrics,
    RollingRiskTracker,
    calc_all_metrics,
    calc_cagr,
    calc_cvar,
    calc_max_consecutive,
    calc_max_drawdown,
    calc_profit_loss_ratio,
    calc_sharpe,
    calc_var,
    calc_win_rate,
    metrics_to_dict,
)


class TestCalcCAGR:
    def test_basic_cagr(self):
        equity = [100.0, 110.0]
        result = calc_cagr(equity, n_days=252)
        assert result > 0

    def test_zero_length(self):
        assert calc_cagr([]) == 0.0
        assert calc_cagr([100.0]) == 0.0

    def test_negative_return(self):
        equity = [100.0, 90.0]
        result = calc_cagr(equity, n_days=252)
        assert result < 0

    def test_returns_positive_for_profitable(self):
        equity = [100000.0, 120000.0]
        result = calc_cagr(equity, n_days=252)
        assert 0.15 < result < 0.25


class TestCalcSharpe:
    def test_positive_sharpe(self, sample_returns):
        result = calc_sharpe(sample_returns)
        assert isinstance(result, float)

    def test_short_returns(self):
        short = pd.Series([0.01, -0.01])
        result = calc_sharpe(short)
        assert isinstance(result, float)

    def test_zero_std(self):
        constant = pd.Series([0.01, 0.01, 0.01])
        assert calc_sharpe(constant) == 0.0


class TestCalcMaxDrawdown:
    def test_basic_drawdown(self, sample_equity_curve):
        result = calc_max_drawdown(sample_equity_curve)
        assert result < 0
        assert result >= -1.0

    def test_no_drawdown(self):
        equity = [100.0, 110.0, 120.0, 130.0]
        result = calc_max_drawdown(equity)
        assert result == 0.0

    def test_empty(self):
        assert calc_max_drawdown([]) == 0.0
        assert calc_max_drawdown([100.0]) == 0.0


class TestCalcWinRate:
    def test_positive_returns(self):
        returns = pd.Series([0.01, -0.005, 0.02, -0.01, 0.015])
        result = calc_win_rate(returns)
        assert 0.0 <= result <= 1.0

    def test_empty(self):
        assert calc_win_rate(pd.Series([])) == 0.0


class TestCalcProfitLossRatio:
    def test_basic_ratio(self):
        returns = pd.Series([0.01, 0.02, -0.01, -0.02, 0.03])
        result = calc_profit_loss_ratio(returns)
        assert result >= 0

    def test_no_losses(self):
        returns = pd.Series([0.01, 0.02, 0.03])
        result = calc_profit_loss_ratio(returns)
        assert result == 99.0

    def test_no_wins(self):
        returns = pd.Series([-0.01, -0.02])
        result = calc_profit_loss_ratio(returns)
        assert result == 0.0


class TestCalcVar:
    def test_var_calculation(self):
        returns = pd.Series(np.random.randn(100) * 0.02)
        result = calc_var(returns, confidence=0.95)
        assert isinstance(result, float)

    def test_insufficient_data(self):
        returns = pd.Series([0.01, -0.01])
        assert calc_var(returns) == 0.0


class TestCalcCVaR:
    def test_cvar_calculation(self):
        returns = pd.Series(np.random.randn(100) * 0.02)
        result = calc_cvar(returns, confidence=0.95)
        assert isinstance(result, float)

    def test_cvar_less_than_var(self):
        returns = pd.Series(np.random.randn(100) * 0.02)
        var = calc_var(returns, confidence=0.95)
        cvar = calc_cvar(returns, confidence=0.95)
        assert abs(cvar) >= abs(var)


class TestCalcMaxConsecutive:
    def test_winning_streak(self):
        returns = pd.Series([0.01, 0.02, 0.03, -0.01, 0.04])
        assert calc_max_consecutive(returns, positive=True) == 3

    def test_losing_streak(self):
        returns = pd.Series([0.01, -0.02, -0.03, -0.04, 0.01])
        assert calc_max_consecutive(returns, positive=False) == 3


class TestRollingRiskTracker:
    def test_basic_update(self):
        tracker = RollingRiskTracker(window=10)
        result = tracker.update(100000.0)
        assert isinstance(result.sharpe, float)

    def test_snapshot_empty(self):
        tracker = RollingRiskTracker(window=10)
        result = tracker.snapshot()
        assert result.sharpe == 0.0

    def test_drawdown_tracking(self):
        tracker = RollingRiskTracker(window=10)
        tracker.update(100000.0)
        tracker.update(105000.0)
        tracker.update(95000.0)
        tracker.update(100000.0)
        result = tracker.snapshot()
        assert result.max_drawdown < 0

    def test_reset(self):
        tracker = RollingRiskTracker(window=10)
        tracker.update(100000.0)
        tracker.update(105000.0)
        tracker.reset()
        assert len(tracker._returns) == 0
        assert tracker._peak_equity == 0.0


class TestCalcAllMetrics:
    def test_full_metrics(self, sample_equity_curve, sample_returns):
        result = calc_all_metrics(sample_equity_curve, sample_returns)
        assert isinstance(result, InstitutionalMetrics)
        assert result.cagr >= 0
        assert 0 <= result.win_rate <= 1

    def test_empty_equity(self):
        result = calc_all_metrics([])
        assert isinstance(result, InstitutionalMetrics)
        assert result.cagr == 0.0


class TestMetricsToDict:
    def test_formatting(self):
        metrics = InstitutionalMetrics(
            cagr=0.15,
            sharpe_ratio=1.5,
            max_drawdown=-0.10,
            win_rate=0.55,
        )
        result = metrics_to_dict(metrics)
        assert "CAGR" in result
        assert "Sharpe Ratio" in result
        assert "%" in result["CAGR"]
