import logging
import time
from dataclasses import dataclass, field
from typing import Dict, List, Optional

import numpy as np

logger = logging.getLogger(__name__)


@dataclass
class RebalanceSuggestion:
    symbol: str
    action: str
    current_weight: float
    suggested_weight: float
    reason: str = ""
    estimated_impact: float = 0.0

    def to_dict(self) -> dict:
        return {
            "symbol": self.symbol, "action": self.action,
            "current_weight": round(self.current_weight, 4),
            "suggested_weight": round(self.suggested_weight, 4),
            "reason": self.reason,
            "estimated_impact": round(self.estimated_impact, 4),
        }


@dataclass
class DailySummary:
    date: str
    portfolio_return: float = 0.0
    market_return: float = 0.0
    alpha: float = 0.0
    risk_level: str = "low"
    top_movers: List[dict] = field(default_factory=list)
    suggestions: List[RebalanceSuggestion] = field(default_factory=list)
    key_events: List[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "date": self.date,
            "portfolio_return": round(self.portfolio_return, 4),
            "market_return": round(self.market_return, 4),
            "alpha": round(self.alpha, 4),
            "risk_level": self.risk_level,
            "top_movers": self.top_movers,
            "suggestions": [s.to_dict() for s in self.suggestions],
            "key_events": self.key_events,
        }


class PortfolioAIAdvisor:
    def __init__(self, target_sharpe: float = 1.5, max_correlation: float = 0.7):
        self.target_sharpe = target_sharpe
        self.max_correlation = max_correlation

    def suggest_rebalance(
        self,
        positions: Dict[str, dict],
        returns_data: Dict[str, np.ndarray],
        correlation_matrix: Optional[np.ndarray] = None,
    ) -> List[RebalanceSuggestion]:
        suggestions = []
        total_value = sum(p.get("value", 0) for p in positions.values())

        if total_value <= 0:
            return suggestions

        for symbol, pos in positions.items():
            weight = pos.get("value", 0) / total_value
            ret = returns_data.get(symbol, np.array([0]))
            avg_ret = np.mean(ret) if len(ret) > 0 else 0
            vol = np.std(ret) if len(ret) > 1 else 0

            if vol > 0:
                sharpe = avg_ret / vol * np.sqrt(252)
            else:
                sharpe = 0

            if sharpe < 0 and weight > 0.1:
                suggestions.append(RebalanceSuggestion(
                    symbol=symbol, action="reduce",
                    current_weight=weight, suggested_weight=max(0.05, weight * 0.5),
                    reason=f"夏普比率低({sharpe:.2f})，建议减仓",
                    estimated_impact=avg_ret * weight * 0.5,
                ))
            elif sharpe > self.target_sharpe and weight < 0.3:
                suggestions.append(RebalanceSuggestion(
                    symbol=symbol, action="increase",
                    current_weight=weight, suggested_weight=min(0.3, weight * 1.5),
                    reason=f"夏普比率高({sharpe:.2f})，建议加仓",
                    estimated_impact=avg_ret * weight * 0.5,
                ))

        if correlation_matrix is not None and len(positions) > 1:
            symbols = list(positions.keys())
            for i in range(len(symbols)):
                for j in range(i + 1, len(symbols)):
                    if i < correlation_matrix.shape[0] and j < correlation_matrix.shape[1]:
                        corr = abs(correlation_matrix[i, j])
                        if corr > self.max_correlation:
                            sym_i = symbols[i]
                            w_i = positions[sym_i].get("value", 0) / total_value
                            suggestions.append(RebalanceSuggestion(
                                symbol=sym_i, action="reduce",
                                current_weight=w_i, suggested_weight=w_i * 0.8,
                                reason=f"与{symbols[j]}相关性过高({corr:.2f})，降低集中度",
                            ))

        return suggestions

    def generate_rebalance_plan(
        self,
        positions: Dict[str, dict],
        returns_data: Dict[str, np.ndarray],
        transaction_cost: float = 0.001,
    ) -> dict:
        suggestions = self.suggest_rebalance(positions, returns_data)
        total_value = sum(p.get("value", 0) for p in positions.values())

        orders = []
        estimated_cost = 0.0

        for s in suggestions:
            if total_value <= 0:
                continue
            current_amount = s.current_weight * total_value
            target_amount = s.suggested_weight * total_value
            trade_amount = abs(target_amount - current_amount)

            if trade_amount > 0:
                side = "buy" if s.action == "increase" else "sell"
                cost = trade_amount * transaction_cost
                estimated_cost += cost

                orders.append({
                    "symbol": s.symbol, "side": side,
                    "amount": round(trade_amount, 2),
                    "current_weight": round(s.current_weight, 4),
                    "target_weight": round(s.suggested_weight, 4),
                    "reason": s.reason,
                    "cost": round(cost, 2),
                })

        return {
            "orders": orders,
            "estimated_cost": round(estimated_cost, 2),
            "total_suggestions": len(suggestions),
        }

    def generate_daily_summary(
        self,
        positions: Dict[str, dict],
        returns_data: Dict[str, np.ndarray],
    ) -> DailySummary:
        total_value = sum(p.get("value", 0) for p in positions.values())
        if total_value <= 0:
            return DailySummary(date=time.strftime("%Y-%m-%d"))

        portfolio_return = 0.0
        for symbol, pos in positions.items():
            weight = pos.get("value", 0) / total_value
            ret = returns_data.get(symbol, np.array([0]))
            latest_ret = ret[-1] if len(ret) > 0 else 0
            portfolio_return += weight * latest_ret

        market_return = 0.0
        all_rets = [r for r in returns_data.values() if len(r) > 0]
        if all_rets:
            market_return = float(np.mean([r[-1] for r in all_rets]))

        alpha = portfolio_return - market_return

        risk_level = "low"
        if abs(portfolio_return) > 0.03:
            risk_level = "high"
        elif abs(portfolio_return) > 0.015:
            risk_level = "medium"

        top_movers = []
        for symbol, pos in positions.items():
            ret = returns_data.get(symbol, np.array([0]))
            if len(ret) > 0:
                latest_ret = ret[-1] if not np.isnan(ret[-1]) else 0
                if abs(latest_ret) > 0.02:
                    top_movers.append({
                        "symbol": symbol,
                        "return": round(latest_ret, 4),
                        "direction": "up" if latest_ret > 0 else "down",
                    })
        top_movers.sort(key=lambda x: abs(x["return"]), reverse=True)

        suggestions = self.suggest_rebalance(positions, returns_data)

        key_events = []
        if portfolio_return > 0.02:
            key_events.append("组合表现优异，超额收益显著")
        elif portfolio_return < -0.02:
            key_events.append("组合出现较大回撤，关注风控")
        if alpha > 0.01:
            key_events.append("Alpha为正，策略有效")
        elif alpha < -0.01:
            key_events.append("Alpha为负，需检视策略")

        return DailySummary(
            date=time.strftime("%Y-%m-%d"),
            portfolio_return=portfolio_return,
            market_return=market_return,
            alpha=alpha,
            risk_level=risk_level,
            top_movers=top_movers[:5],
            suggestions=suggestions[:5],
            key_events=key_events,
        )
