import logging
from dataclasses import dataclass
from typing import Dict, List, Optional


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

    def check_calendar_rebalance(
        self,
        positions: Dict[str, dict],
        target_weights: Dict[str, float],
        current_date: str = "",
        frequency: str = "monthly",
    ) -> List[RebalanceOrder]:
        should_rebalance = False
        if not current_date:
            should_rebalance = True
        else:
            try:
                from datetime import datetime
                last = datetime.strptime(current_date, "%Y-%m-%d")
                now = datetime.now()
                if frequency == "daily":
                    should_rebalance = (now - last).days >= 1
                elif frequency == "weekly":
                    should_rebalance = (now - last).days >= 7
                elif frequency == "monthly":
                    should_rebalance = (now - last).days >= 30
                elif frequency == "quarterly":
                    should_rebalance = (now - last).days >= 90
                else:
                    should_rebalance = True
            except Exception:
                should_rebalance = True

        if not should_rebalance:
            return []

        total_value = sum(p.get("value", 0) for p in positions.values())
        current_weights = {}
        for symbol, pos in positions.items():
            if total_value > 0:
                current_weights[symbol] = pos.get("value", 0) / total_value
            else:
                current_weights[symbol] = 0

        return self._generate_orders(current_weights, target_weights, total_value)

    def check_threshold_rebalance(
        self,
        positions: Dict[str, dict],
        target_weights: Dict[str, float],
        threshold: float = 0.05,
    ) -> List[RebalanceOrder]:
        total_value = sum(p.get("value", 0) for p in positions.values())
        current_weights = {}
        for symbol, pos in positions.items():
            if total_value > 0:
                current_weights[symbol] = pos.get("value", 0) / total_value
            else:
                current_weights[symbol] = 0

        needs_rebalance = False
        for symbol in target_weights:
            current = current_weights.get(symbol, 0)
            target = target_weights.get(symbol, 0)
            if abs(current - target) > threshold:
                needs_rebalance = True
                break

        if not needs_rebalance:
            return []

        return self._generate_orders(current_weights, target_weights, total_value)

    def tax_aware_rebalance(
        self,
        positions: Dict[str, dict],
        target_weights: Dict[str, float],
        tax_rate: float = 0.2,
    ) -> List[RebalanceOrder]:
        total_value = sum(p.get("value", 0) for p in positions.values())
        current_weights = {}
        cost_basis = {}
        for symbol, pos in positions.items():
            if total_value > 0:
                current_weights[symbol] = pos.get("value", 0) / total_value
            else:
                current_weights[symbol] = 0
            cost_basis[symbol] = pos.get("cost_basis", pos.get("value", 0) * 0.9) / max(total_value, 1)

        orders = self._generate_orders(current_weights, target_weights, total_value, cost_basis)

        for o in orders:
            if o.action == "sell" and o.symbol in cost_basis:
                current_value = o.current_weight * total_value
                basis_value = cost_basis[o.symbol] * total_value
                gain = current_value - basis_value
                if gain > 0:
                    o.tax_impact = gain * tax_rate

        tax_free = [o for o in orders if o.tax_impact == 0]
        taxable = [o for o in orders if o.tax_impact > 0]
        tax_free.sort(key=lambda o: abs(o.target_weight - o.current_weight), reverse=True)
        taxable.sort(key=lambda o: o.tax_impact / max(abs(o.trade_value), 1))

        return tax_free + taxable

    def _generate_orders(
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

    def generate_rebalance_orders(
        self,
        current_weights: Dict[str, float],
        target_weights: Dict[str, float],
        total_value: float = 100000.0,
        cost_basis: Optional[Dict[str, float]] = None,
    ) -> List[RebalanceOrder]:
        return self._generate_orders(current_weights, target_weights, total_value, cost_basis)

    def estimate_transaction_costs(self, order_data: List[dict]) -> dict:
        total_trades = sum(o.get("trade_value", 0) for o in order_data)
        total_tax = sum(o.get("tax_impact", 0) for o in order_data)
        transaction_cost = total_trades * self.transaction_cost
        total_cost = total_tax + transaction_cost

        return {
            "total_trade_value": round(total_trades, 2),
            "transaction_cost": round(transaction_cost, 2),
            "tax_impact": round(total_tax, 2),
            "total_cost": round(total_cost, 2),
            "cost_pct": round(total_cost / max(total_trades, 1) * 100, 4),
            "order_count": len(order_data),
        }

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
