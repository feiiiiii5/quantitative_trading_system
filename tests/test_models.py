from dataclasses import FrozenInstanceError

import pytest

from core.models import (
    BacktestMetrics,
    CorrelationResult,
    KlineBar,
    MarketDataPoint,
    PortfolioSnapshot,
    Position,
    TradeSignal,
)


class TestTradeSignal:
    def test_creation_with_defaults(self):
        sig = TradeSignal(signal_type="buy")
        assert sig.signal_type == "buy"
        assert sig.strength == 0.0
        assert sig.reason == ""

    def test_creation_with_all_fields(self):
        sig = TradeSignal(signal_type="sell", strength=0.85, reason="momentum")
        assert sig.signal_type == "sell"
        assert sig.strength == 0.85
        assert sig.reason == "momentum"

    def test_frozen_immutability(self):
        sig = TradeSignal(signal_type="hold")
        with pytest.raises(FrozenInstanceError):
            sig.signal_type = "buy"


class TestKlineBar:
    def test_creation(self):
        bar = KlineBar(date="2025-01-01", open=10.0, high=12.0, low=9.0, close=11.0, volume=1000)
        assert bar.date == "2025-01-01"
        assert bar.open == 10.0
        assert bar.amount == 0.0

    def test_typical_price(self):
        bar = KlineBar(date="d", open=10.0, high=12.0, low=9.0, close=11.0, volume=1000)
        assert bar.typical_price == pytest.approx((12.0 + 9.0 + 11.0) / 3.0)

    def test_range(self):
        bar = KlineBar(date="d", open=10.0, high=12.0, low=9.0, close=11.0, volume=1000)
        assert bar.range == pytest.approx(3.0)

    def test_body(self):
        bar = KlineBar(date="d", open=10.0, high=12.0, low=9.0, close=11.0, volume=1000)
        assert bar.body == pytest.approx(1.0)

    def test_is_bullish_true(self):
        bar = KlineBar(date="d", open=10.0, high=12.0, low=9.0, close=11.0, volume=1000)
        assert bar.is_bullish is True

    def test_is_bullish_false(self):
        bar = KlineBar(date="d", open=11.0, high=12.0, low=9.0, close=10.0, volume=1000)
        assert bar.is_bullish is False


class TestPosition:
    def test_creation_with_defaults(self):
        pos = Position(symbol="AAPL", entry_price=150.0, shares=100)
        assert pos.symbol == "AAPL"
        assert pos.entry_price == 150.0
        assert pos.shares == 100
        assert pos.entry_date == ""
        assert pos.stop_loss == 0.0
        assert pos.take_profit == 0.0

    def test_cost(self):
        pos = Position(symbol="AAPL", entry_price=150.0, shares=100)
        assert pos.cost == pytest.approx(15000.0)

    def test_risk_per_share_with_stop_loss(self):
        pos = Position(symbol="AAPL", entry_price=150.0, shares=100, stop_loss=140.0)
        assert pos.risk_per_share == pytest.approx(10.0)

    def test_risk_per_share_without_stop_loss(self):
        pos = Position(symbol="AAPL", entry_price=150.0, shares=100)
        assert pos.risk_per_share == 0.0


class TestPortfolioSnapshot:
    def test_empty_portfolio(self):
        snap = PortfolioSnapshot(cash=10000.0)
        assert snap.total_position_value == 0.0
        assert snap.total_value == pytest.approx(10000.0)
        assert snap.position_count == 0

    def test_with_positions(self):
        pos_a = Position(symbol="A", entry_price=100.0, shares=10)
        pos_b = Position(symbol="B", entry_price=50.0, shares=20)
        snap = PortfolioSnapshot(cash=5000.0, positions={"A": pos_a, "B": pos_b})
        assert snap.total_position_value == pytest.approx(2000.0)
        assert snap.total_value == pytest.approx(7000.0)
        assert snap.position_count == 2


class TestBacktestMetrics:
    def test_all_defaults(self):
        m = BacktestMetrics()
        assert m.total_return == 0.0
        assert m.annual_return == 0.0
        assert m.sharpe_ratio == 0.0
        assert m.sortino_ratio == 0.0
        assert m.max_drawdown == 0.0
        assert m.win_rate == 0.0
        assert m.profit_factor == 0.0
        assert m.total_trades == 0
        assert m.avg_trade_return == 0.0
        assert m.calmar_ratio == 0.0

    def test_custom_values(self):
        m = BacktestMetrics(total_return=0.25, sharpe_ratio=1.5, total_trades=42)
        assert m.total_return == 0.25
        assert m.sharpe_ratio == 1.5
        assert m.total_trades == 42


class TestMarketDataPoint:
    def test_is_valid_true(self):
        dp = MarketDataPoint(symbol="AAPL", price=150.0)
        assert dp.is_valid is True

    def test_is_valid_zero_price(self):
        dp = MarketDataPoint(symbol="AAPL", price=0.0)
        assert dp.is_valid is False

    def test_is_valid_empty_symbol(self):
        dp = MarketDataPoint(symbol="", price=150.0)
        assert dp.is_valid is False


class TestCorrelationResult:
    def test_is_highly_correlated_above_threshold(self):
        cr = CorrelationResult(symbol_a="A", symbol_b="B", correlation=0.85)
        assert cr.is_highly_correlated is True

    def test_is_highly_correlated_below_threshold(self):
        cr = CorrelationResult(symbol_a="A", symbol_b="B", correlation=0.5)
        assert cr.is_highly_correlated is False

    def test_is_highly_correlated_negative(self):
        cr = CorrelationResult(symbol_a="A", symbol_b="B", correlation=-0.8)
        assert cr.is_highly_correlated is True
