
from core.portfolio_rebalancer import (
    PortfolioRebalancer,
    RebalanceConfig,
    RebalanceStrategy,
    get_rebalancer,
)


class TestPortfolioRebalancer:
    def test_calculate_weights(self):
        r = PortfolioRebalancer()
        holdings = {"AAPL": 50000, "GOOGL": 30000, "MSFT": 20000}
        total = 100000
        weights = r.calculate_current_weights(holdings, total)
        assert abs(weights["AAPL"] - 0.5) < 0.001
        assert abs(weights["GOOGL"] - 0.3) < 0.001
        assert abs(weights["MSFT"] - 0.2) < 0.001

    def test_calculate_drift(self):
        r = PortfolioRebalancer()
        target = {"AAPL": 0.5, "GOOGL": 0.3, "MSFT": 0.2}
        current = {"AAPL": 0.4, "GOOGL": 0.4, "MSFT": 0.2}
        drift = r.calculate_drift(target, current)
        assert drift == 0.1

    def test_check_rebalance_needed_true(self):
        r = PortfolioRebalancer(RebalanceConfig(drift_threshold=0.05))
        target = {"AAPL": 0.5, "GOOGL": 0.3, "MSFT": 0.2}
        current = {"AAPL": 0.4, "GOOGL": 0.4, "MSFT": 0.2}
        needed, drift = r.check_rebalance_needed(target, current)
        assert needed
        assert abs(drift - 0.1) < 0.001

    def test_check_rebalance_needed_false(self):
        r = PortfolioRebalancer(RebalanceConfig(drift_threshold=0.2))
        target = {"AAPL": 0.5, "GOOGL": 0.3, "MSFT": 0.2}
        current = {"AAPL": 0.48, "GOOGL": 0.32, "MSFT": 0.2}
        needed, drift = r.check_rebalance_needed(target, current)
        assert not needed

    def test_threshold_rebalance_generates_orders(self):
        r = PortfolioRebalancer(RebalanceConfig(strategy=RebalanceStrategy.THRESHOLD, drift_threshold=0.01))
        target = {"AAPL": 0.5, "GOOGL": 0.3, "MSFT": 0.2}
        holdings = {"AAPL": 30000, "GOOGL": 40000, "MSFT": 30000}
        prices = {"AAPL": 150, "GOOGL": 2800, "MSFT": 380}
        result = r.generate_orders(target, holdings, 100000, prices)
        assert result.n_orders > 0
        assert result.total_portfolio_value == 100000

    def test_rebalance_reduces_drift(self):
        r = PortfolioRebalancer(RebalanceConfig(strategy=RebalanceStrategy.THRESHOLD))
        target = {"AAPL": 0.5, "GOOGL": 0.3, "MSFT": 0.2}
        holdings = {"AAPL": 30000, "GOOGL": 40000, "MSFT": 30000}
        prices = {"AAPL": 150, "GOOGL": 2800, "MSFT": 380}
        result = r.generate_orders(target, holdings, 100000, prices)
        assert result.weight_drift_after < result.weight_drift_before

    def test_empty_holdings(self):
        r = PortfolioRebalancer()
        target = {"AAPL": 0.5, "GOOGL": 0.5}
        holdings = {}
        prices = {"AAPL": 150, "GOOGL": 2800}
        result = r.generate_orders(target, holdings, 100000, prices)
        assert result.n_orders == 2

    def test_zero_total_value(self):
        r = PortfolioRebalancer()
        result = r.generate_orders({"AAPL": 0.5}, {}, 0, {"AAPL": 150})
        assert result.n_orders == 0

    def test_ignore_small_weights(self):
        cfg = RebalanceConfig(ignore_small_weights=0.15)
        r = PortfolioRebalancer(cfg)
        target = {"AAPL": 0.5, "GOOGL": 0.3, "MSFT": 0.2}
        holdings = {"AAPL": 50000, "GOOGL": 30000, "MSFT": 20000}
        prices = {"AAPL": 150, "GOOGL": 2800, "MSFT": 380}
        result = r.generate_orders(target, holdings, 100000, prices)
        assert result.n_orders == 0


class TestRebalanceStrategies:
    def test_cost_aware_strategy(self):
        cfg = RebalanceConfig(strategy=RebalanceStrategy.COST_AWARE, cost_budget_pct=0.0001)
        r = PortfolioRebalancer(cfg)
        target = {"AAPL": 0.5, "GOOGL": 0.5}
        holdings = {"AAPL": 20000, "GOOGL": 80000}
        prices = {"AAPL": 100, "GOOGL": 100}
        result = r.generate_orders(target, holdings, 100000, prices)
        assert result.n_orders >= 0

    def test_gradual_strategy(self):
        cfg = RebalanceConfig(strategy=RebalanceStrategy.GRADUAL, gradual_days=5)
        r = PortfolioRebalancer(cfg)
        target = {"AAPL": 0.5, "GOOGL": 0.5}
        holdings = {"AAPL": 20000, "GOOGL": 80000}
        prices = {"AAPL": 100, "GOOGL": 100}
        result = r.generate_orders(target, holdings, 100000, prices)
        assert result.n_orders > 0
        assert all(o.quantity < 300 for o in result.orders)

    def test_min_variance_strategy(self):
        cfg = RebalanceConfig(strategy=RebalanceStrategy.MIN_VARIANCE)
        r = PortfolioRebalancer(cfg)
        target = {"AAPL": 0.5, "GOOGL": 0.5}
        holdings = {"AAPL": 30000, "GOOGL": 70000}
        prices = {"AAPL": 100, "GOOGL": 100}
        result = r.generate_orders(target, holdings, 100000, prices)
        assert result.n_orders >= 0

    def test_partial_mode(self):
        cfg = RebalanceConfig(rebalance_mode="partial")
        r = PortfolioRebalancer(cfg)
        target = {"AAPL": 0.4, "GOOGL": 0.3, "MSFT": 0.2, "AMZN": 0.1}
        holdings = {"AAPL": 50000, "GOOGL": 20000, "MSFT": 20000, "AMZN": 10000}
        prices = {"AAPL": 100, "GOOGL": 100, "MSFT": 100, "AMZN": 100}
        result = r.generate_orders(target, holdings, 100000, prices)
        assert result.n_orders <= 4


class TestPortfolioRebalancerHistory:
    def test_rebalance_history(self):
        r = PortfolioRebalancer()
        target = {"AAPL": 0.6, "GOOGL": 0.4}
        holdings = {"AAPL": 30000, "GOOGL": 70000}
        prices = {"AAPL": 100, "GOOGL": 100}
        r.generate_orders(target, holdings, 100000, prices)
        history = r.get_rebalance_history()
        assert len(history) == 1

    def test_performance_summary(self):
        r = PortfolioRebalancer()
        target = {"AAPL": 0.6, "GOOGL": 0.4}
        holdings = {"AAPL": 30000, "GOOGL": 70000}
        prices = {"AAPL": 100, "GOOGL": 100}
        r.generate_orders(target, holdings, 100000, prices)
        summary = r.get_performance_summary()
        assert summary["n_rebalances"] == 1
        assert "avg_turnover_pct" in summary


class TestPortfolioRebalancerSnapshot:
    def test_allocation_snapshot(self):
        r = PortfolioRebalancer()
        target = {"AAPL": 0.5, "GOOGL": 0.5}
        holdings = {"AAPL": 30000, "GOOGL": 70000}
        snap = r.get_allocation_snapshot(target, holdings, 100000)
        assert snap.total_value == 100000
        assert snap.drift > 0
        d = snap.to_dict()
        assert "target_weights" in d


class TestPortfolioRebalancerSingleton:
    def test_singleton(self):
        r1 = get_rebalancer()
        r2 = get_rebalancer()
        assert r1 is r2
