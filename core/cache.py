"""
QuantCore 三级缓存系统
L1: 内存LRU缓存 - 最近Tick数据
L2: Redis缓存 - 分钟级行情 (可选)
L3: Parquet文件 - 全量历史数据
DuckDB: 本地分析数据库 - 直接查询Parquet
"""
import asyncio
import logging
import os
import shutil
import tempfile
import time
from collections import OrderedDict
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)

_BASE_DIR = Path(__file__).parent.parent
_PARQUET_DIR = _BASE_DIR / "data" / "parquet"


class L1MemoryCache:
    """L1 内存LRU缓存 - 存储最近Tick/K线数据"""

    def __init__(self, max_size: int = 2000, default_ttl: int = 300):
        self._cache: OrderedDict = OrderedDict()
        self._max_size = max_size
        self._default_ttl = default_ttl
        self._hits = 0
        self._misses = 0

    def get(self, key: str) -> Optional[Any]:
        entry = self._cache.get(key)
        if entry and (time.time() - entry["ts"]) < entry.get("ttl", self._default_ttl):
            self._cache.move_to_end(key)
            self._hits += 1
            return entry["data"]
        if key in self._cache:
            del self._cache[key]
        self._misses += 1
        return None

    def set(self, key: str, data: Any, ttl: Optional[int] = None):
        if key in self._cache:
            self._cache.move_to_end(key)
        self._cache[key] = {"data": data, "ts": time.time(), "ttl": ttl or self._default_ttl}
        while len(self._cache) > self._max_size:
            self._cache.popitem(last=False)

    def delete(self, key: str):
        self._cache.pop(key, None)

    def clear(self):
        self._cache.clear()

    def stats(self) -> Dict[str, int]:
        total = self._hits + self._misses
        return {
            "size": len(self._cache),
            "max_size": self._max_size,
            "hits": self._hits,
            "misses": self._misses,
            "hit_rate": round(self._hits / total * 100, 2) if total > 0 else 0,
        }


class L2RedisCache:
    """L2 Redis缓存 - 分钟级行情 (可选)"""

    def __init__(self, redis_url: str = "redis://localhost:6379/0", enabled: bool = False):
        self._enabled = enabled
        self._redis = None
        self._url = redis_url

    async def connect(self):
        if not self._enabled:
            return
        try:
            import redis.asyncio as aioredis
            self._redis = await aioredis.from_url(self._url, decode_responses=True)
            await self._redis.ping()
            logger.info("L2 Redis缓存已连接")
        except Exception as e:
            logger.warning(f"L2 Redis连接失败，降级为仅L1+L3: {e}")
            self._enabled = False

    async def get(self, key: str) -> Optional[str]:
        if not self._enabled or not self._redis:
            return None
        try:
            return await self._redis.get(key)
        except Exception:
            return None

    async def set(self, key: str, value: str, ttl: int = 3600):
        if not self._enabled or not self._redis:
            return
        try:
            await self._redis.setex(key, ttl, value)
        except Exception:
            pass

    async def delete(self, key: str):
        if not self._enabled or not self._redis:
            return
        try:
            await self._redis.delete(key)
        except Exception:
            pass

    async def close(self):
        if self._redis:
            await self._redis.close()


class L3ParquetCache:
    """L3 Parquet文件缓存 - 全量历史数据, 原子写入"""

    def __init__(self, base_dir: Optional[Path] = None):
        self._base_dir = base_dir or _PARQUET_DIR
        self._base_dir.mkdir(parents=True, exist_ok=True)

    def _path(self, symbol: str, market: str, kline_type: str, adjust: str) -> Path:
        safe_symbol = symbol.replace(".", "_").replace("/", "_")
        return self._base_dir / market / kline_type / adjust / f"{safe_symbol}.parquet"

    def exists_and_current(self, symbol: str, market: str, kline_type: str,
                           adjust: str, trade_date: Optional[str] = None) -> bool:
        path = self._path(symbol, market, kline_type, adjust)
        if not path.exists():
            return False
        if trade_date is None:
            return True
        try:
            import pyarrow.parquet as pq
            pf = pq.ParquetFile(str(path))
            last_row = pf.read_row_group(pf.num_row_groups - 1).to_pandas()
            if not last_row.empty and "date" in last_row.columns:
                last_date = str(last_row["date"].iloc[-1])[:10]
                return last_date >= trade_date
        except Exception:
            pass
        return True

    def read(self, symbol: str, market: str, kline_type: str, adjust: str,
             start_date: Optional[str] = None, end_date: Optional[str] = None) -> pd.DataFrame:
        path = self._path(symbol, market, kline_type, adjust)
        if not path.exists():
            return pd.DataFrame()
        try:
            df = pd.read_parquet(str(path))
            if start_date and "date" in df.columns:
                df = df[df["date"] >= start_date]
            if end_date and "date" in df.columns:
                df = df[df["date"] <= end_date]
            return df
        except Exception as e:
            logger.debug(f"Parquet读取失败 {path}: {e}")
            return pd.DataFrame()

    def write(self, symbol: str, market: str, kline_type: str, adjust: str,
              df: pd.DataFrame):
        if df.empty:
            return
        path = self._path(symbol, market, kline_type, adjust)
        path.parent.mkdir(parents=True, exist_ok=True)

        existing = pd.DataFrame()
        if path.exists():
            try:
                existing = pd.read_parquet(str(path))
            except Exception:
                existing = pd.DataFrame()

        if not existing.empty and "date" in existing.columns and "date" in df.columns:
            existing_dates = set(existing["date"].astype(str))
            new_rows = df[~df["date"].astype(str).isin(existing_dates)]
            if new_rows.empty:
                return
            combined = pd.concat([existing, new_rows], ignore_index=True)
            combined = combined.sort_values("date").drop_duplicates(
                subset=["date"], keep="last"
            ).reset_index(drop=True)
        else:
            combined = df

        # 原子写入: 先写临时文件再重命名
        tmp_path = str(path) + ".tmp"
        try:
            combined.to_parquet(tmp_path, engine="pyarrow", compression="snappy", index=False)
            shutil.move(tmp_path, str(path))
        except Exception as e:
            logger.debug(f"Parquet写入失败 {path}: {e}")
            if os.path.exists(tmp_path):
                os.remove(tmp_path)

    def upsert(self, symbol: str, market: str, kline_type: str, adjust: str,
               df: pd.DataFrame):
        self.write(symbol, market, kline_type, adjust, df)


class DuckDBAnalyzer:
    """DuckDB本地分析数据库 - 直接查询Parquet文件"""

    def __init__(self, parquet_dir: Optional[Path] = None):
        self._parquet_dir = parquet_dir or _PARQUET_DIR
        self._conn = None

    def _get_conn(self):
        if self._conn is None:
            try:
                import duckdb
                self._conn = duckdb.connect(":memory:")
            except ImportError:
                logger.warning("DuckDB未安装，分析功能不可用")
                return None
        return self._conn

    def query_parquet(self, parquet_path: str, sql_suffix: str = "") -> pd.DataFrame:
        conn = self._get_conn()
        if conn is None:
            return pd.DataFrame()
        try:
            sql = f"SELECT * FROM read_parquet('{parquet_path}')"
            if sql_suffix:
                sql += f" {sql_suffix}"
            return conn.execute(sql).fetchdf()
        except Exception as e:
            logger.debug(f"DuckDB查询失败: {e}")
            return pd.DataFrame()

    def query_symbol(self, symbol: str, market: str = "A", kline_type: str = "daily",
                     adjust: str = "qfq", where: str = "",
                     order_by: str = "date", limit: int = 0) -> pd.DataFrame:
        safe_symbol = symbol.replace(".", "_").replace("/", "_")
        path = self._parquet_dir / market / kline_type / adjust / f"{safe_symbol}.parquet"
        if not path.exists():
            return pd.DataFrame()
        sql_suffix = ""
        if where:
            sql_suffix += f" WHERE {where}"
        if order_by:
            sql_suffix += f" ORDER BY {order_by}"
        if limit > 0:
            sql_suffix += f" LIMIT {limit}"
        return self.query_parquet(str(path), sql_suffix)

    def get_stats(self, symbol: str, market: str = "A") -> Dict[str, Any]:
        df = self.query_symbol(symbol, market)
        if df.empty:
            return {}
        closes = df["close"].values.astype(float)
        returns = np.diff(closes) / closes[:-1]
        return {
            "count": len(df),
            "start_date": str(df["date"].iloc[0])[:10],
            "end_date": str(df["date"].iloc[-1])[:10],
            "mean_return": round(float(np.mean(returns)) * 100, 4),
            "volatility": round(float(np.std(returns) * np.sqrt(252)) * 100, 2),
            "max_price": round(float(np.max(closes)), 2),
            "min_price": round(float(np.min(closes)), 2),
        }

    def close(self):
        if self._conn:
            self._conn.close()
            self._conn = None


class ThreeLevelCache:
    """三级缓存统一管理"""

    def __init__(self, l1_size: int = 2000, l1_ttl: int = 300,
                 redis_url: str = "redis://localhost:6379/0",
                 redis_enabled: bool = False,
                 parquet_dir: Optional[Path] = None):
        self.l1 = L1MemoryCache(max_size=l1_size, default_ttl=l1_ttl)
        self.l2 = L2RedisCache(redis_url=redis_url, enabled=redis_enabled)
        self.l3 = L3ParquetCache(base_dir=parquet_dir)
        self.duckdb = DuckDBAnalyzer(parquet_dir=parquet_dir or _PARQUET_DIR)

    async def initialize(self):
        await self.l2.connect()

    async def close(self):
        await self.l2.close()
        self.duckdb.close()

    def get_history(self, symbol: str, market: str, kline_type: str, adjust: str,
                    start_date: Optional[str] = None, end_date: Optional[str] = None) -> pd.DataFrame:
        # L1 检查
        cache_key = f"hist:{symbol}:{market}:{kline_type}:{adjust}:{start_date}:{end_date}"
        cached = self.l1.get(cache_key)
        if cached is not None:
            return cached

        # L3 检查
        df = self.l3.read(symbol, market, kline_type, adjust, start_date, end_date)
        if not df.empty:
            self.l1.set(cache_key, df.copy(), ttl=300)
            return df

        return pd.DataFrame()

    def set_history(self, symbol: str, market: str, kline_type: str, adjust: str,
                    df: pd.DataFrame):
        if df.empty:
            return
        self.l3.write(symbol, market, kline_type, adjust, df)
        cache_key = f"hist:{symbol}:{market}:{kline_type}:{adjust}:None:None"
        self.l1.set(cache_key, df.copy(), ttl=300)

    def get_realtime(self, symbol: str) -> Optional[Dict]:
        return self.l1.get(f"rt:{symbol}")

    def set_realtime(self, symbol: str, data: Dict, ttl: int = 10):
        self.l1.set(f"rt:{symbol}", data, ttl=ttl)

    def stats(self) -> Dict[str, Any]:
        return {
            "l1": self.l1.stats(),
            "l2_enabled": self.l2._enabled,
        }


_cache_instance: Optional[ThreeLevelCache] = None


def get_cache() -> ThreeLevelCache:
    global _cache_instance
    if _cache_instance is None:
        _cache_instance = ThreeLevelCache()
    return _cache_instance
