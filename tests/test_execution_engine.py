import pandas as pd

from core.execution_engine import (
    CostModel,
    ExecutionEngine,
    ExecutionResult,
    execute_twap,
    execute_vwap,
    generate_volume_profile,
)


class TestCostModel:
    def test_buy_cost(self):
        cm = CostModel()
        cost = cm.calc_buy_cost(10.0, 1000)
        assert cost > 0
        expected_commission = max(10.0 * 1000 * 0.0003, 5.0)
        expected_slippage = 10.0 * 1000 * 0.0001
        assert abs(cost - (expected_commission + expected_slippage)) < 0.01

    def test_sell_cost_includes_stamp_tax(self):
        cm = CostModel()
        buy_cost = cm.calc_buy_cost(10.0, 1000)
        sell_cost = cm.calc_sell_cost(10.0, 1000)
        assert sell_cost > buy_cost

    def test_total_cost(self):
        cm = CostModel()
        total = cm.calc_total_cost(10.0, 11.0, 1000)
        assert total > 0

    def test_cost_pct(self):
        cm = CostModel()
        pct = cm.calc_cost_pct(10.0, 11.0, 1000)
        assert 0 < pct < 0.01

    def test_cost_pct_zero_value(self):
        cm = CostModel()
        pct = cm.calc_cost_pct(0, 0, 0)
        assert pct == 0.0

    def test_min_commission(self):
        cm = CostModel(min_commission=5.0)
        cost = cm.calc_buy_cost(1.0, 1)
        assert cost >= 5.0


class TestExecuteTWAP:
    def test_basic(self):
        qty = execute_twap(600, 6, 0)
        assert qty == 100

    def test_remainder_distribution(self):
        qty0 = execute_twap(605, 6, 0)
        execute_twap(605, 6, 5)
        assert qty0 == 101
        total = sum(execute_twap(605, 6, i) for i in range(6))
        assert total == 605

    def test_zero_quantity(self):
        assert execute_twap(0, 6, 0) == 0

    def test_zero_bars(self):
        assert execute_twap(600, 0, 0) == 0

    def test_negative_quantity(self):
        assert execute_twap(-100, 6, 0) == 0


class TestExecuteVWAP:
    def test_basic(self):
        profile = [100, 200, 300, 200, 100, 100]
        qty = execute_vwap(600, profile, 0)
        assert qty > 0

    def test_zero_quantity(self):
        assert execute_vwap(0, [1, 2, 3], 0) == 0

    def test_empty_profile(self):
        assert execute_vwap(600, [], 0) == 0

    def test_zero_volume_profile(self):
        qty = execute_vwap(600, [0, 0, 0], 0)
        assert qty > 0

    def test_total_filled_equals_quantity(self):
        profile = [100, 200, 300, 200, 100, 100]
        total = sum(execute_vwap(600, profile, i) for i in range(6))
        assert total == 600


class TestGenerateVolumeProfile:
    def test_basic(self):
        df = pd.DataFrame({
            "close": [10 + i * 0.1 for i in range(20)],
            "volume": [1000 + i * 100 for i in range(20)],
        })
        profile = generate_volume_profile(df, 6)
        assert len(profile) == 6
        assert abs(sum(profile) - 1.0) < 0.01

    def test_no_volume_column(self):
        df = pd.DataFrame({"close": [10, 11, 12]})
        profile = generate_volume_profile(df, 6)
        assert len(profile) == 6
        assert abs(sum(profile) - 1.0) < 0.01

    def test_short_df(self):
        df = pd.DataFrame({"close": [10], "volume": [100]})
        profile = generate_volume_profile(df, 6)
        assert len(profile) == 6

    def test_zero_volume(self):
        df = pd.DataFrame({
            "close": [10, 11, 12, 13, 14, 15],
            "volume": [0, 0, 0, 0, 0, 0],
        })
        profile = generate_volume_profile(df, 6)
        assert len(profile) == 6
        assert abs(sum(profile) - 1.0) < 0.01


class TestExecutionEngine:
    def test_market_buy(self):
        engine = ExecutionEngine()
        result = engine.execute_market_order("buy", 1000, 10.0)
        assert isinstance(result, ExecutionResult)
        assert result.filled_quantity == 1000
        assert result.avg_fill_price > 10.0
        assert result.execution_method == "market"

    def test_market_sell(self):
        engine = ExecutionEngine()
        result = engine.execute_market_order("sell", 1000, 10.0)
        assert result.filled_quantity == 1000
        assert result.avg_fill_price < 10.0

    def test_twap_order(self):
        engine = ExecutionEngine()
        df = pd.DataFrame({
            "close": [10 + i * 0.1 for i in range(20)],
            "volume": [1000] * 20,
        })
        result = engine.execute_twap_order("buy", 600, df, 6)
        assert result.filled_quantity > 0
        assert result.execution_method == "twap"

    def test_vwap_order(self):
        engine = ExecutionEngine()
        df = pd.DataFrame({
            "close": [10 + i * 0.1 for i in range(20)],
            "volume": [1000 + i * 100 for i in range(20)],
        })
        result = engine.execute_vwap_order("buy", 600, df, 6)
        assert result.filled_quantity > 0
        assert result.execution_method == "vwap"

    def test_twap_empty_df(self):
        engine = ExecutionEngine()
        result = engine.execute_twap_order("buy", 600, pd.DataFrame(), 6)
        assert result.filled_quantity == 0

    def test_vwap_empty_df(self):
        engine = ExecutionEngine()
        result = engine.execute_vwap_order("buy", 600, pd.DataFrame(), 6)
        assert result.filled_quantity == 0

    def test_custom_cost_model(self):
        cm = CostModel(commission_rate=0.001, slippage_rate=0.0005)
        engine = ExecutionEngine(cost_model=cm)
        result = engine.execute_market_order("buy", 1000, 10.0)
        assert result.total_cost > 0
