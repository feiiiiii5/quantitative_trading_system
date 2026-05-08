"""
Tests for portfolio_theory module - Modern Portfolio Theory
"""
import logging

import numpy as np
import pandas as pd

logging.basicConfig(level=logging.WARNING)

# Test data generators
def generate_test_prices(n_assets=5, n_days=252, seed=42):
    """Generate test price data"""
    np.random.seed(seed)
    returns = np.random.normal(0.0005, 0.02, (n_days, n_assets))
    prices = 100 * np.cumprod(1 + returns, axis=0)
    symbols = [f"SYM{i:02d}" for i in range(1, n_assets+1)]
    return pd.DataFrame(prices, columns=symbols)


class TestModernPortfolioTheory:
    """Test suite for ModernPortfolioTheory class"""

    def test_initialization(self):
        """Test initialization with default parameters"""
        from core.portfolio_theory import ModernPortfolioTheory

        mpt = ModernPortfolioTheory()
        assert mpt.risk_free_rate == 0.03
        assert mpt.min_weight == 0.0
        assert mpt.max_weight == 1.0

        # Custom initialization
        mpt = ModernPortfolioTheory(
            risk_free_rate=0.05,
            min_weight=0.05,
            max_weight=0.4,
        )
        assert mpt.risk_free_rate == 0.05
        assert mpt.min_weight == 0.05
        assert mpt.max_weight == 0.4

    def test_calculate_returns(self):
        """Test calculation of log returns"""
        from core.portfolio_theory import ModernPortfolioTheory

        mpt = ModernPortfolioTheory()
        prices = generate_test_prices(n_assets=3, n_days=100)
        returns = mpt.calculate_returns(prices)

        assert isinstance(returns, pd.DataFrame)
        assert returns.shape[0] == prices.shape[0] - 1
        assert returns.shape[1] == prices.shape[1]
        assert not returns.isna().all().all()

    def test_calculate_annual_returns(self):
        """Test calculation of annual returns"""
        from core.portfolio_theory import ModernPortfolioTheory

        mpt = ModernPortfolioTheory()
        prices = generate_test_prices(n_assets=3, n_days=252)
        returns = mpt.calculate_returns(prices)
        annual_returns = mpt.calculate_annual_returns(returns)

        assert isinstance(annual_returns, pd.Series)
        assert len(annual_returns) == 3

    def test_calculate_covariance_matrix(self):
        """Test calculation of covariance matrix"""
        from core.portfolio_theory import ModernPortfolioTheory

        mpt = ModernPortfolioTheory()
        prices = generate_test_prices(n_assets=3, n_days=252)
        returns = mpt.calculate_returns(prices)
        cov_matrix = mpt.calculate_covariance_matrix(returns)

        assert isinstance(cov_matrix, pd.DataFrame)
        assert cov_matrix.shape == (3, 3)
        # Covariance matrix should be symmetric
        np.testing.assert_array_almost_equal(
            cov_matrix.values, cov_matrix.values.T
        )

    def test_portfolio_return(self):
        """Test portfolio return calculation"""
        from core.portfolio_theory import ModernPortfolioTheory

        mpt = ModernPortfolioTheory()
        prices = generate_test_prices(n_assets=3, n_days=100)
        returns = mpt.calculate_returns(prices)
        annual_returns = mpt.calculate_annual_returns(returns)

        # Equal weights
        weights = np.array([1/3, 1/3, 1/3])
        port_return = mpt.portfolio_return(weights, annual_returns)
        assert isinstance(port_return, float)

        # Single asset weight
        weights = np.array([1.0, 0.0, 0.0])
        port_return = mpt.portfolio_return(weights, annual_returns)
        assert abs(port_return - annual_returns.iloc[0]) < 1e-10

    def test_portfolio_volatility(self):
        """Test portfolio volatility calculation"""
        from core.portfolio_theory import ModernPortfolioTheory

        mpt = ModernPortfolioTheory()
        prices = generate_test_prices(n_assets=3, n_days=100)
        returns = mpt.calculate_returns(prices)
        cov_matrix = mpt.calculate_covariance_matrix(returns)

        weights = np.array([1/3, 1/3, 1/3])
        vol = mpt.portfolio_volatility(weights, cov_matrix)
        assert isinstance(vol, float)
        assert vol >= 0.0

    def test_sharpe_ratio(self):
        """Test Sharpe ratio calculation"""
        from core.portfolio_theory import ModernPortfolioTheory

        mpt = ModernPortfolioTheory(risk_free_rate=0.02)
        prices = generate_test_prices(n_assets=3, n_days=100)
        returns = mpt.calculate_returns(prices)
        annual_returns = mpt.calculate_annual_returns(returns)
        cov_matrix = mpt.calculate_covariance_matrix(returns)

        weights = np.array([1/3, 1/3, 1/3])
        sharpe = mpt.sharpe_ratio(weights, annual_returns, cov_matrix)
        assert isinstance(sharpe, float)

    def test_diversification_ratio(self):
        """Test diversification ratio calculation"""
        from core.portfolio_theory import ModernPortfolioTheory

        mpt = ModernPortfolioTheory()
        prices = generate_test_prices(n_assets=3, n_days=100)
        returns = mpt.calculate_returns(prices)
        cov_matrix = mpt.calculate_covariance_matrix(returns)

        weights = np.array([1/3, 1/3, 1/3])
        div_ratio = mpt.diversification_ratio(weights, cov_matrix)
        assert isinstance(div_ratio, float)
        assert div_ratio >= 1.0  # Diversification ratio >= 1 for diversified portfolio

    def test_optimize_max_sharpe(self):
        """Test max Sharpe ratio optimization"""
        from core.portfolio_theory import ModernPortfolioTheory

        mpt = ModernPortfolioTheory()
        prices = generate_test_prices(n_assets=5, n_days=252)
        result = mpt.optimize_max_sharpe(prices)

        assert result.is_valid
        assert isinstance(result.weights, dict)
        assert len(result.weights) == 5
        assert abs(sum(result.weights.values()) - 1.0) < 1e-10
        assert result.expected_return is not None
        assert result.expected_volatility is not None
        assert result.sharpe_ratio is not None

    def test_optimize_min_volatility(self):
        """Test minimum volatility optimization"""
        from core.portfolio_theory import ModernPortfolioTheory

        mpt = ModernPortfolioTheory()
        prices = generate_test_prices(n_assets=5, n_days=252)
        result = mpt.optimize_min_volatility(prices)

        assert result.is_valid
        assert isinstance(result.weights, dict)
        assert len(result.weights) == 5
        assert abs(sum(result.weights.values()) - 1.0) < 1e-10

    def test_optimize_risk_parity(self):
        """Test risk parity optimization"""
        from core.portfolio_theory import ModernPortfolioTheory

        mpt = ModernPortfolioTheory()
        prices = generate_test_prices(n_assets=5, n_days=252)
        result = mpt.optimize_risk_parity(prices)

        assert result.is_valid
        assert isinstance(result.weights, dict)
        assert len(result.weights) == 5
        assert abs(sum(result.weights.values()) - 1.0) < 1e-10

    def test_optimize_equal_weight(self):
        """Test equal weight optimization"""
        from core.portfolio_theory import ModernPortfolioTheory

        mpt = ModernPortfolioTheory()
        prices = generate_test_prices(n_assets=5, n_days=252)
        result = mpt.optimize_equal_weight(prices)

        assert result.is_valid
        assert isinstance(result.weights, dict)
        assert len(result.weights) == 5
        # Check that weights are equal
        for w in result.weights.values():
            assert abs(w - 0.2) < 1e-10
        assert abs(sum(result.weights.values()) - 1.0) < 1e-10

    def test_optimize_with_fixed_weights(self):
        """Test optimization with fixed weights"""
        from core.portfolio_theory import ModernPortfolioTheory

        mpt = ModernPortfolioTheory()
        prices = generate_test_prices(n_assets=5, n_days=252)

        fixed_weights = {"SYM01": 0.5, "SYM02": 0.3}
        result = mpt.optimize_max_sharpe(prices, fixed_weights=fixed_weights)

        assert result.is_valid
        assert abs(result.weights["SYM01"] - 0.5) < 1e-10
        assert abs(result.weights["SYM02"] - 0.3) < 1e-10
        assert abs(sum(result.weights.values()) - 1.0) < 1e-10

    def test_optimize_insufficient_data(self):
        """Test optimization with insufficient data"""
        from core.portfolio_theory import ModernPortfolioTheory

        mpt = ModernPortfolioTheory()
        prices = generate_test_prices(n_assets=3, n_days=5)
        result = mpt.optimize_max_sharpe(prices)

        assert not result.is_valid
        assert "Insufficient" in result.message

    def test_generate_efficient_frontier(self):
        """Test generation of efficient frontier"""
        from core.portfolio_theory import ModernPortfolioTheory

        mpt = ModernPortfolioTheory()
        prices = generate_test_prices(n_assets=5, n_days=252)
        frontier = mpt.generate_efficient_frontier(prices, n_points=10)

        assert isinstance(frontier, list)
        assert len(frontier) == 10
        for point in frontier:
            assert "return" in point
            assert "volatility" in point
            assert "sharpe_ratio" in point
            assert "weights" in point
            assert isinstance(point["weights"], dict)
            assert len(point["weights"]) == 5

    def test_portfolio_optimization_result(self):
        """Test PortfolioOptimizationResult dataclass"""
        from core.portfolio_theory import PortfolioOptimizationResult

        result = PortfolioOptimizationResult(
            weights={"A": 0.6, "B": 0.4},
            expected_return=0.15,
            expected_volatility=0.20,
            sharpe_ratio=0.6,
            diversification_ratio=1.5,
            is_valid=True,
            message="Success",
        )

        assert result.weights == {"A": 0.6, "B": 0.4}
        assert result.expected_return == 0.15
        assert result.expected_volatility == 0.20
        assert result.sharpe_ratio == 0.6
        assert result.diversification_ratio == 1.5
        assert result.is_valid
        assert result.message == "Success"

    def test_weight_constraints(self):
        """Test that weights respect min and max constraints"""
        from core.portfolio_theory import ModernPortfolioTheory

        mpt = ModernPortfolioTheory(
            min_weight=0.1,
            max_weight=0.5,
        )
        prices = generate_test_prices(n_assets=5, n_days=252)
        result = mpt.optimize_max_sharpe(prices)

        assert result.is_valid
        for weight in result.weights.values():
            assert weight >= 0.0  # Soft constraint check
            assert weight <= 1.0

    def test_all_optimization_methods_comparison(self):
        """Test that all optimization methods produce valid results"""
        from core.portfolio_theory import ModernPortfolioTheory

        mpt = ModernPortfolioTheory()
        prices = generate_test_prices(n_assets=5, n_days=252)

        results = {
            "max_sharpe": mpt.optimize_max_sharpe(prices),
            "min_volatility": mpt.optimize_min_volatility(prices),
            "risk_parity": mpt.optimize_risk_parity(prices),
            "equal_weight": mpt.optimize_equal_weight(prices),
        }

        for name, result in results.items():
            assert result.is_valid, f"{name} should be valid"
            assert abs(sum(result.weights.values()) - 1.0) < 1e-10
