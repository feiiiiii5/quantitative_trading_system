import logging
from dataclasses import dataclass, field
from typing import Dict, List, Optional

import numpy as np
import pandas as pd

from core.strategies import BaseStrategy, SignalType, TradeSignal

logger = logging.getLogger(__name__)


@dataclass
class BacktestTrade:
    entry_date: str
    entry_price: float
    exit_date: str = ""
    exit_price: float = 0.0
    direction: str = "long"
    shares: int = 0
    pnl: float = 0.0
    pnl_pct: float = 0.0
    hold_days: int = 0
    stop_loss: float = 0.0
    take_profit: float = 0.0
    exit_reason: str = ""


@dataclass
class BacktestResult:
    strategy_name: str
    total_return: float = 0.0
    annual_return: float = 0.0
    sharpe_ratio: float = 0.0
    max_drawdown: float = 0.0
    max_drawdown_duration: int = 0
    win_rate: float = 0.0
    profit_factor: float = 0.0
    total_trades: int = 0
    win_trades: int = 0
    loss_trades: int = 0
    avg_profit: float = 0.0
    avg_loss: float = 0.0
    avg_hold_days: float = 0.0
    trades: List[BacktestTrade] = field(default_factory=list)
    equity_curve: List[float] = field(default_factory=list)
    drawdown_curve: List[float] = field(default_factory=list)
    dates: List[str] = field(default_factory=list)
    benchmark_return: float = 0.0
    alpha: float = 0.0
    beta: float = 0.0


class BacktestEngine:
    def __init__(
        self,
        initial_capital: float = 100000.0,
        commission_rate: float = 0.0003,
        slippage: float = 0.001,
        risk_free_rate: float = 0.03,
        max_daily_loss: float = 0.03,
        max_position: float = 0.3,
    ):
        self.initial_capital = initial_capital
        self.commission_rate = commission_rate
        self.slippage = slippage
        self.risk_free_rate = risk_free_rate
        self.max_daily_loss = max_daily_loss
        self.max_position = max_position

    def run(self, strategy: BaseStrategy, df: pd.DataFrame) -> BacktestResult:
        if df is None or len(df) < 60:
            return BacktestResult(strategy_name=strategy.name)

        c = df["close"].values.astype(float)
        h = df["high"].values.astype(float)
        l = df["low"].values.astype(float)
        dates = df["date"].values if "date" in df.columns else np.arange(len(df))
        date_strs = [str(pd.Timestamp(d).date()) if not isinstance(d, str) else d for d in dates]

        strategy_result = strategy.generate_signals(df)

        signal_map: Dict[int, TradeSignal] = {}
        for sig in strategy_result.signals:
            idx = sig.bar_index if sig.bar_index >= 0 else -1
            if idx < 0:
                best_idx = -1
                best_diff = float("inf")
                for i in range(len(c)):
                    diff = abs(c[i] - sig.price)
                    if diff < best_diff:
                        best_diff = diff
                        best_idx = i
                if best_idx >= 0 and best_diff < c[best_idx] * 0.02:
                    idx = best_idx
            if idx >= 0:
                if idx not in signal_map or sig.strength > signal_map[idx].strength:
                    signal_map[idx] = sig

        capital = self.initial_capital
        position = 0
        entry_price = 0.0
        entry_date = ""
        entry_idx = 0
        stop_loss = 0.0
        take_profit = 0.0
        trades: List[BacktestTrade] = []
        equity_curve = [capital]
        peak_equity = capital
        daily_start_capital = capital

        for i in range(1, len(c)):
            if capital <= 0:
                equity_curve.append(0)
                continue

            if position > 0:
                current_pnl_pct = (c[i] - entry_price) / entry_price
                current_equity = capital + position * c[i]
                daily_loss = (current_equity - daily_start_capital) / daily_start_capital

                if stop_loss > 0 and c[i] <= stop_loss:
                    revenue = position * c[i] * (1 - self.commission_rate - self.slippage)
                    capital += revenue
                    trades.append(BacktestTrade(
                        entry_date=entry_date, entry_price=entry_price,
                        exit_date=date_strs[i], exit_price=c[i],
                        direction="long", shares=position,
                        pnl_pct=round(current_pnl_pct * 100, 2),
                        hold_days=i - entry_idx,
                        stop_loss=stop_loss, take_profit=take_profit,
                        exit_reason="stop_loss",
                    ))
                    position = 0
                    equity_curve.append(capital)
                    daily_start_capital = capital
                    continue

                if take_profit > 0 and c[i] >= take_profit:
                    revenue = position * c[i] * (1 - self.commission_rate - self.slippage)
                    capital += revenue
                    trades.append(BacktestTrade(
                        entry_date=entry_date, entry_price=entry_price,
                        exit_date=date_strs[i], exit_price=c[i],
                        direction="long", shares=position,
                        pnl_pct=round(current_pnl_pct * 100, 2),
                        hold_days=i - entry_idx,
                        stop_loss=stop_loss, take_profit=take_profit,
                        exit_reason="take_profit",
                    ))
                    position = 0
                    equity_curve.append(capital)
                    daily_start_capital = capital
                    continue

                if daily_loss < -self.max_daily_loss:
                    revenue = position * c[i] * (1 - self.commission_rate - self.slippage)
                    capital += revenue
                    trades.append(BacktestTrade(
                        entry_date=entry_date, entry_price=entry_price,
                        exit_date=date_strs[i], exit_price=c[i],
                        direction="long", shares=position,
                        pnl_pct=round(current_pnl_pct * 100, 2),
                        hold_days=i - entry_idx,
                        exit_reason="daily_loss_limit",
                    ))
                    position = 0
                    equity_curve.append(capital)
                    daily_start_capital = capital
                    continue

            if i in signal_map:
                sig = signal_map[i]

                if sig.signal_type == SignalType.BUY and position == 0:
                    pos_pct = min(sig.position_pct, self.max_position)
                    invest = capital * pos_pct
                    shares = int(invest / c[i] / 100) * 100
                    if shares <= 0:
                        shares = int(invest / c[i])
                    if shares > 0:
                        cost = shares * c[i] * (1 + self.commission_rate + self.slippage)
                        if cost <= capital:
                            capital -= cost
                            position = shares
                            entry_price = c[i]
                            entry_date = date_strs[i]
                            entry_idx = i
                            stop_loss = sig.stop_loss if sig.stop_loss > 0 else 0
                            take_profit = sig.take_profit if sig.take_profit > 0 else 0
                            daily_start_capital = capital + position * c[i]

                elif sig.signal_type == SignalType.SELL and position > 0:
                    pnl_pct = (c[i] - entry_price) / entry_price * 100
                    revenue = position * c[i] * (1 - self.commission_rate - self.slippage)
                    capital += revenue
                    trades.append(BacktestTrade(
                        entry_date=entry_date, entry_price=entry_price,
                        exit_date=date_strs[i], exit_price=c[i],
                        direction="long", shares=position,
                        pnl_pct=round(pnl_pct, 2),
                        hold_days=i - entry_idx,
                        stop_loss=stop_loss, take_profit=take_profit,
                        exit_reason="signal",
                    ))
                    position = 0
                    daily_start_capital = capital

            current_equity = capital + (position * c[i] if position > 0 else 0)
            equity_curve.append(current_equity)
            peak_equity = max(peak_equity, current_equity)

        if position > 0:
            pnl_pct = (c[-1] - entry_price) / entry_price * 100
            revenue = position * c[-1] * (1 - self.commission_rate - self.slippage)
            capital += revenue
            trades.append(BacktestTrade(
                entry_date=entry_date, entry_price=entry_price,
                exit_date=date_strs[-1], exit_price=c[-1],
                direction="long", shares=position,
                pnl_pct=round(pnl_pct, 2),
                hold_days=len(c) - 1 - entry_idx,
                exit_reason="end_of_data",
            ))

        return self._calculate_metrics(strategy.name, trades, equity_curve, date_strs, c)

    def _calculate_metrics(
        self, name: str, trades: List[BacktestTrade],
        equity_curve: List[float], dates: List[str], prices: np.ndarray,
    ) -> BacktestResult:
        if not equity_curve or len(equity_curve) < 2:
            return BacktestResult(strategy_name=name)

        total_return = (equity_curve[-1] / self.initial_capital - 1) * 100

        n_days = len(equity_curve)
        annual_return = ((equity_curve[-1] / self.initial_capital) ** (252 / max(n_days, 1)) - 1) * 100

        daily_returns = np.diff(equity_curve) / np.maximum(equity_curve[:-1], 1)
        daily_returns = daily_returns[np.isfinite(daily_returns)]

        sharpe = 0.0
        if len(daily_returns) > 10 and np.std(daily_returns) > 0:
            sharpe = (np.mean(daily_returns) - self.risk_free_rate / 252) / np.std(daily_returns) * np.sqrt(252)

        peak = equity_curve[0]
        max_dd = 0.0
        max_dd_duration = 0
        dd_start = 0
        drawdown_curve = []

        for i, eq in enumerate(equity_curve):
            peak = max(peak, eq)
            dd = (peak - eq) / peak * 100 if peak > 0 else 0
            drawdown_curve.append(dd)
            max_dd = max(max_dd, dd)
            if dd > 0:
                max_dd_duration = max(max_dd_duration, i - dd_start)
            else:
                dd_start = i

        win_trades = [t for t in trades if t.pnl_pct > 0]
        loss_trades = [t for t in trades if t.pnl_pct <= 0]
        total_profit = sum(t.pnl_pct for t in win_trades)
        total_loss = abs(sum(t.pnl_pct for t in loss_trades)) if loss_trades else 1

        benchmark_return = (prices[-1] / prices[0] - 1) * 100 if len(prices) > 1 else 0
        alpha = annual_return - benchmark_return

        beta = 1.0
        if len(daily_returns) > 10:
            bm_returns = np.diff(prices) / np.maximum(prices[:-1], 1)
            bm_returns = bm_returns[np.isfinite(bm_returns)]
            min_len = min(len(daily_returns), len(bm_returns))
            if min_len > 10:
                cov = np.cov(daily_returns[:min_len], bm_returns[:min_len])
                var = np.var(bm_returns[:min_len])
                if var > 0:
                    beta = cov[0, 1] / var

        return BacktestResult(
            strategy_name=name,
            total_return=round(total_return, 2),
            annual_return=round(annual_return, 2),
            sharpe_ratio=round(sharpe, 2),
            max_drawdown=round(max_dd, 2),
            max_drawdown_duration=max_dd_duration,
            win_rate=round(len(win_trades) / len(trades) * 100, 2) if trades else 0,
            profit_factor=round(total_profit / total_loss, 2) if total_loss > 0 else 0,
            total_trades=len(trades),
            win_trades=len(win_trades),
            loss_trades=len(loss_trades),
            avg_profit=round(np.mean([t.pnl_pct for t in win_trades]), 2) if win_trades else 0,
            avg_loss=round(np.mean([t.pnl_pct for t in loss_trades]), 2) if loss_trades else 0,
            avg_hold_days=round(np.mean([t.hold_days for t in trades]), 1) if trades else 0,
            trades=trades,
            equity_curve=[round(e, 2) for e in equity_curve],
            drawdown_curve=[round(d, 2) for d in drawdown_curve],
            dates=dates[:len(equity_curve)],
            benchmark_return=round(benchmark_return, 2),
            alpha=round(alpha, 2),
            beta=round(beta, 2),
        )

    def run_multi(self, strategies: List[BaseStrategy], df: pd.DataFrame) -> Dict[str, BacktestResult]:
        results = {}
        for strategy in strategies:
            try:
                results[strategy.name] = self.run(strategy, df)
            except Exception as e:
                logger.debug(f"Backtest failed for {strategy.name}: {e}")
                results[strategy.name] = BacktestResult(strategy_name=strategy.name)
        return results
