import logging
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

import numpy as np
import pandas as pd

from core.strategies import BaseStrategy, SignalType

logger = logging.getLogger(__name__)


@dataclass
class PortfolioPosition:
    symbol: str
    strategy_name: str
    quantity: int = 0
    avg_price: float = 0.0
    entry_date: str = ""
    market: str = "A"

    def to_dict(self) -> dict:
        return {
            "symbol": self.symbol, "strategy_name": self.strategy_name,
            "quantity": self.quantity, "avg_price": self.avg_price,
            "entry_date": self.entry_date, "market": self.market,
        }


@dataclass
class StrategyAllocation:
    strategy_name: str
    weight: float = 0.0
    allocated_capital: float = 0.0
    current_pnl: float = 0.0

    def to_dict(self) -> dict:
        return {
            "strategy_name": self.strategy_name,
            "weight": round(self.weight, 4),
            "allocated_capital": round(self.allocated_capital, 2),
            "current_pnl": round(self.current_pnl, 2),
        }


class PortfolioBacktester:
    def __init__(
        self,
        initial_capital: float = 100000.0,
        commission_rate: float = 0.0003,
        slippage: float = 0.001,
        max_position_pct: float = 0.3,
        max_daily_loss: float = 0.03,
    ):
        self.initial_capital = initial_capital
        self.commission_rate = commission_rate
        self.slippage = slippage
        self.max_position_pct = max_position_pct
        self.max_daily_loss = max_daily_loss

    def run(
        self,
        strategies: Dict[str, BaseStrategy],
        data: Dict[str, pd.DataFrame],
        allocations: Optional[Dict[str, float]] = None,
    ) -> dict:
        if not strategies or not data:
            return {"error": "No strategies or data provided"}

        n_strategies = len(strategies)
        if allocations is None:
            equal_weight = 1.0 / n_strategies
            allocations = {name: equal_weight for name in strategies}

        total_weight = sum(allocations.values())
        if total_weight > 0:
            allocations = {k: v / total_weight for k, v in allocations.items()}

        strategy_results = {}
        all_equity_curves = {}
        all_trades = {}

        for name, strategy in strategies.items():
            capital = self.initial_capital * allocations.get(name, 0)
            if capital < 1000:
                continue

            for symbol, df in data.items():
                if df.empty or len(df) < 30:
                    continue

                result = self._run_single(strategy, df, symbol, capital)
                strategy_results[f"{name}:{symbol}"] = result
                if "equity_curve" in result:
                    all_equity_curves[f"{name}:{symbol}"] = result["equity_curve"]
                if "trades" in result:
                    all_trades[f"{name}:{symbol}"] = result["trades"]

        combined_equity = self._combine_equity_curves(all_equity_curves, allocations)
        correlation_matrix = self._calc_correlation(all_equity_curves)

        portfolio_metrics = self._calc_portfolio_metrics(combined_equity)

        return {
            "strategy_results": strategy_results,
            "portfolio_metrics": portfolio_metrics,
            "correlation_matrix": correlation_matrix,
            "allocations": {k: round(v, 4) for k, v in allocations.items()},
            "combined_equity": combined_equity[-200:] if combined_equity else [],
        }

    def _run_single(
        self, strategy: BaseStrategy, df: pd.DataFrame,
        symbol: str, capital: float,
    ) -> dict:
        c = df["close"].values.astype(float)
        h = df["high"].values.astype(float)
        l = df["low"].values.astype(float)
        dates = df["date"].values if "date" in df.columns else np.arange(len(df))
        date_strs = [str(pd.Timestamp(d).date()) if not isinstance(d, str) else d for d in dates]

        strategy_result = strategy.generate_signals(df)

        signal_map: Dict[int, dict] = {}
        for sig in strategy_result.signals:
            best_idx = -1
            best_diff = float("inf")
            for i in range(len(c)):
                diff = abs(c[i] - sig.price)
                if diff < best_diff:
                    best_diff = diff
                    best_idx = i
            if best_idx >= 0 and best_diff < c[best_idx] * 0.02:
                if best_idx not in signal_map or sig.strength > signal_map[best_idx].get("strength", 0):
                    signal_map[best_idx] = {
                        "signal_type": sig.signal_type.value,
                        "strength": sig.strength,
                        "stop_loss": sig.stop_loss,
                        "take_profit": sig.take_profit,
                    }

        cash = capital
        position = 0
        entry_price = 0.0
        entry_date = ""
        entry_idx = 0
        trades = []
        equity_curve = [capital]
        daily_start = capital

        for i in range(1, len(c)):
            if cash <= 0:
                equity_curve.append(0)
                continue

            if position > 0:
                current_equity = cash + position * c[i]
                daily_loss = (current_equity - daily_start) / daily_start
                pnl_pct = (c[i] - entry_price) / entry_price

                if daily_loss < -self.max_daily_loss:
                    revenue = position * c[i] * (1 - self.commission_rate - self.slippage)
                    cash += revenue
                    trades.append({
                        "entry_price": entry_price, "exit_price": c[i],
                        "pnl_pct": round(pnl_pct * 100, 2), "hold_days": i - entry_idx,
                        "exit_reason": "daily_loss_limit",
                    })
                    position = 0
                    equity_curve.append(cash)
                    daily_start = cash
                    continue

            if i in signal_map:
                sig = signal_map[i]
                if sig["signal_type"] == "buy" and position == 0:
                    invest = cash * self.max_position_pct
                    fill = c[i] * (1 + self.slippage)
                    shares = int(invest / fill / 100) * 100
                    if shares <= 0:
                        shares = int(invest / fill)
                    if shares > 0:
                        cost = shares * fill * (1 + self.commission_rate)
                        if cost <= cash:
                            cash -= cost
                            position = shares
                            entry_price = fill
                            entry_date = date_strs[i] if i < len(date_strs) else ""
                            entry_idx = i
                            daily_start = cash + position * c[i]

                elif sig["signal_type"] == "sell" and position > 0:
                    pnl_pct = (c[i] - entry_price) / entry_price * 100
                    revenue = position * c[i] * (1 - self.commission_rate - self.slippage)
                    cash += revenue
                    trades.append({
                        "entry_price": entry_price, "exit_price": c[i],
                        "pnl_pct": round(pnl_pct, 2), "hold_days": i - entry_idx,
                        "exit_reason": "signal",
                    })
                    position = 0
                    daily_start = cash

            current_equity = cash + (position * c[i] if position > 0 else 0)
            equity_curve.append(current_equity)

        if position > 0:
            pnl_pct = (c[-1] - entry_price) / entry_price * 100
            revenue = position * c[-1] * (1 - self.commission_rate - self.slippage)
            cash += revenue
            trades.append({
                "entry_price": entry_price, "exit_price": c[-1],
                "pnl_pct": round(pnl_pct, 2), "hold_days": len(c) - 1 - entry_idx,
                "exit_reason": "end_of_data",
            })

        total_return = (cash / capital - 1) * 100 if capital > 0 else 0
        win_trades = [t for t in trades if t.get("pnl_pct", 0) > 0]

        return {
            "total_return": round(total_return, 2),
            "win_rate": round(len(win_trades) / len(trades) * 100, 2) if trades else 0,
            "total_trades": len(trades),
            "equity_curve": [round(e, 2) for e in equity_curve[-200:]],
            "trades": trades[-30:],
        }

    def _combine_equity_curves(
        self, curves: Dict[str, List[float]], allocations: Dict[str, float],
    ) -> List[float]:
        if not curves:
            return []

        max_len = max(len(c) for c in curves.values()) if curves else 0
        combined = [0.0] * max_len

        for key, curve in curves.items():
            parts = key.split(":")
            strategy_name = parts[0] if parts else key
            weight = allocations.get(strategy_name, 0)
            for i in range(len(curve)):
                if i < max_len:
                    combined[i] += curve[i] * weight

        return combined

    def _calc_correlation(self, curves: Dict[str, List[float]]) -> dict:
        if len(curves) < 2:
            return {}

        names = list(curves.keys())
        returns_dict = {}
        for name, curve in curves.items():
            if len(curve) > 1:
                returns = np.diff(curve) / np.maximum(curve[:-1], 1)
                returns_dict[name] = returns

        if len(returns_dict) < 2:
            return {}

        min_len = min(len(r) for r in returns_dict.values())
        if min_len < 10:
            return {}

        matrix = {}
        for n1 in returns_dict:
            matrix[n1] = {}
            for n2 in returns_dict:
                r1 = returns_dict[n1][:min_len]
                r2 = returns_dict[n2][:min_len]
                if np.std(r1) > 0 and np.std(r2) > 0:
                    corr = np.corrcoef(r1, r2)[0, 1]
                    matrix[n1][n2] = round(float(corr), 4)
                else:
                    matrix[n1][n2] = 0.0

        return matrix

    def _calc_portfolio_metrics(self, equity_curve: List[float]) -> dict:
        if not equity_curve or len(equity_curve) < 2:
            return {}

        total_return = (equity_curve[-1] / self.initial_capital - 1) * 100
        n_days = len(equity_curve)
        annual_return = ((equity_curve[-1] / self.initial_capital) ** (252 / max(n_days, 1)) - 1) * 100

        daily_returns = np.diff(equity_curve) / np.maximum(equity_curve[:-1], 1)
        daily_returns = daily_returns[np.isfinite(daily_returns)]

        sharpe = 0.0
        if len(daily_returns) > 10 and np.std(daily_returns) > 0:
            sharpe = (np.mean(daily_returns) - 0.03 / 252) / np.std(daily_returns) * np.sqrt(252)

        peak = equity_curve[0]
        max_dd = 0.0
        for e in equity_curve:
            peak = max(peak, e)
            dd = (peak - e) / peak * 100 if peak > 0 else 0
            max_dd = max(max_dd, dd)

        return {
            "total_return": round(total_return, 2),
            "annual_return": round(annual_return, 2),
            "sharpe_ratio": round(sharpe, 2),
            "max_drawdown": round(max_dd, 2),
        }
