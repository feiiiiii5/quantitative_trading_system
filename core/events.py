from collections import defaultdict
from enum import Enum
from typing import Any, Callable, Dict, List, Optional
import logging

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


class Event:
    __slots__ = ("event_type", "data")

    def __init__(self, event_type: EventType, data: Optional[Dict[str, Any]] = None):
        self.event_type = event_type
        self.data = data or {}

    def __repr__(self):
        return f"Event({self.event_type.value}, {self.data})"


class EventBus:
    def __init__(self):
        self._handlers: Dict[EventType, List[Callable]] = defaultdict(list)
        self._once_handlers: Dict[EventType, List[Callable]] = defaultdict(list)

    def subscribe(self, event_type: EventType, handler: Callable) -> None:
        self._handlers[event_type].append(handler)

    def subscribe_once(self, event_type: EventType, handler: Callable) -> None:
        self._once_handlers[event_type].append(handler)

    def unsubscribe(self, event_type: EventType, handler: Callable) -> None:
        try:
            self._handlers[event_type].remove(handler)
        except ValueError:
            pass
        try:
            self._once_handlers[event_type].remove(handler)
        except ValueError:
            pass

    def publish(self, event: Event) -> None:
        handlers = self._handlers.get(event.event_type, [])
        for handler in handlers:
            try:
                handler(event)
            except Exception as e:
                logger.error(f"Event handler error for {event.event_type.value}: {e}")

        once_handlers = self._once_handlers.pop(event.event_type, [])
        for handler in once_handlers:
            try:
                handler(event)
            except Exception as e:
                logger.error(f"Once handler error for {event.event_type.value}: {e}")

    def clear(self) -> None:
        self._handlers.clear()
        self._once_handlers.clear()
