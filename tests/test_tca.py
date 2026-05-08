import numpy as np
import pytest

from core.tca import (
    CostAttribution,
    ExecutionRecommendation,
    Side,
    TCAEngine,
    TCABatchResult,
    TCAReport,
    TradeAnalysis,
    _classify_liquidity,
    _classify_market_cap,
    _classify_time_period,
)


def _make_trade(
    symbol: str = "600000",
    strategy_name: str = "test",
    side: Side = Side.BUY,
    decision_price: float = 10.0,
    arrival_price: float = 10.05,
    execution_price: float = 10.08,
    vwap_benchmark: float = 10.03,
    twap_benchmark: float = 10.04,
    quantity: int = 1000,
    execution_timestamp: str = "2024-01-15 09:35:00",
) -> TradeAnalysis:
    return TradeAnalysis(
        symbol=symbol,
        strategy_name=strategy_name,
        side=side,
        decision_price=decision_price,
        arrival_price=arrival_price,
        execution_price=execution_price,
        vwap_benchmark=vwap_benchmark,
        twap_benchmark=twap_benchmark,
        quantity=quantity,
        execution_timestamp=execution_timestamp,
    )


class TestSide:
    def test_values(self):
        assert Side.BUY == "buy"
        assert Side.SELL == "sell"


class TestTradeAnalysis:
    def test_buy_implementation_shortfall(self):
        trade = _make_trade(side=Side.BUY, decision_price=10.0, execution_price=10.08)
        expected = (10.08 - 10.0) / 10.0
        assert abs(trade.implementation_shortfall - expected) < 1e-10

    def test_sell_implementation_shortfall(self):
        trade = _make_trade(side=Side.SELL, decision_price=10.0, execution_price=9.92)
        expected = (10.0 - 9.92) / 10.0
        assert abs(trade.implementation_shortfall - expected) < 1e-10

    def test_buy_market_impact(self):
        trade = _make_trade(side=Side.BUY, arrival_price=10.05, execution_price=10.08)
        expected = (10.08 - 10.05) / 10.05
        assert abs(trade.market_impact - expected) < 1e-10

    def test_sell_market_impact(self):
        trade = _make_trade(side=Side.SELL, arrival_price=10.05, execution_price=9.98)
        expected = (10.05 - 9.98) / 10.05
        assert abs(trade.market_impact - expected) < 1e-10

    def test_zero_decision_price_is(self):
        trade = _make_trade(decision_price=0.0)
        assert trade.implementation_shortfall == 0.0

    def test_zero_arrival_price_mi(self):
        trade = _make_trade(arrival_price=0.0)
        assert trade.market_impact == 0.0

    def test_total_cost(self):
        trade = _make_trade()
        expected = trade.implementation_shortfall * trade.execution_price * trade.quantity
        assert abs(trade.total_cost - expected) < 1e-6

    def test_vwap_slippage_buy(self):
        trade = _make_trade(side=Side.BUY, execution_price=10.08, vwap_benchmark=10.03)
        expected = (10.08 - 10.03) / 10.03
        assert abs(trade.vwap_slippage - expected) < 1e-10

    def test_twap_slippage_sell(self):
        trade = _make_trade(side=Side.SELL, execution_price=9.90, twap_benchmark=10.04)
        expected = (10.04 - 9.90) / 10.04
        assert abs(trade.twap_slippage - expected) < 1e-10


class TestClassifyMarketCap:
    def test_large_cap(self):
        assert _classify_market_cap(5e10) == "large_cap"

    def test_mid_cap(self):
        assert _classify_market_cap(5e9) == "mid_cap"

    def test_small_cap(self):
        assert _classify_market_cap(1e9) == "small_cap"

    def test_zero(self):
        assert _classify_market_cap(0) == "small_cap"


class TestClassifyTimePeriod:
    def test_opening_session(self):
        assert _classify_time_period("2024-01-15 09:35:00") == "09:30-10:00"

    def test_mid_session(self):
        assert _classify_time_period("2024-01-15 10:30:00") == "10:00-11:00"

    def test_afternoon(self):
        assert _classify_time_period("2024-01-15 13:30:00") == "13:00-14:00"


class TestClassifyLiquidity:
    def test_high_liquidity(self):
        assert _classify_liquidity(0.9) == "high_liquidity"

    def test_medium_liquidity(self):
        assert _classify_liquidity(0.5) == "medium_liquidity"

    def test_low_liquidity(self):
        assert _classify_liquidity(0.1) == "low_liquidity"


class TestTCAEngine:
    def test_analyze_trade(self):
        engine = TCAEngine()
        trade = _make_trade()
        result = engine.analyze_trade(trade)
        assert "implementation_shortfall" in result
        assert "market_impact" in result
        assert "total_cost" in result

    def test_analyze_batch(self):
        engine = TCAEngine()
        trades = [
            _make_trade(symbol="600000", strategy_name="s1"),
            _make_trade(symbol="000001", strategy_name="s2", side=Side.SELL,
                        decision_price=15.0, arrival_price=14.95, execution_price=14.90),
        ]
        result = engine.analyze_batch(trades)
        assert isinstance(result, TCABatchResult)
        assert result.total_trades == 2
        assert result.total_cost > 0

    def test_analyze_batch_empty(self):
        engine = TCAEngine()
        result = engine.analyze_batch([])
        assert result.total_trades == 0
        assert result.total_cost == 0.0

    def test_attribute_by_strategy(self):
        engine = TCAEngine()
        trades = [
            _make_trade(strategy_name="momentum"),
            _make_trade(strategy_name="momentum"),
            _make_trade(strategy_name="mean_revert"),
        ]
        result = engine.attribute_by_strategy(trades)
        assert len(result) == 2
        buckets = {a.bucket for a in result}
        assert "momentum" in buckets
        assert "mean_revert" in buckets

    def test_attribute_by_market_cap(self):
        engine = TCAEngine(market_caps={"600000": 5e10, "000001": 1e9})
        trades = [_make_trade(symbol="600000"), _make_trade(symbol="000001")]
        result = engine.attribute_by_market_cap(trades)
        buckets = {a.bucket for a in result}
        assert "large_cap" in buckets
        assert "small_cap" in buckets

    def test_attribute_by_time_period(self):
        engine = TCAEngine()
        trades = [
            _make_trade(execution_timestamp="2024-01-15 09:35:00"),
            _make_trade(execution_timestamp="2024-01-15 10:30:00"),
        ]
        result = engine.attribute_by_time_period(trades)
        assert len(result) >= 1

    def test_generate_daily_report(self):
        engine = TCAEngine()
        trades = [_make_trade(), _make_trade()]
        report = engine.generate_daily_report(trades, "2024-01-15")
        assert isinstance(report, TCAReport)
        assert report.date == "2024-01-15"
        assert report.total_trades == 2

    def test_generate_daily_report_empty(self):
        engine = TCAEngine()
        report = engine.generate_daily_report([], "2024-01-15")
        assert report.total_trades == 0
        assert report.total_cost_bps == 0.0

    def test_recommend_optimal_execution(self):
        engine = TCAEngine()
        trades = [_make_trade(symbol="600000")]
        rec = engine.recommend_optimal_execution("600000", trades)
        assert isinstance(rec, ExecutionRecommendation)
        assert rec.symbol == "600000"
        assert rec.recommended_algorithm in ("VWAP", "TWAP", "IS")

    def test_recommend_no_historical_trades(self):
        engine = TCAEngine()
        rec = engine.recommend_optimal_execution("999999", [])
        assert rec.recommended_algorithm == "VWAP"
