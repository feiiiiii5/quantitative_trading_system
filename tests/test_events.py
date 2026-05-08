from core.events import BacktestProgressTracker, Event, EventBus, EventType


class TestEventBus:
    def test_subscribe_and_publish(self):
        bus = EventBus()
        received = []
        def handler(e):
            received.append(e)
        bus.subscribe(EventType.ON_BAR, handler)
        bus.publish(Event(EventType.ON_BAR, {"bar": 1}))
        assert len(received) == 1
        assert received[0].data["bar"] == 1

    def test_multiple_subscribers(self):
        bus = EventBus()
        count = [0, 0]
        def handler1(e):
            count[0] += 1
        def handler2(e):
            count[1] += 1
        bus.subscribe(EventType.ON_BAR, handler1)
        bus.subscribe(EventType.ON_BAR, handler2)
        bus.publish(Event(EventType.ON_BAR))
        assert count == [1, 1]

    def test_subscribe_once(self):
        bus = EventBus()
        count = [0]
        def handler(e):
            count[0] += 1
        bus.subscribe_once(EventType.INIT, handler)
        bus.publish(Event(EventType.INIT))
        bus.publish(Event(EventType.INIT))
        assert count[0] == 1

    def test_unsubscribe(self):
        bus = EventBus()
        count = [0]
        def handler(e):
            count[0] += 1
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
        def bad_handler(_e):
            _ = 1 / 0  # Intentional division by zero for testing
        def good_handler(_e):
            count[0] += 1
        bus.subscribe(EventType.ON_BAR, bad_handler)
        bus.subscribe(EventType.ON_BAR, good_handler)
        bus.publish(Event(EventType.ON_BAR))
        assert count[0] == 1

    def test_clear(self):
        bus = EventBus()
        count = [0]
        def handler(e):
            count[0] += 1
        bus.subscribe(EventType.ON_BAR, handler)
        bus.clear()
        bus.publish(Event(EventType.ON_BAR))
        assert count[0] == 0

    def test_event_types_complete(self):
        expected = [
            "INIT", "BEFORE_TRADING", "ON_BAR", "AFTER_TRADING", "ON_TICK",
            "ORDER_PENDING_NEW", "ORDER_CREATED", "ORDER_REJECTED", "ORDER_CANCELLED",
            "TRADE_FILLED", "POST_SETTLEMENT", "RISK_CHECK",
            "STOPLOSS_TRIGGERED", "TAKEPROFIT_TRIGGERED",
            "BACKTEST_STARTED", "BACKTEST_PROGRESS", "BACKTEST_TRADE",
            "BACKTEST_COMPLETED", "BACKTEST_ERROR",
        ]
        for name in expected:
            assert hasattr(EventType, name), f"Missing EventType.{name}"


class TestBacktestProgressTracker:
    def test_start_and_progress(self):
        bus = EventBus()
        events = []
        def on_started(e):
            events.append(("started", e.data))
        def on_progress(e):
            events.append(("progress", e.data))
        bus.subscribe(EventType.BACKTEST_STARTED, on_started)
        bus.subscribe(EventType.BACKTEST_PROGRESS, on_progress)
        tracker = BacktestProgressTracker(bus)
        tracker.start("test_strategy", 100)
        assert len(events) == 1
        assert events[0][0] == "started"
        assert events[0][1]["strategy"] == "test_strategy"
        tracker.on_bar(5, 1000000.0, "2024-01-05")
        tracker.on_bar(10, 1005000.0, "2024-01-10")
        progress_events = [e for e in events if e[0] == "progress"]
        assert len(progress_events) >= 1

    def test_trade_events(self):
        bus = EventBus()
        events = []
        def on_trade(e):
            events.append(e.data)
        bus.subscribe(EventType.BACKTEST_TRADE, on_trade)
        tracker = BacktestProgressTracker(bus)
        tracker.start("test", 100)
        tracker.on_trade("buy", 10.5, 100, "2024-01-05")
        tracker.on_trade("sell", 11.0, 100, "2024-01-10")
        assert len(events) == 2
        assert events[0]["action"] == "buy"
        assert events[1]["action"] == "sell"
        assert events[1]["trade_number"] == 2

    def test_complete_event(self):
        bus = EventBus()
        events = []
        def on_completed(e):
            events.append(e.data)
        bus.subscribe(EventType.BACKTEST_COMPLETED, on_completed)
        tracker = BacktestProgressTracker(bus)
        tracker.start("test", 100)
        tracker.complete({"sharpe_ratio": 1.5})
        assert len(events) == 1
        assert events[0]["result"]["sharpe_ratio"] == 1.5

    def test_progress_property(self):
        tracker = BacktestProgressTracker()
        tracker.start("test", 100)
        assert tracker.progress == 0.0
        tracker.on_bar(50, 1000000.0, "")
        assert 0.0 < tracker.progress <= 1.0

    def test_no_bus_no_crash(self):
        tracker = BacktestProgressTracker()
        tracker.start("test", 100)
        tracker.on_bar(10, 1000000.0, "")
        tracker.on_trade("buy", 10.0, 100, "")
        tracker.complete({})
        tracker.error("test error")
