import numpy as np
import pandas as pd
import pytest

from core.backtest import BacktestEngine, BacktestProfiler, BacktestResult, BatchStrategyRunner, compare_results
from core.strategies import DualMAStrategy, MACDStrategy


class TestBacktestEngine:
    def test_basic_backtest(self, sample_ohlcv):
        engine = BacktestEngine(initial_capital=1000000)
        strategy = DualMAStrategy(short_period=5, long_period=20)
        result = engine.run(strategy, sample_ohlcv)
        assert result.strategy_name == "DualMAStrategy"
        assert result.total_return is not None

    def test_vectorized_backtest(self, sample_ohlcv):
        engine = BacktestEngine(initial_capital=1000000, use_vectorized=True)
        strategy = DualMAStrategy(short_period=5, long_period=20)
        result = engine.run(strategy, sample_ohlcv)
        assert result.strategy_name == "DualMAStrategy"

    def test_non_vectorized_backtest(self, sample_ohlcv):
        engine = BacktestEngine(initial_capital=1000000, use_vectorized=False)
        strategy = DualMAStrategy(short_period=5, long_period=20)
        result = engine.run(strategy, sample_ohlcv)
        assert result.strategy_name == "DualMAStrategy"

    def test_insufficient_data(self):
        from core.backtest import InsufficientDataError
        engine = BacktestEngine()
        strategy = DualMAStrategy()
        small_df = pd.DataFrame({"close": [10], "high": [11], "low": [9], "open": [10], "volume": [1000]})
        with pytest.raises(InsufficientDataError):
            engine.run(strategy, small_df)

    def test_none_data(self):
        from core.backtest import InsufficientDataError
        engine = BacktestEngine()
        strategy = DualMAStrategy()
        with pytest.raises(InsufficientDataError):
            engine.run(strategy, None)

    def test_macd_backtest(self, sample_ohlcv):
        engine = BacktestEngine(initial_capital=1000000)
        strategy = MACDStrategy()
        result = engine.run(strategy, sample_ohlcv)
        assert result.strategy_name == "MACDStrategy"

    def test_trending_market(self, trending_up_ohlcv):
        engine = BacktestEngine(initial_capital=1000000)
        strategy = DualMAStrategy(short_period=5, long_period=20)
        result = engine.run(strategy, trending_up_ohlcv)
        assert result is not None

    def test_backtest_result_fields(self, sample_ohlcv):
        engine = BacktestEngine(initial_capital=1000000)
        strategy = DualMAStrategy(short_period=5, long_period=20)
        result = engine.run(strategy, sample_ohlcv)
        assert hasattr(result, "strategy_name")
        assert hasattr(result, "total_return")
        assert hasattr(result, "max_drawdown")
        assert hasattr(result, "sharpe_ratio")

    def test_forced_close_uses_correct_attributes(self, sample_ohlcv):
        engine = BacktestEngine(initial_capital=1000000, slippage_pct=0.001)
        assert hasattr(engine, "_slippage_pct")
        assert engine._slippage_pct == 0.001
        assert hasattr(engine, "_cost_model")

    def test_stop_loss_with_slippage_no_crash(self, trending_down_ohlcv):
        engine = BacktestEngine(initial_capital=1000000, slippage_pct=0.002)
        strategy = DualMAStrategy(short_period=5, long_period=20)
        result = engine.run(strategy, trending_down_ohlcv)
        assert result is not None
        assert result.strategy_name == "DualMAStrategy"


class TestCompareResults:
    """回测结果对比功能测试"""

    def test_compare_empty_list(self):
        result = compare_results([])
        assert "error" in result

    def test_compare_single_result(self, sample_ohlcv):
        engine = BacktestEngine(initial_capital=1000000)
        strategy = DualMAStrategy(short_period=5, long_period=20)
        bt_result = engine.run(strategy, sample_ohlcv)
        result = compare_results([bt_result])
        assert "comparison" in result
        assert "ranking" in result
        assert "metrics" in result
        assert len(result["ranking"]) == 1
        assert result["ranking"][0]["rank"] == 1

    def test_compare_multiple_strategies(self, sample_ohlcv):
        engine = BacktestEngine(initial_capital=1000000)
        r1 = engine.run(DualMAStrategy(short_period=5, long_period=20), sample_ohlcv)
        r2 = engine.run(MACDStrategy(), sample_ohlcv)
        result = compare_results([r1, r2])
        assert len(result["comparison"]) == 2
        assert len(result["ranking"]) == 2
        assert result["ranking"][0]["rank"] == 1
        assert result["ranking"][1]["rank"] == 2
        assert result["ranking"][0]["score"] >= result["ranking"][1]["score"]

    def test_compare_metrics_structure(self, sample_ohlcv):
        engine = BacktestEngine(initial_capital=1000000)
        r1 = engine.run(DualMAStrategy(short_period=5, long_period=20), sample_ohlcv)
        result = compare_results([r1])
        metric_keys = [m["key"] for m in result["metrics"]]
        assert "total_return" in metric_keys
        assert "sharpe_ratio" in metric_keys
        assert "max_drawdown" in metric_keys
        assert "win_rate" in metric_keys
        for entry in result["comparison"]:
            for _mk in metric_keys:
                assert _mk in entry

    def test_to_dict_returns_dict(self, sample_ohlcv):
        engine = BacktestEngine(initial_capital=1000000)
        strategy = DualMAStrategy(short_period=5, long_period=20)
        result = engine.run(strategy, sample_ohlcv)
        d = result.to_dict()
        assert isinstance(d, dict)
        assert "strategy_name" in d
        assert "total_return" in d
        assert "sharpe_ratio" in d
        assert "total_trades" in d
        assert "equity_curve" in d
        assert isinstance(d["equity_curve"], list)

    def test_to_dict_no_dataclass_methods(self, sample_ohlcv):
        engine = BacktestEngine(initial_capital=1000000)
        strategy = DualMAStrategy(short_period=5, long_period=20)
        result = engine.run(strategy, sample_ohlcv)
        d = result.to_dict()
        assert not hasattr(d, "total_return")
        assert isinstance(d.get("total_return"), (int, float))

    def test_summary_dict(self, sample_ohlcv):
        engine = BacktestEngine(initial_capital=1000000)
        strategy = DualMAStrategy(short_period=5, long_period=20)
        result = engine.run(strategy, sample_ohlcv)
        sd = result.summary_dict()
        assert isinstance(sd, dict)
        assert "strategy_name" in sd
        assert "sharpe_ratio" in sd
        assert "equity_curve" not in sd
        assert "trades" not in sd

    def test_performance_summary(self, sample_ohlcv):
        engine = BacktestEngine(initial_capital=1000000)
        strategy = DualMAStrategy(short_period=5, long_period=20)
        result = engine.run(strategy, sample_ohlcv)
        summary = result.get_performance_summary()
        assert isinstance(summary, dict)
        assert "sharpe" in summary
        assert "win_rate_pct" in summary
        assert summary["total_trades"] >= 0

    def test_compare_with(self, sample_ohlcv):
        engine = BacktestEngine(initial_capital=1000000)
        r1 = engine.run(DualMAStrategy(short_period=5, long_period=20), sample_ohlcv)
        r2 = engine.run(MACDStrategy(), sample_ohlcv)
        comparison = r1.compare_with(r2)
        assert "this" in comparison
        assert "other" in comparison
        assert "sharpe_diff" in comparison
        assert "recommended" in comparison

    def test_to_dict_empty_result(self):
        result = BacktestResult(strategy_name="test")
        d = result.to_dict()
        assert d["strategy_name"] == "test"
        assert d["total_return"] == 0
        assert d["equity_curve"] == []
        assert d["trades"] == []

    def test_summary_dict_empty_result(self):
        result = BacktestResult(strategy_name="test")
        sd = result.summary_dict()
        assert sd["strategy_name"] == "test"
        assert sd["total_return"] == 0

    def test_parameter_grid_scan(self, sample_ohlcv):
        engine = BacktestEngine(initial_capital=1000000)
        result = engine.parameter_grid_scan(
            DualMAStrategy, sample_ohlcv,
            param_x="short_period", param_y="long_period",
            x_range=(3, 10), y_range=(15, 30),
            grid_size=3,
        )
        assert "heatmap" in result
        assert "best_params" in result
        assert "x_values" in result
        assert "y_values" in result
        assert len(result["heatmap"]) > 0
        assert result["param_x"] == "short_period"
        assert result["param_y"] == "long_period"

    def test_parameter_grid_scan_custom_metric(self, sample_ohlcv):
        engine = BacktestEngine(initial_capital=1000000)
        result = engine.parameter_grid_scan(
            DualMAStrategy, sample_ohlcv,
            param_x="short_period", param_y="long_period",
            x_range=(3, 10), y_range=(15, 30),
            grid_size=3, metric="total_return",
        )
        assert result["metric"] == "total_return"
        assert len(result["heatmap"]) > 0

    def test_walk_forward_oos_validation(self, sample_ohlcv):
        from core.backtest import walk_forward_oos_validation
        result = walk_forward_oos_validation(
            DualMAStrategy, sample_ohlcv,
            train_days=30, test_days=15,
            param_grid={"short_period": [5, 10], "long_period": [20, 30]},
        )
        assert "windows" in result
        assert "summary" in result
        assert "verdict" in result
        assert result["verdict"] in ("robust", "moderate", "overfit")
        assert result["summary"]["n_windows"] >= 1

    def test_walk_forward_oos_insufficient_data(self):
        from core.backtest import walk_forward_oos_validation
        small_df = pd.DataFrame({
            "close": [10, 11], "high": [11, 12],
            "low": [9, 10], "open": [10, 10.5], "volume": [1000, 1000],
        })
        result = walk_forward_oos_validation(DualMAStrategy, small_df)
        assert "error" in result

    def test_trailing_stop_triggers_on_reversal(self):
        # 构建先涨后跌的数据，验证追踪止损能触发
        np.random.seed(42)
        n = 120
        dates = pd.date_range("2024-01-01", periods=n, freq="D")
        prices = np.concatenate([
            np.linspace(10, 15, 30),
            np.linspace(15, 25, 30),
            np.linspace(25, 18, 30),
            np.linspace(18, 12, 30),
        ])
        noise = np.random.normal(0, 0.3, n)
        prices = prices + noise
        df = pd.DataFrame({
            "date": dates,
            "close": prices,
            "high": prices + 0.5,
            "low": prices - 0.5,
            "open": prices,
            "volume": np.full(n, 1e7),
            "amount": np.full(n, 1e8),
        })
        engine = BacktestEngine(initial_capital=1000000, use_vectorized=False)
        strategy = MACDStrategy()
        result = engine.run(strategy, df)
        assert result.total_trades > 0

    def test_dynamic_atr_stop_loss_when_strategy_has_no_stop(self):
        # 策略不设stop_loss时，回测引擎应使用ATR动态止损
        np.random.seed(123)
        n = 60
        prices = np.linspace(10, 8, n)
        df = pd.DataFrame({
            "close": prices,
            "high": prices + 0.3,
            "low": prices - 0.3,
            "open": prices,
            "volume": np.full(n, 1e7),
            "amount": np.full(n, 1e8),
        })
        engine = BacktestEngine(initial_capital=1000000, use_vectorized=False)
        strategy = DualMAStrategy(short_period=5, long_period=20)
        result = engine.run(strategy, df)
        assert result is not None
        assert result.strategy_name == "DualMAStrategy"

    def test_short_period_annual_return_no_overflow(self):
        np.random.seed(42)
        n = 15
        prices = np.linspace(10, 11, n)
        df = pd.DataFrame({
            "close": prices,
            "high": prices + 0.1,
            "low": prices - 0.1,
            "open": prices,
            "volume": np.full(n, 1e7),
            "amount": np.full(n, 1e8),
        })
        engine = BacktestEngine(initial_capital=1000000)
        strategy = DualMAStrategy(short_period=5, long_period=10)
        result = engine.run(strategy, df)
        assert abs(result.annual_return) < 1e6, f"Annual return overflowed: {result.annual_return}"

    def test_zero_drawdown_calmar_ratio(self):
        np.random.seed(42)
        n = 100
        prices = np.linspace(10, 15, n)
        df = pd.DataFrame({
            "close": prices,
            "high": prices + 0.1,
            "low": prices - 0.1,
            "open": prices,
            "volume": np.full(n, 1e7),
            "amount": np.full(n, 1e8),
        })
        engine = BacktestEngine(initial_capital=1000000)
        strategy = DualMAStrategy(short_period=5, long_period=20)
        result = engine.run(strategy, df)
        if result.max_drawdown == 0:
            assert result.calmar_ratio == 0


class TestDivisionByZeroGuards:
    def test_flat_equity_no_division_error(self):
        n = 50
        prices = np.full(n, 10.0)
        df = pd.DataFrame({
            "close": prices,
            "high": prices + 0.1,
            "low": prices - 0.1,
            "open": prices,
            "volume": np.full(n, 1e7),
            "amount": np.full(n, 1e8),
        })
        engine = BacktestEngine(initial_capital=1000000)
        strategy = DualMAStrategy(short_period=5, long_period=20)
        result = engine.run(strategy, df)
        assert np.isfinite(result.total_return)
        assert np.isfinite(result.max_drawdown)
        assert np.isfinite(result.calmar_ratio)
        assert np.isfinite(result.profit_factor)

    def test_single_trade_profit_factor(self):
        n = 30
        prices = np.linspace(10, 15, n)
        df = pd.DataFrame({
            "close": prices,
            "high": prices + 0.1,
            "low": prices - 0.1,
            "open": prices,
            "volume": np.full(n, 1e7),
            "amount": np.full(n, 1e8),
        })
        engine = BacktestEngine(initial_capital=1000000)
        strategy = DualMAStrategy(short_period=3, long_period=10)
        result = engine.run(strategy, df)
        assert np.isfinite(result.profit_factor)

    def test_get_param_space_classmethod(self):
        space = DualMAStrategy.get_param_space()
        assert isinstance(space, dict)
        assert "short_period" in space
        assert "long_period" in space

    def test_get_param_space_instance(self):
        strategy = DualMAStrategy(short_period=5, long_period=20)
        space = strategy.get_param_space()
        assert isinstance(space, dict)
        assert "short_period" in space


class TestBatchStrategyRunner:
    """Tests for BatchStrategyRunner class"""

    def test_batch_run_strategies(self, sample_ohlcv):
        runner = BatchStrategyRunner(initial_capital=1000000)
        result = runner.run_strategies(
            [DualMAStrategy, MACDStrategy],
            sample_ohlcv,
            top_n=5,
        )
        assert "results" in result
        assert "rankings" in result
        assert "summary" in result
        assert result["summary"]["total_strategies_tested"] >= 1

    def test_batch_run_invalid_input(self):
        runner = BatchStrategyRunner()
        result = runner.run_strategies([], None)
        assert "error" in result

    def test_batch_auto_optimize(self, sample_ohlcv):
        runner = BatchStrategyRunner(initial_capital=1000000)
        result = runner.auto_optimize(
            [DualMAStrategy, MACDStrategy],
            sample_ohlcv,
            max_combinations=5,
        )
        assert "best_strategy" in result
        assert "best_params" in result
        assert "best_result" in result
        assert "all_candidates_summary" in result

    def test_batch_auto_optimize_with_param_spaces(self, sample_ohlcv):
        runner = BatchStrategyRunner(initial_capital=1000000)
        param_spaces = {
            DualMAStrategy: {
                "short_period": {"min": 3, "max": 10, "step": 3},
                "long_period": {"min": 15, "max": 30, "step": 5},
            }
        }
        result = runner.auto_optimize(
            [DualMAStrategy],
            sample_ohlcv,
            param_spaces=param_spaces,
            max_combinations=10,
        )
        assert "best_strategy" in result
        assert len(result["all_candidates_summary"]) >= 1

    def test_is_better_than(self, sample_ohlcv):
        engine = BacktestEngine(initial_capital=1000000)
        r1 = engine.run(DualMAStrategy(short_period=5, long_period=20), sample_ohlcv)
        r2 = engine.run(DualMAStrategy(short_period=3, long_period=15), sample_ohlcv)
        assert isinstance(r1.is_better_than(r2), bool)

    def test_is_better_than_non_result(self, sample_ohlcv):
        engine = BacktestEngine(initial_capital=1000000)
        r1 = engine.run(DualMAStrategy(short_period=5, long_period=20), sample_ohlcv)
        assert r1.is_better_than(None) is False
        assert r1.is_better_than("not a result") is False

    def test_get_risk_adjusted_metrics(self, sample_ohlcv):
        engine = BacktestEngine(initial_capital=1000000)
        r1 = engine.run(DualMAStrategy(short_period=5, long_period=20), sample_ohlcv)
        metrics = r1.get_risk_adjusted_metrics()
        assert isinstance(metrics, dict)
        assert "sharpe" in metrics
        assert "sortino" in metrics
        assert "calmar" in metrics
        assert "omega" in metrics
        assert "return_risk_ratio" in metrics

    def test_get_drawdown_analysis(self, sample_ohlcv):
        engine = BacktestEngine(initial_capital=1000000)
        r1 = engine.run(DualMAStrategy(short_period=5, long_period=20), sample_ohlcv)
        dd_analysis = r1.get_drawdown_analysis()
        assert isinstance(dd_analysis, dict)
        assert "current_drawdown_pct" in dd_analysis or "error" in dd_analysis

    def test_get_trade_analysis(self, sample_ohlcv):
        engine = BacktestEngine(initial_capital=1000000)
        r1 = engine.run(DualMAStrategy(short_period=5, long_period=20), sample_ohlcv)
        trade_analysis = r1.get_trade_analysis()
        assert isinstance(trade_analysis, dict)
        assert "total_trades" in trade_analysis or "error" in trade_analysis

    def test_get_monthly_returns_table(self, sample_ohlcv):
        engine = BacktestEngine(initial_capital=1000000)
        r1 = engine.run(DualMAStrategy(short_period=5, long_period=20), sample_ohlcv)
        monthly = r1.get_monthly_returns_table()
        assert isinstance(monthly, dict)
        assert "months_count" in monthly or "error" in monthly


class TestBacktestProfiler:
    """Tests for BacktestProfiler class"""

    def test_profiler_basic(self):
        profiler = BacktestProfiler()
        profiler.record("test_phase", 0.001)
        profiler.record("test_phase", 0.002)
        report = profiler.get_report()
        assert "phases" in report
        assert "test_phase" in report["phases"]
        assert report["total_ms"] > 0

    def test_profiler_empty(self):
        profiler = BacktestProfiler()
        report = profiler.get_report()
        assert "error" in report

    def test_profiler_reset(self):
        profiler = BacktestProfiler()
        profiler.record("phase1", 0.001)
        profiler.reset()
        report = profiler.get_report()
        assert "error" in report
