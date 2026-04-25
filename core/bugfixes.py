"""
QuantCore 已知Bug修复模块
1. AkShare高频限流 - 令牌桶+请求队列 (已有rate_limit.py)
2. 富途OpenAPI自动重连 - 指数退避
3. 浮点精度 - Decimal (已在matching_engine.py中使用)
4. 未完成K线标记 - is_complete标记
5. 订单互斥锁 - 防止竞态条件
6. Parquet原子写入 - 先写临时文件再重命名 (已在cache.py中实现)
"""
import asyncio
import logging
import time
from typing import Callable, Optional, TypeVar

logger = logging.getLogger(__name__)

T = TypeVar("T")


class AutoReconnect:
    """带指数退避的自动重连逻辑 - 修复富途OpenAPI断线不重连"""

    def __init__(self, connect_fn: Callable, max_retries: int = 10,
                 base_delay: float = 1.0, max_delay: float = 60.0):
        self._connect_fn = connect_fn
        self._max_retries = max_retries
        self._base_delay = base_delay
        self._max_delay = max_delay
        self._connected = False
        self._retry_count = 0
        self._last_error: Optional[Exception] = None

    async def connect(self) -> bool:
        try:
            if asyncio.iscoroutinefunction(self._connect_fn):
                await self._connect_fn()
            else:
                self._connect_fn()
            self._connected = True
            self._retry_count = 0
            return True
        except Exception as e:
            self._last_error = e
            self._connected = False
            return False

    async def reconnect(self) -> bool:
        self._retry_count += 1
        if self._retry_count > self._max_retries:
            logger.error(f"重连失败，已达最大重试次数 {self._max_retries}")
            return False

        delay = min(self._base_delay * (2 ** (self._retry_count - 1)), self._max_delay)
        jitter = delay * 0.1
        actual_delay = delay + (time.time() % 1) * jitter

        logger.info(f"尝试重连 (第{self._retry_count}次)，等待{actual_delay:.1f}秒...")
        await asyncio.sleep(actual_delay)

        try:
            if asyncio.iscoroutinefunction(self._connect_fn):
                await self._connect_fn()
            else:
                self._connect_fn()
            self._connected = True
            self._retry_count = 0
            logger.info("重连成功")
            return True
        except Exception as e:
            self._last_error = e
            self._connected = False
            return await self.reconnect()

    @property
    def is_connected(self) -> bool:
        return self._connected

    def reset(self):
        self._retry_count = 0
        self._connected = False


class OrderMutex:
    """订单级别互斥锁 - 防止多策略同时对同一标的下单的竞态条件"""

    def __init__(self):
        self._locks: dict[str, asyncio.Lock] = {}

    def _get_lock(self, symbol: str) -> asyncio.Lock:
        if symbol not in self._locks:
            self._locks[symbol] = asyncio.Lock()
        return self._locks[symbol]

    async def acquire(self, symbol: str):
        lock = self._get_lock(symbol)
        await lock.acquire()

    def release(self, symbol: str):
        lock = self._locks.get(symbol)
        if lock and lock.locked():
            lock.release()

    class OrderGuard:
        def __init__(self, mutex: "OrderMutex", symbol: str):
            self._mutex = mutex
            self._symbol = symbol

        async def __aenter__(self):
            await self._mutex.acquire(self._symbol)
            return self

        async def __aexit__(self, *args):
            self._mutex.release(self._symbol)

    def guard(self, symbol: str) -> "OrderGuard":
        return self.OrderGuard(self, symbol)


class IncompleteBarMarker:
    """未完成K线标记 - 最后一根未收盘K线打上标记"""

    @staticmethod
    def mark_incomplete(df) -> dict:
        if df is None or len(df) == 0:
            return {"incomplete_indices": [], "last_is_complete": True}

        incomplete = []
        last_is_complete = True

        if "date" in df.columns:
            dates = df["date"].values
            from datetime import datetime
            today_str = datetime.now().strftime("%Y-%m-%d")
            for i, d in enumerate(dates):
                ds = str(d)[:10]
                if ds == today_str:
                    incomplete.append(i)
                    if i == len(dates) - 1:
                        last_is_complete = False

        return {
            "incomplete_indices": incomplete,
            "last_is_complete": last_is_complete,
        }

    @staticmethod
    def add_complete_flag(df):
        if df is None or len(df) == 0:
            return df
        df = df.copy()
        df["is_complete"] = True
        marker = IncompleteBarMarker.mark_incomplete(df)
        for idx in marker["incomplete_indices"]:
            if idx < len(df):
                df.iloc[idx, df.columns.get_loc("is_complete")] = False
        return df
