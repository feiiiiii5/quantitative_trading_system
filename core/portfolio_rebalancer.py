"""
投资组合再平衡模块 - Portfolio Rebalancing
维持目标风险敞口的系统性调仓机制

支持策略:
1. 阈值再平衡 - 偏离目标权重超过阈值时触发
2. 成本感知再平衡 - 考虑交易成本后的最优再平衡
3. 分批再平衡 - 分批次执行大额调仓，减少市场冲击
4. 最小波动再平衡 - 最小化组合波动率
"""
import logging
import threading
from dataclasses import dataclass, field
from enum import Enum
from typing import Literal

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)


class RebalanceStrategy(Enum):
    THRESHOLD = "threshold"
    COST_AWARE = "cost_aware"
    GRADUAL = "gradual"
    MIN_VARIANCE = "min_variance"


class RebalanceTrigger(Enum):
    THRESHOLD_BREACH = "threshold_breach"
    CALENDAR = "calendar"
    DRIFT = "drift"
    MANUAL = "manual"


@dataclass
class RebalanceOrder:
    symbol: str
    action: Literal["buy", "sell"]
    quantity: int
    target_weight: float
    current_weight: float
    weight_diff: float
    estimated_cost: float = 0.0


@dataclass
class PortfolioAllocation:
    target_weights: dict[str, float]
    current_weights: dict[str, float]
    current_values: dict[str, float]
    total_value: float
    drift: float
    timestamp: float = 0.0

    def to_dict(self) -> dict:
        return {
            "target_weights": {k: round(v, 4) for k, v in self.target_weights.items()},
            "current_weights": {k: round(v, 4) for k, v in self.current_weights.items()},
            "current_values": {k: round(v, 2) for k, v in self.current_values.items()},
            "total_value": round(self.total_value, 2),
            "drift": round(self.drift, 4),
        }


@dataclass
class RebalanceConfig:
    strategy: RebalanceStrategy = RebalanceStrategy.THRESHOLD
    drift_threshold: float = 0.05
    min_trade_value: float = 100.0
    max_trades_per_rebalance: int = 20
    gradual_days: int = 5
    cost_budget_pct: float = 0.001
    rebalance_mode: Literal["full", "partial"] = "full"
    ignore_small_weights: float = 0.01


@dataclass
class RebalanceResult:
    triggered_by: RebalanceTrigger
    strategy: RebalanceStrategy
    total_portfolio_value: float
    n_orders: int
    orders: list[RebalanceOrder]
    total_turnover_pct: float
    estimated_cost: float
    weight_drift_before: float
    weight_drift_after: float
    max_single_trade: float
    rebalanced_symbols: list[str] = field(default_factory=list)


class PortfolioRebalancer:
    def __init__(
        self,
        config: RebalanceConfig | None = None,
        slippage_engine=None,
    ):
        self._config = config or RebalanceConfig()
        self._slippage = slippage_engine
        self._lock = threading.Lock()
        self._last_rebalance_time = 0.0
        self._rebalance_history: list[RebalanceResult] = []

    def calculate_current_weights(
        self,
        holdings: dict[str, float],
        total_value: float,
    ) -> dict[str, float]:
        if total_value <= 0:
            return {}
        return {
            symbol: value / total_value for symbol, value in holdings.items()
        }

    def calculate_drift(
        self,
        target_weights: dict[str, float],
        current_weights: dict[str, float],
    ) -> float:
        all_symbols = set(target_weights.keys()) | set(current_weights.keys())
        drift = 0.0
        for symbol in all_symbols:
            target = target_weights.get(symbol, 0.0)
            current = current_weights.get(symbol, 0.0)
            drift += abs(current - target)
        return drift / 2

    def check_rebalance_needed(
        self,
        target_weights: dict[str, float],
        current_weights: dict[str, float],
    ) -> tuple[bool, float]:
        drift = self.calculate_drift(target_weights, current_weights)
        threshold = self._config.drift_threshold
        return drift > threshold, drift

    def generate_orders(
        self,
        target_weights: dict[str, float],
        holdings: dict[str, float],
        total_value: float,
        prices: dict[str, float],
        rebalance_trigger: RebalanceTrigger = RebalanceTrigger.MANUAL,
    ) -> RebalanceResult:
        with self._lock:
            return self._generate_orders_internal(
                target_weights, holdings, total_value, prices, rebalance_trigger
            )

    def _generate_orders_internal(
        self,
        target_weights: dict[str, float],
        holdings: dict[str, float],
        total_value: float,
        prices: dict[str, float],
        rebalance_trigger: RebalanceTrigger,
    ) -> RebalanceResult:
        if total_value <= 0:
            return RebalanceResult(
                triggered_by=rebalance_trigger,
                strategy=self._config.strategy,
                total_portfolio_value=0.0,
                n_orders=0,
                orders=[],
                total_turnover_pct=0.0,
                estimated_cost=0.0,
                weight_drift_before=0.0,
                weight_drift_after=0.0,
                max_single_trade=0.0,
            )

        current_weights = self.calculate_current_weights(holdings, total_value)
        drift_before = self.calculate_drift(target_weights, current_weights)

        strategy = self._config.strategy
        if strategy == RebalanceStrategy.THRESHOLD:
            orders = self._threshold_rebalance(
                target_weights, holdings, total_value, prices
            )
        elif strategy == RebalanceStrategy.COST_AWARE:
            orders = self._cost_aware_rebalance(
                target_weights, holdings, total_value, prices
            )
        elif strategy == RebalanceStrategy.GRADUAL:
            orders = self._gradual_rebalance(
                target_weights, holdings, total_value, prices
            )
        elif strategy == RebalanceStrategy.MIN_VARIANCE:
            orders = self._min_variance_rebalance(
                target_weights, holdings, total_value, prices
            )
        else:
            orders = self._threshold_rebalance(
                target_weights, holdings, total_value, prices
            )

        if self._config.rebalance_mode == "partial":
            orders = self._partial_rebalance(orders, total_value)

        total_turnover = sum(
            abs(o.quantity * prices.get(o.symbol, 0))
            for o in orders
        )
        total_turnover_pct = total_turnover / total_value if total_value > 0 else 0.0
        estimated_cost = sum(o.estimated_cost for o in orders)

        new_holdings = dict(holdings)
        for order in orders:
            if order.action == "buy":
                new_holdings[order.symbol] = (
                    new_holdings.get(order.symbol, 0.0) + order.quantity * prices.get(order.symbol, 0)
                )
            else:
                new_holdings[order.symbol] = (
                    new_holdings.get(order.symbol, 0.0) - order.quantity * prices.get(order.symbol, 0)
                )
        new_weights = self.calculate_current_weights(new_holdings, total_value)
        drift_after = self.calculate_drift(target_weights, new_weights)

        result = RebalanceResult(
            triggered_by=rebalance_trigger,
            strategy=self._config.strategy,
            total_portfolio_value=total_value,
            n_orders=len(orders),
            orders=orders,
            total_turnover_pct=total_turnover_pct,
            estimated_cost=estimated_cost,
            weight_drift_before=drift_before,
            weight_drift_after=drift_after,
            max_single_trade=max(
                (o.quantity * prices.get(o.symbol, 0) for o in orders), default=0.0
            ),
            rebalanced_symbols=[o.symbol for o in orders],
        )
        self._rebalance_history.append(result)
        self._last_rebalance_time = pd.Timestamp.now().timestamp()
        return result

    def _threshold_rebalance(
        self,
        target_weights: dict[str, float],
        holdings: dict[str, float],
        total_value: float,
        prices: dict[str, float],
    ) -> list[RebalanceOrder]:
        orders: list[RebalanceOrder] = []
        all_symbols = set(target_weights.keys()) | set(holdings.keys())

        for symbol in all_symbols:
            target = target_weights.get(symbol, 0.0)
            current = holdings.get(symbol, 0.0) / total_value if total_value > 0 else 0.0
            weight_diff = target - current

            if abs(weight_diff) < self._config.ignore_small_weights:
                continue

            target_value = target * total_value
            current_value = holdings.get(symbol, 0.0)
            trade_value = target_value - current_value

            if abs(trade_value) < self._config.min_trade_value:
                continue

            price = prices.get(symbol, 0)
            if price <= 0:
                continue

            quantity = int(abs(trade_value) / price)
            if quantity == 0:
                continue

            action: Literal["buy", "sell"] = "buy" if trade_value > 0 else "sell"
            est_cost = abs(trade_value) * self._config.cost_budget_pct

            orders.append(RebalanceOrder(
                symbol=symbol,
                action=action,
                quantity=quantity,
                target_weight=target,
                current_weight=current,
                weight_diff=weight_diff,
                estimated_cost=est_cost,
            ))

        orders.sort(key=lambda o: abs(o.weight_diff), reverse=True)
        return orders[: self._config.max_trades_per_rebalance]

    def _cost_aware_rebalance(
        self,
        target_weights: dict[str, float],
        holdings: dict[str, float],
        total_value: float,
        prices: dict[str, float],
    ) -> list[RebalanceOrder]:
        all_orders = self._threshold_rebalance(
            target_weights, holdings, total_value, prices
        )
        if not all_orders:
            return []

        cost_budget = total_value * self._config.cost_budget_pct
        sorted_orders = sorted(
            all_orders, key=lambda o: abs(o.weight_diff) / (o.estimated_cost + 1e-10), reverse=True
        )

        selected: list[RebalanceOrder] = []
        total_cost = 0.0
        for order in sorted_orders:
            if total_cost + order.estimated_cost <= cost_budget:
                selected.append(order)
                total_cost += order.estimated_cost
            if len(selected) >= self._config.max_trades_per_rebalance:
                break

        return selected

    def _gradual_rebalance(
        self,
        target_weights: dict[str, float],
        holdings: dict[str, float],
        total_value: float,
        prices: dict[str, float],
    ) -> list[RebalanceOrder]:
        full_orders = self._threshold_rebalance(
            target_weights, holdings, total_value, prices
        )
        if not full_orders:
            return []

        fraction = 1.0 / self._config.gradual_days
        partial_orders: list[RebalanceOrder] = []
        for order in full_orders:
            partial_qty = max(1, int(order.quantity * fraction))
            trade_value = partial_qty * prices.get(order.symbol, 0)
            if trade_value < self._config.min_trade_value:
                continue
            partial_orders.append(RebalanceOrder(
                symbol=order.symbol,
                action=order.action,
                quantity=partial_qty,
                target_weight=order.target_weight,
                current_weight=order.current_weight,
                weight_diff=order.weight_diff * fraction,
                estimated_cost=order.estimated_cost * fraction,
            ))
        return partial_orders

    def _min_variance_rebalance(
        self,
        target_weights: dict[str, float],
        holdings: dict[str, float],
        total_value: float,
        prices: dict[str, float],
    ) -> list[RebalanceOrder]:
        orders = self._threshold_rebalance(
            target_weights, holdings, total_value, prices
        )
        if not orders:
            return []

        buy_orders = [o for o in orders if o.action == "buy"]
        sell_orders = [o for o in orders if o.action == "sell"]
        buy_value = sum(o.quantity * prices.get(o.symbol, 0) for o in buy_orders)
        sell_value = sum(o.quantity * prices.get(o.symbol, 0) for o in sell_orders)

        if buy_value > 0 and sell_value > 0:
            adjustment = min(buy_value, sell_value)
            scale = 1.0 - adjustment / buy_value if buy_value > 0 else 1.0
            for order in buy_orders:
                order.quantity = int(order.quantity * scale)
                order.estimated_cost *= scale
            scale = 1.0 - adjustment / sell_value if sell_value > 0 else 1.0
            for order in sell_orders:
                order.quantity = int(order.quantity * scale)
                order.estimated_cost *= scale

        return [o for o in orders if o.quantity > 0]

    def _partial_rebalance(
        self,
        orders: list[RebalanceOrder],
        total_value: float,
    ) -> list[RebalanceOrder]:
        if not orders:
            return []
        sorted_orders = sorted(orders, key=lambda o: abs(o.weight_diff), reverse=True)
        n_keep = max(1, len(orders) // 2)
        return sorted_orders[:n_keep]

    def get_allocation_snapshot(
        self,
        target_weights: dict[str, float],
        holdings: dict[str, float],
        total_value: float,
    ) -> PortfolioAllocation:
        current_weights = self.calculate_current_weights(holdings, total_value)
        drift = self.calculate_drift(target_weights, current_weights)
        return PortfolioAllocation(
            target_weights=target_weights,
            current_weights=current_weights,
            current_values=holdings,
            total_value=total_value,
            drift=drift,
        )

    def get_rebalance_history(self) -> list[RebalanceResult]:
        with self._lock:
            return list(self._rebalance_history)

    def get_performance_summary(self) -> dict:
        with self._lock:
            if not self._rebalance_history:
                return {}
            total_cost = sum(r.estimated_cost for r in self._rebalance_history)
            avg_turnover = np.mean([r.total_turnover_pct for r in self._rebalance_history])
            avg_drift_before = np.mean([r.weight_drift_before for r in self._rebalance_history])
            avg_drift_after = np.mean([r.weight_drift_after for r in self._rebalance_history])
            return {
                "n_rebalances": len(self._rebalance_history),
                "total_estimated_cost": round(total_cost, 2),
                "avg_turnover_pct": round(avg_turnover * 100, 3),
                "avg_drift_before": round(avg_drift_before, 4),
                "avg_drift_after": round(avg_drift_after, 4),
                "avg_drift_reduction": round((avg_drift_before - avg_drift_after) / (avg_drift_before + 1e-10) * 100, 1),
            }


_rebalancer: PortfolioRebalancer | None = None


def get_rebalancer(config: RebalanceConfig | None = None) -> PortfolioRebalancer:
    global _rebalancer
    if _rebalancer is None or config is not None:
        _rebalancer = PortfolioRebalancer(config)
    return _rebalancer
