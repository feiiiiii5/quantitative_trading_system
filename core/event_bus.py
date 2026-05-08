__all__ = ["EventType", "Event", "EventBus", "get_event_bus", "reset_event_bus"]

"""
QuantCore 类型化事件总线
提供发布-订阅模式的事件系统，解耦模块间通信
支持同步和异步事件处理器、事件过滤、事件重放
"""
import asyncio
import logging
import time
from collections import defaultdict
from collections.abc import Callable
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

logger = logging.getLogger(__name__)


class EventType(Enum):
    MARKET_DATA_UPDATED = "market_data_updated"
    ORDER_FILLED = "order_filled"
    ORDER_REJECTED = "order_rejected"
    POSITION_OPENED = "position_opened"
    POSITION_CLOSED = "position_closed"
    PORTFOLIO_REBALANCED = "portfolio_rebalanced"
    RISK_LIMIT_BREACHED = "risk_limit_breached"
    STRATEGY_SIGNAL = "strategy_signal"
    CACHE_INVALIDATED = "cache_invalidated"
    BACKTEST_COMPLETED = "backtest_completed"
    SYSTEM_ERROR = "system_error"


@dataclass
class Event:
    event_type: EventType
    payload: dict[str, Any] = field(default_factory=dict)
    timestamp: float = field(default_factory=time.time)
    source: str = ""
    event_id: str = ""

    def __post_init__(self):
        if not self.event_id:
            import uuid
            self.event_id = uuid.uuid4().hex[:12]


EventHandler = Callable[[Event], None]
AsyncEventHandler = Callable[[Event], Any]


class EventBus:

    def __init__(self, max_history: int = 1000):
        self._sync_handlers: dict[EventType, list[EventHandler]] = defaultdict(list)
        self._async_handlers: dict[EventType, list[AsyncEventHandler]] = defaultdict(list)
        self._wildcard_sync: list[EventHandler] = []
        self._wildcard_async: list[AsyncEventHandler] = []
        self._history: list[Event] = []
        self._max_history = max_history
        self._enabled = True

    def subscribe(
        self,
        event_type: EventType,
        handler: EventHandler | AsyncEventHandler,
    ) -> None:
        if asyncio.iscoroutinefunction(handler):
            self._async_handlers[event_type].append(handler)
        else:
            self._sync_handlers[event_type].append(handler)

    def subscribe_all(self, handler: EventHandler | AsyncEventHandler) -> None:
        if asyncio.iscoroutinefunction(handler):
            self._wildcard_async.append(handler)
        else:
            self._wildcard_sync.append(handler)

    def unsubscribe(
        self,
        event_type: EventType,
        handler: EventHandler | AsyncEventHandler,
    ) -> bool:
        if asyncio.iscoroutinefunction(handler):
            handlers = self._async_handlers.get(event_type, [])
        else:
            handlers = self._sync_handlers.get(event_type, [])

        if handler in handlers:
            handlers.remove(handler)
            return True
        return False

    def publish(self, event: Event) -> None:
        if not self._enabled:
            return

        self._record(event)

        for handler in self._sync_handlers.get(event.event_type, []):
            try:
                handler(event)
            except Exception as e:
                logger.error("Sync handler error for %s: %s", event, e)

        for handler in self._wildcard_sync:
            try:
                handler(event)
            except Exception as e:
                logger.error("Wildcard sync handler error: %s", e)

    async def publish_async(self, event: Event) -> None:
        if not self._enabled:
            return

        self.publish(event)

        for handler in self._async_handlers.get(event.event_type, []):
            try:
                await handler(event)
            except Exception as e:
                logger.error("Async handler error for %s: %s", event, e)

        for handler in self._wildcard_async:
            try:
                await handler(event)
            except Exception as e:
                logger.error("Wildcard async handler error: %s", e)

    def _record(self, event: Event) -> None:
        self._history.append(event)
        if len(self._history) > self._max_history:
            self._history = self._history[-self._max_history:]

    def get_history(
        self,
        event_type: EventType | None = None,
        limit: int = 100,
    ) -> list[Event]:
        if event_type is None:
            return self._history[-limit:]
        return [e for e in self._history if e.event_type == event_type][-limit:]

    def replay(
        self,
        event_type: EventType | None = None,
        handler: EventHandler | AsyncEventHandler | None = None,
    ) -> int:
        events = self.get_history(event_type, limit=self._max_history)
        count = 0
        for event in events:
            if handler:
                try:
                    handler(event)
                except Exception as e:
                    logger.error("Replay handler error: %s", e)
            else:
                self.publish(event)
            count += 1
        return count

    def clear_history(self) -> None:
        self._history.clear()

    def clear_handlers(self) -> None:
        self._sync_handlers.clear()
        self._async_handlers.clear()
        self._wildcard_sync.clear()
        self._wildcard_async.clear()

    @property
    def handler_count(self) -> int:
        sync = sum(len(v) for v in self._sync_handlers.values())
        async_ = sum(len(v) for v in self._async_handlers.values())
        return sync + async_ + len(self._wildcard_sync) + len(self._wildcard_async)

    @property
    def enabled(self) -> bool:
        return self._enabled

    @enabled.setter
    def enabled(self, value: bool) -> None:
        self._enabled = value


_global_bus: EventBus | None = None


def get_event_bus() -> EventBus:
    global _global_bus
    if _global_bus is None:
        _global_bus = EventBus()
    return _global_bus


def reset_event_bus() -> None:
    global _global_bus
    if _global_bus is not None:
        _global_bus.clear_handlers()
        _global_bus.clear_history()
    _global_bus = None
