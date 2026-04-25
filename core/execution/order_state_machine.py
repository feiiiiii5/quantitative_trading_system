import logging
import time
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)


class OrderState(Enum):
    PENDING = auto()
    SUBMITTED = auto()
    PARTIAL_FILLED = auto()
    FILLED = auto()
    CANCELLED = auto()
    REJECTED = auto()
    EXPIRED = auto()


class OrderType(Enum):
    MARKET = "market"
    LIMIT = "limit"
    STOP = "stop"
    STOP_LIMIT = "stop_limit"
    TRAILING_STOP = "trailing_stop"


class OrderSide(Enum):
    BUY = "buy"
    SELL = "sell"


@dataclass
class Order:
    order_id: str
    symbol: str
    side: OrderSide
    order_type: OrderType
    quantity: int
    price: float = 0.0
    stop_price: float = 0.0
    trailing_pct: float = 0.0
    filled_quantity: int = 0
    avg_fill_price: float = 0.0
    state: OrderState = OrderState.PENDING
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)
    metadata: dict = field(default_factory=dict)
    version: int = 1

    @property
    def remaining_quantity(self) -> int:
        return self.quantity - self.filled_quantity

    @property
    def is_active(self) -> bool:
        return self.state in (OrderState.PENDING, OrderState.SUBMITTED, OrderState.PARTIAL_FILLED)

    def to_dict(self) -> dict:
        return {
            "order_id": self.order_id,
            "symbol": self.symbol,
            "side": self.side.value,
            "order_type": self.order_type.value,
            "quantity": self.quantity,
            "price": self.price,
            "stop_price": self.stop_price,
            "trailing_pct": self.trailing_pct,
            "filled_quantity": self.filled_quantity,
            "avg_fill_price": self.avg_fill_price,
            "remaining_quantity": self.remaining_quantity,
            "state": self.state.name,
            "is_active": self.is_active,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "version": self.version,
            "metadata": self.metadata,
        }


class OrderStateMachine:
    def __init__(self):
        self._orders: Dict[str, Order] = {}
        self._symbol_orders: Dict[str, List[str]] = {}
        self._state_history: Dict[str, List[Dict]] = {}
        self._counter = 0

    def _generate_id(self) -> str:
        self._counter += 1
        return f"ORD{int(time.time() * 1000)}{self._counter:06d}"

    def create_order(
        self,
        symbol: str,
        side: OrderSide,
        order_type: OrderType,
        quantity: int,
        price: float = 0.0,
        stop_price: float = 0.0,
        trailing_pct: float = 0.0,
        metadata: Optional[dict] = None,
    ) -> Order:
        order_id = self._generate_id()
        order = Order(
            order_id=order_id,
            symbol=symbol,
            side=side,
            order_type=order_type,
            quantity=quantity,
            price=price,
            stop_price=stop_price,
            trailing_pct=trailing_pct,
            metadata=metadata or {},
        )
        self._orders[order_id] = order
        if symbol not in self._symbol_orders:
            self._symbol_orders[symbol] = []
        self._symbol_orders[symbol].append(order_id)
        self._record_state_change(order_id, OrderState.PENDING, "created")
        logger.info(f"Order created: {order_id} {symbol} {side.value} {quantity}")
        return order

    def submit(self, order_id: str) -> bool:
        order = self._orders.get(order_id)
        if not order:
            logger.warning(f"Order not found: {order_id}")
            return False
        if order.state != OrderState.PENDING:
            logger.warning(f"Cannot submit order in state {order.state.name}")
            return False
        order.state = OrderState.SUBMITTED
        order.updated_at = time.time()
        order.version += 1
        self._record_state_change(order_id, OrderState.SUBMITTED, "submitted")
        return True

    def fill(self, order_id: str, fill_qty: int, fill_price: float) -> bool:
        order = self._orders.get(order_id)
        if not order:
            logger.warning(f"Order not found: {order_id}")
            return False
        if order.state not in (OrderState.SUBMITTED, OrderState.PARTIAL_FILLED):
            logger.warning(f"Cannot fill order in state {order.state.name}")
            return False
        if fill_qty <= 0 or fill_qty > order.remaining_quantity:
            logger.warning(f"Invalid fill quantity: {fill_qty}, remaining: {order.remaining_quantity}")
            return False

        total_cost = order.avg_fill_price * order.filled_quantity + fill_price * fill_qty
        order.filled_quantity += fill_qty
        order.avg_fill_price = total_cost / order.filled_quantity if order.filled_quantity > 0 else 0
        order.updated_at = time.time()
        order.version += 1

        if order.filled_quantity >= order.quantity:
            order.state = OrderState.FILLED
            self._record_state_change(order_id, OrderState.FILLED, f"filled_{fill_qty}@{fill_price}")
            logger.info(f"Order fully filled: {order_id} {fill_qty}@{fill_price}")
        else:
            order.state = OrderState.PARTIAL_FILLED
            self._record_state_change(order_id, OrderState.PARTIAL_FILLED, f"partial_{fill_qty}@{fill_price}")
            logger.info(f"Order partial filled: {order_id} {fill_qty}@{fill_price}")
        return True

    def cancel(self, order_id: str) -> bool:
        order = self._orders.get(order_id)
        if not order:
            logger.warning(f"Order not found: {order_id}")
            return False
        if not order.is_active:
            logger.warning(f"Cannot cancel order in state {order.state.name}")
            return False
        order.state = OrderState.CANCELLED
        order.updated_at = time.time()
        order.version += 1
        self._record_state_change(order_id, OrderState.CANCELLED, "cancelled")
        logger.info(f"Order cancelled: {order_id}")
        return True

    def reject(self, order_id: str, reason: str = "") -> bool:
        order = self._orders.get(order_id)
        if not order:
            logger.warning(f"Order not found: {order_id}")
            return False
        if order.state != OrderState.PENDING:
            logger.warning(f"Cannot reject order in state {order.state.name}")
            return False
        order.state = OrderState.REJECTED
        order.updated_at = time.time()
        order.version += 1
        order.metadata["reject_reason"] = reason
        self._record_state_change(order_id, OrderState.REJECTED, f"rejected: {reason}")
        logger.warning(f"Order rejected: {order_id} reason={reason}")
        return True

    def expire(self, order_id: str) -> bool:
        order = self._orders.get(order_id)
        if not order:
            logger.warning(f"Order not found: {order_id}")
            return False
        if not order.is_active:
            logger.warning(f"Cannot expire order in state {order.state.name}")
            return False
        order.state = OrderState.EXPIRED
        order.updated_at = time.time()
        order.version += 1
        self._record_state_change(order_id, OrderState.EXPIRED, "expired")
        logger.info(f"Order expired: {order_id}")
        return True

    def get_order(self, order_id: str) -> Optional[Order]:
        return self._orders.get(order_id)

    def get_orders_by_symbol(self, symbol: str, active_only: bool = False) -> List[Order]:
        order_ids = self._symbol_orders.get(symbol, [])
        orders = [self._orders[oid] for oid in order_ids if oid in self._orders]
        if active_only:
            orders = [o for o in orders if o.is_active]
        return orders

    def get_all_orders(self, active_only: bool = False) -> List[Order]:
        orders = list(self._orders.values())
        if active_only:
            orders = [o for o in orders if o.is_active]
        return orders

    def get_state_history(self, order_id: str) -> List[Dict]:
        return self._state_history.get(order_id, [])

    def get_state_summary(self) -> dict:
        counts = {}
        for order in self._orders.values():
            state_name = order.state.name
            counts[state_name] = counts.get(state_name, 0) + 1
        return {
            "total_orders": len(self._orders),
            "active_orders": len([o for o in self._orders.values() if o.is_active]),
            "state_counts": counts,
        }

    def _record_state_change(self, order_id: str, new_state: OrderState, detail: str):
        if order_id not in self._state_history:
            self._state_history[order_id] = []
        self._state_history[order_id].append({
            "timestamp": time.time(),
            "state": new_state.name,
            "detail": detail,
        })

    def is_idempotent(self, symbol: str, side: OrderSide, order_type: OrderType, quantity: int, price: float, window_seconds: float = 5.0) -> bool:
        now = time.time()
        for order in self.get_orders_by_symbol(symbol, active_only=True):
            if (order.side == side and order.order_type == order_type and
                order.quantity == quantity and abs(order.price - price) < 0.0001 and
                now - order.created_at < window_seconds):
                return True
        return False
