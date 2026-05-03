import pytest
from core.orders import Order, OrderSide, OrderType, OrderStatus, Trade


class TestOrder:
    def test_create_order(self):
        order = Order(
            order_id="test-001",
            symbol="000001",
            side=OrderSide.BUY,
            order_type=OrderType.MARKET,
            quantity=1000,
            price=10.0,
        )
        assert order.order_id == "test-001"
        assert order.symbol == "000001"
        assert order.side == OrderSide.BUY
        assert order.status == OrderStatus.PENDING_NEW
        assert order.unfilled_quantity == 1000
        assert order.is_active
        assert not order.is_done

    def test_valid_transitions(self):
        order = Order(order_id="t", symbol="s", side=OrderSide.BUY, order_type=OrderType.MARKET, quantity=100)
        assert order.transition_to(OrderStatus.ACTIVE)
        assert order.status == OrderStatus.ACTIVE
        assert order.transition_to(OrderStatus.FILLED)
        assert order.status == OrderStatus.FILLED

    def test_invalid_transition(self):
        order = Order(order_id="t", symbol="s", side=OrderSide.BUY, order_type=OrderType.MARKET, quantity=100)
        assert not order.transition_to(OrderStatus.FILLED)
        assert order.status == OrderStatus.PENDING_NEW

    def test_partial_fill(self):
        order = Order(order_id="t", symbol="s", side=OrderSide.BUY, order_type=OrderType.MARKET, quantity=1000, price=10.0)
        order.transition_to(OrderStatus.ACTIVE)
        order.fill(500, 10.0)
        assert order.filled_quantity == 500
        assert order.unfilled_quantity == 500
        assert order.status == OrderStatus.PARTIALLY_FILLED
        assert order.is_active

    def test_full_fill(self):
        order = Order(order_id="t", symbol="s", side=OrderSide.BUY, order_type=OrderType.MARKET, quantity=1000, price=10.0)
        order.transition_to(OrderStatus.ACTIVE)
        order.fill(1000, 10.0, commission=3.0)
        assert order.filled_quantity == 1000
        assert order.status == OrderStatus.FILLED
        assert order.is_done
        assert order.commission == 3.0

    def test_reject(self):
        order = Order(order_id="t", symbol="s", side=OrderSide.BUY, order_type=OrderType.MARKET, quantity=100)
        order.reject("资金不足")
        assert order.status == OrderStatus.REJECTED
        assert order.reject_reason == "资金不足"
        assert order.is_done

    def test_cancel(self):
        order = Order(order_id="t", symbol="s", side=OrderSide.BUY, order_type=OrderType.MARKET, quantity=100)
        order.transition_to(OrderStatus.ACTIVE)
        order.cancel()
        assert order.status == OrderStatus.CANCELLED
        assert order.is_done

    def test_avg_fill_price(self):
        order = Order(order_id="t", symbol="s", side=OrderSide.BUY, order_type=OrderType.MARKET, quantity=1000, price=10.0)
        order.transition_to(OrderStatus.ACTIVE)
        order.fill(500, 10.0)
        order.fill(500, 11.0)
        assert order.filled_quantity == 1000
        assert abs(order.avg_fill_price - 10.5) < 0.01

    def test_overfill_clamps_quantity(self):
        order = Order(order_id="t", symbol="s", side=OrderSide.BUY, order_type=OrderType.MARKET, quantity=100, price=10.0)
        order.transition_to(OrderStatus.ACTIVE)
        order.fill(80, 10.0)
        order.fill(50, 11.0)
        assert order.filled_quantity == 100
        expected_avg = (80 * 10.0 + 20 * 11.0) / 100
        assert abs(order.avg_fill_price - expected_avg) < 0.01
        assert order.filled_value == 80 * 10.0 + 20 * 11.0

    def test_fill_when_already_filled_is_noop(self):
        order = Order(order_id="t", symbol="s", side=OrderSide.BUY, order_type=OrderType.MARKET, quantity=100, price=10.0)
        order.transition_to(OrderStatus.ACTIVE)
        order.fill(100, 10.0)
        order.fill(50, 12.0)
        assert order.filled_quantity == 100
        assert abs(order.avg_fill_price - 10.0) < 0.01

    def test_to_dict(self):
        order = Order(order_id="t", symbol="s", side=OrderSide.BUY, order_type=OrderType.MARKET, quantity=100, price=10.0)
        d = order.to_dict()
        assert d["order_id"] == "t"
        assert d["side"] == "buy"
        assert d["status"] == "pending_new"


class TestTrade:
    def test_create_trade(self):
        trade = Trade(trade_id="tr-1", order_id="t", symbol="000001", side=OrderSide.BUY, quantity=1000, price=10.0)
        assert trade.amount == 10000.0

    def test_trade_to_dict(self):
        trade = Trade(trade_id="tr-1", order_id="t", symbol="000001", side=OrderSide.BUY, quantity=1000, price=10.0)
        d = trade.to_dict()
        assert d["amount"] == 10000.0
