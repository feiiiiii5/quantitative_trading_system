__all__ = [
    "InsufficientDataError",
    "BacktestResult",
    "BatchStrategyRunner",
    "BacktestEngine",
    "run_backtest",
    "run_walk_forward",
    "walk_forward_oos_validation",
    "run_parallel_backtest",
    "compare_results",
    "grid_search_params",
]

import asyncio
import logging
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from datetime import datetime

import numpy as np
import pandas as pd

from core.data_governance import DataQualityPipeline
from core.events import BacktestProgressTracker, Event, EventBus, EventType
from core.memory_guard import memory_guard
from core.orders import Order, OrderSide, OrderType
from core.risk_manager import EnhancedRiskManager
from core.strategies import STRATEGY_REGISTRY, BaseStrategy, SignalType, StrategyResult

logger = logging.getLogger(__name__)


class InsufficientDataError(ValueError):
    pass


def _vectorized_equity_curve(
    equity: float,
    trades: list[dict],
    n_bars: int,
    entry_indices: list[int],
    exit_indices: list[int],
    pnl_list: list[float],
) -> list[float]:
    """Vectorized equity curve computation for performance.

    This is a fast alternative to the loop-based approach when
    trade data is already computed.
    """
    if n_bars <= 0:
        return [equity]

    equity_curve = [equity] * (n_bars + 1)
    trade_map: dict[int, list[tuple[int, float]]] = {}

    for _idx, (entry, exit_bar, pnl) in enumerate(zip(entry_indices, exit_indices, pnl_list, strict=True)):
        if entry < 0 or entry > n_bars:
            continue
        if entry not in trade_map:
            trade_map[entry] = []
        trade_map[entry].append((exit_bar, pnl))

    for bar in range(1, n_bars + 1):
        cumulative_pnl = 0.0
        closed_trades = []

        if bar in trade_map:
            for exit_bar, pnl in trade_map[bar]:
                if exit_bar <= bar:
                    cumulative_pnl += pnl
                    closed_trades.append((exit_bar, pnl))

        equity_curve[bar] = equity + cumulative_pnl

    return equity_curve


class BacktestProfiler:
    """Profiles backtest performance and identifies bottlenecks."""

    def __init__(self):
        self._timings: dict[str, list[float]] = {}
        self._counts: dict[str, int] = {}

    def record(self, name: str, duration: float) -> None:
        if name not in self._timings:
            self._timings[name] = []
        self._timings[name].append(duration)
        self._counts[name] = self._counts.get(name, 0) + 1

    def get_report(self) -> dict:
        if not self._timings:
            return {"error": "No profiling data collected"}

        report = {}
        for name, times in self._timings.items():
            if not times:
                continue
            avg_ms = float(np.mean(times)) * 1000
            total_ms = float(np.sum(times)) * 1000
            report[name] = {
                "calls": self._counts.get(name, 0),
                "avg_ms": round(avg_ms, 3),
                "total_ms": round(total_ms, 3),
                "min_ms": round(float(np.min(times)) * 1000, 3),
                "max_ms": round(float(np.max(times)) * 1000, 3),
            }

        sorted_report = dict(sorted(report.items(), key=lambda x: x[1]["total_ms"], reverse=True))
        return {
            "phases": sorted_report,
            "total_ms": round(sum(r["total_ms"] for r in report.values()), 3),
        }

    def reset(self) -> None:
        self._timings.clear()
        self._counts.clear()


def _excursion(position_data: dict, exit_idx: int, lows: np.ndarray, highs: np.ndarray, n: int) -> tuple[float, float]:
    entry_price = float(position_data.get("entry_price", 0))
    entry_idx = int(position_data.get("entry_idx", exit_idx))
    if entry_price <= 0:
        return 0.0, 0.0
    if n <= 0 or entry_idx < 0 or exit_idx < 0 or entry_idx >= n or exit_idx >= n:
        return 0.0, 0.0
    start = max(0, min(entry_idx, exit_idx))
    end = max(start, min(exit_idx, n - 1)) + 1
    low_window = lows[start:end] if len(lows) >= end else np.empty(0)
    high_window = highs[start:end] if len(highs) >= end else np.empty(0)
    finite_lows = low_window[np.isfinite(low_window)]
    finite_highs = high_window[np.isfinite(high_window)]
    if len(finite_lows) == 0 or len(finite_highs) == 0:
        return 0.0, 0.0
    mae = (float(np.min(finite_lows)) / entry_price - 1) * 100
    mfe = (float(np.max(finite_highs)) / entry_price - 1) * 100
    return round(mae, 2), round(mfe, 2)


class RealisticCostModel:
    def __init__(
        self,
        commission: float = 0.0002,
        stamp_tax: float = 0.001,
        transfer_fee_sh: float = 0.00001,
        market_impact_pct: float = 0.0005,
        financing_rate: float = 0.045,
        min_commission: float = 5.0,
    ):
        self.commission = commission
        self.stamp_tax = stamp_tax
        self.transfer_fee_sh = transfer_fee_sh
        self.market_impact_pct = market_impact_pct
        self.financing_rate = financing_rate / 365
        self.min_commission = min_commission

    def calc_buy_cost(self, price: float, shares: int, amount: float = 0,
                      daily_amount: float = 0, is_sh: bool = False) -> dict:
        if amount <= 0:
            amount = price * shares
        fee = max(amount * self.commission, self.min_commission)
        transfer = shares * self.transfer_fee_sh if is_sh else 0.0
        impact = 0.0
        if daily_amount > 0:
            participation = amount / daily_amount
            impact = amount * self.market_impact_pct * np.sqrt(participation)
        total = fee + transfer + impact
        return {"commission": round(fee, 2), "transfer_fee": round(transfer, 2),
                "market_impact": round(impact, 2), "total": round(total, 2)}

    def calc_sell_cost(self, price: float, shares: int, amount: float = 0,
                       daily_amount: float = 0, is_sh: bool = False) -> dict:
        if amount <= 0:
            amount = price * shares
        fee = max(amount * self.commission, self.min_commission)
        stamp = amount * self.stamp_tax
        transfer = shares * self.transfer_fee_sh if is_sh else 0.0
        impact = 0.0
        if daily_amount > 0:
            participation = amount / daily_amount
            impact = amount * self.market_impact_pct * np.sqrt(participation)
        total = fee + stamp + transfer + impact
        return {"commission": round(fee, 2), "stamp_tax": round(stamp, 2),
                "transfer_fee": round(transfer, 2), "market_impact": round(impact, 2),
                "total": round(total, 2)}

    def calc_financing_cost(self, borrowed: float, days: int) -> float:
        return round(borrowed * self.financing_rate * days, 2)


def _simulate_call_auction_fill(open_price: float, rng: np.random.Generator = None) -> float:
    """模拟开盘集合竞价：以开盘价±0.1%的随机价格成交"""
    if rng is None:
        rng = np.random.default_rng()
    noise = rng.uniform(-0.001, 0.001)
    return open_price * (1 + noise)


def _simulate_twap_fill(price: float, shares: int, daily_amount: float,
                         n_slices: int = 4, rng: np.random.Generator = None) -> float:
    if daily_amount <= 0 or shares * price < daily_amount * 0.01:
        return price
    if rng is None:
        rng = np.random.default_rng()
    total_fill = 0.0
    remaining = shares
    per_slice = max(shares // n_slices, 1)
    for s in range(n_slices):
        slice_shares = min(per_slice, remaining) if s < n_slices - 1 else remaining
        remaining -= slice_shares
        noise = rng.normal(0, 0.001)
        total_fill += slice_shares * price * (1 + noise)
    return total_fill / shares


def _check_limit_price(prev_close: float, price: float, is_buy: bool,
                       limit_pct: float = 0.10) -> tuple[bool, float]:
    if prev_close <= 0:
        return True, 1.0
    upper = prev_close * (1 + limit_pct)
    lower = prev_close * (1 - limit_pct)
    if is_buy and price >= upper:
        fill_prob = max(0.1, 1.0 - (price - upper) / (upper * 0.01 + 1e-9))
        return False, min(fill_prob, 0.9)
    if not is_buy and price <= lower:
        fill_prob = max(0.1, 1.0 - (lower - price) / (lower * 0.01 + 1e-9))
        return False, min(fill_prob, 0.9)
    return True, 1.0


def _get_limit_pct(symbol: str) -> float:
    if symbol.startswith(("3", "68")):
        return 0.20
    if symbol.startswith("8"):
        return 0.30
    return 0.10


@dataclass
class BacktestResult:
    strategy_name: str
    total_return: float = 0.0
    annual_return: float = 0.0
    sharpe_ratio: float = 0.0
    max_drawdown: float = 0.0
    calmar_ratio: float = 0.0
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
    trades: list = field(default_factory=list)
    kline_with_signals: list = field(default_factory=list)
    max_points: int = 0
    sortino_ratio: float = 0.0
    max_consecutive_losses: int = 0
    omega_ratio: float = 0.0
    tail_ratio: float = 0.0
    information_ratio: float = 0.0
    recovery_factor: float = 0.0
    avg_mae: float = 0.0
    avg_mfe: float = 0.0
    cvar_95: float = 0.0
    var_95: float = 0.0
    annual_volatility: float = 0.0
    downside_deviation: float = 0.0
    monthly_returns: list = field(default_factory=list)
    monte_carlo: dict = field(default_factory=dict)
    optimization: dict = field(default_factory=dict)
    expectancy: float = 0.0
    payoff_ratio: float = 0.0

    def to_dict(self, max_equity: int = 500, max_trades: int = 200, max_kline: int = 500) -> dict:
        """统一的BacktestResult序列化方法，避免各API端点手动构建dict导致属性名错误"""
        equity_curve = []
        if self.equity_curve and self.dates:
            for i in range(min(len(self.dates), len(self.equity_curve))):
                equity_curve.append({"date": self.dates[i], "value": float(self.equity_curve[i])})
        return {
            "strategy_name": self.strategy_name,
            "total_return": round(self.total_return, 4) if self.total_return else 0,
            "annual_return": round(self.annual_return, 4) if self.annual_return else 0,
            "max_drawdown": round(self.max_drawdown, 4) if self.max_drawdown else 0,
            "sharpe_ratio": self.sharpe_ratio,
            "calmar_ratio": self.calmar_ratio,
            "win_rate": round(self.win_rate, 2) if self.win_rate else 0,
            "profit_factor": self.profit_factor,
            "total_trades": self.total_trades,
            "win_trades": self.win_trades,
            "loss_trades": self.loss_trades,
            "avg_profit": self.avg_profit,
            "avg_loss": self.avg_loss,
            "avg_hold_days": self.avg_hold_days,
            "benchmark_return": round(self.benchmark_return, 4) if self.benchmark_return else 0,
            "alpha": round(self.alpha, 4) if self.alpha else 0,
            "beta": self.beta,
            "sortino_ratio": self.sortino_ratio,
            "max_consecutive_losses": self.max_consecutive_losses,
            "omega_ratio": self.omega_ratio,
            "tail_ratio": self.tail_ratio,
            "information_ratio": self.information_ratio,
            "recovery_factor": self.recovery_factor,
            "avg_mae": self.avg_mae,
            "avg_mfe": self.avg_mfe,
            "expectancy": self.expectancy,
            "payoff_ratio": self.payoff_ratio,
            "cvar_95": self.cvar_95,
            "var_95": self.var_95,
            "annual_volatility": self.annual_volatility,
            "downside_deviation": self.downside_deviation,
            "equity_curve": equity_curve[-max_equity:] if equity_curve else [],
            "drawdown_curve": self.drawdown_curve[-max_equity:] if self.drawdown_curve else [],
            "trades": self.trades[-max_trades:] if self.trades else [],
            "kline_with_signals": self.kline_with_signals[-max_kline:] if self.kline_with_signals else [],
        }

    def summary_dict(self) -> dict:
        """轻量级摘要，用于策略比较等不需要完整曲线的场景"""
        return {
            "strategy_name": self.strategy_name,
            "total_return": round(self.total_return, 4),
            "annual_return": round(self.annual_return, 4),
            "sharpe_ratio": round(self.sharpe_ratio, 2),
            "max_drawdown": round(self.max_drawdown, 4),
            "win_rate": round(self.win_rate, 4),
            "profit_factor": round(self.profit_factor, 2),
            "total_trades": self.total_trades,
            "sortino_ratio": round(self.sortino_ratio, 2),
            "calmar_ratio": round(self.calmar_ratio, 2),
            "omega_ratio": round(self.omega_ratio, 2),
        }

    def downsample_curves(self, max_points: int = 500) -> None:
        if max_points <= 0 or len(self.equity_curve) <= max_points:
            return
        step = len(self.equity_curve) / max_points
        indices = [int(i * step) for i in range(max_points)]
        if indices[-1] != len(self.equity_curve) - 1:
            indices.append(len(self.equity_curve) - 1)
        self.equity_curve = [self.equity_curve[i] for i in indices]
        self.drawdown_curve = [self.drawdown_curve[i] for i in indices]
        self.dates = [self.dates[i] for i in indices]

    def get_performance_summary(self) -> dict:
        """Get a concise performance summary for strategy comparison."""
        return {
            "strategy": self.strategy_name,
            "total_return_pct": round(self.total_return * 100, 2),
            "annual_return_pct": round(self.annual_return * 100, 2),
            "sharpe": round(self.sharpe_ratio, 2),
            "max_drawdown_pct": round(self.max_drawdown * 100, 2),
            "win_rate_pct": round(self.win_rate * 100, 1),
            "total_trades": self.total_trades,
            "calmar": round(self.calmar_ratio, 2),
            "sortino": round(self.sortino_ratio, 2),
            "profit_factor": round(self.profit_factor, 2),
            "avg_mae_pct": round(self.avg_mae, 2) if self.avg_mae else 0,
            "avg_mfe_pct": round(self.avg_mfe, 2) if self.avg_mfe else 0,
        }

    def compare_with(self, other: "BacktestResult") -> dict:
        """Compare this result with another for strategy selection."""
        return {
            "this": self.get_performance_summary(),
            "other": other.get_performance_summary(),
            "sharpe_diff": round(self.sharpe_ratio - other.sharpe_ratio, 2),
            "return_diff_pct": round((self.annual_return - other.annual_return) * 100, 2),
            "drawdown_diff_pct": round((self.max_drawdown - other.max_drawdown) * 100, 2),
            "trade_count_diff": self.total_trades - other.total_trades,
            "recommended": self.strategy_name if self.sharpe_ratio >= other.sharpe_ratio else other.strategy_name,
        }

    def is_better_than(self, other: "BacktestResult", metric: str = "sharpe_ratio") -> bool:
        """Check if this result is better than another on the specified metric."""
        if not isinstance(other, BacktestResult):
            return False
        val_a = float(getattr(self, metric, 0.0) or 0.0)
        val_b = float(getattr(other, metric, 0.0) or 0.0)
        if metric == "max_drawdown":
            return val_a <= val_b
        return val_a >= val_b

    def get_risk_adjusted_metrics(self) -> dict:
        """Calculate comprehensive risk-adjusted performance metrics."""
        metrics = {
            "sharpe": round(self.sharpe_ratio, 2),
            "sortino": round(self.sortino_ratio, 2),
            "calmar": round(self.calmar_ratio, 2),
            "omega": round(self.omega_ratio, 2) if self.omega_ratio else 0,
            "tail_ratio": round(self.tail_ratio, 2) if self.tail_ratio else 0,
            "information_ratio": round(self.information_ratio, 2) if self.information_ratio else 0,
            "var_95": round(self.var_95, 4) if self.var_95 else 0,
            "cvar_95": round(self.cvar_95, 4) if self.cvar_95 else 0,
        }
        recovery = self.recovery_factor if self.recovery_factor else 0
        metrics["recovery_factor"] = round(recovery, 2)
        annualized_vol = self.annual_volatility if self.annual_volatility else 0
        metrics["annual_volatility"] = round(annualized_vol, 4)
        downside = self.downside_deviation if self.downside_deviation else 0
        metrics["downside_deviation"] = round(downside, 4)
        metrics["return_risk_ratio"] = round(self.annual_return / max(annualized_vol, 1e-9), 4)
        metrics["upside_capture_ratio"] = round(
            self.annual_return / max(abs(self.benchmark_return), 1e-9) if self.benchmark_return else 0, 2
        )
        return metrics

    def get_drawdown_analysis(self) -> dict:
        """Detailed drawdown analysis including duration and recovery statistics."""
        if not self.equity_curve or len(self.equity_curve) < 2:
            return {"error": "Insufficient equity curve data"}

        eq = np.array(self.equity_curve, dtype=float)
        peaks = np.maximum.accumulate(eq)
        drawdowns = (peaks - eq) / np.where(peaks > 1e-9, peaks, 1.0) * 100

        in_drawdown = False
        drawdown_periods = []
        current_duration = 0
        max_duration = 0
        drawdown_starts = []

        for i, dd in enumerate(drawdowns):
            if dd > 0.1:
                if not in_drawdown:
                    in_drawdown = True
                    drawdown_starts.append(i)
                current_duration += 1
                max_duration = max(max_duration, current_duration)
            else:
                if in_drawdown:
                    drawdown_periods.append({"duration": current_duration, "start_idx": drawdown_starts[-1], "end_idx": i})
                in_drawdown = False
                current_duration = 0

        if in_drawdown:
            drawdown_periods.append({"duration": current_duration, "start_idx": drawdown_starts[-1] if drawdown_starts else 0, "end_idx": len(drawdowns)})

        avg_duration = float(np.mean([p["duration"] for p in drawdown_periods])) if drawdown_periods else 0
        dd_95 = float(np.percentile(drawdowns, 95)) if len(drawdowns) > 0 else 0

        return {
            "current_drawdown_pct": round(float(drawdowns[-1]) if len(drawdowns) > 0 else 0, 2),
            "max_drawdown_pct": round(float(np.max(drawdowns)), 2),
            "avg_drawdown_pct": round(float(np.mean(drawdowns[drawdowns > 0.1])), 2) if np.any(drawdowns > 0.1) else 0,
            "drawdown_95_pct": round(dd_95, 2),
            "max_drawdown_duration": max_duration,
            "avg_drawdown_duration": round(avg_duration, 1),
            "n_drawdown_periods": len(drawdown_periods),
            "recovered_smoothly": all(p["duration"] < max_duration * 1.5 for p in drawdown_periods) if drawdown_periods else True,
        }

    def get_trade_analysis(self) -> dict:
        """Comprehensive trade-level analysis."""
        sell_trades = [t for t in self.trades if t.get("action") == "sell"]
        if not sell_trades:
            return {"error": "No trades to analyze"}

        pnls = [float(t.get("pnl", 0)) for t in sell_trades]
        maes = [abs(float(t.get("mae", 0))) for t in sell_trades]
        mfes = [float(t.get("mfe", 0)) for t in sell_trades]
        hold_days = [t.get("hold_days", 0) for t in sell_trades]

        pnl_arr = np.array(pnls)
        win_count = int(np.sum(pnl_arr > 0))

        return {
            "total_trades": len(sell_trades),
            "win_rate": round(win_count / len(pnls) * 100, 1) if pnls else 0,
            "avg_pnl": round(float(np.mean(pnl_arr)), 2),
            "median_pnl": round(float(np.median(pnl_arr)), 2),
            "best_trade": round(float(np.max(pnl_arr)), 2),
            "worst_trade": round(float(np.min(pnl_arr)), 2),
            "avg_mae_pct": round(float(np.mean(maes)), 2) if maes else 0,
            "avg_mfe_pct": round(float(np.mean(mfes)), 2) if mfes else 0,
            "mfe_mae_ratio": round(float(np.mean(mfes) / max(np.mean(maes), 1e-9)), 2) if mfes and maes else 0,
            "avg_hold_days": round(float(np.mean(hold_days)), 1) if hold_days else 0,
            "max_hold_days": max(hold_days) if hold_days else 0,
            "profit_factor": round(self.profit_factor, 2) if self.profit_factor else 0,
            "expectancy": round(self.expectancy, 2) if self.expectancy else 0,
            "payoff_ratio": round(self.payoff_ratio, 2) if self.payoff_ratio else 0,
            "consecutive_wins": self._count_max_consecutive(sell_trades, positive=True),
            "consecutive_losses": self._count_max_consecutive(sell_trades, positive=False),
        }

    def _count_max_consecutive(self, trades: list[dict], positive: bool = True) -> int:
        count = 0
        max_count = 0
        for t in trades:
            pnl = t.get("pnl", 0)
            if (positive and pnl > 0) or (not positive and pnl < 0):
                count += 1
                max_count = max(max_count, count)
            else:
                count = 0
        return max_count

    def get_monthly_returns_table(self) -> dict:
        """Monthly returns in a structured table format."""
        if not self.monthly_returns:
            return {"error": "No monthly returns data"}

        monthly = {}
        for entry in self.monthly_returns:
            month = entry.get("month", "")
            ret = entry.get("return", 0)
            monthly[month] = round(ret * 100, 2)

        if not monthly:
            return {"error": "Empty monthly returns"}

        months = sorted(monthly.keys())
        returns = [monthly[m] for m in months]
        positive = sum(1 for r in returns if r > 0)
        negative = sum(1 for r in returns if r < 0)
        best_month = max(returns) if returns else 0
        worst_month = min(returns) if returns else 0

        return {
            "monthly": monthly,
            "months_count": len(months),
            "positive_months": positive,
            "negative_months": negative,
            "win_rate": round(positive / len(months) * 100, 1) if months else 0,
            "best_month": best_month,
            "worst_month": worst_month,
            "avg_monthly_return": round(float(np.mean(returns)), 2) if returns else 0,
        }


class BatchStrategyRunner:
    """Batch strategy runner for multi-strategy backtesting and optimization."""

    def __init__(self, initial_capital: float = 1000000, commission: float = 0.0003,
                 slippage_pct: float = 0.001, market_impact_pct: float = 0.0005):
        self._initial_capital = initial_capital
        self._engine = BacktestEngine(
            initial_capital=initial_capital,
            commission=commission,
            slippage_pct=slippage_pct,
            market_impact_pct=market_impact_pct,
        )

    def run_strategies(
        self,
        strategy_classes: list[type[BaseStrategy]],
        df: pd.DataFrame,
        top_n: int = 5,
        metric: str = "sharpe_ratio",
    ) -> dict:
        """Run multiple strategies and return ranked results.

        Args:
            strategy_classes: List of strategy classes to test
            df: Market data
            top_n: Return only top N strategies
            metric: Optimization metric (sharpe_ratio, total_return, max_drawdown, win_rate)

        Returns:
            Dict with results, rankings, and summary
        """
        if not strategy_classes or df is None or len(df) < 10:
            return {"error": "Invalid input: need strategy classes and sufficient data"}

        results: list[BacktestResult] = []
        for strat_cls in strategy_classes:
            try:
                strategy = strat_cls()
                result = self._engine.run(strategy, df)
                results.append(result)
            except Exception as e:
                logger.debug("Strategy %s failed: %s", strat_cls, e)

        if not results:
            return {"error": "All strategies failed"}

        comparison = compare_results(results)
        rankings = comparison.get("ranking", [])
        top_results = []
        for rank_entry in rankings[:top_n]:
            strat_name = rank_entry["strategy_name"]
            matched = next((r for r in results if r.strategy_name == strat_name), None)
            if matched:
                top_results.append(matched)

        return {
            "results": [r.get_performance_summary() for r in top_results],
            "rankings": rankings[:top_n],
            "comparison": comparison.get("comparison", []),
            "summary": self._build_summary(top_results, metric),
        }

    def auto_optimize(
        self,
        strategy_classes: list[type[BaseStrategy]],
        df: pd.DataFrame,
        param_spaces: dict[type[BaseStrategy], dict] = None,
        max_combinations: int = 30,
        metric: str = "sharpe_ratio",
    ) -> dict:
        """Auto-optimize: find best strategy and parameters for the given data.

        Args:
            strategy_classes: List of strategy classes to optimize
            df: Market data
            param_spaces: Optional param spaces per strategy class
            max_combinations: Max parameter combinations to test per strategy
            metric: Optimization metric

        Returns:
            Best strategy, parameters, and performance summary
        """
        if not strategy_classes or df is None or len(df) < 20:
            return {"error": "Need at least 20 bars of data for auto-optimization"}

        param_spaces = param_spaces or {}
        all_candidates: list[dict] = []

        for strat_cls in strategy_classes:
            param_space = param_spaces.get(strat_cls, {})
            if not param_space and hasattr(strat_cls, "get_param_space"):
                param_space = strat_cls.get_param_space()

            if not param_space:
                try:
                    result = self._engine.run(strat_cls(), df)
                    all_candidates.append({
                        "strategy_class": strat_cls,
                        "strategy_name": strat_cls.__name__,
                        "params": {},
                        "result": result,
                    })
                except Exception as e:
                    logger.debug("Default params failed for %s: %s", strat_cls, e)
                continue

            param_names = list(param_space.keys())
            param_values: list[list] = []
            for name in param_names:
                spec = param_space[name]
                if isinstance(spec, dict):
                    v_min = spec.get("min", 5)
                    v_max = spec.get("max", 60)
                    step = spec.get("step", 1)
                else:
                    v_min, v_max, _ = spec if len(spec) >= 3 else (5, 60, 1)
                    step = 5
                vals = list(range(int(v_min), int(v_max) + 1, int(step)))
                if not vals:
                    vals = [v_min]
                param_values.append(vals)

            from itertools import product
            combinations = list(product(*param_values))
            if len(combinations) > max_combinations:
                indices = np.random.default_rng(42).choice(
                    len(combinations), max_combinations, replace=False
                )
                combinations = [combinations[i] for i in sorted(indices)]

            for combo in combinations:
                params = dict(zip(param_names, combo, strict=False))
                try:
                    result = self._engine.run(strat_cls(**params), df)
                    all_candidates.append({
                        "strategy_class": strat_cls,
                        "strategy_name": strat_cls.__name__,
                        "params": params,
                        "result": result,
                    })
                except Exception as e:
                    logger.debug("Param combo failed for %s: %s", strat_cls, e)

        if not all_candidates:
            return {"error": "No valid configurations found"}

        best_candidate = max(
            all_candidates,
            key=lambda x: self._get_metric(x["result"], metric),
        )
        best_result = best_candidate["result"]

        return {
            "best_strategy": best_candidate["strategy_name"],
            "best_params": best_candidate["params"],
            "best_result": best_result.get_performance_summary(),
            "all_candidates_summary": [
                {
                    "strategy": c["strategy_name"],
                    "params": c["params"],
                    "sharpe": round(c["result"].sharpe_ratio, 2),
                    "return_pct": round(c["result"].total_return, 2),
                    "max_dd_pct": round(c["result"].max_drawdown, 2),
                }
                for c in sorted(
                    all_candidates,
                    key=lambda x: self._get_metric(x["result"], metric),
                    reverse=True,
                )[:10]
            ],
        }

    def _get_metric(self, result: BacktestResult, metric: str) -> float:
        val = getattr(result, metric, 0.0) or 0.0
        if metric == "max_drawdown":
            return -val
        return val

    def _build_summary(self, results: list[BacktestResult], metric: str) -> dict:
        if not results:
            return {}
        best = max(results, key=lambda x: self._get_metric(x, metric))
        return {
            "total_strategies_tested": len(results),
            "best_strategy": best.strategy_name,
            "best_sharpe": round(best.sharpe_ratio, 2),
            "best_return_pct": round(best.total_return, 2),
            "best_max_drawdown_pct": round(best.max_drawdown, 2),
            "metric_used": metric,
        }


class BacktestEngine:
    def __init__(self, initial_capital: float = 1000000, commission: float = 0.0003, stamp_tax: float = 0.001,
                 slippage_pct: float = 0.001, market_impact_pct: float = 0.0005,
                 cost_model: RealisticCostModel = None, enable_twap: bool = True,
                 enable_limit_check: bool = True, use_vectorized: bool = True,
                 event_bus: EventBus | None = None, risk_manager: EnhancedRiskManager | None = None,
                 enable_data_quality: bool = True):
        self._initial_capital = initial_capital
        self._slippage_pct = slippage_pct
        self._cost_model = cost_model or RealisticCostModel(
            commission=commission, stamp_tax=stamp_tax, market_impact_pct=market_impact_pct)
        self._enable_twap = enable_twap
        self._enable_limit_check = enable_limit_check
        self._use_vectorized = use_vectorized
        self._rng = np.random.default_rng(42)
        self._event_bus = event_bus or EventBus()
        self._risk_manager = risk_manager or EnhancedRiskManager(initial_capital=initial_capital)
        self._progress_tracker = BacktestProgressTracker(self._event_bus)
        self._data_quality = DataQualityPipeline() if enable_data_quality else None

    def run(self, strategy: BaseStrategy, df: pd.DataFrame, symbol: str = "") -> BacktestResult:
        if df is None or len(df) < 10:
            raise InsufficientDataError(
                f"{strategy.name} requires at least 10 bars; got {len(df) if df is not None else 0}"
            )

        df = df.copy()
        if "date" in df.columns:
            df["date"] = pd.to_datetime(df["date"], errors="coerce")
            df = df.dropna(subset=["date"])
            df = df.sort_values("date").reset_index(drop=True)

        if len(df) < 10:
            raise InsufficientDataError(
                f"{strategy.name} requires at least 10 bars after date parsing/cleaning; got {len(df)}"
            )

        if self._data_quality is not None:
            df = self._data_quality.process(df, symbol)

        strategy.reset()
        self._event_bus.publish(Event(EventType.INIT, {"strategy": strategy.name}))

        result = strategy.generate_signals(df)
        if not result.signals:
            return self._build_result(strategy.name, df, [], [], result)

        buy_signals = sorted(
            [s for s in result.signals if s.signal_type == SignalType.BUY],
            key=lambda s: s.bar_index,
        )
        sell_signals = sorted(
            [s for s in result.signals if s.signal_type == SignalType.SELL],
            key=lambda s: s.bar_index,
        )

        # 买卖信号优先级控制：同一K线同时出现买卖信号时，按优先级过滤
        sell_bars = {s.bar_index for s in sell_signals}
        buy_bars = {s.bar_index for s in buy_signals}
        conflicting_bars = sell_bars & buy_bars
        if conflicting_bars:
            buy_signals = [s for s in buy_signals if s.bar_index not in conflicting_bars]
            logger.debug(
                f"Signal priority: removed {len(conflicting_bars)} conflicting buy signal(s) on bars {conflicting_bars}"
            )

        with memory_guard(f"Backtest_{strategy.name}", max_mb=2048):
            return self._build_result(strategy.name, df, buy_signals, sell_signals, result, symbol)

    def run_event_driven(
        self,
        strategy: BaseStrategy,
        df: pd.DataFrame,
        symbol: str = "",
        enable_risk_check: bool = True,
    ) -> BacktestResult:
        """事件驱动回测 — 逐bar驱动策略+风控+成交模拟

        与 run() 的区别:
        1. 信号在bar到达时即时生成，而非预计算
        2. 止损/止盈在下一bar开盘前检查（日内高低点模拟）
        3. 每笔交易前经过风控引擎检查
        4. T+1约束在成交时强制执行
        """
        if df is None or len(df) < 10:
            raise InsufficientDataError(
                f"{strategy.name} requires at least 10 bars; got {len(df) if df is not None else 0}"
            )

        df = df.copy()
        if "date" in df.columns:
            df["date"] = pd.to_datetime(df["date"], errors="coerce")
            df = df.dropna(subset=["date"])
            df = df.sort_values("date").reset_index(drop=True)

        if len(df) < 10:
            raise InsufficientDataError(
                f"{strategy.name} requires at least 10 bars after date parsing/cleaning; got {len(df)}"
            )

        if self._data_quality is not None:
            df = self._data_quality.process(df, symbol)

        strategy.reset()
        self._event_bus.publish(Event(EventType.INIT, {"strategy": strategy.name}))

        closes = df["close"].values.astype(float) if "close" in df.columns else np.array([])
        opens = df["open"].values.astype(float) if "open" in df.columns else closes
        highs = df["high"].values.astype(float) if "high" in df.columns else closes
        lows = df["low"].values.astype(float) if "low" in df.columns else closes
        dates_col = df["date"].values if "date" in df.columns else np.arange(len(closes))
        volumes = df["volume"].values.astype(float) if "volume" in df.columns else None
        amounts_col = df["amount"].values.astype(float) if "amount" in df.columns else None

        n = len(closes)
        if n < 2:
            return BacktestResult(strategy_name=strategy.name)

        self._progress_tracker.start(strategy.name, n)
        cash = float(self._initial_capital)
        shares = 0
        position = None
        equity_curve = [cash]
        trades = []
        lot_size = 100

        for i in range(1, n):
            bar = {
                "open": float(opens[i]) if i < len(opens) else 0,
                "high": float(highs[i]) if i < len(highs) else 0,
                "low": float(lows[i]) if i < len(lows) else 0,
                "close": float(closes[i]) if i < len(closes) else 0,
                "volume": float(volumes[i]) if volumes is not None and i < len(volumes) else 0,
                "date": str(dates_col[i])[:10] if i < len(dates_col) else "",
                "symbol": symbol,
            }

            if position is not None:
                entry_price = position["entry_price"]
                stop_loss = position.get("stop_loss", 0)
                take_profit = position.get("take_profit", 0)
                bar_high = bar["high"]
                bar_low = bar["low"]

                if stop_loss > 0 and bar_low <= stop_loss:
                    fill_price = max(stop_loss, float(lows[i])) if i < len(lows) else stop_loss
                    fill_price = fill_price * (1 - self._slippage_pct)
                    sell_shares = shares
                    amount = sell_shares * fill_price
                    cost_detail = self._cost_model.calc_sell_cost(fill_price, sell_shares, amount, 0)
                    cash += amount - cost_detail["total"]
                    pnl = (fill_price - entry_price) * sell_shares - cost_detail["total"]
                    date_str = bar["date"]
                    trades.append({
                        "action": "sell",
                        "symbol": symbol,
                        "price": round(fill_price, 2),
                        "shares": sell_shares,
                        "amount": round(amount, 2),
                        "fee": round(cost_detail["total"], 2),
                        "cost_detail": cost_detail,
                        "date": date_str,
                        "bar_index": i,
                        "reason": f"止损@{stop_loss:.2f}",
                        "pnl": round(pnl, 2),
                        "mae": round(min(0, (float(lows[i]) - entry_price) / entry_price), 4) if entry_price > 1e-9 else 0,
                        "mfe": round(max(0, (float(highs[i]) - entry_price) / entry_price), 4) if entry_price > 1e-9 else 0,
                        "hold_days": self._calc_hold_days(position.get("entry_date", ""), date_str),
                    })
                    position = None
                    shares = 0
                    equity_curve.append(cash)
                    continue

                if take_profit > 0 and bar_high >= take_profit:
                    fill_price = min(take_profit, float(highs[i])) if i < len(highs) else take_profit
                    fill_price = fill_price * (1 - self._slippage_pct)
                    sell_shares = shares
                    amount = sell_shares * fill_price
                    cost_detail = self._cost_model.calc_sell_cost(fill_price, sell_shares, amount, 0)
                    cash += amount - cost_detail["total"]
                    pnl = (fill_price - entry_price) * sell_shares - cost_detail["total"]
                    date_str = bar["date"]
                    trades.append({
                        "action": "sell",
                        "symbol": symbol,
                        "price": round(fill_price, 2),
                        "shares": sell_shares,
                        "amount": round(amount, 2),
                        "fee": round(cost_detail["total"], 2),
                        "cost_detail": cost_detail,
                        "date": date_str,
                        "bar_index": i,
                        "reason": f"止盈@{take_profit:.2f}",
                        "pnl": round(pnl, 2),
                        "mae": round(min(0, (float(lows[i]) - entry_price) / entry_price), 4) if entry_price > 1e-9 else 0,
                        "mfe": round(max(0, (float(highs[i]) - entry_price) / entry_price), 4) if entry_price > 1e-9 else 0,
                        "hold_days": self._calc_hold_days(position.get("entry_date", ""), date_str),
                    })
                    position = None
                    shares = 0
                    equity_curve.append(cash)
                    continue

            portfolio = {
                "cash": cash,
                "positions": {symbol: position} if position else {},
                "total_assets": equity_curve[-1],
                "peak_value": max(equity_curve),
            }

            sigs = strategy.on_bar(bar, portfolio)

            for sig in sigs:
                action = sig.get("action", "hold")
                if action not in ("buy", "sell"):
                    continue

                if action == "buy" and position is None:
                    fill_price = bar["open"] if bar["open"] > 0 else bar["close"]
                    if fill_price <= 0:
                        continue

                    if volumes is not None and i < len(volumes):
                        bar_vol = volumes[i]
                        if np.isnan(bar_vol) or bar_vol <= 0:
                            continue

                    fill_price = fill_price * (1 + self._slippage_pct)

                    alloc_pct = sig.get("position_pct", 0.3)
                    if alloc_pct < 0.2:
                        alloc_pct = 0.3
                    alloc_amount = equity_curve[-1] * alloc_pct
                    if alloc_amount > cash * 0.98:
                        alloc_amount = cash * 0.98

                    buy_shares = int(alloc_amount / fill_price / lot_size) * lot_size
                    if buy_shares <= 0:
                        continue

                    bar_amount = 0.0
                    if amounts_col is not None and i < len(amounts_col):
                        bar_amount = float(amounts_col[i]) if not np.isnan(amounts_col[i]) else 0.0
                    if bar_amount <= 0 and volumes is not None and i < len(volumes):
                        bar_amount = float(volumes[i]) * fill_price
                    if bar_amount > 0:
                        max_shares = int(bar_amount * 0.25 / fill_price / lot_size) * lot_size
                        if max_shares > 0 and buy_shares > max_shares:
                            buy_shares = max_shares
                    if buy_shares <= 0:
                        continue

                    amount = buy_shares * fill_price
                    cost_detail = self._cost_model.calc_buy_cost(fill_price, buy_shares, amount, bar_amount)
                    total_cost = amount + cost_detail["total"]

                    if total_cost > cash:
                        buy_shares = int(cash * 0.98 / fill_price / lot_size) * lot_size
                        if buy_shares <= 0:
                            continue
                        amount = buy_shares * fill_price
                        cost_detail = self._cost_model.calc_buy_cost(fill_price, buy_shares, amount, bar_amount)
                        total_cost = amount + cost_detail["total"]
                        if total_cost > cash:
                            continue

                    if enable_risk_check:
                        order = Order(
                            order_id=f"bt_buy_{i}",
                            symbol=symbol,
                            side=OrderSide.BUY,
                            order_type=OrderType.MARKET,
                            quantity=buy_shares,
                            price=fill_price,
                        )
                        risk_ctx = {"total_assets": equity_curve[-1], "current_positions": {}}
                        risk_ok, risk_reason = self._risk_manager.check_order(order, risk_ctx)
                        if not risk_ok:
                            logger.debug("Risk check blocked buy: %s", risk_reason)
                            continue

                    cash -= total_cost
                    shares = buy_shares
                    date_str = bar["date"]
                    position = {
                        "entry_price": fill_price,
                        "shares": buy_shares,
                        "entry_idx": i,
                        "entry_date": date_str,
                        "stop_loss": sig.get("stop_loss", 0),
                        "take_profit": sig.get("take_profit", 0),
                        "highest_price": fill_price,
                    }
                    trades.append({
                        "action": "buy",
                        "symbol": symbol,
                        "price": round(fill_price, 2),
                        "shares": buy_shares,
                        "amount": round(amount, 2),
                        "fee": round(cost_detail["total"], 2),
                        "cost_detail": cost_detail,
                        "date": date_str,
                        "bar_index": i,
                        "reason": sig.get("reason", ""),
                    })

                elif action == "sell" and position is not None:
                    entry_date = position.get("entry_date", "")
                    bar_date = bar["date"]
                    if entry_date and bar_date and entry_date == bar_date:
                        continue

                    fill_price = bar["open"] if bar["open"] > 0 else bar["close"]
                    if fill_price <= 0:
                        continue

                    fill_price = fill_price * (1 - self._slippage_pct)
                    sell_shares = shares
                    amount = sell_shares * fill_price
                    cost_detail = self._cost_model.calc_sell_cost(fill_price, sell_shares, amount, 0)
                    cash += amount - cost_detail["total"]
                    entry_price = position["entry_price"]
                    pnl = (fill_price - entry_price) * sell_shares - cost_detail["total"]
                    date_str = bar["date"]
                    trades.append({
                        "action": "sell",
                        "symbol": symbol,
                        "price": round(fill_price, 2),
                        "shares": sell_shares,
                        "amount": round(amount, 2),
                        "fee": round(cost_detail["total"], 2),
                        "cost_detail": cost_detail,
                        "date": date_str,
                        "bar_index": i,
                        "reason": sig.get("reason", ""),
                        "pnl": round(pnl, 2),
                        "mae": round(min(0, (float(lows[i]) - entry_price) / entry_price), 4) if entry_price > 1e-9 else 0,
                        "mfe": round(max(0, (float(highs[i]) - entry_price) / entry_price), 4) if entry_price > 1e-9 else 0,
                        "hold_days": self._calc_hold_days(position.get("entry_date", ""), date_str),
                    })
                    position = None
                    shares = 0

            if position is not None:
                position["highest_price"] = max(position.get("highest_price", 0), bar["high"])

            eq = cash + (shares * bar["close"] if shares > 0 else 0)
            equity_curve.append(eq)

        return self._finalize_event_driven_result(strategy.name, df, equity_curve, trades, symbol)

    @staticmethod
    def _calc_hold_days(entry_date: str, exit_date: str) -> int:
        if not entry_date or not exit_date:
            return 0
        try:
            d1 = datetime.strptime(entry_date[:10], "%Y-%m-%d")
            d2 = datetime.strptime(exit_date[:10], "%Y-%m-%d")
            return max(0, (d2 - d1).days)
        except (ValueError, TypeError):
            return 0

    def _finalize_event_driven_result(
        self,
        name: str,
        df: pd.DataFrame,
        equity_curve: list[float],
        trades: list[dict],
        symbol: str = "",
    ) -> BacktestResult:
        closes = df["close"].values.astype(float) if "close" in df.columns else np.array([])
        dates_col = df["date"].values if "date" in df.columns else np.arange(len(closes))

        eq = np.array(equity_curve, dtype=float)
        if len(eq) < 2:
            return BacktestResult(strategy_name=name)

        total_return = float((eq[-1] - eq[0]) / eq[0]) if eq[0] > 1e-9 else 0.0
        n_years = max(len(eq) / 252, 1e-6)
        annual_return = (1 + total_return) ** (1 / n_years) - 1 if total_return > -1 else -1.0

        daily_ret = np.diff(eq) / np.where(eq[:-1] > 1e-9, eq[:-1], 1.0)
        std = float(np.std(daily_ret))
        sharpe_ratio = float(np.mean(daily_ret) / std * np.sqrt(252)) if std > 1e-12 else 0.0

        peak_arr = np.maximum.accumulate(eq)
        dd_arr = (peak_arr - eq) / np.where(peak_arr > 1e-9, peak_arr, 1.0)
        max_dd = float(np.max(dd_arr))

        sell_trades = [t for t in trades if t.get("action") == "sell"]
        win_trades = [t for t in sell_trades if t.get("pnl", 0) > 0]
        loss_trades = [t for t in sell_trades if t.get("pnl", 0) <= 0]
        total_trades = len(sell_trades)
        win_rate = len(win_trades) / total_trades if total_trades > 0 else 0.0

        avg_profit = float(np.mean([t["pnl"] for t in win_trades])) if win_trades else 0.0
        avg_loss = abs(float(np.mean([t["pnl"] for t in loss_trades]))) if loss_trades else 0.0
        profit_factor = (avg_profit * len(win_trades)) / (avg_loss * len(loss_trades)) if avg_loss > 1e-9 and loss_trades else (999.0 if win_trades else 0.0)

        avg_hold_days = float(np.mean([t.get("hold_days", 0) for t in sell_trades])) if sell_trades else 0.0

        benchmark_return = float((closes[-1] - closes[0]) / closes[0]) if len(closes) > 0 and closes[0] > 1e-9 else 0.0

        neg_ret = daily_ret[daily_ret < 0]
        downside_dev = float(np.std(neg_ret)) * np.sqrt(252) if len(neg_ret) > 1 else 0.0
        sortino_ratio = annual_return / downside_dev if downside_dev > 1e-9 else 0.0
        calmar_ratio = annual_return / max_dd if max_dd > 1e-9 and annual_return != 0 else 0.0

        return BacktestResult(
            strategy_name=name,
            total_return=total_return,
            annual_return=annual_return,
            sharpe_ratio=round(sharpe_ratio, 4),
            max_drawdown=max_dd,
            win_rate=win_rate,
            profit_factor=round(profit_factor, 2),
            total_trades=total_trades,
            win_trades=len(win_trades),
            loss_trades=len(loss_trades),
            avg_profit=round(avg_profit, 2),
            avg_loss=round(avg_loss, 2),
            avg_hold_days=round(avg_hold_days, 1),
            benchmark_return=round(benchmark_return, 4),
            alpha=round(annual_return - benchmark_return, 4),
            beta=1.0,
            sortino_ratio=round(sortino_ratio, 4),
            calmar_ratio=round(calmar_ratio, 4),
            equity_curve=equity_curve,
            drawdown_curve=(dd_arr * 100).tolist(),
            dates=[str(d)[:10] for d in dates_col[:len(equity_curve)]],
            trades=trades,
            kline_with_signals=[],
        )

    def run_multi(self, strategies: list[BaseStrategy], df: pd.DataFrame) -> dict[str, BacktestResult]:
        results = {}
        for strategy in strategies:
            results[strategy.name] = self.run(strategy, df)
        return results

    def monte_carlo_analysis(self, result: BacktestResult, n_simulations: int = 1000) -> dict:
        sell_trades = [t for t in result.trades if t.get("action") == "sell"]
        if not sell_trades:
            return {"error": "交易样本不足，无法进行蒙特卡洛分析"}

        pnl = np.array([float(t.get("pnl", 0)) for t in sell_trades], dtype=float)
        if len(pnl) < 2:
            return {"error": "交易样本不足，无法进行蒙特卡洛分析"}

        rng = np.random.default_rng(42)
        n_sim = max(1, int(n_simulations))
        n_sample_paths = min(30, n_sim)
        sample_indices = set(rng.choice(n_sim, size=n_sample_paths, replace=False))

        finals = []
        max_dds = []
        sharpes = []
        paths = []
        for sim_idx in range(n_sim):
            sampled = rng.choice(pnl, size=len(pnl), replace=True)
            curve = self._initial_capital + np.cumsum(sampled)
            peak = np.maximum.accumulate(curve)
            dd = np.where(peak > 1e-9, (peak - curve) / peak * 100, 0)
            finals.append(float(curve[-1]))
            max_dds.append(float(np.max(dd)))
            trade_ret = sampled / max(self._initial_capital, 1)
            std = np.std(trade_ret)
            sharpes.append(float(np.mean(trade_ret) / std) if std > 1e-12 else 0.0)
            if sim_idx in sample_indices:
                paths.append((curve / self._initial_capital).tolist())

        final_arr = np.array(finals)
        dd_arr = np.array(max_dds)
        sharpe_arr = np.array(sharpes)
        sim_sharpe_median = float(np.median(sharpe_arr)) if len(sharpe_arr) else 0.0
        robustness = result.sharpe_ratio / sim_sharpe_median if abs(sim_sharpe_median) > 1e-9 else 0.0
        initial = max(self._initial_capital, 1)
        median_final = float(np.percentile(final_arr, 50))
        p5_final = float(np.percentile(final_arr, 5))
        p95_final = float(np.percentile(final_arr, 95))
        ruin_count = int(np.sum(final_arr < initial * 0.5))
        mc_result = {
            "paths": paths,
            "median_return": round((median_final - initial) / initial, 4),
            "p5_return": round((p5_final - initial) / initial, 4),
            "p95_return": round((p95_final - initial) / initial, 4),
            "ruin_prob": round(ruin_count / max(n_sim, 1), 4),
            "final_equity_p5": round(p5_final, 2),
            "final_equity_p50": round(median_final, 2),
            "final_equity_p95": round(p95_final, 2),
            "max_drawdown_p5": round(float(np.percentile(dd_arr, 5)), 2),
            "max_drawdown_p50": round(float(np.percentile(dd_arr, 50)), 2),
            "max_drawdown_p95": round(float(np.percentile(dd_arr, 95)), 2),
            "sharpe_p50": round(sim_sharpe_median, 2),
            "robustness_score": round(float(robustness), 2),
        }
        result.monte_carlo = mc_result
        return mc_result

    def sensitivity_analysis(self, strategy_cls, df: pd.DataFrame,
                             base_params: dict, param_ranges: dict | None = None) -> dict:
        base_params = base_params or {}
        param_ranges = param_ranges or strategy_cls.get_param_space()
        if not param_ranges or df is None or df.empty:
            return {"parameters": {}, "heatmap": [], "recommendation": {}}

        output = {}
        for name, spec in param_ranges.items():
            base_val = base_params.get(name, (spec.get("min", 0) + spec.get("max", 0)) / 2)
            if not isinstance(base_val, (int, float)):
                continue
            low = max(spec.get("min", base_val * 0.8), base_val * 0.8)
            high = min(spec.get("max", base_val * 1.2), base_val * 1.2)
            values = np.linspace(low, high, 5)
            points = []
            sharpes = []
            for value in values:
                params = dict(base_params)
                params[name] = int(round(value)) if isinstance(base_val, int) else round(float(value), 4)
                try:
                    result = self.run(strategy_cls(**params), df)
                    sharpe = float(result.sharpe_ratio)
                except Exception as e:
                    logger.debug("Param scan iteration failed: %s", e)
                    sharpe = 0.0
                sharpes.append(sharpe)
                points.append({"value": params[name], "sharpe_ratio": round(sharpe, 4)})
            param_range = high - low
            elasticity = (max(sharpes) - min(sharpes)) / param_range if sharpes and param_range > 1e-9 else 0.0
            output[name] = {"points": points, "elasticity": round(float(elasticity), 6)}

        heatmap = []
        names = list(output.keys())[:2]
        if len(names) == 2:
            x_name, y_name = names
            x_values = [p["value"] for p in output[x_name]["points"]]
            y_values = [p["value"] for p in output[y_name]["points"]]
            for xv in x_values:
                for yv in y_values:
                    params = dict(base_params)
                    params[x_name] = xv
                    params[y_name] = yv
                    try:
                        result = self.run(strategy_cls(**params), df)
                        sharpe = float(result.sharpe_ratio)
                    except Exception as e:
                        logger.debug("Heatmap scan iteration failed: %s", e)
                        sharpe = 0.0
                    heatmap.append({"x": xv, "y": yv, "sharpe_ratio": round(sharpe, 4)})

        recommendation = {}
        for name, data in output.items():
            points = data.get("points", [])
            if points:
                best = max(points, key=lambda x: x["sharpe_ratio"])
                recommendation[name] = best["value"]
        return {"parameters": output, "heatmap": heatmap, "recommendation": recommendation}

    def parameter_grid_scan(
        self,
        strategy_cls,
        df: pd.DataFrame,
        param_x: str,
        param_y: str,
        x_range: tuple | None = None,
        y_range: tuple | None = None,
        grid_size: int = 7,
        base_params: dict | None = None,
        metric: str = "sharpe_ratio",
    ) -> dict:
        """二维参数网格扫描，生成热图数据

        Args:
            strategy_cls: 策略类
            df: 行情数据
            param_x: X轴参数名
            param_y: Y轴参数名
            x_range: (min, max) 或 None 自动从param_space获取
            y_range: (min, max) 或 None 自动从param_space获取
            grid_size: 每个维度的采样点数
            base_params: 基础参数
            metric: 优化指标 (sharpe_ratio, total_return, max_drawdown, win_rate)
        """
        base_params = base_params or {}
        param_space = strategy_cls.get_param_space() if hasattr(strategy_cls, "get_param_space") else {}

        if x_range is None:
            spec = param_space.get(param_x, {})
            x_min = spec.get("min", 5)
            x_max = spec.get("max", 60)
            x_range = (x_min, x_max)
        if y_range is None:
            spec = param_space.get(param_y, {})
            y_min = spec.get("min", 5)
            y_max = spec.get("max", 60)
            y_range = (y_min, y_max)

        x_base = base_params.get(param_x, (x_range[0] + x_range[1]) / 2)
        y_base = base_params.get(param_y, (y_range[0] + y_range[1]) / 2)
        x_is_int = isinstance(x_base, int)
        y_is_int = isinstance(y_base, int)

        x_values = np.linspace(x_range[0], x_range[1], grid_size)
        y_values = np.linspace(y_range[0], y_range[1], grid_size)
        if x_is_int:
            x_values = np.unique(np.round(x_values).astype(int))
        if y_is_int:
            y_values = np.unique(np.round(y_values).astype(int))

        grid_cells = []
        for xv in x_values:
            for yv in y_values:
                params = dict(base_params)
                params[param_x] = int(round(xv)) if x_is_int else round(float(xv), 4)
                params[param_y] = int(round(yv)) if y_is_int else round(float(yv), 4)
                grid_cells.append((params, param_x, param_y, x_is_int, y_is_int))

        n_workers = min(len(grid_cells), 8)
        heatmap = []

        def _scan_cell(cell: tuple) -> dict:
            params, px, py, xi, yi = cell
            try:
                result = self.run(strategy_cls(**params), df)
                val = getattr(result, metric, 0.0)
                if not np.isfinite(val):
                    val = 0.0
                return {
                    "x": params[px],
                    "y": params[py],
                    metric: round(float(val), 4),
                    "total_return": round(float(result.total_return), 4),
                    "max_drawdown": round(float(result.max_drawdown), 4),
                    "_val": val,
                }
            except InsufficientDataError:
                logger.debug(
                    "Grid scan (%s=%s, %s=%s) skipped: insufficient data",
                    px, params[px], py, params[py],
                )
                return {
                    "x": params[px], "y": params[py],
                    metric: 0.0, "total_return": 0, "max_drawdown": 0, "_val": 0.0,
                }
            except Exception as e:
                logger.debug(
                    "Grid scan (%s=%s, %s=%s) failed: %s",
                    px, params[px], py, params[py], e,
                )
                return {
                    "x": params[px], "y": params[py],
                    metric: 0.0, "total_return": 0, "max_drawdown": 0, "_val": 0.0,
                }

        with ThreadPoolExecutor(max_workers=n_workers) as pool:
            for cell_result in pool.map(_scan_cell, grid_cells):
                clean_result = {k: v for k, v in cell_result.items() if k != "_val"}
                heatmap.append(clean_result)

        best_sharpe = -np.inf
        best_params = {}
        for cell_result in heatmap:
            val = cell_result[metric]
            if val > best_sharpe:
                best_sharpe = val
                best_params = {param_x: cell_result["x"], param_y: cell_result["y"]}

        return {
            "param_x": param_x,
            "param_y": param_y,
            "x_values": [int(v) if x_is_int else round(float(v), 2) for v in x_values],
            "y_values": [int(v) if y_is_int else round(float(v), 2) for v in y_values],
            "metric": metric,
            "heatmap": heatmap,
            "best_params": best_params,
            "best_value": round(float(best_sharpe), 4),
        }

    def parameter_sensitivity(
        self,
        strategy_cls,
        df: pd.DataFrame,
        param_name: str,
        param_range: tuple | None = None,
        num_points: int = 11,
        base_params: dict | None = None,
        metrics: tuple[str, ...] = ("sharpe_ratio", "total_return", "max_drawdown", "win_rate"),
    ) -> dict:
        base_params = base_params or {}
        param_space = strategy_cls.get_param_space() if hasattr(strategy_cls, "get_param_space") else {}

        if param_range is None:
            spec = param_space.get(param_name, {})
            p_min = spec.get("min", 5)
            p_max = spec.get("max", 60)
            param_range = (p_min, p_max)

        p_base = base_params.get(param_name, (param_range[0] + param_range[1]) / 2)
        is_int = isinstance(p_base, int)

        values = np.linspace(param_range[0], param_range[1], num_points)
        if is_int:
            values = np.unique(np.round(values).astype(int))

        results = []
        for v in values:
            params = dict(base_params)
            params[param_name] = int(round(v)) if is_int else round(float(v), 4)
            try:
                r = self.run(strategy_cls(**params), df)
                entry = {"value": params[param_name]}
                for m in metrics:
                    val = getattr(r, m, 0.0)
                    entry[m] = round(float(val), 4) if val is not None and np.isfinite(val) else 0.0
                results.append(entry)
            except Exception as e:
                logger.debug("Sensitivity scan (%s=%s) failed: %s", param_name, params[param_name], e)
                entry = {"value": params[param_name]}
                for m in metrics:
                    entry[m] = 0.0
                results.append(entry)

        if len(results) < 2:
            return {"param_name": param_name, "results": results, "sensitivity": {}, "robustness": {}}

        sensitivity = {}
        robustness = {}
        for m in metrics:
            vals = [r[m] for r in results]
            best_idx = max(range(len(vals)), key=lambda i: vals[i] if m != "max_drawdown" else -vals[i])
            best_val = vals[best_idx]

            deltas = [abs(vals[i + 1] - vals[i]) for i in range(len(vals) - 1)]
            avg_delta = sum(deltas) / len(deltas) if deltas else 0.0
            param_span = values[-1] - values[0] if len(values) > 1 else 1.0
            param_span = max(param_span, 1e-9)
            sensitivity[m] = round(avg_delta / param_span, 6)

            if best_val != 0:
                degradations = [abs(v - best_val) / abs(best_val) for v in vals]
                robustness[m] = round(1.0 - max(degradations), 4)
            else:
                robustness[m] = 0.0

        return {
            "param_name": param_name,
            "param_range": [float(param_range[0]), float(param_range[1])],
            "results": results,
            "sensitivity": sensitivity,
            "robustness": robustness,
        }

    def _build_result(
        self,
        name: str,
        df: pd.DataFrame,
        buy_signals: list,
        sell_signals: list,
        strategy_result: StrategyResult,
        symbol: str = "",
    ) -> BacktestResult:
        closes = df["close"].values.astype(float) if "close" in df.columns else np.array([])
        opens = df["open"].values.astype(float) if "open" in df.columns else closes
        highs = df["high"].values.astype(float) if "high" in df.columns else closes
        lows = df["low"].values.astype(float) if "low" in df.columns else closes
        dates_col = df["date"].values if "date" in df.columns else np.arange(len(closes))

        if len(closes) < 2:
            return BacktestResult(strategy_name=name)

        n = len(closes)
        self._progress_tracker.start(name, n)
        cash = float(self._initial_capital)
        shares = 0
        position = None
        equity_curve = [cash]
        trades = []
        buy_bar_set = set()
        sell_bar_set = set()
        lot_size = 100

        # 预计算ATR用于动态止损
        atr_values = np.zeros(n)
        if n > 14 and len(highs) == n and len(lows) == n:
            tr_arr = np.maximum(
                highs[1:] - lows[1:],
                np.maximum(
                    np.abs(highs[1:] - closes[:-1]),
                    np.abs(lows[1:] - closes[:-1]),
                ),
            )
            tr_arr = np.concatenate([[0], tr_arr])
            cumsum = np.cumsum(tr_arr)
            atr_values[0] = tr_arr[1] if len(tr_arr) > 1 else 0
            window = 14
            for k in range(1, min(window, n)):
                atr_values[k] = cumsum[k] / k
            if n > window:
                atr_values[window:] = (cumsum[window:] - cumsum[:-window]) / window

        buy_idx = 0
        sell_idx = 0

        volumes = df["volume"].values.astype(float) if "volume" in df.columns else None
        amounts_col = df["amount"].values.astype(float) if "amount" in df.columns else None

        prev_closes = np.empty_like(closes)
        prev_closes[0] = closes[0] if len(closes) > 0 else 0
        prev_closes[1:] = closes[:-1]

        for i in range(1, n):
            while buy_idx < len(buy_signals) and buy_signals[buy_idx].bar_index == i:
                sig = buy_signals[buy_idx]
                buy_idx += 1
                if position is not None:
                    continue

                fill_price = opens[i] if i < len(opens) and opens[i] > 0 else closes[i]
                if fill_price <= 0:
                    continue

                fill_price = _simulate_call_auction_fill(fill_price, self._rng)

                if self._enable_limit_check and i > 0:
                    prev_close = prev_closes[i] if i < len(prev_closes) else closes[i - 1]
                    limit_pct = _get_limit_pct(symbol)
                    is_normal, fill_prob = _check_limit_price(float(prev_close), fill_price, is_buy=True, limit_pct=limit_pct)
                    if not is_normal and self._rng.random() > fill_prob:
                        continue

                fill_price = fill_price * (1 + self._slippage_pct)

                if volumes is not None:
                    bar_vol = volumes[i] if i < len(volumes) else 0
                    if np.isnan(bar_vol) or bar_vol <= 0:
                        continue

                alloc_pct = sig.position_pct if sig.position_pct > 0 else 0.3
                if alloc_pct < 0.2:
                    alloc_pct = 0.3
                alloc_amount = equity_curve[-1] * alloc_pct
                if alloc_amount > cash * 0.98:
                    alloc_amount = cash * 0.98

                buy_shares = int(alloc_amount / fill_price / lot_size) * lot_size
                if buy_shares <= 0:
                    continue

                bar_amount = 0.0
                if amounts_col is not None and i < len(amounts_col):
                    bar_amount = float(amounts_col[i]) if not np.isnan(amounts_col[i]) else 0.0
                if bar_amount <= 0 and volumes is not None and i < len(volumes):
                    bar_amount = float(volumes[i]) * fill_price

                if bar_amount > 0:
                    max_shares_by_amount = int(bar_amount * 0.25 / fill_price / lot_size) * lot_size
                    if max_shares_by_amount > 0 and buy_shares > max_shares_by_amount:
                        buy_shares = max_shares_by_amount

                if buy_shares <= 0:
                    continue

                if self._enable_twap and bar_amount > 0:
                    fill_price = _simulate_twap_fill(fill_price, buy_shares, bar_amount, rng=self._rng)

                amount = buy_shares * fill_price
                cost_detail = self._cost_model.calc_buy_cost(fill_price, buy_shares, amount, bar_amount)
                total_cost = amount + cost_detail["total"]

                if total_cost > cash:
                    buy_shares = int(cash * 0.98 / fill_price / lot_size) * lot_size
                    if buy_shares <= 0:
                        continue
                    amount = buy_shares * fill_price
                    cost_detail = self._cost_model.calc_buy_cost(fill_price, buy_shares, amount, bar_amount)
                    total_cost = amount + cost_detail["total"]
                    if total_cost > cash:
                        buy_shares = int((cash - cost_detail["total"]) / fill_price / lot_size) * lot_size
                        if buy_shares <= 0:
                            continue
                        amount = buy_shares * fill_price
                        cost_detail = self._cost_model.calc_buy_cost(fill_price, buy_shares, amount, bar_amount)
                        total_cost = amount + cost_detail["total"]

                cash -= total_cost
                shares = buy_shares

                date_str = str(dates_col[i])[:10] if i < len(dates_col) else ""
                position = {
                    "entry_price": fill_price,
                    "shares": buy_shares,
                    "entry_idx": i,
                    "entry_date": date_str,
                    "stop_loss": sig.stop_loss,
                    "take_profit": sig.take_profit,
                    "highest_price": fill_price,
                }
                buy_bar_set.add(i)

                trades.append({
                    "action": "buy",
                    "symbol": "",
                    "price": fill_price,
                    "shares": buy_shares,
                    "amount": round(amount, 2),
                    "fee": round(cost_detail["total"], 2),
                    "cost_detail": cost_detail,
                    "date": date_str,
                    "bar_index": i,
                    "reason": sig.reason,
                })

            while sell_idx < len(sell_signals) and sell_signals[sell_idx].bar_index == i:
                sig = sell_signals[sell_idx]
                sell_idx += 1
                if position is None:
                    continue

                entry_date = position.get("entry_date", "")
                bar_date = str(dates_col[i])[:10] if i < len(dates_col) else ""
                if entry_date and bar_date and entry_date == bar_date:
                    continue

                fill_price = opens[i] if i < len(opens) and opens[i] > 0 else closes[i]
                if fill_price <= 0:
                    continue

                fill_price = _simulate_call_auction_fill(fill_price, self._rng)

                if self._enable_limit_check and i > 0:
                    prev_close = prev_closes[i] if i < len(prev_closes) else closes[i - 1]
                    limit_pct = _get_limit_pct(symbol)
                    is_normal, fill_prob = _check_limit_price(float(prev_close), fill_price, is_buy=False, limit_pct=limit_pct)
                    if not is_normal and self._rng.random() > fill_prob:
                        continue

                fill_price = fill_price * (1 - self._slippage_pct)

                sell_shares = shares
                bar_amount = 0.0
                if amounts_col is not None and i < len(amounts_col):
                    bar_amount = float(amounts_col[i]) if not np.isnan(amounts_col[i]) else 0.0
                if bar_amount <= 0 and volumes is not None and i < len(volumes):
                    bar_amount = float(volumes[i]) * fill_price

                if bar_amount > 0:
                    max_shares_by_amount = int(bar_amount * 0.25 / fill_price / lot_size) * lot_size
                    if max_shares_by_amount > 0 and sell_shares > max_shares_by_amount:
                        sell_shares = max_shares_by_amount

                if self._enable_twap and bar_amount > 0:
                    fill_price = _simulate_twap_fill(fill_price, sell_shares, bar_amount, rng=self._rng)

                revenue = sell_shares * fill_price
                cost_detail = self._cost_model.calc_sell_cost(fill_price, sell_shares, revenue, bar_amount)
                total_fee = cost_detail["total"]
                net_revenue = revenue - total_fee

                pnl = (fill_price - position["entry_price"]) * sell_shares - total_fee

                cash += net_revenue

                date_str = str(dates_col[i])[:10] if i < len(dates_col) else ""
                hold_days = i - position["entry_idx"]
                mae, mfe = _excursion(position, i, lows, highs, n)

                trades.append({
                    "action": "sell",
                    "symbol": "",
                    "price": fill_price,
                    "shares": sell_shares,
                    "amount": round(revenue, 2),
                    "fee": round(total_fee, 2),
                    "cost_detail": cost_detail,
                    "date": date_str,
                    "bar_index": i,
                    "pnl": round(pnl, 2),
                    "hold_days": hold_days,
                    "mae": mae,
                    "mfe": mfe,
                    "reason": sig.reason,
                })

                sell_bar_set.add(i)
                shares -= sell_shares
                if shares <= 0:
                    shares = 0
                    position = None
                elif position is not None:
                    position["shares"] = shares

            if position is not None:
                bar_low = float(lows[i]) if i < len(lows) else closes[i]
                bar_high = float(highs[i]) if i < len(highs) else closes[i]

                if bar_high > position["highest_price"]:
                    position["highest_price"] = bar_high

                effective_stop = position["stop_loss"]
                if effective_stop <= 0 and i < len(atr_values) and atr_values[i] > 0:
                    effective_stop = position["entry_price"] - 2 * atr_values[i]

                trailing_stop = 0.0
                if i < len(atr_values) and atr_values[i] > 0:
                    trailing_stop = position["highest_price"] - 2 * atr_values[i]

                if trailing_stop > 0:
                    effective_stop = max(effective_stop, trailing_stop)

                exit_reason = None
                exit_price = 0.0
                if effective_stop > 0 and bar_low <= effective_stop:
                    exit_reason = "止损"
                    exit_price = effective_stop * (1 - self._slippage_pct)
                elif position["take_profit"] > 0 and bar_high >= position["take_profit"]:
                    exit_reason = "止盈"
                    exit_price = position["take_profit"] * (1 - self._slippage_pct)

                if exit_reason is not None:
                    revenue = shares * exit_price
                    cost_detail = self._cost_model.calc_sell_cost(exit_price, shares, revenue)
                    total_fee = cost_detail["total"]
                    pnl = (exit_price - position["entry_price"]) * shares - total_fee
                    cash += revenue - total_fee
                    date_str = str(dates_col[i])[:10] if i < len(dates_col) else ""
                    hold_days = i - position["entry_idx"]
                    mae, mfe = _excursion(position, i, lows, highs, n)
                    trades.append({
                        "action": "sell",
                        "symbol": "",
                        "price": exit_price,
                        "shares": shares,
                        "amount": round(revenue, 2),
                        "fee": round(total_fee, 2),
                        "cost_detail": cost_detail,
                        "date": date_str,
                        "bar_index": i,
                        "pnl": round(pnl, 2),
                        "hold_days": hold_days,
                        "mae": mae,
                        "mfe": mfe,
                        "reason": exit_reason,
                    })
                    sell_bar_set.add(i)
                    shares = 0
                    position = None

            bar_equity = cash + (shares * closes[i] if shares > 0 else 0)
            equity_curve.append(bar_equity)
            date_str_progress = str(dates_col[i])[:10] if i < len(dates_col) else ""
            self._progress_tracker.on_bar(i, bar_equity, date_str_progress)

        dates_list = []
        for d in dates_col:
            ds = str(d)[:10] if hasattr(d, "__str__") else str(d)[:10]
            dates_list.append(ds)

        if position is not None and shares > 0:
            close_price = closes[-1] * (1 - self._slippage_pct)
            close_cost_detail = self._cost_model.calc_sell_cost(close_price, shares, shares * close_price)
            close_fee = close_cost_detail["total"]
            cash += shares * close_price - close_fee
            trades.append({
                "date": dates_list[-1] if dates_list else "",
                "action": "sell",
                "price": round(close_price, 4),
                "shares": shares,
                "fee": round(close_fee, 2),
                "pnl": round(shares * close_price - shares * position["entry_price"] - close_fee, 2),
                "reason": "回测结束强平",
            })
            shares = 0
            position = None

        eq_arr = np.array(equity_curve)
        peak_arr = np.maximum.accumulate(eq_arr)
        drawdown_curve = ((peak_arr - eq_arr) / np.where(peak_arr > 1e-9, peak_arr, 1.0) * 100).tolist()
        max_dd = float(np.max(drawdown_curve))

        sell_trades = [t for t in trades if t["action"] == "sell"]
        total_trades = len(sell_trades)
        win_trades = 0
        loss_trades = 0
        total_win = 0.0
        total_loss = 0.0
        win_pnls = []
        loss_pnls = []
        hold_days_list = []
        for t in sell_trades:
            pnl = t.get("pnl", 0)
            if pnl > 0:
                win_trades += 1
                total_win += pnl
                win_pnls.append(pnl)
            elif pnl < 0:
                loss_trades += 1
                total_loss += abs(pnl)
                loss_pnls.append(abs(pnl))
            hd = t.get("hold_days", 0)
            if hd:
                hold_days_list.append(hd)
        win_rate = (win_trades / total_trades * 100) if total_trades > 0 else 0
        profit_factor = (total_win / total_loss) if total_loss > 0 else (999.0 if total_win > 0 else 0.0)
        avg_profit = float(np.mean(win_pnls)) if win_pnls else 0.0
        avg_loss = float(np.mean(loss_pnls)) if loss_pnls else 0.0
        avg_hold_days = float(np.mean(hold_days_list)) if hold_days_list else 0.0

        total_return = (equity_curve[-1] - equity_curve[0]) / equity_curve[0] * 100 if equity_curve[0] > 1e-9 else 0.0
        trading_days = len(equity_curve)
        if trading_days >= 20:
            annual_return = ((1 + total_return / 100) ** min(252 / trading_days, 3) - 1) * 100
        else:
            annual_return = total_return

        calmar_ratio = (annual_return / max_dd) if max_dd > 1e-9 and annual_return != 0 else 0.0

        returns = []
        eq_arr_full = np.array(equity_curve)
        if len(eq_arr_full) > 1:
            mask = eq_arr_full[:-1] > 0
            ret = np.where(mask, (eq_arr_full[1:] - eq_arr_full[:-1]) / eq_arr_full[:-1], 0)
            returns = ret.tolist()

        sharpe = 0
        if returns:
            avg_ret = np.mean(returns)
            std_ret = np.std(returns)
            if std_ret > 0:
                sharpe = avg_ret / std_ret * np.sqrt(252)

        sortino = 0.0
        if returns:
            ret_arr = np.array(returns)
            avg_ret = np.mean(ret_arr)
            downside = ret_arr[ret_arr < 0]
            if len(downside) > 0:
                downside_dev = np.sqrt(np.mean(downside ** 2))
                if downside_dev > 1e-12:
                    sortino = (avg_ret * 252) / (downside_dev * np.sqrt(252))

        max_consec_losses = 0
        consec_count = 0
        for t in sell_trades:
            if t.get("pnl", 0) < 0:
                consec_count += 1
                if consec_count > max_consec_losses:
                    max_consec_losses = consec_count
            else:
                consec_count = 0

        benchmark_return = (closes[-1] - closes[0]) / closes[0] * 100 if len(closes) > 0 and closes[0] > 1e-9 else 0.0
        alpha = total_return - benchmark_return

        bench_returns = []
        for i in range(1, len(closes)):
            if closes[i - 1] > 0:
                bench_returns.append((closes[i] - closes[i - 1]) / closes[i - 1])

        beta = 1.0
        information_ratio = 0.0
        if len(returns) > 1 and len(bench_returns) > 1:
            min_len = min(len(returns), len(bench_returns))
            r = np.array(returns[:min_len])
            b = np.array(bench_returns[:min_len])
            bench_var = np.var(b)
            if bench_var > 0:
                beta = float(np.cov(r, b)[0][1] / bench_var)
            excess = r - b
            tracking_error = np.std(excess)
            if tracking_error > 0:
                information_ratio = float(np.mean(excess) / tracking_error * np.sqrt(252))

        omega_ratio = 0.0
        tail_ratio = 0.0
        if returns:
            ret_arr = np.array(returns, dtype=float)
            ret_arr = ret_arr[np.isfinite(ret_arr)]
            if len(ret_arr) > 0:
                gains = ret_arr[ret_arr > 0].sum()
                losses = abs(ret_arr[ret_arr < 0].sum())
                if losses > 0:
                    omega_ratio = float(gains / losses)
                elif gains > 0:
                    omega_ratio = 999.0
                q95 = float(np.percentile(ret_arr, 95))
                q05 = float(np.percentile(ret_arr, 5))
                tail_ratio = abs(q95 / q05) if abs(q05) > 1e-09 else 0.0

        recovery_factor = (total_return / max_dd) if max_dd > 1e-9 else 0.0
        avg_mae = np.mean([abs(t.get("mae", 0)) for t in sell_trades]) if sell_trades else 0.0
        avg_mfe = np.mean([t.get("mfe", 0) for t in sell_trades]) if sell_trades else 0.0
        win_rate_frac = win_trades / total_trades if total_trades > 0 else 0.0
        loss_rate_frac = loss_trades / total_trades if total_trades > 0 else 0.0
        expectancy = win_rate_frac * avg_profit - loss_rate_frac * avg_loss
        payoff_ratio = (avg_profit / avg_loss) if avg_loss > 1e-9 else (999.0 if avg_profit > 0 else 0.0)

        cvar_95 = 0.0
        var_95 = 0.0
        annual_vol = 0.0
        downside_dev = 0.0
        monthly_rets = []
        if returns:
            ret_arr = np.array(returns, dtype=float)
            ret_arr = ret_arr[np.isfinite(ret_arr)]
            if len(ret_arr) > 1:
                annual_vol = float(np.std(ret_arr) * np.sqrt(252))
                neg_rets = ret_arr[ret_arr < 0]
                if len(neg_rets) > 0:
                    downside_dev = float(np.std(neg_rets) * np.sqrt(252))
                var_5 = float(np.percentile(ret_arr, 5))
                var_95 = -var_5
                tail_5 = ret_arr[ret_arr <= var_5]
                if len(tail_5) > 0:
                    cvar_95 = float(-np.mean(tail_5))
        if len(dates_list) > 20 and len(equity_curve) > 20:
            try:
                eq_arr = np.array(equity_curve, dtype=float)
                eq_dates = list(dates_list)
                monthly_map: dict[str, list[float]] = {}
                for j in range(1, len(eq_arr)):
                    if j >= len(eq_dates):
                        break
                    d = str(eq_dates[j])[:7]
                    if d not in monthly_map:
                        monthly_map[d] = []
                    if eq_arr[j - 1] > 0:
                        monthly_map[d].append((eq_arr[j] / eq_arr[j - 1]) - 1)
                for m in sorted(monthly_map.keys()):
                    vals = monthly_map[m]
                    if vals:
                        monthly_rets.append({"month": m, "return": float(np.mean(vals))})
            except Exception as e:
                logger.debug("Monthly return calculation failed: %s", e)

        kline_with_signals = []
        vols = df["volume"].values.astype(float) if "volume" in df.columns else np.zeros(n)
        for idx in range(n):
            item = {
                "date": dates_list[idx] if idx < len(dates_list) else "",
                "open": float(opens[idx]) if idx < len(opens) else 0,
                "close": float(closes[idx]),
                "high": float(highs[idx]),
                "low": float(lows[idx]),
                "volume": float(vols[idx]),
            }
            if idx in buy_bar_set:
                item["signal"] = "buy"
            elif idx in sell_bar_set:
                item["signal"] = "sell"
            kline_with_signals.append(item)

        result = BacktestResult(
            strategy_name=name,
            total_return=round(total_return, 2),
            annual_return=round(annual_return, 2),
            sharpe_ratio=round(sharpe, 2),
            max_drawdown=round(max_dd, 2),
            calmar_ratio=round(calmar_ratio, 2),
            win_rate=round(win_rate, 2),
            profit_factor=round(profit_factor, 2) if profit_factor != 999 else 999,
            total_trades=total_trades,
            win_trades=win_trades,
            loss_trades=loss_trades,
            avg_profit=round(avg_profit, 2),
            avg_loss=round(avg_loss, 2),
            avg_hold_days=round(avg_hold_days, 1),
            benchmark_return=round(benchmark_return, 2),
            alpha=round(alpha, 2),
            beta=round(beta, 2),
            equity_curve=equity_curve,
            drawdown_curve=drawdown_curve,
            dates=dates_list,
            trades=trades,
            kline_with_signals=kline_with_signals,
            sortino_ratio=round(sortino, 2),
            max_consecutive_losses=max_consec_losses,
            omega_ratio=round(omega_ratio, 2) if omega_ratio != 999.0 else 999.0,
            tail_ratio=round(tail_ratio, 2),
            information_ratio=round(information_ratio, 2),
            recovery_factor=round(recovery_factor, 2),
            avg_mae=round(float(avg_mae), 2),
            avg_mfe=round(float(avg_mfe), 2),
            cvar_95=round(cvar_95, 4),
            var_95=round(var_95, 4),
            annual_volatility=round(annual_vol, 4),
            downside_deviation=round(downside_dev, 4),
            monthly_returns=monthly_rets,
            expectancy=round(float(expectancy), 2),
            payoff_ratio=round(float(payoff_ratio), 2) if payoff_ratio != 999 else 999,
        )
        result.downsample_curves(500)
        self._progress_tracker.complete(result.summary_dict())
        return result


def _get_strategy_min_bars(strategy_name: str, params: dict | None = None) -> int:
    _min_bars = {
        "ma_cross": 30, "dual_ma": 30, "macd": 45, "rsi": 30,
        "supertrend": 25, "kdj": 25, "bollinger": 35, "bollinger_breakout": 35,
        "momentum": 35, "volume_breakout": 35, "multi_factor": 65,
        "adaptive_trend": 70, "mean_reversion_pro": 55, "mean_reversion": 55,
        "vol_squeeze": 45, "volatility_squeeze": 45,
        "ichimoku": 90, "ichimoku_cloud": 90,
        "vwap_deviation": 40, "vwap": 40,
        "order_flow": 30, "order_flow_imbalance": 30,
        "regime_switching": 90, "regime": 90,
        "fractal_breakout": 35, "fractal": 35,
        "wyckoff": 70, "wyckoff_accumulation": 70,
        "elliott_wave": 140, "elliott": 140,
        "market_microstructure": 35, "microstructure": 35,
        "copula": 80, "copula_correlation": 80,
        "quantile": 80, "quantile_regression": 80,
        "rsi_mean_reversion": 30,
        "turtle": 35, "turtle_trading": 35,
        "dual_thrust": 30,
        "atr_channel": 30, "atr_channel_breakout": 30,
        "donchian": 30, "donchian_channel": 30,
        "chande_kroll": 40, "chande_kroll_stop": 40,
        "vw_macd": 50, "volume_weighted_macd": 50,
        "ornstein_uhlenbeck": 60,
        "kaufman_adaptive": 40,
        "garch_volatility": 60,
        "mtf_momentum": 50, "multi_timeframe_momentum": 50,
        "adx_trend": 55, "adx_trend_strength": 55,
        "cmf": 50, "chaikin_money_flow": 50,
        "psar": 25, "parabolic_sar": 25,
        "hurst": 100, "hurst_exponent": 100,
        "pairs": 65, "pairs_trading": 65,
    }
    return _min_bars.get(strategy_name, 30)


def run_backtest(
    symbol: str,
    strategy_name: str = "ma_cross",
    start_date: str = "2024-01-01",
    end_date: str = "2025-12-31",
    initial_capital: float = 1000000,
    params: dict | None = None,
    _df=None,
) -> dict:
    from core.data_fetcher import get_fetcher
    from core.memory_guard import check_and_reclaim_if_needed
    check_and_reclaim_if_needed()

    if strategy_name == "adaptive":
        return _run_adaptive_backtest(symbol, start_date, end_date, initial_capital, params, _df)

    if strategy_name not in STRATEGY_REGISTRY:
        return {"error": f"未知策略: {strategy_name}"}

    strategy_cls = STRATEGY_REGISTRY[strategy_name]
    try:
        strategy = strategy_cls(**(params or {}))
    except (TypeError, ValueError) as e:
        return {"error": f"策略参数错误: {e}"}

    fetcher = get_fetcher()

    try:
        start_dt = datetime.strptime(start_date, "%Y-%m-%d")
        datetime.strptime(end_date, "%Y-%m-%d")
        days_from_now = (datetime.now() - start_dt).days
    except (ValueError, TypeError):
        days_from_now = 370

    hist_period = "all" if days_from_now > 730 or days_from_now > 365 else "1y"

    if _df is not None:
        df = _df.copy()
    else:
        async def _fetch():
            return await fetcher.get_history(symbol, period=hist_period, kline_type="daily", adjust="qfq")

        try:
            try:
                loop = asyncio.get_running_loop()
                df = asyncio.run_coroutine_threadsafe(_fetch(), loop).result(timeout=30)
            except RuntimeError:
                df = asyncio.run(_fetch())
        except Exception as e:
            logger.error("Data fetch failed for %s: %s", symbol, e)
            return {"error": f"获取 {symbol} 数据失败: {e}"}

    if df is None or df.empty:
        return {"error": f"无法获取 {symbol} 的历史数据，请检查股票代码是否正确"}

    min_bars = _get_strategy_min_bars(strategy_name, params)

    if "date" in df.columns:
        df["date"] = pd.to_datetime(df["date"], errors="coerce")
        df = df.dropna(subset=["date"])
        df_full = df.copy()
        if start_date:
            df = df[df["date"] >= start_date]
        if end_date:
            df = df[df["date"] <= end_date]
        df = df.sort_values("date").reset_index(drop=True)
        if len(df) < min_bars and len(df_full) >= min_bars:
            logger.warning("Date range %s~%s only has %s bars, using available data", start_date, end_date, len)
            df = df_full.sort_values("date").reset_index(drop=True)

    if len(df) < min_bars:
        return {"error": f"数据不足：仅有 {len(df)} 个交易日，{strategy_cls.__name__}策略至少需要{min_bars}个交易日，请选择更长的时间段"}

    try:
        engine = BacktestEngine(initial_capital=initial_capital, slippage_pct=0.001, market_impact_pct=0.0005)
        result = engine.run(strategy, df)
        try:
            from core.metrics import metrics
            metrics.increment("backtest_runs", tags={"strategy": strategy_name})
            metrics.gauge("backtest_sharpe", result.sharpe_ratio, tags={"strategy": strategy_name})
        except Exception as e:
            logger.debug("Metrics reporting failed: %s", e)
    except Exception as e:
        logger.error("Backtest engine failed for %s with %s: %s", symbol, strategy_name, e)
        return {"error": f"回测执行失败: {e}"}

    if not result.dates or not result.equity_curve:
        return {"error": "回测未产生有效结果，请尝试更长的回测时间段"}

    closes_raw = df["close"].values.astype(float)
    date_close_map = {}
    if "date" in df.columns:
        ds_arr = df["date"].dt.strftime("%Y-%m-%d").values if hasattr(df["date"].dt, "strftime") else [str(d)[:10] for d in df["date"].values]
        close_arr = df["close"].values.astype(float)
        for j in range(len(ds_arr)):
            date_close_map[ds_arr[j]] = float(close_arr[j])

    first_close = float(closes_raw[0]) if closes_raw[0] > 0 else 1.0
    benchmark_curve = []
    for i in range(len(result.dates)):
        d = result.dates[i]
        close_val = date_close_map.get(d)
        if close_val is None:
            if i < len(closes_raw):
                close_val = float(closes_raw[i])
            else:
                continue
        benchmark_curve.append({"date": d, "value": initial_capital * (close_val / first_close)})

    result_dict = result.to_dict()
    result_dict["slippage_model"] = "fixed_pct"
    result_dict["benchmark_curve"] = benchmark_curve[-500:] if benchmark_curve else []
    return result_dict


def _run_adaptive_backtest(
    symbol: str,
    start_date: str = "2024-01-01",
    end_date: str = "2025-12-31",
    initial_capital: float = 1000000,
    params: dict | None = None,
    _df=None,
) -> dict:
    from core.adaptive_strategy import AdaptiveStrategyEngine

    if _df is not None:
        df = _df.copy()
    else:
        from core.data_fetcher import get_fetcher
        fetcher = get_fetcher()

        try:
            start_dt = datetime.strptime(start_date, "%Y-%m-%d")
            days_from_now = (datetime.now() - start_dt).days
        except (ValueError, TypeError):
            days_from_now = 370

        hist_period = "all" if days_from_now > 365 else "1y"

        import asyncio

        async def _fetch():
            return await fetcher.get_history(symbol, period=hist_period, kline_type="daily", adjust="qfq")

        try:
            try:
                loop = asyncio.get_running_loop()
                df = asyncio.run_coroutine_threadsafe(_fetch(), loop).result(timeout=30)
            except RuntimeError:
                df = asyncio.run(_fetch())
        except Exception as e:
            logger.error("Data fetch failed for %s: %s", symbol, e)
            return {"error": f"获取 {symbol} 数据失败: {e}"}

    if df is None or df.empty:
        return {"error": f"无法获取 {symbol} 的历史数据"}

    if "date" in df.columns:
        df["date"] = pd.to_datetime(df["date"], errors="coerce")
        df = df.dropna(subset=["date"])
        df_full = df.copy()
        if start_date:
            df = df[df["date"] >= start_date]
        if end_date:
            df = df[df["date"] <= end_date]
        df = df.sort_values("date").reset_index(drop=True)
        if len(df) < 40 and len(df_full) >= 40:
            logger.warning("Adaptive: Date range %s~%s only has %s bars, using available data", start_date, end_date, len)
            df = df_full.sort_values("date").reset_index(drop=True)

    if len(df) < 40:
        return {"error": f"数据不足：自适应策略至少需要40个交易日，当前仅{len(df)}个"}

    try:
        engine = AdaptiveStrategyEngine(initial_capital=initial_capital)
        result = engine.run(df)
    except Exception as e:
        logger.error("Adaptive backtest failed for %s: %s", symbol, e)
        return {"error": f"自适应回测执行失败: {e}"}

    if not result.get("equity_curve"):
        return {"error": "回测未产生有效结果，请尝试更长的回测时间段"}

    equity_curve = result.get("equity_curve", [])
    benchmark_curve = result.get("benchmark_curve", [])

    if equity_curve and isinstance(equity_curve[0], dict):
        equity_curve = [
            {"date": str(e.get("date", "")), "value": float(e.get("value", 0))}
            for e in equity_curve if isinstance(e, dict)
        ]
    else:
        dates_list = result.get("dates", [])
        ec_raw = equity_curve
        bc_raw = benchmark_curve
        equity_curve = []
        for i in range(min(len(dates_list), len(ec_raw))):
            equity_curve.append({"date": str(dates_list[i]), "value": float(ec_raw[i])})

    if benchmark_curve and isinstance(benchmark_curve[0], dict):
        benchmark_curve = [
            {"date": str(b.get("date", "")), "value": float(b.get("value", 0))}
            for b in benchmark_curve if isinstance(b, dict)
        ]
    else:
        dates_list = result.get("dates", [])
        bc_raw = result.get("benchmark_curve", [])
        benchmark_curve = []
        for i in range(min(len(dates_list), len(bc_raw))):
            benchmark_curve.append({"date": str(dates_list[i]), "value": float(bc_raw[i])})

    return {
        "strategy_name": result.get("strategy_name", "自适应量化策略引擎"),
        "total_return": result.get("total_return", 0),
        "annual_return": result.get("annual_return", 0),
        "max_drawdown": result.get("max_drawdown", 0),
        "sharpe_ratio": result.get("sharpe_ratio", 0),
        "sortino_ratio": result.get("sortino_ratio", 0),
        "calmar_ratio": result.get("calmar_ratio", 0),
        "win_rate": result.get("win_rate", 0),
        "profit_factor": result.get("profit_factor", 0),
        "total_trades": result.get("total_trades", 0),
        "win_trades": result.get("win_trades", 0),
        "loss_trades": result.get("loss_trades", 0),
        "avg_profit": result.get("avg_profit", 0),
        "avg_loss": result.get("avg_loss", 0),
        "avg_hold_days": result.get("avg_hold_days", 0),
        "max_consecutive_losses": result.get("max_consecutive_losses", 0),
        "omega_ratio": result.get("omega_ratio", 0),
        "tail_ratio": result.get("tail_ratio", 0),
        "information_ratio": result.get("information_ratio", 0),
        "recovery_factor": result.get("recovery_factor", 0),
        "expectancy": result.get("expectancy", 0),
        "payoff_ratio": result.get("payoff_ratio", 0),
        "benchmark_return": result.get("benchmark_return", 0),
        "alpha": result.get("alpha", 0),
        "beta": result.get("beta", 1),
        "cvar_95": result.get("cvar_95", 0),
        "var_95": result.get("var_95", 0),
        "annual_volatility": result.get("annual_volatility", 0),
        "downside_deviation": result.get("downside_deviation", 0),
        "equity_curve": equity_curve,
        "benchmark_curve": benchmark_curve,
        "trades": result.get("trades", []),
        "kline_with_signals": result.get("kline_with_signals", []),
        "market_regime_labels": result.get("market_regime_labels", []),
        "strategy_allocation": result.get("strategy_allocation", []),
    }


def grid_search_params(strategy_cls, df, max_combinations: int = 50) -> list:
    import random
    param_space = strategy_cls.get_param_space()
    if not param_space:
        return []

    param_names = list(param_space.keys())
    param_values_list = []
    for name in param_names:
        spec = param_space[name]
        vals = []
        v = spec["min"]
        while v <= spec["max"]:
            vals.append(v)
            v += spec["step"]
        param_values_list.append(vals)

    from itertools import product
    all_combos = list(product(*param_values_list))

    if len(all_combos) > max_combinations:
        all_combos = random.sample(all_combos, max_combinations)

    results = []
    for combo in all_combos:
        params = dict(zip(param_names, combo, strict=False))
        try:
            bt_result = run_backtest(
                symbol="grid_search",
                strategy_name=strategy_cls.__name__,
                initial_capital=1000000,
                params=params,
                _df=df,
            )
        except Exception as e:
            logger.debug("Grid search iteration failed: %s", e)
            continue

        if "error" in bt_result:
            continue

        results.append({
            "params": params,
            "sharpe_ratio": bt_result.get("sharpe_ratio", 0),
            "total_return": bt_result.get("total_return", 0),
            "max_drawdown": bt_result.get("max_drawdown", 0),
        })

    results.sort(key=lambda x: x["sharpe_ratio"], reverse=True)
    return results[:10]


def run_walk_forward(
    symbol: str,
    strategy_name: str = "ma_cross",
    start_date: str = "2024-01-01",
    end_date: str = "2025-12-31",
    train_days: int = 252,
    test_days: int = 63,
    initial_capital: float = 1000000,
    params: dict | None = None,
) -> dict:
    import asyncio

    from core.data_fetcher import get_fetcher

    fetcher = get_fetcher()

    async def _fetch_df():
        return await fetcher.get_history(symbol, period="all", kline_type="daily", adjust="qfq")

    try:
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            loop = None

        if loop and loop.is_running():
            import concurrent.futures
            with concurrent.futures.ThreadPoolExecutor() as pool:
                df = pool.submit(asyncio.run, _fetch_df()).result(timeout=30)
        else:
            df = asyncio.run(_fetch_df())
    except Exception as e:
        logger.error("Walk-forward data fetch failed for %s: %s", symbol, e)
        return {"error": f"获取数据失败: {e}"}

    if df is None or df.empty:
        return {"error": f"无法获取 {symbol} 的历史数据"}

    if "date" in df.columns:
        df["date"] = pd.to_datetime(df["date"], errors="coerce")
        df = df.dropna(subset=["date"])
        df = df.sort_values("date").reset_index(drop=True)

    start_dt = pd.Timestamp(start_date)
    end_dt = pd.Timestamp(end_date)
    df = df[(df["date"] >= start_dt) & (df["date"] <= end_dt)].reset_index(drop=True)

    if len(df) < train_days + test_days:
        return {"error": f"数据不足：至少需要{train_days + test_days}个交易日，当前仅{len(df)}个"}

    windows = []
    i = 0
    while i + train_days + test_days <= len(df):
        train_df = df.iloc[i:i + train_days]
        test_df = df.iloc[i + train_days:i + train_days + test_days]

        train_start = str(train_df["date"].iloc[0])[:10]
        train_end = str(train_df["date"].iloc[-1])[:10]
        test_start = str(test_df["date"].iloc[0])[:10]
        test_end = str(test_df["date"].iloc[-1])[:10]

        bt_result = run_backtest(
            symbol=symbol,
            strategy_name=strategy_name,
            start_date=test_start,
            end_date=test_end,
            initial_capital=initial_capital,
            params=params,
            _df=test_df,
        )

        metrics = {}
        if "error" not in bt_result:
            metrics = {
                "sharpe_ratio": bt_result.get("sharpe_ratio", 0),
                "total_return": bt_result.get("total_return", 0),
                "max_drawdown": bt_result.get("max_drawdown", 0),
            }
        else:
            metrics = {"sharpe_ratio": 0, "total_return": 0, "max_drawdown": 0}

        windows.append({
            "train_start": train_start,
            "train_end": train_end,
            "test_start": test_start,
            "test_end": test_end,
            "metrics": metrics,
        })

        i += test_days

    if not windows:
        return {"error": "无法生成有效的滚动窗口"}

    test_sharpes = [w["metrics"]["sharpe_ratio"] for w in windows]
    test_returns = [w["metrics"]["total_return"] for w in windows]
    profitable_count = sum(1 for r in test_returns if r > 0)

    return {
        "windows": windows,
        "avg_test_sharpe": round(float(np.mean(test_sharpes)), 4) if test_sharpes else 0,
        "avg_test_return": round(float(np.mean(test_returns)), 4) if test_returns else 0,
        "consistency_rate": round(profitable_count / len(windows), 4) if windows else 0,
    }


def walk_forward_oos_validation(
    strategy_cls,
    df: pd.DataFrame,
    train_days: int = 252,
    test_days: int = 63,
    initial_capital: float = 1000000,
    param_grid: dict | None = None,
) -> dict:
    """Walk-Forward Out-of-Sample验证引擎

    在每个训练窗口优化参数，在测试窗口验证，计算过拟合比和参数稳定性。

    Args:
        strategy_cls: 策略类
        df: 行情数据
        train_days: 训练窗口天数
        test_days: 测试窗口天数
        initial_capital: 初始资金
        param_grid: 参数搜索空间，如 {"short_period": [5,10,15], "long_period": [20,30,40]}

    Returns:
        包含IS/OOS对比、过拟合比、参数稳定性的完整验证报告
    """
    if df is None or len(df) < train_days + test_days:
        return {"error": f"数据不足：至少需要{train_days + test_days}个交易日"}

    if "date" in df.columns:
        df = df.copy()
        df["date"] = pd.to_datetime(df["date"], errors="coerce")
        df = df.dropna(subset=["date"])
        df = df.sort_values("date").reset_index(drop=True)

    if param_grid is None:
        param_grid = strategy_cls.get_param_space() if hasattr(strategy_cls, "get_param_space") else {}

    windows = []
    i = 0
    while i + train_days + test_days <= len(df):
        train_df = df.iloc[i:i + train_days]
        test_df = df.iloc[i + train_days:i + train_days + test_days]

        train_start = str(train_df["date"].iloc[0])[:10]
        train_end = str(train_df["date"].iloc[-1])[:10]
        test_start = str(test_df["date"].iloc[0])[:10]
        test_end = str(test_df["date"].iloc[-1])[:10]

        engine = BacktestEngine(initial_capital=initial_capital)

        best_is_sharpe = -np.inf
        best_params = {}
        best_is_result = None

        if param_grid:
            param_names = list(param_grid.keys())
            param_values = list(param_grid.values())
            if all(isinstance(v, list) for v in param_values):
                from itertools import product
                for combo in product(*param_values):
                    p = dict(zip(param_names, combo, strict=False))
                    try:
                        r = engine.run(strategy_cls(**p), train_df)
                        if r.sharpe_ratio > best_is_sharpe:
                            best_is_sharpe = r.sharpe_ratio
                            best_params = p
                            best_is_result = r
                    except Exception as e:
                        logger.debug("参数组合回测失败: %s, %s", p, e)
                        continue

        if not best_params:
            try:
                best_is_result = engine.run(strategy_cls(), train_df)
                best_is_sharpe = best_is_result.sharpe_ratio
            except Exception as e:
                logger.debug("默认参数回测失败: %s", e)
                best_is_sharpe = 0

        oos_result = None
        try:
            oos_result = engine.run(strategy_cls(**best_params), test_df)
            oos_sharpe = oos_result.sharpe_ratio
            oos_return = oos_result.total_return
            oos_max_dd = oos_result.max_drawdown
        except Exception as e:
            logger.debug("样本外回测失败: %s", e)
            oos_sharpe = 0
            oos_return = 0
            oos_max_dd = 0

        is_sharpe = best_is_sharpe if np.isfinite(best_is_sharpe) else 0
        is_return = best_is_result.total_return if best_is_result else 0

        degradation = 0.0
        if abs(is_sharpe) > 1e-9:
            degradation = (is_sharpe - oos_sharpe) / abs(is_sharpe)
        degradation = max(0, degradation)

        windows.append({
            "train_start": train_start,
            "train_end": train_end,
            "test_start": test_start,
            "test_end": test_end,
            "best_params": best_params,
            "is_sharpe": round(float(is_sharpe), 4),
            "is_return": round(float(is_return), 4),
            "oos_sharpe": round(float(oos_sharpe), 4),
            "oos_return": round(float(oos_return), 4),
            "oos_max_drawdown": round(float(oos_max_dd), 4),
            "degradation": round(float(degradation), 4),
        })

        i += test_days

    if not windows:
        return {"error": "无法生成有效的滚动窗口"}

    is_sharpes = [w["is_sharpe"] for w in windows]
    oos_sharpes = [w["oos_sharpe"] for w in windows]
    oos_returns = [w["oos_return"] for w in windows]
    degradations = [w["degradation"] for w in windows]

    avg_is_sharpe = float(np.mean(is_sharpes))
    avg_oos_sharpe = float(np.mean(oos_sharpes))
    avg_degradation = float(np.mean(degradations))

    overfitting_ratio = 0.0
    if abs(avg_is_sharpe) > 1e-9:
        overfitting_ratio = (avg_is_sharpe - avg_oos_sharpe) / abs(avg_is_sharpe)
    overfitting_ratio = max(0.0, overfitting_ratio)

    profitable_count = sum(1 for r in oos_returns if r > 0)
    consistency = profitable_count / len(windows) if windows else 0

    param_stability = {}
    if param_grid:
        for pname in param_grid:
            vals = [w["best_params"].get(pname) for w in windows if pname in w["best_params"]]
            if vals and len(vals) > 1:
                unique_vals = len(set(vals))
                param_stability[pname] = {
                    "unique_values": unique_vals,
                    "stability_ratio": round(1.0 - (unique_vals - 1) / len(vals), 4),
                    "values": vals,
                }

    return {
        "windows": windows,
        "summary": {
            "avg_is_sharpe": round(avg_is_sharpe, 4),
            "avg_oos_sharpe": round(avg_oos_sharpe, 4),
            "avg_oos_return": round(float(np.mean(oos_returns)), 4),
            "overfitting_ratio": round(overfitting_ratio, 4),
            "avg_degradation": round(avg_degradation, 4),
            "consistency_rate": round(consistency, 4),
            "n_windows": len(windows),
        },
        "param_stability": param_stability,
        "verdict": (
            "robust" if overfitting_ratio < 0.3 and consistency > 0.6 else
            "moderate" if overfitting_ratio < 0.5 and consistency > 0.4 else
            "overfit"
        ),
    }


def _run_single_backtest(args: tuple) -> dict:
    strategy_name, strategy_cls_name, params, df_dict, symbol, initial_capital = args
    strategy_cls = STRATEGY_REGISTRY.get(strategy_cls_name)
    if strategy_cls is None:
        return {"strategy": strategy_name, "error": f"Unknown strategy: {strategy_cls_name}"}
    try:
        strat = strategy_cls(**(params or {}))
        df = pd.DataFrame(df_dict)
        engine = BacktestEngine(initial_capital=initial_capital)
        result = engine.run(strat, df, symbol=symbol)
        sell_trades = [t for t in result.trades if t.get("action") == "sell"]
        total_trades = len(sell_trades)
        win_trades = sum(1 for t in sell_trades if t.get("pnl", 0) > 0)
        return {
            "strategy": strategy_name,
            "total_return": round(result.total_return, 4),
            "sharpe_ratio": round(result.sharpe_ratio, 4),
            "max_drawdown": round(result.max_drawdown, 4),
            "win_rate": round(win_trades / total_trades, 4) if total_trades > 0 else 0.0,
            "total_trades": total_trades,
        }
    except Exception as e:
        return {"strategy": strategy_name, "error": str(e)}


def run_parallel_backtest(
    strategies: list[dict],
    df: pd.DataFrame,
    symbol: str = "",
    initial_capital: float = 1000000,
    max_workers: int = 0,
) -> list[dict]:
    import multiprocessing as mp

    from core.memory_guard import (
        MemoryGuard,
        check_and_reclaim_if_needed,
        get_memory_usage,
        is_memory_critical,
        is_memory_pressure,
    )

    mem_info = get_memory_usage()
    logger.info("并行回测启动 - 内存状态: RSS=%.0fMB, 系统使用率=%.1f%%",
                mem_info.get('rss_mb', 0), mem_info.get('system_used_pct', 0))

    if is_memory_critical():
        max_workers = 1
        logger.warning("内存临界状态，回退至单线程回测")
    elif is_memory_pressure():
        max_workers = min(max_workers if max_workers > 0 else 2, 2)
        logger.warning("内存压力较高，限制并行度为 %s", max_workers)
        check_and_reclaim_if_needed()

    if max_workers <= 0:
        cpu_count = mp.cpu_count() or 4
        mem_factor = min(1.0, (100 - mem_info.get('system_used_pct', 50)) / 60)
        max_workers = max(1, int(min(cpu_count, 4) * mem_factor))

    df_dict = df.to_dict("list")
    args_list = []
    for s in strategies:
        name = s.get("name", "")
        cls_name = s.get("class_name", name)
        params = s.get("params", {})
        args_list.append((name, cls_name, params, df_dict, symbol, initial_capital))

    if len(args_list) <= 2 or max_workers <= 1:
        results = []
        for i, args in enumerate(args_list):
            if i > 0 and i % 3 == 0:
                check_and_reclaim_if_needed()
            results.append(_run_single_backtest(args))
        return results

    try:
        with MemoryGuard("并行回测", max_mb=12000), mp.Pool(processes=max_workers) as pool:
            results = pool.map(_run_single_backtest, args_list)
        return results
    except MemoryError as e:
        logger.error("并行回测内存不足: %s", e)
        check_and_reclaim_if_needed()
        return [_run_single_backtest(a) for a in args_list]
    except Exception as e:
        logger.warning("Parallel backtest failed, falling back to sequential: %s", e)
        return [_run_single_backtest(a) for a in args_list]


def compare_results(results: list[BacktestResult]) -> dict:
    """对比多个回测结果，返回排名和对比数据"""
    if not results:
        return {"error": "no results to compare"}

    metrics = [
        ("total_return", "总收益率", True),
        ("annual_return", "年化收益率", True),
        ("sharpe_ratio", "夏普比率", True),
        ("max_drawdown", "最大回撤", False),
        ("win_rate", "胜率", True),
        ("profit_factor", "盈亏比", True),
        ("calmar_ratio", "卡尔马比率", True),
        ("sortino_ratio", "索提诺比率", True),
        ("total_trades", "交易次数", True),
        ("avg_hold_days", "平均持仓天数", False),
        ("expectancy", "期望值", True),
        ("payoff_ratio", "赔率", True),
    ]

    comparison = []
    for r in results:
        entry = {"strategy_name": r.strategy_name}
        for metric_key, _, _ in metrics:
            entry[metric_key] = getattr(r, metric_key, 0.0)
        comparison.append(entry)

    # 综合排名：对每个指标排名后加权
    ranks = {r.strategy_name: 0.0 for r in results}
    weights = {
        "total_return": 0.20, "sharpe_ratio": 0.25, "max_drawdown": 0.15,
        "win_rate": 0.10, "profit_factor": 0.10, "calmar_ratio": 0.10,
        "sortino_ratio": 0.10,
    }

    for metric_key, _, higher_is_better in metrics:
        if metric_key not in weights:
            continue
        values = [(r.strategy_name, getattr(r, metric_key, 0.0)) for r in results]
        values.sort(key=lambda x: x[1], reverse=higher_is_better)
        for rank, (name, _) in enumerate(values):
            ranks[name] += (len(values) - rank) * weights[metric_key]

    ranked = sorted(ranks.items(), key=lambda x: x[1], reverse=True)
    final_ranking = [{"rank": i + 1, "strategy_name": name, "score": round(score, 4)}
                     for i, (name, score) in enumerate(ranked)]

    return {
        "comparison": comparison,
        "ranking": final_ranking,
        "metrics": [{"key": k, "label": label} for k, label, _ in metrics],
    }
