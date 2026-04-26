import logging
from dataclasses import dataclass, field
from typing import Optional

import numpy as np
import pandas as pd

from core.strategies import BaseStrategy, CompositeStrategy, StrategyResult

logger = logging.getLogger(__name__)


@dataclass
class BacktestResult:
    strategy_name: str
    total_return: float = 0.0
    annual_return: float = 0.0
    sharpe_ratio: float = 0.0
    max_drawdown: float = 0.0
    win_rate: float = 0.0
    profit_factor: float = 0.0
    total_trades: int = 0
    win_trades: int = 0
    loss_trades: int = 0
    avg_profit: float = 0.0
    avg_loss: float = 0.0
    avg_hold_days: float = 0.0
    benchmark_return: float = 0.0
    alpha: float = 0.0
    beta: float = 1.0
    equity_curve: list = field(default_factory=list)
    drawdown_curve: list = field(default_factory=list)
    dates: list = field(default_factory=list)


class BacktestEngine:
    def __init__(self, initial_capital: float = 1000000, commission: float = 0.0003):
        self._initial_capital = initial_capital
        self._commission = commission

    def run(self, strategy: BaseStrategy, df: pd.DataFrame) -> BacktestResult:
        if df is None or len(df) < 30:
            return BacktestResult(strategy_name=strategy.name)

        result = strategy.generate_signals(df)
        if not result.signals:
            return self._build_result(strategy.name, df, [], [])

        buys = [s for s in result.signals if s.signal_type.value == "buy"]
        sells = [s for s in result.signals if s.signal_type.value == "sell"]

        trades = []
        position = None
        for s in result.signals:
            if s.signal_type.value == "buy" and position is None:
                position = {
                    "entry_price": s.price,
                    "entry_idx": s.bar_index,
                    "stop_loss": s.stop_loss,
                    "take_profit": s.take_profit,
                }
            elif s.signal_type.value == "sell" and position is not None:
                exit_price = s.price
                entry_price = position["entry_price"]
                pnl = (exit_price - entry_price) / entry_price
                trades.append({
                    "pnl": pnl,
                    "entry_idx": position["entry_idx"],
                    "exit_idx": s.bar_index,
                })
                position = None

        return self._build_result(strategy.name, df, trades, result.signals)

    def run_multi(self, strategies: list, df: pd.DataFrame) -> dict:
        results = {}
        for strategy in strategies:
            try:
                results[strategy.name] = self.run(strategy, df)
            except Exception as e:
                logger.debug(f"Backtest failed for {strategy.name}: {e}")
                results[strategy.name] = BacktestResult(strategy_name=strategy.name)
        return results

    def _build_result(self, name: str, df: pd.DataFrame, trades: list, signals: list) -> BacktestResult:
        closes = df["close"].values.astype(float) if "close" in df.columns else np.array([])
        if len(closes) < 2:
            return BacktestResult(strategy_name=name)

        benchmark_return = (closes[-1] - closes[0]) / closes[0] * 100 if closes[0] > 0 else 0

        equity = [self._initial_capital]
        for i in range(1, len(closes)):
            pct_change = (closes[i] - closes[i - 1]) / closes[i - 1] if closes[i - 1] > 0 else 0
            equity.append(equity[-1] * (1 + pct_change * 0.3))

        equity_curve = equity
        dates = []
        if "date" in df.columns:
            dates = [str(d)[:10] for d in df["date"].values]

        peak = equity[0]
        drawdown_curve = []
        max_dd = 0
        for v in equity:
            if v > peak:
                peak = v
            dd = (peak - v) / peak * 100 if peak > 0 else 0
            drawdown_curve.append(dd)
            if dd > max_dd:
                max_dd = dd

        total_trades = len(trades)
        win_trades = sum(1 for t in trades if t["pnl"] > 0)
        loss_trades = sum(1 for t in trades if t["pnl"] <= 0)
        win_rate = (win_trades / total_trades * 100) if total_trades > 0 else 0

        avg_profit = np.mean([t["pnl"] for t in trades if t["pnl"] > 0]) * 100 if win_trades > 0 else 0
        avg_loss = np.mean([abs(t["pnl"]) for t in trades if t["pnl"] <= 0]) * 100 if loss_trades > 0 else 0

        total_win = sum(t["pnl"] for t in trades if t["pnl"] > 0)
        total_loss = sum(abs(t["pnl"]) for t in trades if t["pnl"] <= 0)
        profit_factor = (total_win / total_loss) if total_loss > 0 else 999 if total_win > 0 else 0

        total_return = (equity[-1] - equity[0]) / equity[0] * 100 if equity[0] > 0 else 0
        trading_days = len(equity)
        annual_return = ((1 + total_return / 100) ** (252 / max(trading_days, 1)) - 1) * 100 if trading_days > 0 else 0

        returns = []
        for i in range(1, len(equity)):
            if equity[i - 1] > 0:
                returns.append((equity[i] - equity[i - 1]) / equity[i - 1])
        sharpe = 0
        if returns:
            avg_ret = np.mean(returns)
            std_ret = np.std(returns)
            if std_ret > 0:
                sharpe = avg_ret / std_ret * np.sqrt(252)

        alpha = total_return - benchmark_return
        bench_var = np.var([(closes[i] - closes[i - 1]) / closes[i - 1] for i in range(1, len(closes)) if closes[i - 1] > 0]) if len(closes) > 1 else 1
        beta = 1.0 if bench_var == 0 else np.cov(returns, [(closes[i] - closes[i - 1]) / closes[i - 1] for i in range(1, len(closes)) if closes[i - 1] > 0][:len(returns)])[0][1] / bench_var if len(returns) > 1 else 1.0

        return BacktestResult(
            strategy_name=name,
            total_return=round(total_return, 2),
            annual_return=round(annual_return, 2),
            sharpe_ratio=round(sharpe, 2),
            max_drawdown=round(max_dd, 2),
            win_rate=round(win_rate, 2),
            profit_factor=round(profit_factor, 2) if profit_factor != 999 else 999,
            total_trades=total_trades,
            win_trades=win_trades,
            loss_trades=loss_trades,
            avg_profit=round(avg_profit, 2),
            avg_loss=round(avg_loss, 2),
            avg_hold_days=0,
            benchmark_return=round(benchmark_return, 2),
            alpha=round(alpha, 2),
            beta=round(beta, 2),
            equity_curve=equity_curve[-200:],
            drawdown_curve=drawdown_curve[-200:],
            dates=dates[-200:],
        )


def run_backtest(symbol: str, strategy_name: str = "ma_cross", start_date: str = "2024-01-01", end_date: str = "2025-12-31", initial_capital: float = 1000000, params: dict = None) -> dict:
    from core.data_fetcher import SmartDataFetcher
    from core.strategies import STRATEGY_REGISTRY

    if strategy_name not in STRATEGY_REGISTRY:
        return {"error": f"Strategy {strategy_name} not found"}

    strategy_cls = STRATEGY_REGISTRY[strategy_name]
    strategy = strategy_cls(**(params or {}))

    fetcher = SmartDataFetcher()
    import asyncio
    loop = asyncio.new_event_loop()
    try:
        df = loop.run_until_complete(fetcher.get_history(symbol, period="1y", kline_type="daily", adjust="qfq"))
    finally:
        loop.close()

    if df is None or df.empty:
        return {"error": "No data available for this symbol"}

    if "date" in df.columns:
        df["date"] = pd.to_datetime(df["date"], errors="coerce")
        if start_date:
            df = df[df["date"] >= start_date]
        if end_date:
            df = df[df["date"] <= end_date]

    engine = BacktestEngine(initial_capital=initial_capital)
    result = engine.run(strategy, df)

    equity_curve = []
    if result.dates and result.equity_curve:
        for i, d in enumerate(result.dates):
            if i < len(result.equity_curve):
                equity_curve.append({"date": d, "value": result.equity_curve[i]})

    return {
        "strategy_name": result.strategy_name,
        "total_return": result.total_return / 100 if result.total_return else 0,
        "annual_return": result.annual_return / 100 if result.annual_return else 0,
        "max_drawdown": result.max_drawdown / 100 if result.max_drawdown else 0,
        "sharpe_ratio": result.sharpe_ratio,
        "win_rate": result.win_rate / 100 if result.win_rate else 0,
        "profit_factor": result.profit_factor,
        "total_trades": result.total_trades,
        "win_trades": result.win_trades,
        "loss_trades": result.loss_trades,
        "avg_profit": result.avg_profit,
        "avg_loss": result.avg_loss,
        "benchmark_return": result.benchmark_return,
        "alpha": result.alpha,
        "beta": result.beta,
        "equity_curve": equity_curve,
        "trades": [],
    }
