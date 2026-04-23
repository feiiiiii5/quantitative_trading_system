import logging
import math
from dataclasses import dataclass
from enum import Enum
from typing import Dict, List, Optional, Tuple

import numpy as np

logger = logging.getLogger(__name__)


class SlippageModel(Enum):
    FIXED = "fixed"
    PERCENTAGE = "percentage"
    VOLUME_IMPACT = "volume_impact"


class OrderBookMechanism(Enum):
    FIFO = "fifo"
    PRO_RATA = "pro_rata"


@dataclass
class OrderBookLevel:
    price: float
    volume: float
    order_count: int = 1


@dataclass
class SimulatedFill:
    requested_price: float
    fill_price: float
    fill_quantity: int
    slippage: float
    market_impact: float
    commission: float
    total_cost: float

    def to_dict(self) -> dict:
        return {
            "requested_price": self.requested_price,
            "fill_price": round(self.fill_price, 4),
            "fill_quantity": self.fill_quantity,
            "slippage": round(self.slippage, 4),
            "market_impact": round(self.market_impact, 4),
            "commission": round(self.commission, 4),
            "total_cost": round(self.total_cost, 4),
        }


class MicrostructureSimulator:
    def __init__(
        self,
        slippage_model: SlippageModel = SlippageModel.PERCENTAGE,
        fixed_slippage: float = 0.01,
        percentage_slippage: float = 0.001,
        commission_rate: float = 0.0003,
        orderbook_mechanism: OrderBookMechanism = OrderBookMechanism.FIFO,
        volatility_impact_coeff: float = 0.1,
        volume_impact_coeff: float = 0.05,
    ):
        self.slippage_model = slippage_model
        self.fixed_slippage = fixed_slippage
        self.percentage_slippage = percentage_slippage
        self.commission_rate = commission_rate
        self.orderbook_mechanism = orderbook_mechanism
        self.volatility_impact_coeff = volatility_impact_coeff
        self.volume_impact_coeff = volume_impact_coeff

    def simulate_fill(
        self,
        price: float,
        quantity: int,
        direction: str,
        avg_volume: float = 0,
        volatility: float = 0,
        orderbook: Optional[Dict] = None,
    ) -> SimulatedFill:
        slippage = self._calc_slippage(price, quantity, direction, avg_volume, volatility)
        market_impact = self._calc_market_impact(price, quantity, avg_volume, volatility)

        if direction == "buy":
            fill_price = price + slippage + market_impact
        else:
            fill_price = price - slippage - market_impact

        commission = abs(fill_price * quantity * self.commission_rate)
        total_cost = fill_price * quantity + commission if direction == "buy" else fill_price * quantity - commission

        return SimulatedFill(
            requested_price=price,
            fill_price=fill_price,
            fill_quantity=quantity,
            slippage=slippage,
            market_impact=market_impact,
            commission=commission,
            total_cost=total_cost,
        )

    def _calc_slippage(
        self, price: float, quantity: int, direction: str,
        avg_volume: float, volatility: float,
    ) -> float:
        if self.slippage_model == SlippageModel.FIXED:
            return self.fixed_slippage

        elif self.slippage_model == SlippageModel.PERCENTAGE:
            base_slip = price * self.percentage_slippage
            vol_adj = base_slip * volatility * self.volatility_impact_coeff if volatility > 0 else 0
            return base_slip + vol_adj

        elif self.slippage_model == SlippageModel.VOLUME_IMPACT:
            base_slip = price * self.percentage_slippage
            if avg_volume > 0:
                participation = quantity / avg_volume
                volume_impact = base_slip * participation * self.volume_impact_coeff
            else:
                volume_impact = 0
            vol_adj = base_slip * volatility * self.volatility_impact_coeff if volatility > 0 else 0
            return base_slip + volume_impact + vol_adj

        return 0

    def _calc_market_impact(
        self, price: float, quantity: int, avg_volume: float, volatility: float,
    ) -> float:
        if avg_volume <= 0:
            return 0
        sigma = volatility if volatility > 0 else 0.02
        X = quantity * price
        V = avg_volume * price
        if V <= 0:
            return 0

        permanent_impact = self.volatility_impact_coeff * sigma * math.sqrt(abs(X) / V) * price
        temporary_impact = self.volume_impact_coeff * sigma * (abs(X) / V) * price

        return permanent_impact + temporary_impact

    def simulate_orderbook_fill(
        self,
        orderbook: List[OrderBookLevel],
        quantity: int,
        direction: str,
    ) -> SimulatedFill:
        if not orderbook:
            return SimulatedFill(
                requested_price=0, fill_price=0, fill_quantity=0,
                slippage=0, market_impact=0, commission=0, total_cost=0,
            )

        if direction == "buy":
            levels = sorted(orderbook, key=lambda x: x.price)
        else:
            levels = sorted(orderbook, key=lambda x: -x.price)

        remaining = quantity
        total_cost = 0.0
        total_filled = 0
        best_price = levels[0].price if levels else 0

        for level in levels:
            if remaining <= 0:
                break

            if self.orderbook_mechanism == OrderBookMechanism.FIFO:
                fill_qty = min(remaining, int(level.volume))
            else:
                fill_qty = min(remaining, int(level.volume * remaining / max(sum(l.volume for l in levels), 1)))

            total_cost += fill_qty * level.price
            total_filled += fill_qty
            remaining -= fill_qty

        avg_fill_price = total_cost / total_filled if total_filled > 0 else best_price
        slippage = abs(avg_fill_price - best_price)
        commission = avg_fill_price * total_filled * self.commission_rate

        return SimulatedFill(
            requested_price=best_price,
            fill_price=avg_fill_price,
            fill_quantity=total_filled,
            slippage=slippage,
            market_impact=abs(avg_fill_price - best_price),
            commission=commission,
            total_cost=total_cost + commission if direction == "buy" else total_cost - commission,
        )

    def get_model_info(self) -> dict:
        return {
            "slippage_model": self.slippage_model.value,
            "fixed_slippage": self.fixed_slippage,
            "percentage_slippage": self.percentage_slippage,
            "commission_rate": self.commission_rate,
            "orderbook_mechanism": self.orderbook_mechanism.value,
            "volatility_impact_coeff": self.volatility_impact_coeff,
            "volume_impact_coeff": self.volume_impact_coeff,
        }
