import pytest
from core.events import EventBus, Event, EventType


class TestEventBus:
    def test_subscribe_and_publish(self):
        bus = EventBus()
        received = []
        bus.subscribe(EventType.ON_BAR, lambda e: received.append(e))
        bus.publish(Event(EventType.ON_BAR, {"bar": 1}))
        assert len(received) == 1
        assert received[0].data["bar"] == 1

    def test_multiple_subscribers(self):
        bus = EventBus()
        count = [0, 0]
        bus.subscribe(EventType.ON_BAR, lambda e: count.__setitem__(0, count[0] + 1))
        bus.subscribe(EventType.ON_BAR, lambda e: count.__setitem__(1, count[1] + 1))
        bus.publish(Event(EventType.ON_BAR))
        assert count == [1, 1]

    def test_subscribe_once(self):
        bus = EventBus()
        count = [0]
        bus.subscribe_once(EventType.INIT, lambda e: count.__setitem__(0, count[0] + 1))
        bus.publish(Event(EventType.INIT))
        bus.publish(Event(EventType.INIT))
        assert count[0] == 1

    def test_unsubscribe(self):
        bus = EventBus()
        count = [0]
        handler = lambda e: count.__setitem__(0, count[0] + 1)
        bus.subscribe(EventType.ON_BAR, handler)
        bus.publish(Event(EventType.ON_BAR))
        assert count[0] == 1
        bus.unsubscribe(EventType.ON_BAR, handler)
        bus.publish(Event(EventType.ON_BAR))
        assert count[0] == 1

    def test_no_handlers_no_error(self):
        bus = EventBus()
        bus.publish(Event(EventType.ON_BAR))

    def test_handler_exception_doesnt_break_others(self):
        bus = EventBus()
        count = [0]
        bus.subscribe(EventType.ON_BAR, lambda e: 1 / 0)
        bus.subscribe(EventType.ON_BAR, lambda e: count.__setitem__(0, count[0] + 1))
        bus.publish(Event(EventType.ON_BAR))
        assert count[0] == 1

    def test_clear(self):
        bus = EventBus()
        count = [0]
        bus.subscribe(EventType.ON_BAR, lambda e: count.__setitem__(0, count[0] + 1))
        bus.clear()
        bus.publish(Event(EventType.ON_BAR))
        assert count[0] == 0

    def test_event_types_complete(self):
        expected = [
            "INIT", "BEFORE_TRADING", "ON_BAR", "AFTER_TRADING", "ON_TICK",
            "ORDER_PENDING_NEW", "ORDER_CREATED", "ORDER_REJECTED", "ORDER_CANCELLED",
            "TRADE_FILLED", "POST_SETTLEMENT", "RISK_CHECK",
            "STOPLOSS_TRIGGERED", "TAKEPROFIT_TRIGGERED",
        ]
        for name in expected:
            assert hasattr(EventType, name), f"Missing EventType.{name}"
