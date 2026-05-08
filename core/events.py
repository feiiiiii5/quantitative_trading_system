import contextlib
import logging
import threading
import time
from collections import defaultdict
from collections.abc import Callable
from enum import Enum
from typing import Any

logger = logging.getLogger(__name__)


class EventType(Enum):
    INIT = "init"
    BEFORE_TRADING = "before_trading"
    ON_BAR = "on_bar"
    AFTER_TRADING = "after_trading"
    ON_TICK = "on_tick"
    ORDER_PENDING_NEW = "order_pending_new"
    ORDER_CREATED = "order_created"
    ORDER_REJECTED = "order_rejected"
    ORDER_CANCELLED = "order_cancelled"
    TRADE_FILLED = "trade_filled"
    POST_SETTLEMENT = "post_settlement"
    RISK_CHECK = "risk_check"
    STOPLOSS_TRIGGERED = "stoploss_triggered"
    TAKEPROFIT_TRIGGERED = "takeprofit_triggered"
    BACKTEST_STARTED = "backtest_started"
    BACKTEST_PROGRESS = "backtest_progress"
    BACKTEST_TRADE = "backtest_trade"
    BACKTEST_COMPLETED = "backtest_completed"
    BACKTEST_ERROR = "backtest_error"


class Event:
    __slots__ = ("event_type", "data")

    def __init__(self, event_type: EventType, data: dict[str, Any] | None = None):
        self.event_type = event_type
        self.data = data or {}

    def __repr__(self):
        return f"Event({self.event_type.value}, {self.data})"


class EventBus:
    def __init__(self):
        self._handlers: dict[EventType, list[Callable]] = defaultdict(list)
        self._once_handlers: dict[EventType, list[Callable]] = defaultdict(list)
        self._lock = threading.Lock()

    def subscribe(self, event_type: EventType, handler: Callable) -> None:
        with self._lock:
            self._handlers[event_type].append(handler)

    def subscribe_once(self, event_type: EventType, handler: Callable) -> None:
        with self._lock:
            self._once_handlers[event_type].append(handler)

    def unsubscribe(self, event_type: EventType, handler: Callable) -> None:
        with self._lock:
            with contextlib.suppress(ValueError):
                self._handlers[event_type].remove(handler)
            with contextlib.suppress(ValueError):
                self._once_handlers[event_type].remove(handler)

    def publish(self, event: Event) -> None:
        with self._lock:
            handlers = list(self._handlers.get(event.event_type, []))
            once_handlers = self._once_handlers.pop(event.event_type, [])
        for handler in handlers:
            try:
                handler(event)
            except Exception as e:
                logger.error("Event handler error for %s: %s", event, e)
        for handler in once_handlers:
            try:
                handler(event)
            except Exception as e:
                logger.error("Once handler error for %s: %s", event, e)

    def clear(self) -> None:
        with self._lock:
            self._handlers.clear()
            self._once_handlers.clear()


class BacktestProgressTracker:
    """回测进度追踪器，通过EventBus发布实时进度事件，支持WebSocket推送"""

    def __init__(self, event_bus: EventBus | None = None):
        self._event_bus = event_bus
        self._total_bars = 0
        self._current_bar = 0
        self._trades: list[dict] = []
        self._equity_snapshots: list[dict] = []
        self._start_time: float | None = None
        self._strategy_name = ""

    def start(self, strategy_name: str, total_bars: int) -> None:
        self._strategy_name = strategy_name
        self._total_bars = total_bars
        self._current_bar = 0
        self._trades = []
        self._equity_snapshots = []
        self._start_time = time.monotonic()
        if self._event_bus:
            self._event_bus.publish(Event(EventType.BACKTEST_STARTED, {
                "strategy": strategy_name,
                "total_bars": total_bars,
            }))

    def on_bar(self, bar_index: int, equity: float, date_str: str = "") -> None:
        self._current_bar = bar_index
        if self._total_bars > 0 and bar_index % max(1, self._total_bars // 20) == 0:
            progress = bar_index / self._total_bars
            self._equity_snapshots.append({"date": date_str, "equity": round(equity, 2)})
            if self._event_bus:
                self._event_bus.publish(Event(EventType.BACKTEST_PROGRESS, {
                    "strategy": self._strategy_name,
                    "progress": round(progress, 4),
                    "bar": bar_index,
                    "total": self._total_bars,
                    "equity": round(equity, 2),
                    "date": date_str,
                    "elapsed_seconds": round(time.monotonic() - self._start_time, 2) if self._start_time else 0,
                }))

    def on_trade(self, action: str, price: float, shares: int, date_str: str = "") -> None:
        self._trades.append({"action": action, "price": price, "shares": shares, "date": date_str})
        if self._event_bus:
            self._event_bus.publish(Event(EventType.BACKTEST_TRADE, {
                "strategy": self._strategy_name,
                "action": action,
                "price": price,
                "shares": shares,
                "date": date_str,
                "trade_number": len(self._trades),
            }))

    def complete(self, result_summary: dict) -> None:
        if self._event_bus:
            elapsed = round(time.monotonic() - self._start_time, 2) if self._start_time else 0
            self._event_bus.publish(Event(EventType.BACKTEST_COMPLETED, {
                "strategy": self._strategy_name,
                "elapsed_seconds": elapsed,
                "total_trades": len(self._trades),
                "result": result_summary,
            }))

    def error(self, error_msg: str) -> None:
        if self._event_bus:
            self._event_bus.publish(Event(EventType.BACKTEST_ERROR, {
                "strategy": self._strategy_name,
                "error": error_msg,
            }))

    @property
    def progress(self) -> float:
        return self._current_bar / self._total_bars if self._total_bars > 0 else 0.0

    @property
    def trades(self) -> list:
        return self._trades

    @property
    def equity_snapshots(self) -> list:
        return self._equity_snapshots
