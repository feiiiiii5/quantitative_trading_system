import logging
import time
from dataclasses import dataclass, field
from typing import Dict, List, Optional

import numpy as np

logger = logging.getLogger(__name__)


@dataclass
class RebalanceOrder:
    symbol: str
    action: str
    current_weight: float
    target_weight: float
    trade_value: float = 0.0
    tax_impact: float = 0.0

    def to_dict(self) -> dict:
        return {
            "symbol": self.symbol, "action": self.action,
            "current_weight": round(self.current_weight, 4),
            "target_weight": round(self.target_weight, 4),
            "trade_value": round(self.trade_value, 2),
            "tax_impact": round(self.tax_impact, 2),
        }


class RebalanceEngine:
    def __init__(
        self,
        threshold: float = 0.05,
        tax_rate: float = 0.1,
        transaction_cost: float = 0.001,
    ):
        self.threshold = threshold
        self.tax_rate = tax_rate
        self.transaction_cost = transaction_cost

    def check_calendar_rebalance(self, last_rebalance: str, frequency: str = "monthly") -> bool:
        if not last_rebalance:
            return True
        try:
            from datetime import datetime
            last = datetime.strptime(last_rebalance, "%Y-%m-%d")
            now = datetime.now()
            if frequency == "daily":
                return (now - last).days >= 1
            elif frequency == "weekly":
                return (now - last).days >= 7
            elif frequency == "monthly":
                return (now - last).days >= 30
            elif frequency == "quarterly":
                return (now - last).days >= 90
        except Exception:
            return True
        return False

    def check_threshold_rebalance(
        self, current_weights: Dict[str, float], target_weights: Dict[str, float],
    ) -> bool:
        for symbol in target_weights:
            current = current_weights.get(symbol, 0)
            target = target_weights.get(symbol, 0)
            if abs(current - target) > self.threshold:
                return True
        return False

    def generate_rebalance_orders(
        self,
        current_weights: Dict[str, float],
        target_weights: Dict[str, float],
        total_value: float = 100000.0,
        cost_basis: Optional[Dict[str, float]] = None,
    ) -> List[RebalanceOrder]:
        orders = []
        cost_basis = cost_basis or {}

        for symbol in set(list(current_weights.keys()) + list(target_weights.keys())):
            current = current_weights.get(symbol, 0)
            target = target_weights.get(symbol, 0)
            diff = target - current

            if abs(diff) < self.threshold * 0.5:
                continue

            trade_value = abs(diff) * total_value
            tax_impact = 0.0

            if diff < 0 and symbol in cost_basis:
                current_value = current * total_value
                basis = cost_basis[symbol] * total_value
                gain = current_value - basis
                if gain > 0:
                    tax_impact = gain * self.tax_rate

            action = "buy" if diff > 0 else "sell"
            orders.append(RebalanceOrder(
                symbol=symbol, action=action,
                current_weight=current, target_weight=target,
                trade_value=trade_value, tax_impact=tax_impact,
            ))

        orders.sort(key=lambda o: abs(o.target_weight - o.current_weight), reverse=True)
        return orders

    def tax_aware_rebalance(
        self,
        current_weights: Dict[str, float],
        target_weights: Dict[str, float],
        total_value: float = 100000.0,
        cost_basis: Optional[Dict[str, float]] = None,
    ) -> List[RebalanceOrder]:
        orders = self.generate_rebalance_orders(current_weights, target_weights, total_value, cost_basis)

        tax_free_orders = [o for o in orders if o.tax_impact == 0]
        taxable_orders = [o for o in orders if o.tax_impact > 0]

        tax_free_orders.sort(key=lambda o: abs(o.target_weight - o.current_weight), reverse=True)

        taxable_orders.sort(key=lambda o: o.tax_impact / max(abs(o.trade_value), 1))

        return tax_free_orders + taxable_orders

    def estimate_rebalance_cost(self, orders: List[RebalanceOrder]) -> dict:
        total_trades = sum(o.trade_value for o in orders)
        total_tax = sum(o.tax_impact for o in orders)
        transaction_cost = total_trades * self.transaction_cost
        total_cost = total_tax + transaction_cost

        return {
            "total_trade_value": round(total_trades, 2),
            "transaction_cost": round(transaction_cost, 2),
            "tax_impact": round(total_tax, 2),
            "total_cost": round(total_cost, 2),
            "cost_pct": round(total_cost / max(total_trades, 1) * 100, 4),
            "order_count": len(orders),
        }
