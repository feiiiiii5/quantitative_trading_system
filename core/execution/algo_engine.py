import logging
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional

import numpy as np

logger = logging.getLogger(__name__)


class AlgoType(Enum):
    TWAP = "twap"
    VWAP = "vwap"
    POV = "pov"
    IS = "implementation_shortfall"


@dataclass
class AlgoOrder:
    symbol: str
    side: str
    total_quantity: int
    algo_type: AlgoType
    slices: List[dict] = field(default_factory=list)
    status: str = "pending"
    progress: float = 0.0
    avg_fill_price: float = 0.0
    filled_quantity: int = 0
    total_slippage: float = 0.0
    start_time: str = ""
    end_time: str = ""

    def to_dict(self) -> dict:
        return {
            "symbol": self.symbol, "side": self.side,
            "total_quantity": self.total_quantity,
            "algo_type": self.algo_type.value,
            "slices": self.slices,
            "status": self.status,
            "progress": round(self.progress, 4),
            "avg_fill_price": round(self.avg_fill_price, 4),
            "filled_quantity": self.filled_quantity,
            "total_slippage": round(self.total_slippage, 4),
            "start_time": self.start_time, "end_time": self.end_time,
        }


class AlgoExecutionEngine:
    def __init__(self, commission_rate: float = 0.0003, slippage_rate: float = 0.001):
        self.commission_rate = commission_rate
        self.slippage_rate = slippage_rate

    def execute_twap(
        self, symbol: str, side: str, quantity: int,
        price: float, n_slices: int = 4, interval_seconds: int = 300,
    ) -> AlgoOrder:
        order = AlgoOrder(
            symbol=symbol, side=side, total_quantity=quantity,
            algo_type=AlgoType.TWAP, start_time=time.strftime("%Y-%m-%d %H:%M:%S"),
        )

        slice_qty = quantity // n_slices
        remaining = quantity

        for i in range(n_slices):
            qty = slice_qty if i < n_slices - 1 else remaining
            remaining -= qty

            slippage = price * self.slippage_rate * (1 + i * 0.1)
            fill_price = price + slippage if side == "buy" else price - slippage

            order.slices.append({
                "slice": i + 1, "total_slices": n_slices,
                "quantity": qty, "fill_price": round(fill_price, 4),
                "interval_seconds": interval_seconds,
                "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
            })

            order.filled_quantity += qty
            order.total_slippage += qty * slippage

        order.progress = 1.0
        order.status = "completed"
        order.avg_fill_price = price + (order.total_slippage / quantity if quantity > 0 else 0)
        order.end_time = time.strftime("%Y-%m-%d %H:%M:%S")

        return order

    def execute_vwap(
        self, symbol: str, side: str, quantity: int,
        price: float, volume_profile: Optional[List[float]] = None,
    ) -> AlgoOrder:
        order = AlgoOrder(
            symbol=symbol, side=side, total_quantity=quantity,
            algo_type=AlgoType.VWAP, start_time=time.strftime("%Y-%m-%d %H:%M:%S"),
        )

        n_slices = 6
        if volume_profile is None:
            volume_profile = [0.05, 0.10, 0.15, 0.25, 0.25, 0.20]

        total_vol = sum(volume_profile)
        if total_vol <= 0:
            volume_profile = [1.0 / n_slices] * n_slices
            total_vol = 1.0

        remaining = quantity
        for i in range(n_slices):
            vol_pct = volume_profile[i] / total_vol
            qty = int(quantity * vol_pct)
            if i == n_slices - 1:
                qty = remaining
            remaining -= qty

            slippage = price * self.slippage_rate * (1 + vol_pct * 2)
            fill_price = price + slippage if side == "buy" else price - slippage

            order.slices.append({
                "slice": i + 1, "total_slices": n_slices,
                "quantity": qty, "fill_price": round(fill_price, 4),
                "volume_pct": round(vol_pct, 4),
                "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
            })

            order.filled_quantity += qty
            order.total_slippage += qty * slippage

        order.progress = 1.0
        order.status = "completed"
        order.avg_fill_price = price + (order.total_slippage / quantity if quantity > 0 else 0)
        order.end_time = time.strftime("%Y-%m-%d %H:%M:%S")

        return order

    def execute_pov(
        self, symbol: str, side: str, quantity: int,
        price: float, participation_rate: float = 0.1,
        market_volume: int = 1000000,
    ) -> AlgoOrder:
        order = AlgoOrder(
            symbol=symbol, side=side, total_quantity=quantity,
            algo_type=AlgoType.POV, start_time=time.strftime("%Y-%m-%d %H:%M:%S"),
        )

        n_slices = max(1, int(quantity / max(1, market_volume * participation_rate)))
        n_slices = min(n_slices, 20)
        slice_qty = quantity // n_slices
        remaining = quantity

        for i in range(n_slices):
            qty = slice_qty if i < n_slices - 1 else remaining
            remaining -= qty

            slippage = price * self.slippage_rate * (1 + participation_rate)
            fill_price = price + slippage if side == "buy" else price - slippage

            order.slices.append({
                "slice": i + 1, "total_slices": n_slices,
                "quantity": qty, "fill_price": round(fill_price, 4),
                "participation_rate": round(participation_rate, 4),
                "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
            })

            order.filled_quantity += qty
            order.total_slippage += qty * slippage

        order.progress = 1.0
        order.status = "completed"
        order.avg_fill_price = price + (order.total_slippage / quantity if quantity > 0 else 0)
        order.end_time = time.strftime("%Y-%m-%d %H:%M:%S")

        return order

    def execute_is(
        self, symbol: str, side: str, quantity: int,
        price: float, arrival_price: float = 0.0,
        urgency: str = "medium",
    ) -> AlgoOrder:
        order = AlgoOrder(
            symbol=symbol, side=side, total_quantity=quantity,
            algo_type=AlgoType.IS, start_time=time.strftime("%Y-%m-%d %H:%M:%S"),
        )

        if arrival_price <= 0:
            arrival_price = price

        urgency_map = {"low": 8, "medium": 4, "high": 2}
        n_slices = urgency_map.get(urgency, 4)

        front_load = {"low": 0.3, "medium": 0.5, "high": 0.7}.get(urgency, 0.5)
        first_qty = int(quantity * front_load)
        remaining = quantity - first_qty

        slippage = price * self.slippage_rate
        fill_price = price + slippage if side == "buy" else price - slippage

        order.slices.append({
            "slice": 1, "total_slices": n_slices,
            "quantity": first_qty, "fill_price": round(fill_price, 4),
            "front_load": True, "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        })
        order.filled_quantity += first_qty
        order.total_slippage += first_qty * slippage

        if remaining > 0 and n_slices > 1:
            slice_qty = remaining // (n_slices - 1)
            for i in range(1, n_slices):
                qty = slice_qty if i < n_slices - 1 else remaining
                remaining -= qty
                delay_slip = slippage * (1 + i * 0.05)
                fp = price + delay_slip if side == "buy" else price - delay_slip
                order.slices.append({
                    "slice": i + 1, "total_slices": n_slices,
                    "quantity": qty, "fill_price": round(fp, 4),
                    "front_load": False,
                    "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
                })
                order.filled_quantity += qty
                order.total_slippage += qty * delay_slip

        is_cost = abs(order.avg_fill_price - arrival_price) * quantity if quantity > 0 else 0
        order.progress = 1.0
        order.status = "completed"
        order.avg_fill_price = price + (order.total_slippage / quantity if quantity > 0 else 0)
        order.end_time = time.strftime("%Y-%m-%d %H:%M:%S")

        return order

    def get_algo_info(self) -> dict:
        return {
            "available_algos": [t.value for t in AlgoType],
            "commission_rate": self.commission_rate,
            "slippage_rate": self.slippage_rate,
        }
