"""
QuantCore 策略抽象基类 - 终极版
7个生命周期回调: on_init, on_start, on_stop, on_tick, on_bar, on_order, on_fill
10个操作接口: buy_market, sell_market, buy_limit, sell_limit, buy_stop,
              cancel_order, cancel_all, get_position, get_cash, get_portfolio_value
"""
import asyncio
import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from enum import Enum
from typing import Any, Dict, List, Optional

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)


class Side(Enum):
    BUY = "buy"
    SELL = "sell"


class OrderType(Enum):
    MARKET = "market"
    LIMIT = "limit"
    STOP = "stop"


class OrderStatus(Enum):
    PENDING = "pending"
    FILLED = "filled"
    CANCELLED = "cancelled"
    REJECTED = "rejected"


@dataclass
class Order:
    id: str = ""
    symbol: str = ""
    side: Side = Side.BUY
    order_type: OrderType = OrderType.MARKET
    quantity: int = 0
    price: float = 0.0
    stop_price: float = 0.0
    status: OrderStatus = OrderStatus.PENDING
    filled_price: float = 0.0
    filled_quantity: int = 0
    commission: float = 0.0
    timestamp: datetime = field(default_factory=datetime.now)
    strategy_name: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id, "symbol": self.symbol, "side": self.side.value,
            "order_type": self.order_type.value, "quantity": self.quantity,
            "price": self.price, "stop_price": self.stop_price,
            "status": self.status.value, "filled_price": self.filled_price,
            "filled_quantity": self.filled_quantity, "commission": self.commission,
            "timestamp": self.timestamp.isoformat(), "strategy_name": self.strategy_name,
        }


@dataclass
class Fill:
    order_id: str = ""
    symbol: str = ""
    side: str = ""
    price: float = 0.0
    quantity: int = 0
    commission: float = 0.0
    timestamp: datetime = field(default_factory=datetime.now)


@dataclass
class Position:
    symbol: str = ""
    quantity: int = 0
    avg_price: float = 0.0
    current_price: float = 0.0
    unrealized_pnl: float = 0.0
    realized_pnl: float = 0.0

    @property
    def market_value(self) -> float:
        return self.current_price * self.quantity

    def to_dict(self) -> Dict[str, Any]:
        return {
            "symbol": self.symbol, "quantity": self.quantity,
            "avg_price": round(self.avg_price, 4),
            "current_price": round(self.current_price, 4),
            "unrealized_pnl": round(self.unrealized_pnl, 2),
            "realized_pnl": round(self.realized_pnl, 2),
            "market_value": round(self.market_value, 2),
        }


@dataclass
class Bar:
    symbol: str = ""
    timestamp: datetime = field(default_factory=datetime.now)
    open: float = 0.0
    high: float = 0.0
    low: float = 0.0
    close: float = 0.0
    volume: int = 0
    amount: float = 0.0
    is_complete: bool = True


@dataclass
class Tick:
    symbol: str = ""
    timestamp: datetime = field(default_factory=datetime.now)
    price: float = 0.0
    volume: int = 0
    bid: float = 0.0
    ask: float = 0.0


class StrategyContext:
    """策略运行上下文 - 提供操作接口"""

    def __init__(self):
        self._cash: Decimal = Decimal("1000000")
        self._positions: Dict[str, Position] = {}
        self._orders: Dict[str, Order] = {}
        self._fills: List[Fill] = []
        self._order_counter = 0
        self._order_lock = asyncio.Lock()
        self._initial_capital: Decimal = Decimal("1000000")

    def _next_order_id(self) -> str:
        self._order_counter += 1
        return f"ORD-{self._order_counter:06d}"

    def buy_market(self, symbol: str, quantity: int, strategy_name: str = "") -> Order:
        order = Order(
            id=self._next_order_id(), symbol=symbol, side=Side.BUY,
            order_type=OrderType.MARKET, quantity=quantity,
            strategy_name=strategy_name,
        )
        self._orders[order.id] = order
        return order

    def sell_market(self, symbol: str, quantity: int, strategy_name: str = "") -> Order:
        order = Order(
            id=self._next_order_id(), symbol=symbol, side=Side.SELL,
            order_type=OrderType.MARKET, quantity=quantity,
            strategy_name=strategy_name,
        )
        self._orders[order.id] = order
        return order

    def buy_limit(self, symbol: str, quantity: int, price: float,
                  strategy_name: str = "") -> Order:
        order = Order(
            id=self._next_order_id(), symbol=symbol, side=Side.BUY,
            order_type=OrderType.LIMIT, quantity=quantity, price=price,
            strategy_name=strategy_name,
        )
        self._orders[order.id] = order
        return order

    def sell_limit(self, symbol: str, quantity: int, price: float,
                   strategy_name: str = "") -> Order:
        order = Order(
            id=self._next_order_id(), symbol=symbol, side=Side.SELL,
            order_type=OrderType.LIMIT, quantity=quantity, price=price,
            strategy_name=strategy_name,
        )
        self._orders[order.id] = order
        return order

    def buy_stop(self, symbol: str, quantity: int, stop_price: float,
                 strategy_name: str = "") -> Order:
        order = Order(
            id=self._next_order_id(), symbol=symbol, side=Side.BUY,
            order_type=OrderType.STOP, quantity=quantity, stop_price=stop_price,
            strategy_name=strategy_name,
        )
        self._orders[order.id] = order
        return order

    def cancel_order(self, order_id: str) -> bool:
        if order_id in self._orders and self._orders[order_id].status == OrderStatus.PENDING:
            self._orders[order_id].status = OrderStatus.CANCELLED
            return True
        return False

    def cancel_all(self, symbol: str = "") -> int:
        cancelled = 0
        for oid, order in self._orders.items():
            if order.status == OrderStatus.PENDING:
                if not symbol or order.symbol == symbol:
                    order.status = OrderStatus.CANCELLED
                    cancelled += 1
        return cancelled

    def get_position(self, symbol: str) -> Position:
        return self._positions.get(symbol, Position(symbol=symbol))

    def get_cash(self) -> float:
        return float(self._cash)

    def get_portfolio_value(self) -> float:
        total = self._cash
        for pos in self._positions.values():
            total += Decimal(str(pos.market_value))
        return float(total)

    def process_fill(self, order: Order, fill_price: float, fill_qty: int,
                     commission: float = 0.0):
        order.filled_price = fill_price
        order.filled_quantity = fill_qty
        order.commission = commission
        order.status = OrderStatus.FILLED

        fill = Fill(
            order_id=order.id, symbol=order.symbol,
            side=order.side.value, price=fill_price,
            quantity=fill_qty, commission=commission,
        )
        self._fills.append(fill)

        amount = Decimal(str(fill_price)) * Decimal(str(fill_qty))
        comm = Decimal(str(commission))

        if order.side == Side.BUY:
            self._cash -= (amount + comm)
            if order.symbol in self._positions:
                pos = self._positions[order.symbol]
                total_cost = Decimal(str(pos.avg_price)) * Decimal(str(pos.quantity)) + amount
                pos.quantity += fill_qty
                pos.avg_price = float(total_cost / Decimal(str(pos.quantity)))
            else:
                self._positions[order.symbol] = Position(
                    symbol=order.symbol, quantity=fill_qty, avg_price=fill_price,
                )
        else:
            self._cash += (amount - comm)
            if order.symbol in self._positions:
                pos = self._positions[order.symbol]
                realized = (fill_price - pos.avg_price) * fill_qty - commission
                pos.realized_pnl += realized
                pos.quantity -= fill_qty
                if pos.quantity <= 0:
                    del self._positions[order.symbol]


class Strategy(ABC):
    """
    QuantCore 策略抽象基类
    7个生命周期回调 + 10个操作接口
    策略代码在回测/模拟/实盘三种场景下一字不改运行
    """

    name: str = "BaseStrategy"
    description: str = ""
    version: str = "1.0.0"
    risk_level: str = "medium"
    supported_markets: List[str] = ["A"]
    params: Dict[str, Any] = {}

    def __init__(self, **kwargs):
        self.params = {**self.params, **kwargs}
        self._ctx: Optional[StrategyContext] = None
        self._data_buffer: List[Bar] = []
        self._max_buffer_size = 1000
        self._initialized = False
        self._running = False

    def set_context(self, ctx: StrategyContext):
        self._ctx = ctx

    @property
    def ctx(self) -> StrategyContext:
        if self._ctx is None:
            self._ctx = StrategyContext()
        return self._ctx

    # ==================== 7个生命周期回调 ====================

    async def on_init(self):
        """策略初始化 - 加载参数、预热数据"""
        self._initialized = True

    async def on_start(self):
        """策略启动 - 开始运行"""
        self._running = True

    async def on_stop(self):
        """策略停止 - 清理资源"""
        self._running = False

    @abstractmethod
    async def on_tick(self, tick: Tick):
        """Tick回调 - 实盘逐笔数据"""
        pass

    @abstractmethod
    async def on_bar(self, bar: Bar):
        """K线回调 - 每根K线触发"""
        self._data_buffer.append(bar)
        if len(self._data_buffer) > self._max_buffer_size:
            self._data_buffer.pop(0)

    async def on_order(self, order: Order):
        """订单状态变化回调"""
        pass

    async def on_fill(self, fill: Fill):
        """成交通知回调"""
        pass

    # ==================== 10个操作接口 ====================

    def buy_market(self, symbol: str, quantity: int) -> Order:
        return self.ctx.buy_market(symbol, quantity, self.name)

    def sell_market(self, symbol: str, quantity: int) -> Order:
        return self.ctx.sell_market(symbol, quantity, self.name)

    def buy_limit(self, symbol: str, quantity: int, price: float) -> Order:
        return self.ctx.buy_limit(symbol, quantity, price, self.name)

    def sell_limit(self, symbol: str, quantity: int, price: float) -> Order:
        return self.ctx.sell_limit(symbol, quantity, price, self.name)

    def buy_stop(self, symbol: str, quantity: int, stop_price: float) -> Order:
        return self.ctx.buy_stop(symbol, quantity, stop_price, self.name)

    def cancel_order(self, order_id: str) -> bool:
        return self.ctx.cancel_order(order_id)

    def cancel_all(self, symbol: str = "") -> int:
        return self.ctx.cancel_all(symbol)

    def get_position(self, symbol: str) -> Position:
        return self.ctx.get_position(symbol)

    def get_cash(self) -> float:
        return self.ctx.get_cash()

    def get_portfolio_value(self) -> float:
        return self.ctx.get_portfolio_value()

    # ==================== 辅助方法 ====================

    def get_param(self, key: str, default: Any = None) -> Any:
        return self.params.get(key, default)

    def set_param(self, key: str, value: Any):
        self.params[key] = value

    def get_state(self) -> Dict[str, Any]:
        return {
            "name": self.name, "description": self.description,
            "version": self.version, "risk_level": self.risk_level,
            "params": self.params, "initialized": self._initialized,
            "running": self._running,
        }

    def get_closes_array(self) -> np.ndarray:
        return np.array([b.close for b in self._data_buffer])

    def reset(self):
        self._data_buffer.clear()
        self._initialized = False
        self._running = False
