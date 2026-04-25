import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional

import numpy as np
import pandas as pd


logger = logging.getLogger(__name__)


class AlphaSignal(Enum):
    STRONG_BUY = "strong_buy"
    BUY = "buy"
    NEUTRAL = "neutral"
    SELL = "sell"
    STRONG_SELL = "strong_sell"


@dataclass
class AlphaOutput:
    signal: AlphaSignal = AlphaSignal.NEUTRAL
    strength: float = 0.0
    score: float = 0.0
    reasons: List[str] = field(default_factory=list)
    target_symbols: List[str] = field(default_factory=list)
    metadata: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "signal": self.signal.value,
            "strength": round(self.strength, 4),
            "score": round(self.score, 4),
            "reasons": self.reasons,
            "target_symbols": self.target_symbols,
        }


class AlphaModel(ABC):
    @abstractmethod
    def generate_alpha(self, data: Dict[str, pd.DataFrame]) -> AlphaOutput:
        pass

    @property
    @abstractmethod
    def name(self) -> str:
        pass


class MomentumAlpha(AlphaModel):
    @property
    def name(self) -> str:
        return "momentum_alpha"

    def generate_alpha(self, data: Dict[str, pd.DataFrame]) -> AlphaOutput:
        scores = {}
        for symbol, df in data.items():
            if df.empty or len(df) < 20:
                continue
            c = df["close"].values.astype(float)
            ret_20 = (c[-1] / c[-20] - 1) if len(c) >= 20 else 0
            ret_5 = (c[-1] / c[-5] - 1) if len(c) >= 5 else 0
            scores[symbol] = ret_20 * 0.6 + ret_5 * 0.4

        if not scores:
            return AlphaOutput()

        avg_score = np.mean(list(scores.values()))
        best = max(scores, key=scores.get)
        signal = AlphaSignal.NEUTRAL
        if avg_score > 0.05:
            signal = AlphaSignal.STRONG_BUY
        elif avg_score > 0.01:
            signal = AlphaSignal.BUY
        elif avg_score < -0.05:
            signal = AlphaSignal.STRONG_SELL
        elif avg_score < -0.01:
            signal = AlphaSignal.SELL

        return AlphaOutput(
            signal=signal, strength=min(abs(avg_score) * 10, 1.0),
            score=avg_score, reasons=[f"动量得分: {avg_score:.4f}"],
            target_symbols=[best] if scores[best] > 0 else [],
        )


class MeanReversionAlpha(AlphaModel):
    @property
    def name(self) -> str:
        return "mean_reversion_alpha"

    def generate_alpha(self, data: Dict[str, pd.DataFrame]) -> AlphaOutput:
        scores = {}
        for symbol, df in data.items():
            if df.empty or len(df) < 20:
                continue
            c = df["close"].values.astype(float)
            ma20 = np.mean(c[-20:])
            deviation = (c[-1] - ma20) / ma20
            scores[symbol] = -deviation

        if not scores:
            return AlphaOutput()

        avg_score = np.mean(list(scores.values()))
        signal = AlphaSignal.NEUTRAL
        if avg_score > 0.03:
            signal = AlphaSignal.BUY
        elif avg_score > 0.01:
            signal = AlphaSignal.NEUTRAL
        elif avg_score < -0.03:
            signal = AlphaSignal.SELL

        return AlphaOutput(
            signal=signal, strength=min(abs(avg_score) * 10, 1.0),
            score=avg_score, reasons=[f"均值回归得分: {avg_score:.4f}"],
        )


@dataclass
class PortfolioOutput:
    target_weights: Dict[str, float] = field(default_factory=dict)
    rebalance_needed: bool = False
    risk_budget: Dict[str, float] = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "target_weights": {k: round(v, 4) for k, v in self.target_weights.items()},
            "rebalance_needed": self.rebalance_needed,
            "risk_budget": {k: round(v, 4) for k, v in self.risk_budget.items()},
        }


class PortfolioModel(ABC):
    @abstractmethod
    def allocate(self, alpha: AlphaOutput, current_weights: Dict[str, float]) -> PortfolioOutput:
        pass


class EqualWeightPortfolio(PortfolioModel):
    def allocate(self, alpha: AlphaOutput, current_weights: Dict[str, float]) -> PortfolioOutput:
        symbols = alpha.target_symbols or list(current_weights.keys())
        if not symbols:
            return PortfolioOutput()
        weight = 1.0 / len(symbols)
        target = {s: weight for s in symbols}
        rebalance = any(abs(target.get(s, 0) - current_weights.get(s, 0)) > 0.05 for s in symbols)
        return PortfolioOutput(target_weights=target, rebalance_needed=rebalance)


class RiskParityPortfolio(PortfolioModel):
    def allocate(self, alpha: AlphaOutput, current_weights: Dict[str, float]) -> PortfolioOutput:
        symbols = alpha.target_symbols or list(current_weights.keys())
        if not symbols:
            return PortfolioOutput()
        inv_vol = {s: 1.0 / max(0.01, alpha.strength) for s in symbols}
        total = sum(inv_vol.values())
        target = {s: v / total for s, v in inv_vol.items()}
        return PortfolioOutput(target_weights=target, rebalance_needed=True)


@dataclass
class RiskOutput:
    approved: bool = True
    position_limit: Dict[str, float] = field(default_factory=dict)
    stop_losses: Dict[str, float] = field(default_factory=dict)
    warnings: List[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "approved": self.approved,
            "position_limit": {k: round(v, 4) for k, v in self.position_limit.items()},
            "stop_losses": {k: round(v, 2) for k, v in self.stop_losses.items()},
            "warnings": self.warnings,
        }


class RiskModel(ABC):
    @abstractmethod
    def check(self, portfolio: PortfolioOutput, current_positions: Dict[str, dict]) -> RiskOutput:
        pass


class BasicRiskModel(RiskModel):
    def __init__(self, max_single_pct: float = 0.3, max_total: float = 1.0, max_drawdown: float = 0.15):
        self.max_single_pct = max_single_pct
        self.max_total = max_total
        self.max_drawdown = max_drawdown

    def check(self, portfolio: PortfolioOutput, current_positions: Dict[str, dict]) -> RiskOutput:
        warnings = []
        position_limit = {}
        stop_losses = {}

        for symbol, weight in portfolio.target_weights.items():
            if weight > self.max_single_pct:
                position_limit[symbol] = self.max_single_pct
                warnings.append(f"{symbol} 仓位{weight:.2%}超过单标的上限{self.max_single_pct:.0%}")
            else:
                position_limit[symbol] = weight

            if symbol in current_positions:
                entry = current_positions[symbol].get("entry_price", 0)
                if entry > 0:
                    stop_losses[symbol] = entry * 0.95

        total_weight = sum(portfolio.target_weights.values())
        if total_weight > self.max_total:
            warnings.append(f"总仓位{total_weight:.2%}超过上限{self.max_total:.0%}")

        approved = len(warnings) == 0 or all("超过" not in w for w in warnings)
        return RiskOutput(approved=approved, position_limit=position_limit,
                          stop_losses=stop_losses, warnings=warnings)


@dataclass
class ExecutionOutput:
    orders: List[dict] = field(default_factory=list)
    estimated_cost: float = 0.0
    estimated_slippage: float = 0.0

    def to_dict(self) -> dict:
        return {
            "orders": self.orders,
            "estimated_cost": round(self.estimated_cost, 2),
            "estimated_slippage": round(self.estimated_slippage, 2),
        }


class ExecutionModel(ABC):
    @abstractmethod
    def execute(self, risk: RiskOutput, portfolio: PortfolioOutput,
                prices: Dict[str, float], capital: float) -> ExecutionOutput:
        pass


class TWAPExecution(ExecutionModel):
    def execute(self, risk: RiskOutput, portfolio: PortfolioOutput,
                prices: Dict[str, float], capital: float) -> ExecutionOutput:
        orders = []
        total_cost = 0.0
        total_slippage = 0.0
        n_slices = 4

        for symbol, limit_pct in risk.position_limit.items():
            price = prices.get(symbol, 0)
            if price <= 0:
                continue
            invest = capital * limit_pct
            shares = int(invest / price / 100) * 100
            if shares <= 0:
                continue
            slice_shares = shares // n_slices
            slippage = price * 0.001
            for i in range(n_slices):
                orders.append({
                    "symbol": symbol, "direction": "buy",
                    "shares": slice_shares if i < n_slices - 1 else shares - slice_shares * (n_slices - 1),
                    "price": round(price + slippage, 2),
                    "slice": i + 1, "total_slices": n_slices,
                    "algo": "TWAP",
                })
            total_cost += shares * price
            total_slippage += shares * slippage

        return ExecutionOutput(orders=orders, estimated_cost=total_cost, estimated_slippage=total_slippage)


class VWAPExecution(ExecutionModel):
    def execute(self, risk: RiskOutput, portfolio: PortfolioOutput,
                prices: Dict[str, float], capital: float) -> ExecutionOutput:
        orders = []
        total_cost = 0.0
        total_slippage = 0.0

        for symbol, limit_pct in risk.position_limit.items():
            price = prices.get(symbol, 0)
            if price <= 0:
                continue
            invest = capital * limit_pct
            shares = int(invest / price / 100) * 100
            if shares <= 0:
                continue
            slippage = price * 0.0008
            orders.append({
                "symbol": symbol, "direction": "buy",
                "shares": shares, "price": round(price + slippage, 2),
                "algo": "VWAP",
            })
            total_cost += shares * price
            total_slippage += shares * slippage

        return ExecutionOutput(orders=orders, estimated_cost=total_cost, estimated_slippage=total_slippage)


class SignalExecutionDecoupler:
    def __init__(
        self,
        alpha_model: Optional[AlphaModel] = None,
        portfolio_model: Optional[PortfolioModel] = None,
        risk_model: Optional[RiskModel] = None,
        execution_model: Optional[ExecutionModel] = None,
    ):
        self.alpha = alpha_model or MomentumAlpha()
        self.portfolio = portfolio_model or EqualWeightPortfolio()
        self.risk = risk_model or BasicRiskModel()
        self.execution = execution_model or TWAPExecution()

    def run_pipeline(
        self,
        data: Dict[str, pd.DataFrame],
        current_weights: Dict[str, float],
        current_positions: Dict[str, dict],
        prices: Dict[str, float],
        capital: float,
    ) -> dict:
        alpha_output = self.alpha.generate_alpha(data)
        portfolio_output = self.portfolio.allocate(alpha_output, current_weights)
        risk_output = self.risk.check(portfolio_output, current_positions)
        execution_output = self.execution.execute(risk_output, portfolio_output, prices, capital)

        return {
            "alpha": alpha_output.to_dict(),
            "portfolio": portfolio_output.to_dict(),
            "risk": risk_output.to_dict(),
            "execution": execution_output.to_dict(),
            "pipeline_status": "approved" if risk_output.approved else "rejected",
        }

    def get_model_info(self) -> dict:
        return {
            "alpha_model": self.alpha.name,
            "portfolio_model": type(self.portfolio).__name__,
            "risk_model": type(self.risk).__name__,
            "execution_model": type(self.execution).__name__,
        }
