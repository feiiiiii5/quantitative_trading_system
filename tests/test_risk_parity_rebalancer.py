import numpy as np

from core.risk_parity_rebalancer import RebalanceResult, RiskParityRebalancer


class TestRiskParityRebalancerBasic:
    def test_insufficient_positions(self):
        rebalancer = RiskParityRebalancer()
        result = rebalancer.analyze(
            [{"symbol": "A", "weight": 1.0}],
            np.array([[0.01]]),
        )
        assert not result.needs_rebalance
        assert "不足" in result.reason

    def test_cov_matrix_mismatch(self):
        rebalancer = RiskParityRebalancer()
        positions = [
            {"symbol": "A", "weight": 0.5},
            {"symbol": "B", "weight": 0.5},
        ]
        result = rebalancer.analyze(positions, np.array([[0.01]]))
        assert not result.needs_rebalance
        assert "不匹配" in result.reason

    def test_equal_risk_rebalance(self):
        rebalancer = RiskParityRebalancer(drift_threshold=0.01)
        np.random.seed(42)
        n = 4
        cov = np.eye(n) * 0.04
        cov[0, 1] = cov[1, 0] = 0.01
        cov[2, 3] = cov[3, 2] = 0.01
        positions = [
            {"symbol": f"S{i}", "name": f"Stock{i}", "weight": 0.5 if i == 0 else 0.5 / (n - 1)}
            for i in range(n)
        ]
        result = rebalancer.analyze(positions, cov)
        assert isinstance(result, RebalanceResult)
        assert result.max_drift > 0

    def test_no_rebalance_when_close(self):
        rebalancer = RiskParityRebalancer(drift_threshold=0.5)
        np.random.seed(42)
        n = 3
        cov = np.eye(n) * 0.04
        positions = [
            {"symbol": f"S{i}", "name": f"Stock{i}", "weight": 1.0 / n}
            for i in range(n)
        ]
        result = rebalancer.analyze(positions, cov)
        assert not result.needs_rebalance or result.max_drift < 0.5

    def test_zero_weights(self):
        rebalancer = RiskParityRebalancer()
        positions = [
            {"symbol": "A", "weight": 0.0},
            {"symbol": "B", "weight": 0.0},
        ]
        cov = np.eye(2) * 0.04
        result = rebalancer.analyze(positions, cov)
        assert isinstance(result, RebalanceResult)


class TestRiskParityRebalancerTurnover:
    def test_turnover_cap(self):
        rebalancer = RiskParityRebalancer(drift_threshold=0.01, turnover_cap=0.10)
        np.random.seed(42)
        n = 5
        cov = np.eye(n) * 0.04
        positions = [
            {"symbol": f"S{i}", "name": f"Stock{i}", "weight": 0.8 if i == 0 else 0.2 / (n - 1)}
            for i in range(n)
        ]
        result = rebalancer.analyze(positions, cov)
        assert result.total_turnover <= 0.10 + 0.001


class TestRiskParityRebalancerTrades:
    def test_trade_actions(self):
        rebalancer = RiskParityRebalancer(drift_threshold=0.01)
        np.random.seed(42)
        n = 3
        cov = np.eye(n) * 0.04
        positions = [
            {"symbol": "A", "name": "StockA", "weight": 0.8},
            {"symbol": "B", "name": "StockB", "weight": 0.1},
            {"symbol": "C", "name": "StockC", "weight": 0.1},
        ]
        result = rebalancer.analyze(positions, cov, prices={"A": 10.0, "B": 20.0, "C": 30.0}, capital=100000)
        for trade in result.trades:
            assert trade.action in ("buy", "sell")
            if trade.action == "buy":
                assert trade.weight_delta > 0
            else:
                assert trade.weight_delta < 0

    def test_shares_calculation(self):
        rebalancer = RiskParityRebalancer(drift_threshold=0.01)
        n = 3
        cov = np.eye(n) * 0.04
        positions = [
            {"symbol": "A", "name": "StockA", "weight": 0.8},
            {"symbol": "B", "name": "StockB", "weight": 0.1},
            {"symbol": "C", "name": "StockC", "weight": 0.1},
        ]
        result = rebalancer.analyze(positions, cov, prices={"A": 10.0, "B": 20.0, "C": 30.0}, capital=100000)
        for trade in result.trades:
            if trade.price > 0 and trade.shares > 0:
                assert trade.shares % 100 == 0

    def test_no_prices_zero_shares(self):
        rebalancer = RiskParityRebalancer(drift_threshold=0.01)
        n = 3
        cov = np.eye(n) * 0.04
        positions = [
            {"symbol": "A", "name": "StockA", "weight": 0.8},
            {"symbol": "B", "name": "StockB", "weight": 0.1},
            {"symbol": "C", "name": "StockC", "weight": 0.1},
        ]
        result = rebalancer.analyze(positions, cov, prices={}, capital=100000)
        for trade in result.trades:
            assert trade.shares == 0
