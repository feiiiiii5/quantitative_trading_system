import numpy as np
import pandas as pd
import pytest

from core.backtest_v2.event_engine import EventBacktestEngine, EventType, Event, BacktestAccount
from core.backtest_v2.microstructure import MicrostructureSimulator, SlippageModel, OrderBookLevel
from core.backtest_v2.portfolio_backtest import PortfolioBacktester
from core.backtest_v2.param_optimizer import ParamOptimizer
from core.backtest_v2.monte_carlo import MonteCarloStressTest
from core.strategies import DualMAStrategy, MACDStrategy


def _make_df(n=200):
    np.random.seed(42)
    dates = pd.date_range("2023-01-01", periods=n)
    close = 100 + np.cumsum(np.random.randn(n) * 2)
    return pd.DataFrame({
        "date": dates,
        "open": close + np.random.randn(n),
        "high": close + abs(np.random.randn(n)),
        "low": close - abs(np.random.randn(n)),
        "close": close,
        "volume": np.random.randint(10000, 100000, n),
    })


class TestEventBacktestEngine:
    def test_run_dual_ma(self):
        engine = EventBacktestEngine()
        df = _make_df()
        strategy = DualMAStrategy()
        result = engine.run(strategy, df, "TEST")
        assert "total_return" in result
        assert "sharpe_ratio" in result
        assert "equity_curve" in result

    def test_run_macd(self):
        engine = EventBacktestEngine()
        df = _make_df()
        strategy = MACDStrategy()
        result = engine.run(strategy, df, "TEST")
        assert "total_return" in result

    def test_empty_data(self):
        engine = EventBacktestEngine()
        result = engine.run(DualMAStrategy(), pd.DataFrame(), "TEST")
        assert result["total_trades"] == 0

    def test_short_data(self):
        engine = EventBacktestEngine()
        df = _make_df(10)
        result = engine.run(DualMAStrategy(), df, "TEST")
        assert result["total_trades"] == 0


class TestMicrostructureSimulator:
    def test_fixed_slippage(self):
        sim = MicrostructureSimulator(slippage_model=SlippageModel.FIXED, fixed_slippage=0.05)
        fill = sim.simulate_fill(100.0, 1000, "buy")
        assert fill.fill_price > 100.0
        assert fill.slippage == 0.05

    def test_percentage_slippage(self):
        sim = MicrostructureSimulator(slippage_model=SlippageModel.PERCENTAGE, percentage_slippage=0.001)
        fill = sim.simulate_fill(100.0, 1000, "buy")
        assert fill.fill_price > 100.0

    def test_volume_impact_slippage(self):
        sim = MicrostructureSimulator(slippage_model=SlippageModel.VOLUME_IMPACT)
        fill = sim.simulate_fill(100.0, 1000, "buy", avg_volume=10000, volatility=0.02)
        assert fill.fill_price > 100.0
        assert fill.market_impact > 0

    def test_sell_slippage(self):
        sim = MicrostructureSimulator(slippage_model=SlippageModel.PERCENTAGE)
        fill = sim.simulate_fill(100.0, 1000, "sell")
        assert fill.fill_price < 100.0

    def test_orderbook_fill(self):
        sim = MicrostructureSimulator()
        levels = [
            OrderBookLevel(price=100.0, volume=500),
            OrderBookLevel(price=100.1, volume=500),
            OrderBookLevel(price=100.2, volume=500),
        ]
        fill = sim.simulate_orderbook_fill(levels, 800, "buy")
        assert fill.fill_quantity == 800
        assert fill.fill_price >= 100.0

    def test_model_info(self):
        sim = MicrostructureSimulator()
        info = sim.get_model_info()
        assert "slippage_model" in info
        assert "commission_rate" in info


class TestPortfolioBacktester:
    def test_run_portfolio(self):
        bt = PortfolioBacktester()
        df = _make_df()
        strategies = {"dual_ma": DualMAStrategy(), "macd": MACDStrategy()}
        data = {"TEST": df}
        result = bt.run(strategies, data)
        assert "strategy_results" in result
        assert "portfolio_metrics" in result

    def test_custom_allocations(self):
        bt = PortfolioBacktester()
        df = _make_df()
        strategies = {"dual_ma": DualMAStrategy()}
        data = {"TEST": df}
        result = bt.run(strategies, data, allocations={"dual_ma": 1.0})
        assert "strategy_results" in result


class TestParamOptimizer:
    def test_grid_search(self):
        optimizer = ParamOptimizer()
        df = _make_df()
        param_grid = {"fast": [3, 5], "slow": [15, 20]}
        results = optimizer.grid_search(DualMAStrategy, param_grid, df, "TEST", top_n=4)
        assert len(results) <= 4
        assert all(r.sharpe_ratio != 0 or r.total_return != 0 for r in results)

    def test_walk_forward(self):
        optimizer = ParamOptimizer()
        df = _make_df(300)
        param_grid = {"fast": [3, 5], "slow": [15, 20]}
        result = optimizer.walk_forward(DualMAStrategy, param_grid, df, "TEST", n_splits=3)
        assert "train_results" in result.to_dict()

    def test_heatmap_data(self):
        optimizer = ParamOptimizer()
        df = _make_df()
        param_grid = {"fast": [3, 5, 7], "slow": [15, 20, 25]}
        results = optimizer.grid_search(DualMAStrategy, param_grid, df, "TEST", top_n=9)
        heatmap = optimizer.generate_heatmap_data(results, "fast", "slow")
        assert "x" in heatmap
        assert "z" in heatmap


class TestMonteCarloStressTest:
    def test_bootstrap(self):
        mc = MonteCarloStressTest(n_simulations=100)
        equity = list(np.cumsum(np.random.randn(200) * 100 + 100000))
        result = mc.run(equity, n_simulations=100, method="bootstrap")
        assert result.n_simulations == 100
        assert 0 <= result.ruin_probability <= 1

    def test_parametric(self):
        mc = MonteCarloStressTest()
        equity = list(np.cumsum(np.random.randn(200) * 100 + 100000))
        result = mc.run(equity, n_simulations=100, method="parametric")
        assert result.n_simulations == 100

    def test_stress_scenarios(self):
        mc = MonteCarloStressTest()
        equity = list(np.cumsum(np.random.randn(200) * 100 + 100000))
        scenarios = {
            "test_shock": {"shock": -0.3, "duration": 20, "volatility_mult": 2.0},
        }
        results = mc.run_stress_scenarios(equity, scenarios)
        assert "test_shock" in results
        assert results["test_shock"].n_simulations > 0

    def test_empty_equity(self):
        mc = MonteCarloStressTest()
        result = mc.run([], n_simulations=10)
        assert result.n_simulations == 10
