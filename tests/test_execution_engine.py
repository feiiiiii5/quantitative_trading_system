import numpy as np
import pandas as pd
import pytest

from core.execution_engine import (
    CostModel,
    execute_twap,
    execute_vwap,
    generate_volume_profile,
    ExecutionEngine,
)


class TestCostModel:
    def test_buy_cost(self):
        model = CostModel()
        cost = model.calc_buy_cost(10.0, 1000)
        assert cost > 0

    def test_sell_cost(self):
        model = CostModel()
        cost = model.calc_sell_cost(10.0, 1000)
        assert cost > 0

    def test_sell_more_expensive(self):
        model = CostModel()
        buy_cost = model.calc_buy_cost(10.0, 1000)
        sell_cost = model.calc_sell_cost(10.0, 1000)
        assert sell_cost > buy_cost

    def test_total_cost(self):
        model = CostModel()
        cost = model.calc_total_cost(10.0, 11.0, 1000)
        assert cost > 0

    def test_cost_pct(self):
        model = CostModel()
        pct = model.calc_cost_pct(10.0, 11.0, 1000)
        assert 0 < pct < 0.01


class TestTWAP:
    def test_basic(self):
        qty = execute_twap(600, 6, 0)
        assert qty == 100

    def test_remainder(self):
        qty = execute_twap(605, 6, 0)
        assert qty == 101

    def test_last_bar(self):
        qty = execute_twap(600, 6, 5)
        assert qty == 100

    def test_zero_quantity(self):
        qty = execute_twap(0, 6, 0)
        assert qty == 0


class TestVWAP:
    def test_basic(self):
        profile = [0.1, 0.2, 0.3, 0.2, 0.1, 0.1]
        qty = execute_vwap(1000, profile, 0)
        assert qty > 0

    def test_cumulative(self):
        profile = [0.2, 0.3, 0.5]
        total = 0
        for i in range(3):
            total += execute_vwap(1000, profile, i)
        assert total == 1000

    def test_empty_profile(self):
        qty = execute_vwap(1000, [], 0)
        assert qty == 0


class TestVolumeProfile:
    def test_basic(self, sample_ohlcv):
        profile = generate_volume_profile(sample_ohlcv, 6)
        assert len(profile) == 6
        assert abs(sum(profile) - 1.0) < 0.01

    def test_short_data(self):
        df = pd.DataFrame({"close": [10, 11], "volume": [100, 200]})
        profile = generate_volume_profile(df, 6)
        assert len(profile) == 6


class TestExecutionEngine:
    def test_market_order_buy(self):
        engine = ExecutionEngine()
        result = engine.execute_market_order("buy", 1000, 10.0)
        assert result.filled_quantity == 1000
        assert result.avg_fill_price > 10.0
        assert result.total_cost > 0

    def test_market_order_sell(self):
        engine = ExecutionEngine()
        result = engine.execute_market_order("sell", 1000, 10.0)
        assert result.filled_quantity == 1000
        assert result.avg_fill_price < 10.0
        assert result.total_cost > 0

    def test_twap_order(self, sample_ohlcv):
        engine = ExecutionEngine()
        result = engine.execute_twap_order("buy", 6000, sample_ohlcv, 6)
        assert result.filled_quantity == 6000
        assert result.execution_method == "twap"
        assert len(result.bar_details) > 0

    def test_vwap_order(self, sample_ohlcv):
        engine = ExecutionEngine()
        result = engine.execute_vwap_order("buy", 6000, sample_ohlcv, 6)
        assert result.filled_quantity == 6000
        assert result.execution_method == "vwap"
        assert len(result.bar_details) > 0

    def test_empty_data(self):
        engine = ExecutionEngine()
        result = engine.execute_twap_order("buy", 1000, pd.DataFrame(), 6)
        assert result.filled_quantity == 0

    def test_custom_cost_model(self):
        model = CostModel(commission_rate=0.001, slippage_rate=0.0005)
        engine = ExecutionEngine(cost_model=model)
        result = engine.execute_market_order("buy", 1000, 10.0)
        assert result.total_cost > 0
