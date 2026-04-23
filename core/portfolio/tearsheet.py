import logging
import time
from dataclasses import dataclass, field
from typing import Dict, List, Optional

import numpy as np

logger = logging.getLogger(__name__)


@dataclass
class TearsheetData:
    strategy_name: str = ""
    start_date: str = ""
    end_date: str = ""
    initial_capital: float = 100000.0
    final_capital: float = 100000.0
    total_return: float = 0.0
    annual_return: float = 0.0
    sharpe_ratio: float = 0.0
    sortino_ratio: float = 0.0
    calmar_ratio: float = 0.0
    max_drawdown: float = 0.0
    max_drawdown_duration: int = 0
    win_rate: float = 0.0
    profit_factor: float = 0.0
    avg_win: float = 0.0
    avg_loss: float = 0.0
    total_trades: int = 0
    avg_hold_days: float = 0.0
    monthly_returns: Dict[str, float] = field(default_factory=dict)
    daily_returns: List[float] = field(default_factory=list)
    equity_curve: List[float] = field(default_factory=list)
    benchmark_return: float = 0.0
    alpha: float = 0.0
    beta: float = 0.0
    information_ratio: float = 0.0
    tracking_error: float = 0.0

    def to_dict(self) -> dict:
        return {
            "strategy_name": self.strategy_name,
            "period": {"start": self.start_date, "end": self.end_date},
            "capital": {"initial": round(self.initial_capital, 2), "final": round(self.final_capital, 2)},
            "returns": {
                "total": round(self.total_return, 4),
                "annual": round(self.annual_return, 4),
                "monthly": self.monthly_returns,
            },
            "risk_metrics": {
                "sharpe": round(self.sharpe_ratio, 2),
                "sortino": round(self.sortino_ratio, 2),
                "calmar": round(self.calmar_ratio, 2),
                "max_drawdown": round(self.max_drawdown, 4),
                "max_drawdown_duration": self.max_drawdown_duration,
            },
            "trade_stats": {
                "total_trades": self.total_trades,
                "win_rate": round(self.win_rate, 4),
                "profit_factor": round(self.profit_factor, 2),
                "avg_win": round(self.avg_win, 4),
                "avg_loss": round(self.avg_loss, 4),
                "avg_hold_days": round(self.avg_hold_days, 1),
            },
            "benchmark": {
                "benchmark_return": round(self.benchmark_return, 4),
                "alpha": round(self.alpha, 4),
                "beta": round(self.beta, 4),
                "information_ratio": round(self.information_ratio, 2),
                "tracking_error": round(self.tracking_error, 4),
            },
        }


class TearsheetGenerator:
    def __init__(self, risk_free_rate: float = 0.03):
        self.risk_free_rate = risk_free_rate

    def generate(
        self,
        equity_curve: List[float],
        trades: Optional[List[dict]] = None,
        strategy_name: str = "",
        benchmark_curve: Optional[List[float]] = None,
    ) -> TearsheetData:
        if not equity_curve or len(equity_curve) < 2:
            return TearsheetData(strategy_name=strategy_name)

        eq = np.array(equity_curve)
        daily_returns = np.diff(eq) / np.maximum(eq[:-1], 1)
        daily_returns = daily_returns[np.isfinite(daily_returns)]

        initial = eq[0]
        final = eq[-1]
        total_return = (final / initial - 1)
        n_days = len(eq)
        annual_return = (final / initial) ** (252 / max(n_days, 1)) - 1

        sharpe = self._calc_sharpe(daily_returns)
        sortino = self._calc_sortino(daily_returns)
        max_dd, max_dd_dur = self._calc_max_drawdown(eq)
        calmar = annual_return / max_dd if max_dd > 0 else 0

        win_rate = 0.0
        profit_factor = 0.0
        avg_win = 0.0
        avg_loss = 0.0
        avg_hold = 0.0

        if trades:
            win_trades = [t for t in trades if t.get("pnl_pct", 0) > 0]
            loss_trades = [t for t in trades if t.get("pnl_pct", 0) <= 0]
            total = len(trades)
            win_rate = len(win_trades) / total if total > 0 else 0
            avg_win = np.mean([t["pnl_pct"] for t in win_trades]) if win_trades else 0
            avg_loss = np.mean([t["pnl_pct"] for t in loss_trades]) if loss_trades else 0
            total_profit = sum(t.get("pnl_pct", 0) for t in win_trades)
            total_loss = abs(sum(t.get("pnl_pct", 0) for t in loss_trades))
            profit_factor = total_profit / total_loss if total_loss > 0 else 0
            avg_hold = np.mean([t.get("hold_days", 0) for t in trades]) if trades else 0

        monthly_returns = self._calc_monthly_returns(equity_curve)

        benchmark_return = 0.0
        alpha = 0.0
        beta = 0.0
        ir = 0.0
        te = 0.0

        if benchmark_curve and len(benchmark_curve) > 1:
            bm = np.array(benchmark_curve)
            benchmark_return = (bm[-1] / bm[0] - 1)
            bm_daily = np.diff(bm) / np.maximum(bm[:-1], 1)
            min_len = min(len(daily_returns), len(bm_daily))
            if min_len > 10:
                dr = daily_returns[:min_len]
                br = bm_daily[:min_len]
                cov_matrix = np.cov(dr, br)
                var_bm = np.var(br)
                if var_bm > 0:
                    beta = cov_matrix[0, 1] / var_bm
                alpha = annual_return - (self.risk_free_rate + beta * (benchmark_return - self.risk_rate))
                excess = dr - br
                te = np.std(excess) * np.sqrt(252)
                ir = np.mean(excess) / np.std(excess) * np.sqrt(252) if np.std(excess) > 0 else 0

        return TearsheetData(
            strategy_name=strategy_name,
            start_date="",
            end_date="",
            initial_capital=initial,
            final_capital=final,
            total_return=total_return,
            annual_return=annual_return,
            sharpe_ratio=sharpe,
            sortino_ratio=sortino,
            calmar_ratio=calmar,
            max_drawdown=max_dd,
            max_drawdown_duration=max_dd_dur,
            win_rate=win_rate,
            profit_factor=profit_factor,
            avg_win=avg_win,
            avg_loss=avg_loss,
            total_trades=len(trades) if trades else 0,
            avg_hold_days=avg_hold,
            monthly_returns=monthly_returns,
            daily_returns=daily_returns.tolist()[-200:],
            equity_curve=eq.tolist()[-200:],
            benchmark_return=benchmark_return,
            alpha=alpha,
            beta=beta,
            information_ratio=ir,
            tracking_error=te,
        )

    def _calc_sharpe(self, returns: np.ndarray) -> float:
        if len(returns) < 10 or np.std(returns) <= 0:
            return 0.0
        return (np.mean(returns) - self.risk_free_rate / 252) / np.std(returns) * np.sqrt(252)

    def _calc_sortino(self, returns: np.ndarray) -> float:
        if len(returns) < 10:
            return 0.0
        downside = returns[returns < 0]
        if len(downside) == 0:
            return 0.0
        downside_std = np.sqrt(np.mean(downside ** 2))
        if downside_std <= 0:
            return 0.0
        return (np.mean(returns) - self.risk_free_rate / 252) / downside_std * np.sqrt(252)

    def _calc_max_drawdown(self, equity: np.ndarray) -> tuple:
        peak = equity[0]
        max_dd = 0.0
        max_dd_dur = 0
        current_dur = 0
        peak_idx = 0

        for i in range(len(equity)):
            if equity[i] > peak:
                peak = equity[i]
                peak_idx = i
                current_dur = 0
            else:
                current_dur = i - peak_idx
                dd = (peak - equity[i]) / peak if peak > 0 else 0
                if dd > max_dd:
                    max_dd = dd
                    max_dd_dur = current_dur

        return max_dd * 100, max_dd_dur

    def _calc_monthly_returns(self, equity_curve: List[float]) -> Dict[str, float]:
        if len(equity_curve) < 22:
            return {}
        monthly = {}
        n_months = len(equity_curve) // 22
        for m in range(n_months):
            start_idx = m * 22
            end_idx = min((m + 1) * 22, len(equity_curve))
            if start_idx < len(equity_curve) and end_idx <= len(equity_curve):
                ret = equity_curve[end_idx - 1] / equity_curve[start_idx] - 1
                monthly[f"M{m + 1}"] = round(ret, 4)
        return monthly

    @property
    def risk_rate(self):
        return self.risk_free_rate
