"""
QuantCore 依赖注入模块

提供 FastAPI 兼容的依赖注入功能，改善代码可测试性和可维护性。

使用方式：
    from core.dependencies import get_db, get_config

    @app.get("/api/data")
    async def get_data(db: SQLiteStore = Depends(get_db)):
        return db.fetchall("SELECT * FROM table")
"""
from typing import Annotated

from fastapi import Depends

from core.backtest import BacktestEngine
from core.config import ConfigType, get_config
from core.data_fetcher import DataFetcher, get_fetcher
from core.database import AsyncDatabaseSession, SQLiteStore, get_db
from core.simulated_trading import SimulatedTrading
from core.strategies import CompositeStrategy


def get_db_sync() -> SQLiteStore:
    """获取同步数据库连接依赖

    Returns:
        SQLiteStore 实例
    """
    return get_db()


async def get_db_async() -> AsyncDatabaseSession:
    """获取异步数据库会话依赖

    Returns:
        AsyncDatabaseSession 实例
    """
    async with AsyncDatabaseSession() as session:
        yield session


def get_config_dep() -> ConfigType:
    """获取配置依赖

    Returns:
        配置字典
    """
    return get_config()


def get_fetcher_dep() -> DataFetcher:
    """获取数据获取器依赖

    Returns:
        DataFetcher 实例
    """
    return get_fetcher()


def get_composite_strategy() -> CompositeStrategy:
    """获取组合策略依赖

    Returns:
        CompositeStrategy 实例
    """
    return CompositeStrategy()


def get_backtest_engine() -> BacktestEngine:
    """获取回测引擎依赖

    Returns:
        BacktestEngine 实例
    """
    return BacktestEngine()


def get_simulated_trading() -> SimulatedTrading:
    """获取模拟交易依赖

    Returns:
        SimulatedTrading 实例
    """
    return SimulatedTrading()


# 类型别名，简化依赖声明
DbDep = Annotated[SQLiteStore, Depends(get_db_sync)]
ConfigDep = Annotated[ConfigType, Depends(get_config_dep)]
FetcherDep = Annotated[DataFetcher, Depends(get_fetcher_dep)]
StrategyDep = Annotated[CompositeStrategy, Depends(get_composite_strategy)]
BacktestDep = Annotated[BacktestEngine, Depends(get_backtest_engine)]
TradingDep = Annotated[SimulatedTrading, Depends(get_simulated_trading)]


__all__ = [
    'get_db_sync',
    'get_db_async',
    'get_config_dep',
    'get_fetcher_dep',
    'get_composite_strategy',
    'get_backtest_engine',
    'get_simulated_trading',
    'DbDep',
    'ConfigDep',
    'FetcherDep',
    'StrategyDep',
    'BacktestDep',
    'TradingDep',
]
