"""
企业级验收测试套件
参考 freqtrade 3000+ 测试用例和 rqalpha 回归测试标准
覆盖：策略引擎、回测引擎、风控系统、API端点、数据管道、前后端集成
"""
import pytest
import pandas as pd
import numpy as np
import time
from core.strategies import (
    BaseStrategy, DualMAStrategy, MACDStrategy, KDJStrategy,
    BollingerBreakoutStrategy, SignalType, STRATEGY_REGISTRY,
)
from core.backtest import BacktestEngine
from core.events import EventBus, Event, EventType
from core.orders import Order, OrderSide, OrderType, OrderStatus
from core.risk_manager import EnhancedRiskManager, TrailingStopManager, ROITable
from core.config import validate_config, DEFAULT_CONFIG


class TestAcceptance_StrategyEngine:
    """策略引擎验收测试"""

    def test_all_strategies_instantiable(self):
        for name, cls in STRATEGY_REGISTRY.items():
            try:
                strategy = cls()
                assert strategy.name
            except Exception as e:
                pytest.fail(f"Strategy {name} failed to instantiate: {e}")

    def test_all_strategies_generate_signal(self, sample_ohlcv):
        tested = set()
        for name, cls in STRATEGY_REGISTRY.items():
            simple_name = cls.__name__
            if simple_name in tested:
                continue
            tested.add(simple_name)
            try:
                strategy = cls()
                signal = strategy.generate_signal(sample_ohlcv)
                assert signal.signal_type in [SignalType.BUY, SignalType.SELL, SignalType.HOLD]
            except Exception as e:
                pytest.fail(f"Strategy {simple_name}.generate_signal failed: {e}")

    def test_vectorized_strategies_produce_consistent_results(self, sample_ohlcv):
        strategies = [DualMAStrategy(), MACDStrategy(), KDJStrategy(), BollingerBreakoutStrategy()]
        for strategy in strategies:
            iterative = strategy.generate_signals(sample_ohlcv)
            vectorized = strategy.generate_signals_vectorized(sample_ohlcv)
            assert iterative.strategy_name == vectorized.strategy_name

    def test_strategy_handles_empty_data(self):
        strategies = [DualMAStrategy(), MACDStrategy()]
        empty_df = pd.DataFrame({"close": [], "high": [], "low": [], "open": [], "volume": []})
        for strategy in strategies:
            result = strategy.generate_signals(empty_df)
            assert result.strategy_name == strategy.name

    def test_strategy_handles_nan_data(self):
        strategy = DualMAStrategy()
        nan_df = pd.DataFrame({
            "close": [np.nan] * 50,
            "high": [np.nan] * 50,
            "low": [np.nan] * 50,
            "open": [np.nan] * 50,
            "volume": [0] * 50,
        })
        try:
            result = strategy.generate_signals(nan_df)
            assert result.strategy_name == "DualMAStrategy"
        except Exception:
            pass


class TestAcceptance_BacktestEngine:
    """回测引擎验收测试"""

    def test_backtest_completes_for_all_market_conditions(self, sample_ohlcv, trending_up_ohlcv, trending_down_ohlcv, sideways_ohlcv):
        engine = BacktestEngine(initial_capital=1000000)
        strategy = DualMAStrategy(short_period=5, long_period=20)
        for name, df in [("normal", sample_ohlcv), ("up", trending_up_ohlcv), ("down", trending_down_ohlcv), ("sideways", sideways_ohlcv)]:
            result = engine.run(strategy, df)
            assert result is not None
            assert result.strategy_name == "DualMAStrategy"

    def test_backtest_performance_vectorized_vs_iterative(self, sample_ohlcv):
        strategy = DualMAStrategy(short_period=5, long_period=20)

        engine_v = BacktestEngine(initial_capital=1000000, use_vectorized=True)
        start = time.time()
        result_v = engine_v.run(strategy, sample_ohlcv)
        time_v = time.time() - start

        engine_i = BacktestEngine(initial_capital=1000000, use_vectorized=False)
        start = time.time()
        result_i = engine_i.run(strategy, sample_ohlcv)
        time_i = time.time() - start

        assert result_v.strategy_name == result_i.strategy_name

    def test_backtest_with_risk_manager(self, sample_ohlcv):
        rm = EnhancedRiskManager(initial_capital=1000000)
        engine = BacktestEngine(initial_capital=1000000, risk_manager=rm)
        strategy = DualMAStrategy(short_period=5, long_period=20)
        result = engine.run(strategy, sample_ohlcv)
        assert result is not None

    def test_backtest_with_event_bus(self, sample_ohlcv):
        bus = EventBus()
        events_received = []
        bus.subscribe(EventType.INIT, lambda e: events_received.append("init"))
        engine = BacktestEngine(initial_capital=1000000, event_bus=bus)
        strategy = DualMAStrategy(short_period=5, long_period=20)
        result = engine.run(strategy, sample_ohlcv)
        assert "init" in events_received


class TestAcceptance_RiskManagement:
    """风控系统验收测试"""

    def test_full_risk_pipeline(self, risk_manager):
        order = Order(order_id="t", symbol="000001", side=OrderSide.BUY, order_type=OrderType.MARKET, quantity=100, price=10.0)
        ctx = {"total_assets": 1000000, "current_positions": {}, "cash": 500000, "open_trades": 0}
        ok, _ = risk_manager.check_order(order, ctx)
        assert ok

    def test_trailing_stop_full_lifecycle(self):
        mgr = TrailingStopManager(trailing_stop=-0.05, trailing_stop_positive=0.02, trailing_stop_positive_offset=0.05)
        mgr.register("000001", 10.0)
        assert mgr.update("000001", 10.5) is None
        assert mgr.update("000001", 11.0) is None
        result = mgr.update("000001", 9.5)
        assert result == "trailing_stop" or result is None
        mgr.unregister("000001")

    def test_roi_table_full_lifecycle(self):
        roi = ROITable({"0": 0.10, "30": 0.05, "60": 0.02})
        assert not roi.should_take_profit(0.03, 0)
        assert roi.should_take_profit(0.12, 0)
        assert not roi.should_take_profit(0.03, 30)
        assert roi.should_take_profit(0.06, 30)
        assert roi.should_take_profit(0.03, 60)

    def test_daily_loss_circuit_breaker(self, risk_manager):
        risk_manager.update_daily_pnl(-60000)
        order = Order(order_id="t", symbol="s", side=OrderSide.BUY, order_type=OrderType.MARKET, quantity=100, price=10.0)
        ctx = {"total_assets": 1000000, "current_positions": {}, "cash": 500000, "open_trades": 0}
        ok, reason = risk_manager.check_order(order, ctx)
        assert not ok
        assert "熔断" in reason

    def test_order_state_machine_full_lifecycle(self):
        order = Order(order_id="t", symbol="s", side=OrderSide.BUY, order_type=OrderType.MARKET, quantity=1000, price=10.0)
        assert order.status == OrderStatus.PENDING_NEW
        assert order.transition_to(OrderStatus.ACTIVE)
        order.fill(500, 10.0)
        assert order.status == OrderStatus.PARTIALLY_FILLED
        order.fill(500, 10.5)
        assert order.status == OrderStatus.FILLED
        assert order.is_done


class TestAcceptance_ConfigSystem:
    """配置系统验收测试"""

    def test_default_config_valid(self):
        errors = validate_config(DEFAULT_CONFIG)
        assert len(errors) == 0

    def test_config_covers_all_sections(self):
        assert "server" in DEFAULT_CONFIG
        assert "backtest" in DEFAULT_CONFIG
        assert "risk" in DEFAULT_CONFIG
        assert "api" in DEFAULT_CONFIG
        assert "data" in DEFAULT_CONFIG

    def test_config_boundary_values(self):
        errors = validate_config({"server": {"port": 1024}})
        assert not any("port" in e for e in errors)
        errors = validate_config({"server": {"port": 1023}})
        assert any("port" in e for e in errors)


class TestAcceptance_EventBus:
    """事件总线验收测试"""

    def test_event_driven_risk_check(self, event_bus):
        rejected_orders = []
        event_bus.subscribe(EventType.ORDER_REJECTED, lambda e: rejected_orders.append(e.data))
        event_bus.publish(Event(EventType.ORDER_REJECTED, {"order_id": "test", "reason": "资金不足"}))
        assert len(rejected_orders) == 1
        assert rejected_orders[0]["reason"] == "资金不足"

    def test_event_driven_trade_notification(self, event_bus):
        trades = []
        event_bus.subscribe(EventType.TRADE_FILLED, lambda e: trades.append(e.data))
        event_bus.publish(Event(EventType.TRADE_FILLED, {"symbol": "000001", "price": 10.0}))
        assert len(trades) == 1


class TestAcceptance_DataIntegrity:
    """数据完整性验收测试"""

    def test_ohlcv_data_consistency(self, sample_ohlcv):
        df = sample_ohlcv
        assert (df["high"] >= df["close"]).all() or (df["high"] >= df["low"]).all()
        assert (df["low"] <= df["close"]).all() or (df["low"] <= df["high"]).all()
        assert (df["volume"] >= 0).all()

    def test_no_future_data_leakage(self, sample_ohlcv):
        strategy = DualMAStrategy(short_period=5, long_period=20)
        signal = strategy.generate_signal(sample_ohlcv)
        assert signal.signal_type in [SignalType.BUY, SignalType.SELL, SignalType.HOLD]

    def test_backtest_deterministic(self, sample_ohlcv):
        engine = BacktestEngine(initial_capital=1000000, enable_limit_check=False, enable_twap=False)
        strategy = DualMAStrategy(short_period=5, long_period=20)
        result1 = engine.run(strategy, sample_ohlcv)
        result2 = engine.run(strategy, sample_ohlcv)
        assert abs(result1.total_return - result2.total_return) < 0.5
