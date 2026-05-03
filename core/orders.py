from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Optional
import logging

logger = logging.getLogger(__name__)


class OrderSide(Enum):
    BUY = "buy"
    SELL = "sell"


class OrderType(Enum):
    MARKET = "market"
    LIMIT = "limit"
    STOP = "stop"
    STOP_LIMIT = "stop_limit"


class OrderStatus(Enum):
    PENDING_NEW = "pending_new"
    ACTIVE = "active"
    PARTIALLY_FILLED = "partially_filled"
    FILLED = "filled"
    REJECTED = "rejected"
    PENDING_CANCEL = "pending_cancel"
    CANCELLED = "cancelled"


_VALID_TRANSITIONS = {
    OrderStatus.PENDING_NEW: {OrderStatus.ACTIVE, OrderStatus.REJECTED},
    OrderStatus.ACTIVE: {OrderStatus.PARTIALLY_FILLED, OrderStatus.FILLED, OrderStatus.PENDING_CANCEL, OrderStatus.REJECTED},
    OrderStatus.PARTIALLY_FILLED: {OrderStatus.FILLED, OrderStatus.PENDING_CANCEL, OrderStatus.REJECTED},
    OrderStatus.PENDING_CANCEL: {OrderStatus.CANCELLED, OrderStatus.FILLED, OrderStatus.PARTIALLY_FILLED},
}


@dataclass
class Order:
    order_id: str
    symbol: str
    side: OrderSide
    order_type: OrderType
    quantity: int
    price: Optional[float] = None
    stop_price: Optional[float] = None
    status: OrderStatus = OrderStatus.PENDING_NEW
    filled_quantity: int = 0
    filled_value: float = 0.0
    avg_fill_price: float = 0.0
    commission: float = 0.0
    slippage: float = 0.0
    reject_reason: str = ""
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    strategy_name: str = ""

    @property
    def unfilled_quantity(self) -> int:
        return self.quantity - self.filled_quantity

    @property
    def is_active(self) -> bool:
        return self.status in {OrderStatus.ACTIVE, OrderStatus.PARTIALLY_FILLED, OrderStatus.PENDING_NEW}

    @property
    def is_done(self) -> bool:
        return self.status in {OrderStatus.FILLED, OrderStatus.CANCELLED, OrderStatus.REJECTED}

    def transition_to(self, new_status: OrderStatus) -> bool:
        valid = _VALID_TRANSITIONS.get(self.status, set())
        if new_status not in valid:
            logger.warning(f"Invalid order transition: {self.status.value} -> {new_status.value} for order {self.order_id}")
            return False
        self.status = new_status
        self.updated_at = datetime.now()
        return True

    def fill(self, fill_quantity: int, fill_price: float, commission: float = 0.0, slippage: float = 0.0) -> None:
        actual_fill = min(fill_quantity, self.quantity - self.filled_quantity)
        if actual_fill <= 0:
            return
        self.filled_value += actual_fill * fill_price
        self.filled_quantity += actual_fill
        self.avg_fill_price = self.filled_value / self.filled_quantity if self.filled_quantity > 0 else 0.0
        self.commission += commission
        self.slippage += slippage
        self.updated_at = datetime.now()

        if self.filled_quantity >= self.quantity:
            self.transition_to(OrderStatus.FILLED)
        elif self.filled_quantity > 0:
            self.transition_to(OrderStatus.PARTIALLY_FILLED)

    def reject(self, reason: str) -> None:
        self.reject_reason = reason
        self.transition_to(OrderStatus.REJECTED)

    def cancel(self) -> None:
        if self.is_active:
            self.transition_to(OrderStatus.PENDING_CANCEL)
            self.transition_to(OrderStatus.CANCELLED)

    def to_dict(self) -> dict:
        return {
            "order_id": self.order_id,
            "symbol": self.symbol,
            "side": self.side.value,
            "order_type": self.order_type.value,
            "quantity": self.quantity,
            "price": self.price,
            "stop_price": self.stop_price,
            "status": self.status.value,
            "filled_quantity": self.filled_quantity,
            "filled_value": round(self.filled_value, 2),
            "avg_fill_price": round(self.avg_fill_price, 2),
            "commission": round(self.commission, 2),
            "slippage": round(self.slippage, 2),
            "reject_reason": self.reject_reason,
            "strategy_name": self.strategy_name,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }


@dataclass
class Trade:
    trade_id: str
    order_id: str
    symbol: str
    side: OrderSide
    quantity: int
    price: float
    commission: float = 0.0
    slippage: float = 0.0
    timestamp: datetime = field(default_factory=datetime.now)
    strategy_name: str = ""

    @property
    def amount(self) -> float:
        return self.quantity * self.price

    def to_dict(self) -> dict:
        return {
            "trade_id": self.trade_id,
            "order_id": self.order_id,
            "symbol": self.symbol,
            "side": self.side.value,
            "quantity": self.quantity,
            "price": round(self.price, 2),
            "amount": round(self.amount, 2),
            "commission": round(self.commission, 2),
            "slippage": round(self.slippage, 2),
            "strategy_name": self.strategy_name,
            "timestamp": self.timestamp.isoformat(),
        }
