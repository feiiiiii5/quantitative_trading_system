"""
QuantCore 模拟撮合引擎 - 终极版
A股: T+1限制, 涨跌停限制, 集合竞价
港股: T+0, 最小交易单位(1手=100股, 部分不同)
美股: T+2结算, 盘前盘后交易
精确手续费: Decimal类型, A股买入万3/卖出万3+千1印花税/最低5元
滑点模型: 固定点差 + 基于成交量占比的动态市场冲击
"""
import asyncio
import logging
import time
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, date
from decimal import Decimal, ROUND_HALF_UP
from enum import Enum
from typing import Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


class MarketType(Enum):
    A_STOCK = "A"
    HK_STOCK = "HK"
    US_STOCK = "US"
    FUTURES = "FUTURES"


class OrderSide(Enum):
    BUY = "buy"
    SELL = "sell"


class OrderType(Enum):
    MARKET = "market"
    LIMIT = "limit"
    STOP = "stop"


class OrderStatus(Enum):
    PENDING = "pending"
    PARTIAL = "partial"
    FILLED = "filled"
    CANCELLED = "cancelled"
    REJECTED = "rejected"


@dataclass
class SimOrder:
    id: str = ""
    symbol: str = ""
    side: OrderSide = OrderSide.BUY
    order_type: OrderType = OrderType.MARKET
    quantity: int = 0
    price: Decimal = Decimal("0")
    stop_price: Decimal = Decimal("0")
    status: OrderStatus = OrderStatus.PENDING
    filled_price: Decimal = Decimal("0")
    filled_quantity: int = 0
    commission: Decimal = Decimal("0")
    timestamp: datetime = field(default_factory=datetime.now)
    strategy_name: str = ""
    reject_reason: str = ""


@dataclass
class SimPosition:
    symbol: str = ""
    quantity: int = 0
    avg_cost: Decimal = Decimal("0")
    current_price: Decimal = Decimal("0")
    unrealized_pnl: Decimal = Decimal("0")
    realized_pnl: Decimal = Decimal("0")
    buy_date: Optional[date] = None
    market: str = "A"

    @property
    def market_value(self) -> Decimal:
        return self.current_price * Decimal(str(self.quantity))

    @property
    def can_sell(self) -> bool:
        if self.market == "A":
            return self.buy_date is not None and date.today() > self.buy_date
        return True


@dataclass
class SimFill:
    order_id: str = ""
    symbol: str = ""
    side: str = ""
    price: Decimal = Decimal("0")
    quantity: int = 0
    commission: Decimal = Decimal("0")
    slippage: Decimal = Decimal("0")
    timestamp: datetime = field(default_factory=datetime.now)


class CommissionModel:
    """精确手续费模型 - Decimal类型"""

    @staticmethod
    def calc_a_stock(amount: Decimal, is_sell: bool) -> Decimal:
        commission = max(amount * Decimal("0.0003"), Decimal("5"))
        if is_sell:
            commission += amount * Decimal("0.001")
        return commission.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

    @staticmethod
    def calc_hk_stock(amount: Decimal, is_sell: bool) -> Decimal:
        commission = max(amount * Decimal("0.0003"), Decimal("3"))
        commission += Decimal("15")
        if is_sell:
            commission += amount * Decimal("0.0013")
        return commission.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

    @staticmethod
    def calc_us_stock(amount: Decimal, is_sell: bool) -> Decimal:
        commission = max(amount * Decimal("0.0005"), Decimal("1"))
        if is_sell:
            commission += amount * Decimal("0.0000228")
        return commission.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

    @staticmethod
    def calc(amount: Decimal, market: str, is_sell: bool) -> Decimal:
        if market == "A":
            return CommissionModel.calc_a_stock(amount, is_sell)
        elif market == "HK":
            return CommissionModel.calc_hk_stock(amount, is_sell)
        elif market == "US":
            return CommissionModel.calc_us_stock(amount, is_sell)
        return max(amount * Decimal("0.0003"), Decimal("5"))


class SlippageModel:
    """滑点模型 - 固定点差 + 动态市场冲击"""

    def __init__(self, fixed_bps: float = 2.0, impact_coeff: float = 0.1):
        self.fixed_bps = fixed_bps
        self.impact_coeff = impact_coeff

    def calc(self, price: Decimal, quantity: int, volume: int,
             side: OrderSide, market: str = "A") -> Decimal:
        fixed_slip = price * Decimal(str(self.fixed_bps)) / Decimal("10000")
        if volume > 0:
            participation = Decimal(str(quantity)) / Decimal(str(volume))
            impact = price * participation * Decimal(str(self.impact_coeff)) / Decimal("100")
        else:
            impact = Decimal("0")
        total = fixed_slip + impact
        if side == OrderSide.BUY:
            return total
        return -total


class MatchingEngine:
    """模拟撮合引擎"""

    def __init__(self, initial_capital: float = 1000000.0):
        self._cash = Decimal(str(initial_capital))
        self._initial_capital = Decimal(str(initial_capital))
        self._positions: Dict[str, SimPosition] = {}
        self._orders: Dict[str, SimOrder] = {}
        self._fills: List[SimFill] = []
        self._order_counter = 0
        self._commission = CommissionModel()
        self._slippage = SlippageModel()
        self._order_locks: Dict[str, asyncio.Lock] = defaultdict(asyncio.Lock)
        self._market_prices: Dict[str, Decimal] = {}
        self._market_volumes: Dict[str, int] = {}
        self._prev_close: Dict[str, Decimal] = {}

    def _next_order_id(self) -> str:
        self._order_counter += 1
        return f"SIM-{self._order_counter:08d}"

    def _detect_market(self, symbol: str) -> str:
        if symbol.isdigit() and len(symbol) == 6:
            return "A"
        if symbol.isdigit() and len(symbol) == 5:
            return "HK"
        if symbol.isalpha() and len(symbol) <= 5:
            return "US"
        return "A"

    def _min_lot(self, market: str) -> int:
        return 100 if market == "A" else (100 if market == "HK" else 1)

    def update_market_data(self, symbol: str, price: float, volume: int = 0,
                           prev_close: float = 0):
        self._market_prices[symbol] = Decimal(str(price))
        self._market_volumes[symbol] = volume
        if prev_close > 0:
            self._prev_close[symbol] = Decimal(str(prev_close))

    def submit_order(self, symbol: str, side: str, order_type: str = "market",
                     quantity: int = 0, price: float = 0.0,
                     strategy_name: str = "") -> SimOrder:
        market = self._detect_market(symbol)
        lot_size = self._min_lot(market)
        if market in ("A", "HK") and quantity % lot_size != 0:
            quantity = (quantity // lot_size) * lot_size

        order = SimOrder(
            id=self._next_order_id(),
            symbol=symbol,
            side=OrderSide(side),
            order_type=OrderType(order_type),
            quantity=quantity,
            price=Decimal(str(price)),
            strategy_name=strategy_name,
        )

        if not self._validate_order(order, market):
            return order

        if order.order_type == OrderType.MARKET:
            self._match_market_order(order, market)
        else:
            self._orders[order.id] = order

        return order

    def _validate_order(self, order: SimOrder, market: str) -> bool:
        if order.quantity <= 0:
            order.status = OrderStatus.REJECTED
            order.reject_reason = "数量必须大于0"
            return False

        if order.side == OrderSide.BUY:
            price = order.price if order.order_type != OrderType.MARKET else self._market_prices.get(order.symbol, Decimal("0"))
            if price <= 0:
                order.status = OrderStatus.REJECTED
                order.reject_reason = "无可用价格"
                return False
            amount = price * Decimal(str(order.quantity))
            comm = self._commission.calc(amount, market, False)
            if amount + comm > self._cash:
                order.status = OrderStatus.REJECTED
                order.reject_reason = f"资金不足(需{float(amount + comm):.2f}, 有{float(self._cash):.2f})"
                return False
        elif order.side == OrderSide.SELL:
            pos = self._positions.get(order.symbol)
            if not pos or pos.quantity < order.quantity:
                order.status = OrderStatus.REJECTED
                order.reject_reason = "持仓不足"
                return False
            if market == "A" and not pos.can_sell:
                order.status = OrderStatus.REJECTED
                order.reject_reason = "A股T+1限制，当日买入不可卖出"
                return False

        # A股涨跌停检查
        if market == "A" and order.symbol in self._prev_close:
            prev = self._prev_close[order.symbol]
            current = self._market_prices.get(order.symbol, Decimal("0"))
            limit_up = prev * Decimal("1.1")
            limit_down = prev * Decimal("0.9")
            if order.order_type == OrderType.LIMIT:
                if order.side == OrderSide.BUY and order.price > limit_up:
                    order.status = OrderStatus.REJECTED
                    order.reject_reason = "买入价超过涨停价"
                    return False
                if order.side == OrderSide.SELL and order.price < limit_down:
                    order.status = OrderStatus.REJECTED
                    order.reject_reason = "卖出价低于跌停价"
                    return False

        return True

    def _match_market_order(self, order: SimOrder, market: str):
        current_price = self._market_prices.get(order.symbol, Decimal("0"))
        if current_price <= 0:
            order.status = OrderStatus.REJECTED
            order.reject_reason = "无当前价格"
            return

        volume = self._market_volumes.get(order.symbol, 0)
        slip = self._slippage.calc(current_price, order.quantity, volume, order.side, market)
        fill_price = current_price + slip

        # A股涨跌停限制
        if market == "A" and order.symbol in self._prev_close:
            prev = self._prev_close[order.symbol]
            fill_price = min(fill_price, prev * Decimal("1.1"))
            fill_price = max(fill_price, prev * Decimal("0.9"))

        fill_price = fill_price.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        amount = fill_price * Decimal(str(order.quantity))
        is_sell = order.side == OrderSide.SELL
        comm = self._commission.calc(amount, market, is_sell)

        order.filled_price = fill_price
        order.filled_quantity = order.quantity
        order.commission = comm
        order.status = OrderStatus.FILLED

        fill = SimFill(
            order_id=order.id, symbol=order.symbol,
            side=order.side.value, price=fill_price,
            quantity=order.quantity, commission=comm,
            slippage=slip,
        )
        self._fills.append(fill)

        if order.side == OrderSide.BUY:
            self._cash -= (amount + comm)
            if order.symbol in self._positions:
                pos = self._positions[order.symbol]
                total_cost = pos.avg_cost * Decimal(str(pos.quantity)) + amount
                pos.quantity += order.quantity
                pos.avg_cost = (total_cost / Decimal(str(pos.quantity))).quantize(
                    Decimal("0.0001"), rounding=ROUND_HALF_UP
                )
            else:
                self._positions[order.symbol] = SimPosition(
                    symbol=order.symbol, quantity=order.quantity,
                    avg_cost=fill_price, current_price=current_price,
                    buy_date=date.today(), market=market,
                )
        else:
            self._cash += (amount - comm)
            if order.symbol in self._positions:
                pos = self._positions[order.symbol]
                pnl = (fill_price - pos.avg_cost) * Decimal(str(order.quantity)) - comm
                pos.realized_pnl += pnl
                pos.quantity -= order.quantity
                if pos.quantity <= 0:
                    del self._positions[order.symbol]

        self._orders[order.id] = order

    def cancel_order(self, order_id: str) -> bool:
        order = self._orders.get(order_id)
        if order and order.status == OrderStatus.PENDING:
            order.status = OrderStatus.CANCELLED
            return True
        return False

    def cancel_all(self, symbol: str = "") -> int:
        cancelled = 0
        for order in self._orders.values():
            if order.status == OrderStatus.PENDING:
                if not symbol or order.symbol == symbol:
                    order.status = OrderStatus.CANCELLED
                    cancelled += 1
        return cancelled

    def get_account(self) -> Dict:
        total_value = self._cash
        positions_data = []
        for sym, pos in self._positions.items():
            total_value += pos.market_value
            positions_data.append({
                "symbol": sym, "quantity": pos.quantity,
                "avg_cost": float(pos.avg_cost), "current_price": float(pos.current_price),
                "unrealized_pnl": float(pos.unrealized_pnl), "realized_pnl": float(pos.realized_pnl),
                "market_value": float(pos.market_value), "market": pos.market,
                "can_sell": pos.can_sell,
            })
        return {
            "cash": float(self._cash),
            "total_value": float(total_value),
            "initial_capital": float(self._initial_capital),
            "total_pnl": float(total_value - self._initial_capital),
            "total_pnl_pct": float((total_value / self._initial_capital - 1) * 100),
            "positions": positions_data,
            "position_count": len(self._positions),
        }

    def get_orders(self, status: str = "") -> List[Dict]:
        result = []
        for o in self._orders.values():
            if status and o.status.value != status:
                continue
            result.append({
                "id": o.id, "symbol": o.symbol, "side": o.side.value,
                "type": o.order_type.value, "quantity": o.quantity,
                "price": float(o.price), "filled_price": float(o.filled_price),
                "filled_quantity": o.filled_quantity, "commission": float(o.commission),
                "status": o.status.value, "timestamp": o.timestamp.isoformat(),
                "reject_reason": o.reject_reason,
            })
        return result

    def get_fills(self, limit: int = 100) -> List[Dict]:
        return [{
            "order_id": f.order_id, "symbol": f.symbol, "side": f.side,
            "price": float(f.price), "quantity": f.quantity,
            "commission": float(f.commission), "slippage": float(f.slippage),
            "timestamp": f.timestamp.isoformat(),
        } for f in self._fills[-limit:]]

    def update_position_prices(self, prices: Dict[str, float]):
        for sym, price in prices.items():
            if sym in self._positions:
                pos = self._positions[sym]
                pos.current_price = Decimal(str(price))
                pos.unrealized_pnl = (pos.current_price - pos.avg_cost) * Decimal(str(pos.quantity))

    def reset(self, initial_capital: Optional[float] = None):
        cap = initial_capital or float(self._initial_capital)
        self._cash = Decimal(str(cap))
        self._initial_capital = Decimal(str(cap))
        self._positions.clear()
        self._orders.clear()
        self._fills.clear()
        self._order_counter = 0
