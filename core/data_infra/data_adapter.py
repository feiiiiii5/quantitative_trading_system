import asyncio
import logging
import time
from abc import ABC, abstractmethod
from dataclasses import asdict, dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)


class SourceStatus(Enum):
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    DOWN = "down"


@dataclass
class SourceHealth:
    name: str
    status: SourceStatus = SourceStatus.HEALTHY
    latency_ms: float = 0.0
    success_rate: float = 1.0
    last_check: float = 0.0
    last_error: str = ""
    total_requests: int = 0
    total_failures: int = 0

    def to_dict(self) -> dict:
        d = asdict(self)
        d["status"] = self.status.value
        return d


class DataSourceAdapter(ABC):
    @abstractmethod
    async def fetch_realtime(self, symbol: str, market: str) -> Optional[dict]:
        pass

    @abstractmethod
    async def fetch_history(self, symbol: str, market: str, start: str, end: str) -> Optional[pd.DataFrame]:
        pass

    @abstractmethod
    async def fetch_hot(self) -> Optional[list]:
        pass

    @abstractmethod
    async def health_check(self) -> SourceHealth:
        pass

    @property
    @abstractmethod
    def name(self) -> str:
        pass

    @property
    @abstractmethod
    def priority(self) -> int:
        pass


class DataSourceHealth:
    def __init__(self):
        self._health: Dict[str, SourceHealth] = {}
        self._check_interval = int(os.environ.get("HEALTH_CHECK_INTERVAL", "30"))
        self._failure_threshold = float(os.environ.get("FAILURE_THRESHOLD", "0.5"))

    def record_success(self, source_name: str, latency_ms: float):
        if source_name not in self._health:
            self._health[source_name] = SourceHealth(name=source_name)
        h = self._health[source_name]
        h.total_requests += 1
        h.latency_ms = (h.latency_ms * 0.8 + latency_ms * 0.2)
        h.last_check = time.time()
        if h.total_requests > 0:
            h.success_rate = 1.0 - (h.total_failures / h.total_requests)
        if h.success_rate > 0.8:
            h.status = SourceStatus.HEALTHY
        elif h.success_rate > self._failure_threshold:
            h.status = SourceStatus.DEGRADED

    def record_failure(self, source_name: str, error: str = ""):
        if source_name not in self._health:
            self._health[source_name] = SourceHealth(name=source_name)
        h = self._health[source_name]
        h.total_requests += 1
        h.total_failures += 1
        h.last_error = error
        h.last_check = time.time()
        if h.total_requests > 0:
            h.success_rate = 1.0 - (h.total_failures / h.total_requests)
        if h.success_rate < self._failure_threshold:
            h.status = SourceStatus.DOWN
        elif h.success_rate < 0.8:
            h.status = SourceStatus.DEGRADED

    def get_health(self, source_name: str) -> SourceHealth:
        return self._health.get(source_name, SourceHealth(name=source_name))

    def get_all_health(self) -> Dict[str, dict]:
        return {name: h.to_dict() for name, h in self._health.items()}

    def is_available(self, source_name: str) -> bool:
        h = self.get_health(source_name)
        return h.status != SourceStatus.DOWN

    def should_check(self, source_name: str) -> bool:
        h = self.get_health(source_name)
        return (time.time() - h.last_check) > self._check_interval


import os


class EastMoneyAdapter(DataSourceAdapter):
    def __init__(self):
        from core.data_fetcher import EastMoneySource
        self._source = EastMoneySource

    @property
    def name(self) -> str:
        return "eastmoney"

    @property
    def priority(self) -> int:
        return 4

    async def fetch_realtime(self, symbol: str, market: str) -> Optional[dict]:
        try:
            return await asyncio.to_thread(self._source.fetch_realtime, symbol, market)
        except Exception:
            return None

    async def fetch_history(self, symbol: str, market: str, start: str, end: str) -> Optional[pd.DataFrame]:
        try:
            return await asyncio.to_thread(self._source.fetch_history, symbol, market, start, end)
        except Exception:
            return None

    async def fetch_hot(self) -> Optional[list]:
        try:
            return await asyncio.to_thread(self._source.fetch_hot_stocks)
        except Exception:
            return None

    async def health_check(self) -> SourceHealth:
        h = SourceHealth(name=self.name)
        try:
            start_t = time.time()
            result = await asyncio.to_thread(self._source.fetch_hot_stocks)
            h.latency_ms = (time.time() - start_t) * 1000
            h.status = SourceStatus.HEALTHY if result else SourceStatus.DOWN
        except Exception as e:
            h.status = SourceStatus.DOWN
            h.last_error = str(e)
        h.last_check = time.time()
        return h


class TencentAdapter(DataSourceAdapter):
    def __init__(self):
        from core.data_fetcher import TencentSource
        self._source = TencentSource

    @property
    def name(self) -> str:
        return "tencent"

    @property
    def priority(self) -> int:
        return 1

    async def fetch_realtime(self, symbol: str, market: str) -> Optional[dict]:
        try:
            return await asyncio.to_thread(self._source.fetch_realtime, symbol, market)
        except Exception:
            return None

    async def fetch_history(self, symbol: str, market: str, start: str, end: str) -> Optional[pd.DataFrame]:
        try:
            return await asyncio.to_thread(self._source.fetch_history, symbol, market, start, end)
        except Exception:
            return None

    async def fetch_hot(self) -> Optional[list]:
        try:
            return await asyncio.to_thread(self._source.fetch_hot_stocks)
        except Exception:
            return None

    async def health_check(self) -> SourceHealth:
        h = SourceHealth(name=self.name)
        try:
            start_t = time.time()
            result = await asyncio.to_thread(self._source.fetch_hot_stocks)
            h.latency_ms = (time.time() - start_t) * 1000
            h.status = SourceStatus.HEALTHY if result else SourceStatus.DOWN
        except Exception as e:
            h.status = SourceStatus.DOWN
            h.last_error = str(e)
        h.last_check = time.time()
        return h


class AkshareAdapter(DataSourceAdapter):
    def __init__(self):
        from core.data_fetcher import AkshareSource
        self._source = AkshareSource

    @property
    def name(self) -> str:
        return "akshare"

    @property
    def priority(self) -> int:
        return 2

    async def fetch_realtime(self, symbol: str, market: str) -> Optional[dict]:
        try:
            return await asyncio.to_thread(self._source.fetch_realtime, symbol, market)
        except Exception:
            return None

    async def fetch_history(self, symbol: str, market: str, start: str, end: str) -> Optional[pd.DataFrame]:
        try:
            return await asyncio.to_thread(self._source.fetch_history, symbol, market, start, end)
        except Exception:
            return None

    async def fetch_hot(self) -> Optional[list]:
        try:
            return await asyncio.to_thread(self._source.fetch_hot_stocks)
        except Exception:
            return None

    async def health_check(self) -> SourceHealth:
        h = SourceHealth(name=self.name)
        try:
            import akshare as ak
            start_t = time.time()
            ak.stock_zh_a_spot_em()
            h.latency_ms = (time.time() - start_t) * 1000
            h.status = SourceStatus.HEALTHY
        except Exception as e:
            h.status = SourceStatus.DOWN
            h.last_error = str(e)
        h.last_check = time.time()
        return h


class SinaAdapter(DataSourceAdapter):
    def __init__(self):
        from core.data_fetcher import SinaSource
        self._source = SinaSource

    @property
    def name(self) -> str:
        return "sina"

    @property
    def priority(self) -> int:
        return 3

    async def fetch_realtime(self, symbol: str, market: str) -> Optional[dict]:
        try:
            return await asyncio.to_thread(self._source.fetch_realtime, symbol, market)
        except Exception:
            return None

    async def fetch_history(self, symbol: str, market: str, start: str, end: str) -> Optional[pd.DataFrame]:
        try:
            return await asyncio.to_thread(self._source.fetch_history, symbol, market, start, end)
        except Exception:
            return None

    async def fetch_hot(self) -> Optional[list]:
        return None

    async def health_check(self) -> SourceHealth:
        h = SourceHealth(name=self.name)
        try:
            start_t = time.time()
            result = await asyncio.to_thread(self._source.fetch_realtime, "000001", "A")
            h.latency_ms = (time.time() - start_t) * 1000
            h.status = SourceStatus.HEALTHY if result else SourceStatus.DOWN
        except Exception as e:
            h.status = SourceStatus.DOWN
            h.last_error = str(e)
        h.last_check = time.time()
        return h


class YFinanceAdapter(DataSourceAdapter):
    def __init__(self):
        self._available = False
        try:
            import yfinance
            self._available = True
        except ImportError:
            pass

    @property
    def name(self) -> str:
        return "yfinance"

    @property
    def priority(self) -> int:
        return 6

    async def fetch_realtime(self, symbol: str, market: str) -> Optional[dict]:
        if not self._available:
            return None
        try:
            import yfinance as yf
            if market == "US":
                ticker = yf.Ticker(symbol)
                info = ticker.fast_info
                return {
                    "price": getattr(info, "last_price", 0),
                    "name": symbol,
                    "market": "US",
                }
        except Exception:
            pass
        return None

    async def fetch_history(self, symbol: str, market: str, start: str, end: str) -> Optional[pd.DataFrame]:
        if not self._available:
            return None
        try:
            import yfinance as yf
            if market == "US":
                ticker = yf.Ticker(symbol)
                df = ticker.history(start=start, end=end)
                if df is not None and not df.empty:
                    df = df.reset_index()
                    df.columns = [c.lower().replace(" ", "_") for c in df.columns]
                    if "date" not in df.columns and "index" in df.columns:
                        df = df.rename(columns={"index": "date"})
                    return df
        except Exception:
            pass
        return None

    async def fetch_hot(self) -> Optional[list]:
        return None

    async def health_check(self) -> SourceHealth:
        h = SourceHealth(name=self.name)
        if not self._available:
            h.status = SourceStatus.DOWN
            h.last_error = "yfinance not installed"
        else:
            h.status = SourceStatus.HEALTHY
        h.last_check = time.time()
        return h


class TushareAdapter(DataSourceAdapter):
    def __init__(self):
        self._token = os.environ.get("TUSHARE_TOKEN", "")
        self._available = False
        if self._token:
            try:
                import tushare as ts
                ts.set_token(self._token)
                self._available = True
            except ImportError:
                pass

    @property
    def name(self) -> str:
        return "tushare"

    @property
    def priority(self) -> int:
        return 5

    async def fetch_realtime(self, symbol: str, market: str) -> Optional[dict]:
        if not self._available or market != "A":
            return None
        try:
            import tushare as ts
            pro = ts.pro_api()
            df = pro.daily(ts_code=f"{symbol}.SH" if symbol.startswith("6") else f"{symbol}.SZ")
            if df is not None and not df.empty:
                r = df.iloc[0]
                return {
                    "price": float(r.get("close", 0)),
                    "open": float(r.get("open", 0)),
                    "high": float(r.get("high", 0)),
                    "low": float(r.get("low", 0)),
                    "volume": float(r.get("vol", 0)),
                }
        except Exception:
            pass
        return None

    async def fetch_history(self, symbol: str, market: str, start: str, end: str) -> Optional[pd.DataFrame]:
        if not self._available or market != "A":
            return None
        try:
            import tushare as ts
            pro = ts.pro_api()
            ts_code = f"{symbol}.SH" if symbol.startswith("6") else f"{symbol}.SZ"
            df = pro.daily(ts_code=ts_code, start_date=start, end_date=end)
            if df is not None and not df.empty:
                df = df.rename(columns={"trade_date": "date", "vol": "volume"})
                df = df.sort_values("date").reset_index(drop=True)
                return df
        except Exception:
            pass
        return None

    async def fetch_hot(self) -> Optional[list]:
        return None

    async def health_check(self) -> SourceHealth:
        h = SourceHealth(name=self.name)
        if not self._available:
            h.status = SourceStatus.DOWN
            h.last_error = "tushare not configured"
        else:
            h.status = SourceStatus.HEALTHY
        h.last_check = time.time()
        return h


class UnifiedDataAdapter:
    def __init__(self):
        self._adapters: Dict[str, DataSourceAdapter] = {}
        self._health = DataSourceHealth()
        self._register_default_adapters()

    def _register_default_adapters(self):
        for adapter_cls in [TencentAdapter, AkshareAdapter, SinaAdapter, EastMoneyAdapter, TushareAdapter, YFinanceAdapter]:
            try:
                adapter = adapter_cls()
                self._adapters[adapter.name] = adapter
            except Exception as e:
                logger.debug(f"Failed to register {adapter_cls.__name__}: {e}")

    def register_adapter(self, adapter: DataSourceAdapter):
        self._adapters[adapter.name] = adapter

    def _get_sorted_adapters(self, market: str) -> List[DataSourceAdapter]:
        available = [a for a in self._adapters.values() if self._health.is_available(a.name)]
        available.sort(key=lambda a: a.priority)
        return available

    async def fetch_realtime(self, symbol: str, market: str) -> Optional[dict]:
        adapters = self._get_sorted_adapters(market)
        for adapter in adapters:
            start_t = time.time()
            try:
                result = await adapter.fetch_realtime(symbol, market)
                latency = (time.time() - start_t) * 1000
                if result:
                    self._health.record_success(adapter.name, latency)
                    result["_source"] = adapter.name
                    return result
                self._health.record_failure(adapter.name, "empty result")
            except Exception as e:
                self._health.record_failure(adapter.name, str(e))
        return None

    async def fetch_history(self, symbol: str, market: str, start: str, end: str) -> Optional[pd.DataFrame]:
        adapters = self._get_sorted_adapters(market)
        for adapter in adapters:
            start_t = time.time()
            try:
                result = await adapter.fetch_history(symbol, market, start, end)
                latency = (time.time() - start_t) * 1000
                if result is not None and not result.empty:
                    self._health.record_success(adapter.name, latency)
                    return result
                self._health.record_failure(adapter.name, "empty result")
            except Exception as e:
                self._health.record_failure(adapter.name, str(e))
        return None

    async def fetch_hot(self) -> Optional[list]:
        adapters = self._get_sorted_adapters("A")
        for adapter in adapters:
            try:
                result = await adapter.fetch_hot()
                if result:
                    self._health.record_success(adapter.name, 0)
                    return result
            except Exception as e:
                self._health.record_failure(adapter.name, str(e))
        return None

    async def run_health_check(self) -> Dict[str, dict]:
        results = {}
        for name, adapter in self._adapters.items():
            try:
                h = await adapter.health_check()
                self._health._health[name] = h
                results[name] = h.to_dict()
            except Exception as e:
                results[name] = {"name": name, "status": "down", "error": str(e)}
        return results

    def get_health_status(self) -> Dict[str, dict]:
        return self._health.get_all_health()

    def get_adapter_info(self) -> List[dict]:
        info = []
        for name, adapter in self._adapters.items():
            h = self._health.get_health(name)
            info.append({
                "name": name,
                "priority": adapter.priority,
                "status": h.status.value,
                "latency_ms": round(h.latency_ms, 2),
                "success_rate": round(h.success_rate, 4),
            })
        return info
