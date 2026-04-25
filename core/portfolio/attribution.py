import logging
import time
from dataclasses import dataclass, field
from typing import Dict, List

import numpy as np

logger = logging.getLogger(__name__)


@dataclass
class AttributionResult:
    date: str = ""
    total_return: float = 0.0
    strategy_attribution: Dict[str, float] = field(default_factory=dict)
    symbol_attribution: Dict[str, float] = field(default_factory=dict)
    benchmark_return: float = 0.0
    excess_return: float = 0.0
    selection_effect: float = 0.0
    allocation_effect: float = 0.0

    def to_dict(self) -> dict:
        return {
            "date": self.date,
            "total_return": round(self.total_return, 4),
            "strategy_attribution": {k: round(v, 4) for k, v in self.strategy_attribution.items()},
            "symbol_attribution": {k: round(v, 4) for k, v in self.symbol_attribution.items()},
            "benchmark_return": round(self.benchmark_return, 4),
            "excess_return": round(self.excess_return, 4),
            "selection_effect": round(self.selection_effect, 4),
            "allocation_effect": round(self.allocation_effect, 4),
        }


class PerformanceAttribution:
    def __init__(self, benchmark_return: float = 0.08):
        self.benchmark_return = benchmark_return
        self._daily_attributions: List[AttributionResult] = []

    def attribute_daily(
        self,
        portfolio_return: float,
        strategy_returns: Dict[str, float],
        strategy_weights: Dict[str, float],
        symbol_returns: Dict[str, float],
        symbol_weights: Dict[str, float],
        date: str = "",
    ) -> AttributionResult:
        strategy_attr = {}
        for name, ret in strategy_returns.items():
            weight = strategy_weights.get(name, 0)
            strategy_attr[name] = ret * weight

        symbol_attr = {}
        for symbol, ret in symbol_returns.items():
            weight = symbol_weights.get(symbol, 0)
            symbol_attr[symbol] = ret * weight

        excess_return = portfolio_return - self.benchmark_return / 252

        selection = 0.0
        allocation = 0.0
        for name, ret in strategy_returns.items():
            weight = strategy_weights.get(name, 0)
            benchmark_ret = self.benchmark_return / 252
            selection += weight * (ret - benchmark_ret)
            allocation += (weight - 1.0 / max(len(strategy_returns), 1)) * benchmark_ret

        result = AttributionResult(
            date=date or time.strftime("%Y-%m-%d"),
            total_return=portfolio_return,
            strategy_attribution=strategy_attr,
            symbol_attribution=symbol_attr,
            benchmark_return=self.benchmark_return / 252,
            excess_return=excess_return,
            selection_effect=selection,
            allocation_effect=allocation,
        )
        self._daily_attributions.append(result)
        return result

    def get_rolling_attribution(self, window: int = 20) -> Dict[str, float]:
        if len(self._daily_attributions) < window:
            return {}

        recent = self._daily_attributions[-window:]
        strategy_cum = {}
        for attr in recent:
            for name, val in attr.strategy_attribution.items():
                strategy_cum[name] = strategy_cum.get(name, 0) + val

        total = sum(abs(v) for v in strategy_cum.values())
        if total > 0:
            return {k: round(v / total, 4) for k, v in strategy_cum.items()}
        return strategy_cum

    def get_period_summary(self, period: str = "1m") -> dict:
        if not self._daily_attributions:
            return {}

        if period == "1m":
            n = min(20, len(self._daily_attributions))
        elif period == "3m":
            n = min(60, len(self._daily_attributions))
        elif period == "1y":
            n = min(252, len(self._daily_attributions))
        else:
            n = len(self._daily_attributions)

        recent = self._daily_attributions[-n:]
        total_ret = sum(a.total_return for a in recent)
        total_excess = sum(a.excess_return for a in recent)
        avg_selection = np.mean([a.selection_effect for a in recent])
        avg_allocation = np.mean([a.allocation_effect for a in recent])

        return {
            "period": period,
            "days": n,
            "total_return": round(total_ret, 4),
            "total_excess": round(total_excess, 4),
            "avg_selection_effect": round(avg_selection, 4),
            "avg_allocation_effect": round(avg_allocation, 4),
            "rolling_attribution": self.get_rolling_attribution(min(n, 20)),
        }

    def decompose_excess_return(self, n_days: int = 20) -> dict:
        if len(self._daily_attributions) < n_days:
            return {}

        recent = self._daily_attributions[-n_days:]
        total_excess = sum(a.excess_return for a in recent)
        total_selection = sum(a.selection_effect for a in recent)
        total_allocation = sum(a.allocation_effect for a in recent)
        residual = total_excess - total_selection - total_allocation

        return {
            "total_excess": round(total_excess, 4),
            "selection": round(total_selection, 4),
            "allocation": round(total_allocation, 4),
            "residual": round(residual, 4),
            "selection_pct": round(total_selection / total_excess, 4) if total_excess != 0 else 0,
            "allocation_pct": round(total_allocation / total_excess, 4) if total_excess != 0 else 0,
        }

    # 路由兼容别名方法
    def daily_attribution(self, portfolio_returns, benchmark_returns, portfolio_weights, benchmark_weights):
        pr = float(np.mean(list(portfolio_returns.values()))) if isinstance(portfolio_returns, dict) else float(portfolio_returns)
        return self.attribute_daily(
            pr,
            portfolio_returns if isinstance(portfolio_returns, dict) else {},
            portfolio_weights,
            portfolio_returns if isinstance(portfolio_returns, dict) else {},
            portfolio_weights,
        )

    def rolling_attribution(self, portfolio_returns, benchmark_returns, window=22):
        return self.get_rolling_attribution(window)

    def excess_return_decomposition(self, portfolio_returns, benchmark_returns):
        if isinstance(portfolio_returns, str):
            portfolio_returns = [float(x) for x in portfolio_returns.split(",") if x.strip()]
        n = len(portfolio_returns) if hasattr(portfolio_returns, "__len__") else 20
        return self.decompose_excess_return(n)
