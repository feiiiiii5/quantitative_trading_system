import logging
import time
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

import numpy as np

logger = logging.getLogger(__name__)


@dataclass
class StrategyMetrics:
    name: str
    sharpe: float = 0.0
    volatility: float = 0.0
    return_rate: float = 0.0
    max_drawdown: float = 0.0
    weight: float = 0.0
    capital: float = 0.0

    def to_dict(self) -> dict:
        return {
            "name": self.name, "sharpe": round(self.sharpe, 4),
            "volatility": round(self.volatility, 4), "return_rate": round(self.return_rate, 4),
            "max_drawdown": round(self.max_drawdown, 4), "weight": round(self.weight, 4),
            "capital": round(self.capital, 2),
        }


class CapitalAllocator:
    def __init__(self, total_capital: float = 1000000.0, rebalance_threshold: float = 0.1):
        self.total_capital = total_capital
        self.rebalance_threshold = rebalance_threshold
        self._strategies: Dict[str, StrategyMetrics] = {}
        self._correlation_matrix: Optional[np.ndarray] = None

    def add_strategy(self, metrics: StrategyMetrics):
        self._strategies[metrics.name] = metrics

    def remove_strategy(self, name: str):
        self._strategies.pop(name, None)

    def allocate_by_sharpe(self) -> Dict[str, float]:
        if not self._strategies:
            return {}

        positive_sharpe = {k: max(v.sharpe, 0) for k, v in self._strategies.items()}
        total = sum(positive_sharpe.values())

        if total <= 0:
            n = len(self._strategies)
            return {k: 1.0 / n for k in self._strategies}

        weights = {k: v / total for k, v in positive_sharpe.items()}
        return self._apply_constraints(weights)

    def allocate_by_risk_parity(self) -> Dict[str, float]:
        if not self._strategies:
            return {}

        inv_vols = {k: 1.0 / max(v.volatility, 0.001) for k, v in self._strategies.items()}
        total = sum(inv_vols.values())

        if total <= 0:
            n = len(self._strategies)
            return {k: 1.0 / n for k in self._strategies}

        weights = {k: v / total for k, v in inv_vols.items()}
        return self._apply_constraints(weights)

    def allocate_by_volatility_contribution(self) -> Dict[str, float]:
        if not self._strategies:
            return {}

        target_vol = 0.15
        vol_contributions = {}
        for name, metrics in self._strategies.items():
            vol_contributions[name] = target_vol / max(metrics.volatility * len(self._strategies), 0.001)

        total = sum(vol_contributions.values())
        if total <= 0:
            n = len(self._strategies)
            return {k: 1.0 / n for k in self._strategies}

        weights = {k: v / total for k, v in vol_contributions.items()}
        return self._apply_constraints(weights)

    def _apply_constraints(self, weights: Dict[str, float]) -> Dict[str, float]:
        max_weight = 0.4
        min_weight = 0.05
        adjusted = {}
        for k, w in weights.items():
            adjusted[k] = max(min_weight, min(max_weight, w))

        total = sum(adjusted.values())
        if total > 0:
            adjusted = {k: v / total for k, v in adjusted.items()}

        return adjusted

    def auto_rebalance(self) -> Dict[str, dict]:
        if not self._strategies:
            return {}

        current_weights = {k: v.weight for k, v in self._strategies.items()}
        target_weights = self.allocate_by_sharpe()

        actions = {}
        for name in self._strategies:
            current = current_weights.get(name, 0)
            target = target_weights.get(name, 0)
            diff = target - current

            if abs(diff) > self.rebalance_threshold:
                if diff > 0:
                    actions[name] = {"action": "increase", "from": round(current, 4), "to": round(target, 4), "diff": round(diff, 4)}
                else:
                    actions[name] = {"action": "decrease", "from": round(current, 4), "to": round(target, 4), "diff": round(diff, 4)}

        return actions

    def get_allocation_info(self) -> dict:
        return {
            "total_capital": self.total_capital,
            "strategy_count": len(self._strategies),
            "strategies": {k: v.to_dict() for k, v in self._strategies.items()},
            "sharpe_allocation": self.allocate_by_sharpe(),
            "risk_parity_allocation": self.allocate_by_risk_parity(),
        }
