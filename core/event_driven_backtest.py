import heapq
import logging
import uuid
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import date, datetime
from typing import Any

import numpy as np

from core.events import Event, EventBus, EventType
from core.orders import Order, OrderSide, OrderType

logger = logging.getLogger(__name__)


@dataclass
class BarEvent:
    timestamp: datetime
    symbol: str
    open: float
    high: float
    low: float
    close: float
    volume: float
    amount: float = 0.0

    @property
    def vwap(self) -> float:
        if self.volume > 0:
            return self.amount / self.volume
        return self.close


@dataclass
class TickEvent:
    timestamp: datetime
    symbol: str
    price: float
    volume: float
    side: str = ""
    order_book: dict[str, Any] = field(default_factory=dict)


@dataclass
class OrderEvent:
    timestamp: datetime
    symbol: str
    side: OrderSide
    order_type: OrderType
    quantity: int
    price: float | None = None
    stop_price: float | None = None
    strategy_name: str = ""
    order_id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])

    def to_order(self) -> Order:
        return Order(
            order_id=self.order_id,
            symbol=self.symbol,
            side=self.side,
            order_type=self.order_type,
            quantity=self.quantity,
            price=self.price,
            stop_price=self.stop_price,
            strategy_name=self.strategy_name,
        )


@dataclass
class FillEvent:
    timestamp: datetime
    symbol: str
    side: OrderSide
    quantity: int
    price: float
    commission: float = 0.0
    stamp_tax: float = 0.0
    transfer_fee: float = 0.0
    market_impact: float = 0.0
    slippage: float = 0.0
    order_id: str = ""
    strategy_name: str = ""

    @property
    def total_fees(self) -> float:
        return self.commission + self.stamp_tax + self.transfer_fee + self.market_impact

    @property
    def net_amount(self) -> float:
        gross = self.quantity * self.price
        if self.side == OrderSide.BUY:
            return gross + self.total_fees
        return gross - self.total_fees


@dataclass
class DailyPnLRecord:
    date: date
    holding_pnl: float = 0.0
    trading_pnl: float = 0.0
    fees: float = 0.0
    total_pnl: float = 0.0


class AShareCostModel:
    def __init__(
        self,
        commission_rate: float = 0.0002,
        min_commission: float = 5.0,
        stamp_tax_rate: float = 0.001,
        transfer_fee_rate: float = 0.00001,
        impact_coefficient: float = 0.1,
    ):
        self.commission_rate = commission_rate
        self.min_commission = min_commission
        self.stamp_tax_rate = stamp_tax_rate
        self.transfer_fee_rate = transfer_fee_rate
        self.impact_coefficient = impact_coefficient

    def _is_shanghai(self, symbol: str) -> bool:
        return symbol.startswith("6")

    def _calc_market_impact(self, price: float, quantity: int, daily_amount: float) -> float:
        if daily_amount <= 0:
            return 0.0
        order_amount = price * quantity
        participation_rate = order_amount / daily_amount
        impact = self.impact_coefficient * price * np.sqrt(participation_rate) * quantity
        return round(impact, 2)

    def calc_buy_cost(
        self,
        symbol: str,
        price: float,
        quantity: int,
        daily_amount: float = 0.0,
    ) -> dict[str, float]:
        amount = price * quantity
        commission = max(amount * self.commission_rate, self.min_commission)
        transfer_fee = quantity * self.transfer_fee_rate if self._is_shanghai(symbol) else 0.0
        market_impact = self._calc_market_impact(price, quantity, daily_amount)
        total = commission + transfer_fee + market_impact
        return {
            "commission": round(commission, 2),
            "stamp_tax": 0.0,
            "transfer_fee": round(transfer_fee, 2),
            "market_impact": round(market_impact, 2),
            "total": round(total, 2),
        }

    def calc_sell_cost(
        self,
        symbol: str,
        price: float,
        quantity: int,
        daily_amount: float = 0.0,
    ) -> dict[str, float]:
        amount = price * quantity
        commission = max(amount * self.commission_rate, self.min_commission)
        stamp_tax = amount * self.stamp_tax_rate
        transfer_fee = quantity * self.transfer_fee_rate if self._is_shanghai(symbol) else 0.0
        market_impact = self._calc_market_impact(price, quantity, daily_amount)
        total = commission + stamp_tax + transfer_fee + market_impact
        return {
            "commission": round(commission, 2),
            "stamp_tax": round(stamp_tax, 2),
            "transfer_fee": round(transfer_fee, 2),
            "market_impact": round(market_impact, 2),
            "total": round(total, 2),
        }

    def create_fill_event(
        self,
        symbol: str,
        side: OrderSide,
        quantity: int,
        price: float,
        timestamp: datetime,
        daily_amount: float = 0.0,
        slippage: float = 0.0,
        order_id: str = "",
        strategy_name: str = "",
    ) -> FillEvent:
        if side == OrderSide.BUY:
            cost = self.calc_buy_cost(symbol, price, quantity, daily_amount)
        else:
            cost = self.calc_sell_cost(symbol, price, quantity, daily_amount)
        return FillEvent(
            timestamp=timestamp,
            symbol=symbol,
            side=side,
            quantity=quantity,
            price=price,
            commission=cost["commission"],
            stamp_tax=cost["stamp_tax"],
            transfer_fee=cost["transfer_fee"],
            market_impact=cost["market_impact"],
            slippage=slippage,
            order_id=order_id,
            strategy_name=strategy_name,
        )


@dataclass
class PositionRecord:
    symbol: str
    quantity: int = 0
    avg_cost: float = 0.0
    buy_date: date | None = None
    sector: str = ""
    current_price: float = 0.0

    @property
    def market_value(self) -> float:
        return self.quantity * self.current_price

    @property
    def unrealized_pnl(self) -> float:
        return (self.current_price - self.avg_cost) * self.quantity if self.avg_cost > 0 else 0.0

    @property
    def can_sell(self) -> bool:
        if self.buy_date is None:
            return True
        return date.today() > self.buy_date


class T1Constraint:
    def __init__(self, margin_mode: bool = False):
        self.margin_mode = margin_mode
        self._buy_dates: dict[str, date] = {}

    def record_buy(self, symbol: str, trade_date: date) -> None:
        self._buy_dates[symbol] = trade_date

    def can_sell(self, symbol: str, current_date: date) -> bool:
        buy_date = self._buy_dates.get(symbol)
        if buy_date is None:
            return True
        if self.margin_mode:
            return True
        return current_date > buy_date

    def check_and_reject(
        self,
        symbol: str,
        side: OrderSide,
        current_date: date,
    ) -> tuple[bool, str]:
        if side == OrderSide.BUY:
            return True, ""
        if self.can_sell(symbol, current_date):
            return True, ""
        buy_date = self._buy_dates.get(symbol)
        return False, f"T+1 violation: bought on {buy_date}, cannot sell on {current_date}"

    def clear(self) -> None:
        self._buy_dates.clear()


def check_capacity(
    symbol: str,
    order_quantity: int,
    price: float,
    adv_history: list[float],
    threshold_pct: float = 0.05,
    lookback: int = 20,
) -> dict[str, Any]:
    if not adv_history:
        return {"symbol": symbol, "capacity_ok": True, "warning": ""}
    recent_adv = adv_history[-lookback:] if len(adv_history) >= lookback else adv_history
    adv = float(np.mean(recent_adv)) if recent_adv else 0.0
    if adv <= 0:
        return {"symbol": symbol, "capacity_ok": True, "warning": ""}
    order_amount = order_quantity * price
    participation = order_amount / adv
    capacity_ok = participation <= threshold_pct
    warning = ""
    if not capacity_ok:
        warning = (
            f"Capacity warning for {symbol}: order {order_amount:,.0f} CNY "
            f"is {participation:.1%} of ADV {adv:,.0f} CNY (threshold {threshold_pct:.0%})"
        )
        logger.warning(warning)
    return {
        "symbol": symbol,
        "capacity_ok": capacity_ok,
        "participation_rate": round(participation, 6),
        "adv_20d": round(adv, 2),
        "order_amount": round(order_amount, 2),
        "warning": warning,
    }


def simulate_partial_fill(
    order_event: OrderEvent,
    bar: BarEvent,
    adv_history: list[float],
    n_slices: int = 4,
    lot_size: int = 100,
    rng: np.random.Generator | None = None,
) -> list[FillEvent]:
    if rng is None:
        rng = np.random.default_rng()
    total_qty = order_event.quantity
    if total_qty <= 0:
        return []

    daily_amount = bar.amount if bar.amount > 0 else bar.volume * bar.close
    capacity = check_capacity(order_event.symbol, total_qty, bar.close, adv_history)

    if capacity["capacity_ok"] or n_slices <= 1:
        fill_price = bar.close * (1 + rng.normal(0, 0.001))
        if order_event.side == OrderSide.BUY:
            fill_price = max(fill_price, bar.close * (1 - 0.001))
        else:
            fill_price = min(fill_price, bar.close * (1 + 0.001))
        slippage = abs(fill_price - bar.close) * total_qty
        cost_model = AShareCostModel()
        fill = cost_model.create_fill_event(
            symbol=order_event.symbol,
            side=order_event.side,
            quantity=total_qty,
            price=round(fill_price, 4),
            timestamp=order_event.timestamp,
            daily_amount=daily_amount,
            slippage=round(slippage, 2),
            order_id=order_event.order_id,
            strategy_name=order_event.strategy_name,
        )
        return [fill]

    fills: list[FillEvent] = []
    per_slice = (total_qty // n_slices // lot_size) * lot_size
    remaining = total_qty
    cost_model = AShareCostModel()

    for i in range(n_slices):
        slice_qty = per_slice if i < n_slices - 1 else remaining
        if slice_qty <= 0:
            break
        remaining -= slice_qty
        noise = rng.normal(0, 0.0005 * (i + 1))
        fill_price = bar.close * (1 + noise)
        fill_price = round(max(fill_price, bar.low * 0.99), 4)
        fill_price = round(min(fill_price, bar.high * 1.01), 4)
        slippage = abs(fill_price - bar.close) * slice_qty
        fill = cost_model.create_fill_event(
            symbol=order_event.symbol,
            side=order_event.side,
            quantity=slice_qty,
            price=fill_price,
            timestamp=order_event.timestamp,
            daily_amount=daily_amount,
            slippage=round(slippage, 2),
            order_id=order_event.order_id,
            strategy_name=order_event.strategy_name,
        )
        fills.append(fill)

    return fills


class Portfolio:
    def __init__(self, initial_cash: float = 1_000_000.0):
        self.cash: float = initial_cash
        self.initial_cash: float = initial_cash
        self.positions: dict[str, PositionRecord] = {}
        self.peak_value: float = initial_cash
        self.daily_pnl_records: list[DailyPnLRecord] = []
        self._sector_map: dict[str, str] = {}
        self._prev_total_value: float = initial_cash

    @property
    def total_value(self) -> float:
        positions_value = sum(p.market_value for p in self.positions.values())
        return self.cash + positions_value

    @property
    def max_drawdown(self) -> float:
        if self.peak_value <= 0:
            return 0.0
        return round((self.peak_value - self.total_value) / self.peak_value * 100, 2)

    def update_price(self, symbol: str, price: float) -> None:
        if symbol in self.positions:
            self.positions[symbol].current_price = price

    def process_fill(self, fill: FillEvent) -> None:
        if fill.side == OrderSide.BUY:
            self._apply_buy(fill)
        else:
            self._apply_sell(fill)
        self._update_peak()

    def _apply_buy(self, fill: FillEvent) -> None:
        total_cost = fill.net_amount
        if total_cost > self.cash:
            affordable_qty = int(self.cash / fill.price / 100) * 100
            if affordable_qty <= 0:
                logger.warning("Insufficient cash for buy order %s", fill.order_id)
                return
            fill.quantity = affordable_qty
            total_cost = fill.net_amount
        self.cash -= total_cost
        trade_date = fill.timestamp.date() if isinstance(fill.timestamp, datetime) else fill.timestamp
        if fill.symbol in self.positions:
            pos = self.positions[fill.symbol]
            total_qty = pos.quantity + fill.quantity
            if total_qty > 0:
                pos.avg_cost = (pos.avg_cost * pos.quantity + fill.price * fill.quantity) / total_qty
            pos.quantity = total_qty
            pos.buy_date = trade_date
        else:
            self.positions[fill.symbol] = PositionRecord(
                symbol=fill.symbol,
                quantity=fill.quantity,
                avg_cost=fill.price,
                buy_date=trade_date,
                current_price=fill.price,
                sector=self._sector_map.get(fill.symbol, ""),
            )

    def _apply_sell(self, fill: FillEvent) -> None:
        if fill.symbol not in self.positions:
            logger.warning("Sell on non-existent position: %s", fill.symbol)
            return
        pos = self.positions[fill.symbol]
        sell_qty = min(fill.quantity, pos.quantity)
        fill.quantity = sell_qty
        self.cash += fill.net_amount
        pos.quantity -= sell_qty
        if pos.quantity <= 0:
            del self.positions[fill.symbol]

    def _update_peak(self) -> None:
        current = self.total_value
        if current > self.peak_value:
            self.peak_value = current

    def record_daily_pnl(self, record_date: date) -> DailyPnLRecord:
        current_value = self.total_value
        holding_pnl = sum(p.unrealized_pnl for p in self.positions.values())
        total_pnl = current_value - self._prev_total_value
        trading_pnl = total_pnl - holding_pnl
        fees = 0.0
        if self.daily_pnl_records:
            fees = total_pnl - trading_pnl - holding_pnl
        record = DailyPnLRecord(
            date=record_date,
            holding_pnl=round(holding_pnl, 2),
            trading_pnl=round(trading_pnl, 2),
            fees=round(fees, 2),
            total_pnl=round(total_pnl, 2),
        )
        self.daily_pnl_records.append(record)
        self._prev_total_value = current_value
        return record

    def position_weight(self, symbol: str) -> float:
        total = self.total_value
        if total <= 0 or symbol not in self.positions:
            return 0.0
        return self.positions[symbol].market_value / total

    def sector_exposure(self) -> dict[str, float]:
        total = self.total_value
        if total <= 0:
            return {}
        exposure: dict[str, float] = {}
        for pos in self.positions.values():
            sector = pos.sector or "unknown"
            exposure[sector] = exposure.get(sector, 0.0) + pos.market_value
        return {s: round(v / total, 6) for s, v in exposure.items()}

    def set_sector_map(self, sector_map: dict[str, str]) -> None:
        self._sector_map = sector_map
        for symbol, pos in self.positions.items():
            if symbol in sector_map:
                pos.sector = sector_map[symbol]


StrategyCallback = Callable[[BarEvent, Portfolio], list[OrderEvent]]


class EventDrivenBacktestEngine:
    def __init__(
        self,
        initial_cash: float = 1_000_000.0,
        cost_model: AShareCostModel | None = None,
        margin_mode: bool = False,
        event_bus: EventBus | None = None,
        lot_size: int = 100,
        slippage_pct: float = 0.001,
        capacity_threshold: float = 0.05,
        partial_fill_slices: int = 4,
        rng_seed: int = 42,
    ):
        self._initial_cash = initial_cash
        self._cost_model = cost_model or AShareCostModel()
        self._t1 = T1Constraint(margin_mode=margin_mode)
        self._event_bus = event_bus or EventBus()
        self._lot_size = lot_size
        self._slippage_pct = slippage_pct
        self._capacity_threshold = capacity_threshold
        self._partial_fill_slices = partial_fill_slices
        self._rng = np.random.default_rng(rng_seed)
        self._portfolio = Portfolio(initial_cash)
        self._event_queue: list[tuple[int, Any]] = []
        self._adv_history: dict[str, list[float]] = {}
        self._sequence = 0

    @property
    def portfolio(self) -> Portfolio:
        return self._portfolio

    def _push_event(self, priority: int, event: Any) -> None:
        self._sequence += 1
        heapq.heappush(self._event_queue, (priority, self._sequence, event))

    def _process_bar(self, bar: BarEvent) -> None:
        self._update_adv(bar)
        self._portfolio.update_price(bar.symbol, bar.close)
        self._event_bus.publish(Event(EventType.ON_BAR, {
            "symbol": bar.symbol,
            "close": bar.close,
            "volume": bar.volume,
        }))

    def _update_adv(self, bar: BarEvent) -> None:
        daily_amount = bar.amount if bar.amount > 0 else bar.volume * bar.close
        if bar.symbol not in self._adv_history:
            self._adv_history[bar.symbol] = []
        self._adv_history[bar.symbol].append(daily_amount)

    def _process_order(self, order_event: OrderEvent, current_bar: BarEvent) -> list[FillEvent]:
        if order_event.side == OrderSide.SELL:
            allowed, reason = self._t1.check_and_reject(
                order_event.symbol, order_event.side, current_bar.timestamp.date()
            )
            if not allowed:
                logger.info("Order rejected: %s", reason)
                self._event_bus.publish(Event(EventType.ORDER_REJECTED, {
                    "order_id": order_event.order_id,
                    "reason": reason,
                }))
                return []

        if order_event.side == OrderSide.SELL:
            pos = self._portfolio.positions.get(order_event.symbol)
            if pos is not None and order_event.quantity > pos.quantity:
                order_event.quantity = pos.quantity

        if order_event.side == OrderSide.BUY:
            max_affordable = int(self._portfolio.cash * 0.98 / current_bar.close / self._lot_size) * self._lot_size
            if order_event.quantity > max_affordable:
                order_event.quantity = max_affordable

        if order_event.quantity <= 0:
            return []

        adv = self._adv_history.get(order_event.symbol, [])
        fills = simulate_partial_fill(
            order_event=order_event,
            bar=current_bar,
            adv_history=adv,
            n_slices=self._partial_fill_slices,
            lot_size=self._lot_size,
            rng=self._rng,
        )

        if order_event.side == OrderSide.BUY:
            self._t1.record_buy(order_event.symbol, current_bar.timestamp.date())

        self._event_bus.publish(Event(EventType.ORDER_CREATED, {
            "order_id": order_event.order_id,
            "symbol": order_event.symbol,
            "side": order_event.side.value,
            "quantity": order_event.quantity,
        }))

        return fills

    def _process_fill(self, fill: FillEvent) -> None:
        self._portfolio.process_fill(fill)
        self._event_bus.publish(Event(EventType.TRADE_FILLED, {
            "symbol": fill.symbol,
            "side": fill.side.value,
            "quantity": fill.quantity,
            "price": fill.price,
            "total_fees": fill.total_fees,
            "order_id": fill.order_id,
        }))

    def run(
        self,
        bars: list[BarEvent],
        strategy: StrategyCallback,
    ) -> dict[str, Any]:
        self._portfolio = Portfolio(self._initial_cash)
        self._t1.clear()
        self._adv_history.clear()
        self._event_queue.clear()
        self._sequence = 0

        if not bars:
            return self._build_result()

        self._event_bus.publish(Event(EventType.BACKTEST_STARTED, {
            "initial_cash": self._initial_cash,
            "total_bars": len(bars),
        }))

        current_date = None
        for bar in bars:
            bar_date = bar.timestamp.date() if isinstance(bar.timestamp, datetime) else bar.timestamp
            if current_date is not None and bar_date > current_date:
                self._portfolio.record_daily_pnl(current_date)
            current_date = bar_date

            self._process_bar(bar)

            signals = strategy(bar, self._portfolio)
            for order_event in signals:
                fills = self._process_order(order_event, bar)
                for fill in fills:
                    self._process_fill(fill)

            self._portfolio._update_peak()

        if current_date is not None:
            self._portfolio.record_daily_pnl(current_date)

        self._event_bus.publish(Event(EventType.BACKTEST_COMPLETED, {
            "final_value": round(self._portfolio.total_value, 2),
            "total_return": round(
                (self._portfolio.total_value - self._initial_cash) / self._initial_cash * 100, 4
            ),
        }))

        return self._build_result()

    def _build_result(self) -> dict[str, Any]:
        total_value = self._portfolio.total_value
        total_return = (
            (total_value - self._initial_cash) / self._initial_cash * 100
            if self._initial_cash > 0 else 0.0
        )
        max_dd = self._portfolio.max_drawdown
        pnl_records = self._portfolio.daily_pnl_records
        daily_returns = []
        if len(pnl_records) > 1:
            for i in range(1, len(pnl_records)):
                prev_total = (
                    self._initial_cash + sum(r.total_pnl for r in pnl_records[:i])
                )
                if prev_total > 0:
                    daily_returns.append(pnl_records[i].total_pnl / prev_total)

        sharpe = 0.0
        if daily_returns:
            ret_arr = np.array(daily_returns)
            std = float(np.std(ret_arr))
            if std > 0:
                sharpe = float(np.mean(ret_arr)) / std * np.sqrt(252)

        return {
            "initial_cash": self._initial_cash,
            "final_value": round(total_value, 2),
            "total_return": round(total_return, 4),
            "max_drawdown": round(max_dd, 2),
            "sharpe_ratio": round(sharpe, 2),
            "positions": {
                sym: {
                    "quantity": pos.quantity,
                    "avg_cost": round(pos.avg_cost, 4),
                    "market_value": round(pos.market_value, 2),
                    "unrealized_pnl": round(pos.unrealized_pnl, 2),
                }
                for sym, pos in self._portfolio.positions.items()
            },
            "sector_exposure": self._portfolio.sector_exposure(),
            "daily_pnl": [
                {
                    "date": r.date.isoformat(),
                    "holding_pnl": r.holding_pnl,
                    "trading_pnl": r.trading_pnl,
                    "fees": r.fees,
                    "total_pnl": r.total_pnl,
                }
                for r in pnl_records
            ],
        }
