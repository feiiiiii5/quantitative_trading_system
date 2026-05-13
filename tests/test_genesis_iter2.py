from __future__ import annotations

import asyncio

import numpy as np
import pytest

from core.backtest.stats import compute_backtest_statistics
from core.data_fetcher import _get_inflight_lock


class TestInflightLockLazyInit:
    def test_get_inflight_lock_returns_lock(self):
        lock = _get_inflight_lock()
        assert isinstance(lock, asyncio.Lock)

    def test_get_inflight_lock_idempotent(self):
        lock1 = _get_inflight_lock()
        lock2 = _get_inflight_lock()
        assert lock1 is lock2


class TestStatsRatioCaps:
    def _make_stats(self, equity_curve, closes, trades, dates):
        return compute_backtest_statistics(equity_curve, closes, trades, dates)

    def test_profit_factor_capped_at_99_99(self):
        equity = [100000, 100100, 100200, 100300, 100400, 100500]
        closes = np.array([10.0, 10.1, 10.2, 10.3, 10.4, 10.5])
        trades = [
            {"action": "sell", "pnl": 100000, "hold_days": 5},
            {"action": "sell", "pnl": -1, "hold_days": 2},
        ]
        dates = [f"2024-01-{i:02d}" for i in range(1, 7)]
        stats = self._make_stats(equity, closes, trades, dates)
        assert stats["profit_factor"] <= 99.99

    def test_payoff_ratio_capped_at_99_99(self):
        equity = [100000, 100100, 100200, 100300, 100400, 100500]
        closes = np.array([10.0, 10.1, 10.2, 10.3, 10.4, 10.5])
        trades = [
            {"action": "sell", "pnl": 50000, "hold_days": 5},
            {"action": "sell", "pnl": -0.01, "hold_days": 2},
        ]
        dates = [f"2024-01-{i:02d}" for i in range(1, 7)]
        stats = self._make_stats(equity, closes, trades, dates)
        assert stats["payoff_ratio"] <= 99.99

    def test_omega_ratio_capped_at_99_99(self):
        equity = list(np.linspace(100000, 200000, 60))
        closes = np.linspace(10.0, 20.0, 60)
        trades = [{"action": "sell", "pnl": 1000, "hold_days": 5}] * 10
        dates = [f"2024-{i // 30 + 1:02d}-{i % 30 + 1:02d}" for i in range(60)]
        stats = self._make_stats(equity, closes, trades, dates)
        assert stats["omega_ratio"] <= 99.99

    def test_zero_loss_profit_factor(self):
        equity = [100000, 100100, 100200]
        closes = np.array([10.0, 10.1, 10.2])
        trades = [{"action": "sell", "pnl": 100, "hold_days": 1}]
        dates = ["2024-01-01", "2024-01-02", "2024-01-03"]
        stats = self._make_stats(equity, closes, trades, dates)
        assert stats["profit_factor"] == 99.99

    def test_no_trades_profit_factor(self):
        equity = [100000, 100000, 100000]
        closes = np.array([10.0, 10.0, 10.0])
        trades = []
        dates = ["2024-01-01", "2024-01-02", "2024-01-03"]
        stats = self._make_stats(equity, closes, trades, dates)
        assert stats["profit_factor"] == 0.0

    def test_calmar_ratio_with_tiny_annual_return(self):
        equity = [100000, 100000.0001, 100000.0002]
        closes = np.array([10.0, 10.0, 10.0])
        trades = []
        dates = ["2024-01-01", "2024-01-02", "2024-01-03"]
        stats = self._make_stats(equity, closes, trades, dates)
        assert stats["calmar_ratio"] == 0.0


class TestEngineFillPriceGuard:
    def test_fill_price_zero_skips_buy(self):
        from core.backtest.engine import BacktestEngine
        import pandas as pd

        engine = BacktestEngine(initial_capital=100000)
        df = pd.DataFrame({
            "date": ["2024-01-01", "2024-01-02", "2024-01-03",
                     "2024-01-04", "2024-01-05", "2024-01-06",
                     "2024-01-07", "2024-01-08", "2024-01-09",
                     "2024-01-10", "2024-01-11"],
            "open": [0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0],
            "high": [0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0],
            "low": [0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0],
            "close": [0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0],
            "volume": [1000] * 11,
        })
        from core.strategies import DualMAStrategy
        strategy = DualMAStrategy(short_period=5, long_period=10)
        result = engine.run(strategy, df)
        assert result is not None
        assert result.total_trades == 0
