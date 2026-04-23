import logging
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)


class OrderType(Enum):
    MARKET = "market"
    LIMIT = "limit"
    STOP = "stop"
    STOP_LIMIT = "stop_limit"
    OCO = "oco"
    ICEBERG = "iceberg"
    CONDITIONAL = "conditional"


class OrderSide(Enum):
    BUY = "buy"
    SELL = "sell"


@dataclass
class OrderRequest:
    symbol: str
    side: OrderSide
    quantity: int
    price: float = 0.0
    order_type: OrderType = OrderType.MARKET
    stop_price: float = 0.0
    time_in_force: str = "day"
    iceberg_display: int = 0
    condition: dict = field(default_factory=dict)
    oco_order: Optional["OrderRequest"] = None

    def to_dict(self) -> dict:
        d = {
            "symbol": self.symbol, "side": self.side.value,
            "quantity": self.quantity, "price": self.price,
            "order_type": self.order_type.value,
            "stop_price": self.stop_price,
            "time_in_force": self.time_in_force,
        }
        if self.order_type == OrderType.ICEBERG:
            d["iceberg_display"] = self.iceberg_display
        if self.order_type == OrderType.OCO and self.oco_order:
            d["oco_order"] = self.oco_order.to_dict()
        return d


@dataclass
class BrokerQuote:
    broker: str
    bid_price: float = 0.0
    ask_price: float = 0.0
    bid_size: int = 0
    ask_size: int = 0
    latency_ms: float = 0.0

    def to_dict(self) -> dict:
        return {
            "broker": self.broker,
            "bid_price": self.bid_price, "ask_price": self.ask_price,
            "bid_size": self.bid_size, "ask_size": self.ask_size,
            "latency_ms": round(self.latency_ms, 2),
        }


@dataclass
class RoutedOrder:
    request: OrderRequest
    selected_broker: str
    routed_price: float
    routed_quantity: int
    split_orders: List[dict] = field(default_factory=list)
    estimated_slippage: float = 0.0
    timestamp: str = ""

    def to_dict(self) -> dict:
        return {
            "request": self.request.to_dict(),
            "selected_broker": self.selected_broker,
            "routed_price": round(self.routed_price, 4),
            "routed_quantity": self.routed_quantity,
            "split_orders": self.split_orders,
            "estimated_slippage": round(self.estimated_slippage, 4),
            "timestamp": self.timestamp,
        }


class SmartOrderRouter:
    def __init__(self):
        self._brokers: Dict[str, dict] = {}
        self._register_default_brokers()

    def _register_default_brokers(self):
        self._brokers = {
            "broker_a": {"name": "券商A", "commission": 0.0003, "latency_ms": 50, "enabled": True},
            "broker_b": {"name": "券商B", "commission": 0.00025, "latency_ms": 80, "enabled": True},
            "broker_c": {"name": "券商C", "commission": 0.00035, "latency_ms": 30, "enabled": True},
        }

    def register_broker(self, broker_id: str, name: str, commission: float, latency_ms: float):
        self._brokers[broker_id] = {
            "name": name, "commission": commission,
            "latency_ms": latency_ms, "enabled": True,
        }

    def route_order(self, request: OrderRequest, quotes: Optional[Dict[str, BrokerQuote]] = None) -> RoutedOrder:
        if quotes is None:
            quotes = self._simulate_quotes(request)

        best_broker = self._select_best_broker(request, quotes)
        routed_price = self._calc_routed_price(request, quotes.get(best_broker))
        split_orders = self._split_order(request, best_broker)

        return RoutedOrder(
            request=request,
            selected_broker=best_broker,
            routed_price=routed_price,
            routed_quantity=request.quantity,
            split_orders=split_orders,
            estimated_slippage=abs(routed_price - request.price) if request.price > 0 else 0,
            timestamp=time.strftime("%Y-%m-%d %H:%M:%S"),
        )

    def _select_best_broker(self, request: OrderRequest, quotes: Dict[str, BrokerQuote]) -> str:
        scores = {}
        for broker_id, quote in quotes.items():
            broker_info = self._brokers.get(broker_id, {})
            if not broker_info.get("enabled", True):
                continue

            if request.side == OrderSide.BUY:
                price_score = -quote.ask_price
            else:
                price_score = quote.bid_price

            commission = broker_info.get("commission", 0.0003)
            cost = request.quantity * request.price * commission if request.price > 0 else 0
            latency = broker_info.get("latency_ms", 100)

            score = price_score * 1000 - cost * 0.1 - latency * 0.01
            scores[broker_id] = score

        if not scores:
            return list(self._brokers.keys())[0] if self._brokers else "unknown"

        return max(scores, key=scores.get)

    def _calc_routed_price(self, request: OrderRequest, quote: Optional[BrokerQuote]) -> float:
        if not quote:
            return request.price

        if request.side == OrderSide.BUY:
            return quote.ask_price if quote.ask_price > 0 else request.price
        else:
            return quote.bid_price if quote.bid_price > 0 else request.price

    def _split_order(self, request: OrderRequest, broker: str) -> List[dict]:
        if request.order_type == OrderType.ICEBERG and request.iceberg_display > 0:
            orders = []
            remaining = request.quantity
            display = request.iceberg_display
            i = 0
            while remaining > 0:
                qty = min(display, remaining)
                orders.append({
                    "broker": broker, "slice": i + 1,
                    "quantity": qty, "price": request.price,
                    "visible": display,
                })
                remaining -= qty
                i += 1
            return orders

        if request.order_type == OrderType.OCO and request.oco_order:
            return [
                {"broker": broker, "type": "primary", "quantity": request.quantity, "price": request.price},
                {"broker": broker, "type": "oco", "quantity": request.oco_order.quantity, "price": request.oco_order.price},
            ]

        return [{"broker": broker, "quantity": request.quantity, "price": request.price}]

    def _simulate_quotes(self, request: OrderRequest) -> Dict[str, BrokerQuote]:
        quotes = {}
        for broker_id, info in self._brokers.items():
            if not info.get("enabled", True):
                continue
            spread = info.get("commission", 0.0003) * request.price * 2 if request.price > 0 else 0.1
            quotes[broker_id] = BrokerQuote(
                broker=broker_id,
                bid_price=request.price - spread / 2 if request.price > 0 else 0,
                ask_price=request.price + spread / 2 if request.price > 0 else 0,
                bid_size=1000,
                ask_size=1000,
                latency_ms=info.get("latency_ms", 100),
            )
        return quotes

    def get_brokers(self) -> List[dict]:
        return [{"id": k, **v} for k, v in self._brokers.items()]

    def create_oco_order(
        self, symbol: str, quantity: int,
        take_profit_price: float, stop_loss_price: float,
    ) -> OrderRequest:
        primary = OrderRequest(
            symbol=symbol, side=OrderSide.SELL, quantity=quantity,
            price=take_profit_price, order_type=OrderType.LIMIT,
        )
        oco = OrderRequest(
            symbol=symbol, side=OrderSide.SELL, quantity=quantity,
            price=stop_loss_price, order_type=OrderType.STOP,
            stop_price=stop_loss_price,
        )
        primary.order_type = OrderType.OCO
        primary.oco_order = oco
        return primary

    def create_iceberg_order(
        self, symbol: str, side: OrderSide, quantity: int,
        price: float, display_size: int = 100,
    ) -> OrderRequest:
        return OrderRequest(
            symbol=symbol, side=side, quantity=quantity,
            price=price, order_type=OrderType.ICEBERG,
            iceberg_display=display_size,
        )

    def create_conditional_order(
        self, symbol: str, side: OrderSide, quantity: int,
        condition_type: str, condition_value: float,
    ) -> OrderRequest:
        return OrderRequest(
            symbol=symbol, side=side, quantity=quantity,
            order_type=OrderType.CONDITIONAL,
            condition={"type": condition_type, "value": condition_value},
        )
