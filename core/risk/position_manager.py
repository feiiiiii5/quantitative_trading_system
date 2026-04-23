import logging
import math
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional, Tuple

import numpy as np

logger = logging.getLogger(__name__)


class PositionMode(Enum):
    FIXED_PCT = "fixed_pct"
    FIXED_RISK = "fixed_risk"
    VOLATILITY_TARGET = "vol_target"
    KELLY = "kelly"
    HALF_KELLY = "half_kelly"


@dataclass
class PositionConstraint:
    max_single_pct: float = 0.3
    max_industry_pct: float = 0.5
    max_market_cap_pct: float = 0.6
    max_total_exposure: float = 1.0

    def to_dict(self) -> dict:
        return {
            "max_single_pct": self.max_single_pct,
            "max_industry_pct": self.max_industry_pct,
            "max_market_cap_pct": self.max_market_cap_pct,
            "max_total_exposure": self.max_total_exposure,
        }


@dataclass
class PositionResult:
    symbol: str
    position_pct: float
    shares: int
    invest_amount: float
    mode: str
    risk_amount: float = 0.0
    constraint_applied: str = ""

    def to_dict(self) -> dict:
        return {
            "symbol": self.symbol,
            "position_pct": round(self.position_pct, 4),
            "shares": self.shares,
            "invest_amount": round(self.invest_amount, 2),
            "mode": self.mode,
            "risk_amount": round(self.risk_amount, 2),
            "constraint_applied": self.constraint_applied,
        }


class DynamicPositionManager:
    def __init__(
        self,
        mode: PositionMode = PositionMode.HALF_KELLY,
        risk_pct: float = 0.02,
        target_volatility: float = 0.15,
        constraints: Optional[PositionConstraint] = None,
    ):
        self.mode = mode
        self.risk_pct = risk_pct
        self.target_volatility = target_volatility
        self.constraints = constraints or PositionConstraint()
        self._current_positions: Dict[str, float] = {}
        self._industry_map: Dict[str, str] = {}
        self._market_cap_map: Dict[str, str] = {}

    def set_industry_map(self, mapping: Dict[str, str]):
        self._industry_map = mapping

    def set_market_cap_map(self, mapping: Dict[str, str]):
        self._market_cap_map = mapping

    def calculate_position(
        self,
        symbol: str,
        capital: float,
        price: float,
        atr: float = 0.0,
        volatility: float = 0.0,
        win_rate: float = 0.5,
        avg_win_loss_ratio: float = 1.5,
        current_positions: Optional[Dict[str, float]] = None,
    ) -> PositionResult:
        if current_positions is None:
            current_positions = self._current_positions

        if self.mode == PositionMode.FIXED_PCT:
            pct = self.risk_pct
        elif self.mode == PositionMode.FIXED_RISK:
            pct = self._fixed_risk_position(capital, price, atr)
        elif self.mode == PositionMode.VOLATILITY_TARGET:
            pct = self._vol_target_position(volatility)
        elif self.mode == PositionMode.KELLY:
            pct = self._kelly_position(win_rate, avg_win_loss_ratio)
        elif self.mode == PositionMode.HALF_KELLY:
            pct = self._kelly_position(win_rate, avg_win_loss_ratio) / 2
        else:
            pct = self.risk_pct

        pct, constraint_msg = self._apply_constraints(symbol, pct, capital, current_positions)

        invest = capital * pct
        shares = int(invest / price / 100) * 100
        if shares <= 0:
            shares = int(invest / price)
        risk_amount = capital * self.risk_pct

        return PositionResult(
            symbol=symbol,
            position_pct=pct,
            shares=shares,
            invest_amount=shares * price,
            mode=self.mode.value,
            risk_amount=risk_amount,
            constraint_applied=constraint_msg,
        )

    def _fixed_risk_position(self, capital: float, price: float, atr: float) -> float:
        if atr <= 0:
            return self.risk_pct
        risk_amount = capital * self.risk_pct
        stop_distance = atr * 2
        position_value = risk_amount / stop_distance * price
        return min(position_value / capital, self.constraints.max_single_pct)

    def _vol_target_position(self, volatility: float) -> float:
        if volatility <= 0:
            return self.risk_pct
        position = self.target_volatility / volatility
        return min(max(position, 0.01), self.constraints.max_single_pct)

    def _kelly_position(self, win_rate: float, avg_win_loss_ratio: float) -> float:
        if win_rate <= 0 or win_rate >= 1:
            return self.risk_pct
        kelly = win_rate - (1 - win_rate) / avg_win_loss_ratio
        return max(0, min(kelly, self.constraints.max_single_pct))

    def _apply_constraints(
        self, symbol: str, pct: float, capital: float,
        current_positions: Dict[str, float],
    ) -> Tuple[float, str]:
        constraint_msg = ""

        if pct > self.constraints.max_single_pct:
            pct = self.constraints.max_single_pct
            constraint_msg = "单标的最大暴露度约束"

        total_exposure = sum(current_positions.values()) / capital if capital > 0 else 0
        if total_exposure + pct > self.constraints.max_total_exposure:
            pct = max(0, self.constraints.max_total_exposure - total_exposure)
            constraint_msg = "总暴露度约束"

        industry = self._industry_map.get(symbol, "")
        if industry:
            industry_exposure = sum(
                v for s, v in current_positions.items()
                if self._industry_map.get(s) == industry
            ) / capital if capital > 0 else 0
            if industry_exposure + pct > self.constraints.max_industry_pct:
                pct = max(0, self.constraints.max_industry_pct - industry_exposure)
                constraint_msg = "行业暴露度约束"

        cap_tier = self._market_cap_map.get(symbol, "")
        if cap_tier:
            tier_exposure = sum(
                v for s, v in current_positions.items()
                if self._market_cap_map.get(s) == cap_tier
            ) / capital if capital > 0 else 0
            if tier_exposure + pct > self.constraints.max_market_cap_pct:
                pct = max(0, self.constraints.max_market_cap_pct - tier_exposure)
                constraint_msg = "市值档暴露度约束"

        return pct, constraint_msg

    def get_portfolio_risk(self, positions: Dict[str, dict]) -> dict:
        if not positions:
            return {"total_exposure": 0, "position_count": 0}

        total_value = sum(p.get("value", 0) for p in positions.values())
        total_invested = sum(p.get("invested", 0) for p in positions.values())

        industry_exposure: Dict[str, float] = {}
        for symbol, pos in positions.items():
            industry = self._industry_map.get(symbol, "unknown")
            industry_exposure[industry] = industry_exposure.get(industry, 0) + pos.get("invested", 0)

        return {
            "total_exposure": round(total_invested / total_value, 4) if total_value > 0 else 0,
            "position_count": len(positions),
            "industry_exposure": {k: round(v / total_value, 4) for k, v in industry_exposure.items()} if total_value > 0 else {},
            "concentration_hhi": round(sum((v / total_invested) ** 2 for v in [p.get("invested", 0) for p in positions.values()]) if total_invested > 0 else 0, 4),
        }

    def get_mode_info(self) -> dict:
        return {
            "mode": self.mode.value,
            "risk_pct": self.risk_pct,
            "target_volatility": self.target_volatility,
            "constraints": self.constraints.to_dict(),
        }
