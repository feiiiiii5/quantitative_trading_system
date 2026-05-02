import numpy as np
import pandas as pd
import pytest
from datetime import datetime, timedelta


@pytest.fixture
def sample_ohlcv():
    np.random.seed(42)
    n = 200
    dates = pd.date_range("2024-01-01", periods=n, freq="B")
    base = 10.0
    returns = np.random.randn(n) * 0.02 + 0.0003
    close = base * np.cumprod(1 + returns)
    high = close * (1 + np.abs(np.random.randn(n)) * 0.01)
    low = close * (1 - np.abs(np.random.randn(n)) * 0.01)
    open_p = close * (1 + np.random.randn(n) * 0.005)
    volume = np.random.randint(500000, 5000000, n).astype(float)
    amount = close * volume

    return pd.DataFrame({
        "date": dates,
        "open": open_p,
        "high": high,
        "low": low,
        "close": close,
        "volume": volume,
        "amount": amount,
    }).reset_index(drop=True)


@pytest.fixture
def trending_up_ohlcv():
    n = 100
    dates = pd.date_range("2024-01-01", periods=n, freq="B")
    close = np.linspace(10, 20, n)
    high = close * 1.01
    low = close * 0.99
    open_p = close * 0.998
    volume = np.ones(n) * 1000000
    return pd.DataFrame({
        "date": dates, "open": open_p, "high": high, "low": low,
        "close": close, "volume": volume, "amount": close * volume,
    }).reset_index(drop=True)


@pytest.fixture
def trending_down_ohlcv():
    n = 100
    dates = pd.date_range("2024-01-01", periods=n, freq="B")
    close = np.linspace(20, 10, n)
    high = close * 1.01
    low = close * 0.99
    open_p = close * 1.002
    volume = np.ones(n) * 1000000
    return pd.DataFrame({
        "date": dates, "open": open_p, "high": high, "low": low,
        "close": close, "volume": volume, "amount": close * volume,
    }).reset_index(drop=True)


@pytest.fixture
def sideways_ohlcv():
    n = 100
    dates = pd.date_range("2024-01-01", periods=n, freq="B")
    np.random.seed(42)
    close = 15 + np.random.randn(n) * 0.3
    high = close + 0.2
    low = close - 0.2
    open_p = close + np.random.randn(n) * 0.1
    volume = np.ones(n) * 1000000
    return pd.DataFrame({
        "date": dates, "open": open_p, "high": high, "low": low,
        "close": close, "volume": volume, "amount": close * volume,
    }).reset_index(drop=True)


@pytest.fixture
def event_bus():
    from core.events import EventBus
    return EventBus()


@pytest.fixture
def risk_manager():
    from core.risk_manager import EnhancedRiskManager
    return EnhancedRiskManager(initial_capital=1000000)
