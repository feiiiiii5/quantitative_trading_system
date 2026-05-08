"""
Tests for portfolio_analyzer module - Portfolio Backtest Analyzer
"""
from datetime import datetime, timedelta

import numpy as np
import pandas as pd
import pytest

from core.portfolio_analyzer import (
    PortfolioBacktester,
    PortfolioBacktestResult,
    RebalanceFrequency,
)


def generate_test_price_data(
    n_symbols: int = 5,
    n_days: int = 252,
    start_date: str = "2023-01-01",
    base_price: float = 100.0,
    seed: int = 42,
) -> pd.DataFrame:
    """Generate test price data"""
    np.random.seed(seed)

    # Generate dates
    dates = [datetime.strptime(start_date, "%Y-%m-%d") + timedelta(days=i)
             for i in range(n_days)]

    # Generate prices with random walks
    data = {}
    for i in range(n_symbols):
        # Generate returns
        daily_returns = np.random.normal(0.0005, 0.02, n_days)
        # Compute price series
        prices = base_price * np.cumprod(1 + daily_returns)
        data[f"SYM{i:02d}"] = prices

    return pd.DataFrame(data, index=dates)


class TestPortfolioBacktester:
    """Test suite for PortfolioBacktester class"""

    def test_initialization(self):
        """Test initialization with default parameters"""
        bt = PortfolioBacktester()
        assert bt.initial_capital == 100000.0
        assert bt.rebalance_frequency == RebalanceFrequency.MONTHLY
        assert bt.commission_rate == 0.0003
        assert bt.slippage_rate == 0.001
        assert bt.risk_free_rate == 0.03

    def test_initialization_custom(self):
        """Test initialization with custom parameters"""
        bt = PortfolioBacktester(
            initial_capital=50000.0,
            rebalance_frequency=RebalanceFrequency.QUARTERLY,
            commission_rate=0.001,
            slippage_rate=0.002,
            risk_free_rate=0.05,
        )
        assert bt.initial_capital == 50000.0
        assert bt.rebalance_frequency == RebalanceFrequency.QUARTERLY
        assert bt.commission_rate == 0.001
        assert bt.slippage_rate == 0.002
        assert bt.risk_free_rate == 0.05

    def test_load_price_data(self):
        """Test loading price data"""
        prices = generate_test_price_data()
        bt = PortfolioBacktester()
        bt.load_price_data(prices)
        assert bt._price_data is not None
        assert len(bt._price_data) == len(prices)
        assert len(bt._price_data.columns) == len(prices.columns)

    def test_set_static_weights_normalizes(self):
        """Test that static weights are normalized if they don't sum to 1"""
        bt = PortfolioBacktester()
        # Set weights that don't sum to 1
        bt.set_static_weights({"A": 0.3, "B": 0.3, "C": 0.3})
        # Should normalize to ~0.333 each
        total = sum(bt._weights.values())
        assert abs(total - 1.0) < 1e-6
        for weight in bt._weights.values():
            assert abs(weight - 0.3333333333333333) < 1e-6

    def test_set_static_weights_keeps_normalized(self):
        """Test that already normalized weights are preserved"""
        bt = PortfolioBacktester()
        bt.set_static_weights({"A": 0.2, "B": 0.3, "C": 0.5})
        assert bt._weights["A"] == 0.2
        assert bt._weights["B"] == 0.3
        assert bt._weights["C"] == 0.5

    def test_run_backtest_basic(self):
        """Test running a basic backtest"""
        prices = generate_test_price_data(n_symbols=3, n_days=126)
        bt = PortfolioBacktester(initial_capital=10000.0)
        bt.load_price_data(prices)
        bt.set_static_weights({
            "SYM00": 0.4,
            "SYM01": 0.3,
            "SYM02": 0.3,
        })

        result = bt.run_backtest()

        assert isinstance(result, PortfolioBacktestResult)
        assert result.initial_capital == 10000.0
        assert result.final_capital > 0
        assert len(result.equity_curve) == 126
        assert len(result.rebalance_dates) > 0

    def test_backtest_returns_correct_columns(self):
        """Test that backtest includes all symbols in weights"""
        prices = generate_test_price_data(n_symbols=5, n_days=60)
        bt = PortfolioBacktester()
        bt.load_price_data(prices)
        bt.set_static_weights({"SYM00": 0.5, "SYM02": 0.5})

        result = bt.run_backtest()

        # Basic checks
        assert result.total_trades >= 0
        assert result.annualized_return is not None

    def test_get_rebalance_dates_monthly(self):
        """Test monthly rebalance date calculation"""
        prices = generate_test_price_data(n_symbols=3, n_days=365)
        bt = PortfolioBacktester(rebalance_frequency=RebalanceFrequency.MONTHLY)
        bt.load_price_data(prices)

        dates = bt._get_rebalance_dates()
        assert len(dates) > 0
        assert dates[0] == prices.index[0]
        assert dates[-1] == prices.index[-1]

        # Check number of rebalances (should be around 12-13 for a year)
        assert 10 <= len(dates) <= 15

    def test_get_rebalance_dates_weekly(self):
        """Test weekly rebalance date calculation"""
        prices = generate_test_price_data(n_symbols=3, n_days=90)
        bt = PortfolioBacktester(rebalance_frequency=RebalanceFrequency.WEEKLY)
        bt.load_price_data(prices)

        dates = bt._get_rebalance_dates()
        assert len(dates) > 0
        assert len(dates) >= 10  # Should have at least ~12 weeks for 90 days

    def test_backtest_result_to_dict(self):
        """Test converting PortfolioBacktestResult to dict"""
        prices = generate_test_price_data(n_symbols=3, n_days=60)
        bt = PortfolioBacktester()
        bt.load_price_data(prices)
        bt.set_static_weights({"SYM00": 0.5, "SYM01": 0.5})

        result = bt.run_backtest()
        result_dict = result.to_dict()

        assert isinstance(result_dict, dict)
        assert "initial_capital" in result_dict
        assert "final_capital" in result_dict
        assert "total_return" in result_dict
        assert "annualized_return" in result_dict
        assert "sharpe_ratio" in result_dict
        assert "max_drawdown" in result_dict
        assert "equity_curve" in result_dict

    def test_backtest_without_weights_raises_error(self):
        """Test that backtest raises error if no weights set"""
        prices = generate_test_price_data()
        bt = PortfolioBacktester()
        bt.load_price_data(prices)

        with pytest.raises(ValueError):
            bt.run_backtest()

    def test_backtest_without_price_data_raises_error(self):
        """Test that backtest raises error if no price data loaded"""
        bt = PortfolioBacktester()
        bt.set_static_weights({"A": 0.5, "B": 0.5})

        with pytest.raises(ValueError):
            bt.run_backtest()

    def test_backtest_missing_symbol_raises_error(self):
        """Test backtest raises error if price data missing for a symbol"""
        prices = generate_test_price_data(n_symbols=3)
        bt = PortfolioBacktester()
        bt.load_price_data(prices)
        # Set weights containing symbol not in prices
        bt.set_static_weights({"SYM00": 0.5, "SYM99": 0.5})

        with pytest.raises(ValueError):
            bt.run_backtest()

    def test_different_rebalance_frequencies(self):
        """Test backtest with different rebalance frequencies"""
        prices = generate_test_price_data(n_symbols=2, n_days=126)

        frequencies = [
            RebalanceFrequency.DAILY,
            RebalanceFrequency.WEEKLY,
            RebalanceFrequency.MONTHLY,
            RebalanceFrequency.QUARTERLY,
            RebalanceFrequency.YEARLY,
        ]

        for freq in frequencies:
            bt = PortfolioBacktester(rebalance_frequency=freq)
            bt.load_price_data(prices)
            bt.set_static_weights({"SYM00": 0.5, "SYM01": 0.5})

            result = bt.run_backtest()
            assert isinstance(result, PortfolioBacktestResult)
            assert len(result.rebalance_dates) > 0


class TestPortfolioBacktestResult:
    """Test suite for PortfolioBacktestResult class"""

    def test_creation_with_defaults(self):
        """Test creating a result with basic values"""
        dates = pd.date_range(start="2023-01-01", periods=60, freq="D")
        equity = pd.Series(100000.0, index=dates)

        result = PortfolioBacktestResult(
            initial_capital=100000.0,
            final_capital=100000.0,
            total_return=0.0,
            annualized_return=0.0,
            annualized_volatility=0.0,
            sharpe_ratio=0.0,
            sortino_ratio=0.0,
            max_drawdown=0.0,
            max_drawdown_duration=0,
            win_rate=0.5,
            total_trades=0,
            turnover=0.0,
            equity_curve=equity,
            drawdown_curve=pd.Series(0.0, index=dates),
            monthly_returns=pd.Series(),
        )

        assert result.initial_capital == 100000.0
        assert result.final_capital == 100000.0
        assert result.total_trades == 0
