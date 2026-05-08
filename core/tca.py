import logging
from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any

import numpy as np

logger = logging.getLogger(__name__)


class Side(StrEnum):
    BUY = "buy"
    SELL = "sell"


@dataclass
class TradeAnalysis:
    symbol: str
    strategy_name: str
    side: Side
    decision_price: float
    arrival_price: float
    execution_price: float
    vwap_benchmark: float
    twap_benchmark: float
    quantity: int
    execution_timestamp: str

    @property
    def implementation_shortfall(self) -> float:
        if self.decision_price == 0:
            return 0.0
        if self.side == Side.BUY:
            return (self.execution_price - self.decision_price) / self.decision_price
        return (self.decision_price - self.execution_price) / self.decision_price

    @property
    def market_impact(self) -> float:
        if self.arrival_price == 0:
            return 0.0
        if self.side == Side.BUY:
            return (self.execution_price - self.arrival_price) / self.arrival_price
        return (self.arrival_price - self.execution_price) / self.arrival_price

    @property
    def timing_cost(self) -> float:
        if self.decision_price == 0:
            return 0.0
        if self.side == Side.BUY:
            return (self.arrival_price - self.decision_price) / self.decision_price
        return (self.decision_price - self.arrival_price) / self.decision_price

    @property
    def vwap_slippage(self) -> float:
        if self.vwap_benchmark == 0:
            return 0.0
        if self.side == Side.BUY:
            return (self.execution_price - self.vwap_benchmark) / self.vwap_benchmark
        return (self.vwap_benchmark - self.execution_price) / self.vwap_benchmark

    @property
    def twap_slippage(self) -> float:
        if self.twap_benchmark == 0:
            return 0.0
        if self.side == Side.BUY:
            return (self.execution_price - self.twap_benchmark) / self.twap_benchmark
        return (self.twap_benchmark - self.execution_price) / self.twap_benchmark

    @property
    def total_cost(self) -> float:
        return self.implementation_shortfall * self.execution_price * self.quantity


@dataclass
class CostAttribution:
    dimension: str
    bucket: str
    avg_implementation_shortfall: float
    avg_market_impact: float
    avg_vwap_slippage: float
    trade_count: int
    total_cost: float


@dataclass
class TCABatchResult:
    total_trades: int
    total_cost: float
    avg_implementation_shortfall: float
    avg_market_impact: float
    avg_vwap_slippage: float
    cost_breakdown: dict[str, float] = field(default_factory=dict)


@dataclass
class TCAReport:
    date: str
    total_trades: int
    total_cost_bps: float
    strategy_breakdown: list[CostAttribution] = field(default_factory=list)
    market_cap_breakdown: list[CostAttribution] = field(default_factory=list)
    time_breakdown: list[CostAttribution] = field(default_factory=list)
    liquidity_breakdown: list[CostAttribution] = field(default_factory=list)


@dataclass
class ExecutionRecommendation:
    symbol: str
    recommended_algorithm: str
    recommended_time_window: str
    recommended_slice_count: int
    estimated_cost_bps: float


_MARK_CAP_THRESHOLDS: dict[str, tuple[float, float]] = {
    "large_cap": (10_000_000_000, float("inf")),
    "mid_cap": (2_000_000_000, 10_000_000_000),
    "small_cap": (0, 2_000_000_000),
}

_TIME_SESSIONS: list[tuple[str, str, str]] = [
    ("09:30-10:00", "09:30", "10:00"),
    ("10:00-11:00", "10:00", "11:00"),
    ("11:00-12:00", "11:00", "12:00"),
    ("12:00-13:00", "12:00", "13:00"),
    ("13:00-14:00", "13:00", "14:00"),
    ("14:00-15:00", "14:00", "15:00"),
    ("15:00-16:00", "15:00", "16:00"),
]

_LIQUIDITY_BUCKETS: list[tuple[str, float, float]] = [
    ("high_liquidity", 0.75, float("inf")),
    ("medium_liquidity", 0.25, 0.75),
    ("low_liquidity", 0.0, 0.25),
]


def _classify_market_cap(market_cap: float) -> str:
    for bucket, (low, high) in _MARK_CAP_THRESHOLDS.items():
        if low <= market_cap < high:
            return bucket
    return "small_cap"


def _classify_time_period(timestamp: str) -> str:
    time_part = timestamp.split(" ")[-1] if " " in timestamp else timestamp
    for label, start, end in _TIME_SESSIONS:
        if start <= time_part < end:
            return label
    return _TIME_SESSIONS[-1][0]


def _classify_liquidity(adv_percentile: float) -> str:
    for label, low, high in _LIQUIDITY_BUCKETS:
        if low <= adv_percentile < high:
            return label
    return "low_liquidity"


def _aggregate_trades(
    trades: list[TradeAnalysis],
    dimension: str,
    key_fn: Any,
) -> list[CostAttribution]:
    buckets: dict[str, list[TradeAnalysis]] = {}
    for trade in trades:
        bucket_key = key_fn(trade)
        buckets.setdefault(bucket_key, []).append(trade)

    results: list[CostAttribution] = []
    for bucket_key, bucket_trades in buckets.items():
        n = len(bucket_trades)
        is_vals = [t.implementation_shortfall for t in bucket_trades]
        mi_vals = [t.market_impact for t in bucket_trades]
        vs_vals = [t.vwap_slippage for t in bucket_trades]
        total = sum(t.total_cost for t in bucket_trades)
        results.append(CostAttribution(
            dimension=dimension,
            bucket=bucket_key,
            avg_implementation_shortfall=float(np.mean(is_vals)) if n else 0.0,
            avg_market_impact=float(np.mean(mi_vals)) if n else 0.0,
            avg_vwap_slippage=float(np.mean(vs_vals)) if n else 0.0,
            trade_count=n,
            total_cost=round(total, 4),
        ))
    return results


class TCAEngine:
    def __init__(
        self,
        market_caps: dict[str, float] | None = None,
        adv_percentiles: dict[str, float] | None = None,
    ) -> None:
        self._market_caps = market_caps or {}
        self._adv_percentiles = adv_percentiles or {}

    def analyze_trade(self, trade: TradeAnalysis) -> dict[str, float]:
        return {
            "implementation_shortfall": trade.implementation_shortfall,
            "market_impact": trade.market_impact,
            "timing_cost": trade.timing_cost,
            "vwap_slippage": trade.vwap_slippage,
            "twap_slippage": trade.twap_slippage,
            "total_cost": trade.total_cost,
        }

    def analyze_batch(self, trades: list[TradeAnalysis]) -> TCABatchResult:
        if not trades:
            return TCABatchResult(
                total_trades=0,
                total_cost=0.0,
                avg_implementation_shortfall=0.0,
                avg_market_impact=0.0,
                avg_vwap_slippage=0.0,
            )

        is_vals = np.array([t.implementation_shortfall for t in trades])
        mi_vals = np.array([t.market_impact for t in trades])
        vs_vals = np.array([t.vwap_slippage for t in trades])
        total = sum(t.total_cost for t in trades)

        breakdown = {
            "implementation_shortfall_total": float(np.sum(is_vals)),
            "market_impact_total": float(np.sum(mi_vals)),
            "vwap_slippage_total": float(np.sum(vs_vals)),
        }

        return TCABatchResult(
            total_trades=len(trades),
            total_cost=round(total, 4),
            avg_implementation_shortfall=round(float(np.mean(is_vals)), 8),
            avg_market_impact=round(float(np.mean(mi_vals)), 8),
            avg_vwap_slippage=round(float(np.mean(vs_vals)), 8),
            cost_breakdown=breakdown,
        )

    def attribute_by_strategy(self, trades: list[TradeAnalysis]) -> list[CostAttribution]:
        return _aggregate_trades(trades, "strategy", lambda t: t.strategy_name)

    def attribute_by_market_cap(self, trades: list[TradeAnalysis]) -> list[CostAttribution]:
        return _aggregate_trades(
            trades,
            "market_cap_bucket",
            lambda t: _classify_market_cap(self._market_caps.get(t.symbol, 0)),
        )

    def attribute_by_time_period(self, trades: list[TradeAnalysis]) -> list[CostAttribution]:
        return _aggregate_trades(
            trades,
            "time_period",
            lambda t: _classify_time_period(t.execution_timestamp),
        )

    def attribute_by_liquidity(self, trades: list[TradeAnalysis]) -> list[CostAttribution]:
        return _aggregate_trades(
            trades,
            "liquidity_bucket",
            lambda t: _classify_liquidity(self._adv_percentiles.get(t.symbol, 0)),
        )

    def generate_daily_report(
        self,
        trades: list[TradeAnalysis],
        date: str,
    ) -> TCAReport:
        if not trades:
            return TCAReport(date=date, total_trades=0, total_cost_bps=0.0)

        total_notional = sum(t.execution_price * t.quantity for t in trades)
        total_cost = sum(t.total_cost for t in trades)
        cost_bps = (total_cost / total_notional * 10_000) if total_notional > 0 else 0.0

        return TCAReport(
            date=date,
            total_trades=len(trades),
            total_cost_bps=round(cost_bps, 4),
            strategy_breakdown=self.attribute_by_strategy(trades),
            market_cap_breakdown=self.attribute_by_market_cap(trades),
            time_breakdown=self.attribute_by_time_period(trades),
            liquidity_breakdown=self.attribute_by_liquidity(trades),
        )

    def recommend_optimal_execution(
        self,
        symbol: str,
        historical_trades: list[TradeAnalysis],
    ) -> ExecutionRecommendation:
        symbol_trades = [t for t in historical_trades if t.symbol == symbol]

        if not symbol_trades:
            logger.warning("No historical trades for symbol=%s, defaulting to VWAP", symbol)
            return ExecutionRecommendation(
                symbol=symbol,
                recommended_algorithm="VWAP",
                recommended_time_window="09:30-15:00",
                recommended_slice_count=6,
                estimated_cost_bps=0.0,
            )

        algo_costs: dict[str, list[float]] = {
            "TWAP": [],
            "VWAP": [],
            "IS": [],
        }
        for trade in symbol_trades:
            twap_cost = abs(trade.twap_slippage) * 10_000
            vwap_cost = abs(trade.vwap_slippage) * 10_000
            is_cost = abs(trade.implementation_shortfall) * 10_000
            algo_costs["TWAP"].append(twap_cost)
            algo_costs["VWAP"].append(vwap_cost)
            algo_costs["IS"].append(is_cost)

        avg_costs = {
            algo: float(np.mean(costs)) for algo, costs in algo_costs.items() if costs
        }

        best_algo = min(avg_costs, key=lambda k: avg_costs[k]) if avg_costs else "VWAP"

        time_attr = self.attribute_by_time_period(symbol_trades)
        if time_attr:
            best_period = min(time_attr, key=lambda a: a.avg_implementation_shortfall)
            time_window = best_period.bucket
        else:
            time_window = "09:30-15:00"

        liquidity = self._adv_percentiles.get(symbol, 0.5)
        if liquidity >= 0.75:
            slice_count = 4
        elif liquidity >= 0.5:
            slice_count = 6
        elif liquidity >= 0.25:
            slice_count = 8
        else:
            slice_count = 12

        estimated_bps = avg_costs.get(best_algo, 0.0)

        return ExecutionRecommendation(
            symbol=symbol,
            recommended_algorithm=best_algo,
            recommended_time_window=time_window,
            recommended_slice_count=slice_count,
            estimated_cost_bps=round(estimated_bps, 4),
        )
