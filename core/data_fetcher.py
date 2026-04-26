"""
QuantCore 数据获取模块 - 重构版
使用中国大陆最稳定的数据源，修复连接断开问题
"""

import asyncio
import json
import logging
import re
import time
from collections import OrderedDict, defaultdict, deque
from datetime import datetime, timedelta
from typing import Any, Optional
from pathlib import Path

import numpy as np
import pandas as pd
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from core.database import get_db
from core.market_detector import MarketDetector
from core.stock_search import get_stock_name


class _TokenBucket:
    def __init__(self, rate=10, capacity=15):
        self.rate = rate
        self.capacity = capacity
        self._tokens = capacity
        self._last = time.monotonic()

    def wait(self):
        now = time.monotonic()
        self._tokens = min(self.capacity, self._tokens + (now - self._last) * self.rate)
        self._last = now
        if self._tokens < 1:
            time.sleep((1 - self._tokens) / self.rate)
            self._tokens = 0
        else:
            self._tokens -= 1


logger = logging.getLogger(__name__)

PERIOD_MAP = {
    "1d": 5,
    "1w": 15,
    "1m": 35,
    "3m": 95,
    "1y": 370,
    "all": None,
}

KLINE_TYPE_MAP = {
    "1d": "intraday",
    "1w": "daily",
    "1m": "daily",
    "3m": "daily",
    "1y": "daily",
    "all": "daily",
}

_MAX_CACHE_SIZE = 500
_history_cache: OrderedDict = OrderedDict()
_realtime_cache: OrderedDict = OrderedDict()
_HIST_CACHE_TTL = 300
_RT_CACHE_TTL = 10
_TODAY_CACHE_TTL_SECONDS = 900
_AKSHARE_BUCKET = _TokenBucket(rate=10, capacity=15)

_DB_CONNECTION_POOL = {}
_DB_POOL_SIZE = 5

_UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"

_global_session = None

def _get_session() -> requests.Session:
    global _global_session
    if _global_session is None:
        _global_session = requests.Session()
        retry_strategy = Retry(
            total=3,
            backoff_factor=1,
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=["GET", "POST"],
            raise_on_status=False,
        )
        adapter = HTTPAdapter(
            max_retries=retry_strategy,
            pool_connections=20,
            pool_maxsize=50,
            pool_block=False,
        )
        _global_session.mount("http://", adapter)
        _global_session.mount("https://", adapter)
        _global_session.headers.update({
            "Connection": "keep-alive",
            "Accept-Encoding": "gzip, deflate",
            "Accept": "application/json, text/plain, */*",
        })
    return _global_session


_BASE_DIR = Path(__file__).parent.parent

def _get_db_connection():
    import sqlite3
    import hashlib

    db_path = str(_BASE_DIR / "data" / "market_cache.db")
    key = hashlib.md5(db_path.encode()).hexdigest()

    if key in _DB_CONNECTION_POOL and _DB_CONNECTION_POOL[key]:
        return _DB_CONNECTION_POOL[key].pop()

    conn = sqlite3.connect(db_path, check_same_thread=False, timeout=10)
    conn.row_factory = sqlite3.Row
    return conn


def _return_db_connection(conn):
    import sqlite3
    import hashlib

    if not conn or not isinstance(conn, sqlite3.Connection):
        return

    try:
        db_path = conn.execute("PRAGMA database_list").fetchone()[2]
        key = hashlib.md5(db_path.encode()).hexdigest()

        if key not in _DB_CONNECTION_POOL:
            _DB_CONNECTION_POOL[key] = []

        if len(_DB_CONNECTION_POOL[key]) < _DB_POOL_SIZE:
            _DB_CONNECTION_POOL[key].append(conn)
        else:
            conn.close()
    except Exception:
        try:
            conn.close()
        except Exception:
            pass


_EM_HEADERS = {
    "User-Agent": _UA,
    "Referer": "https://quote.eastmoney.com/",
    "Accept": "application/json, text/plain, */*",
    "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
}

_TENCENT_HEADERS = {
    "User-Agent": _UA,
    "Referer": "https://guojijj.com/",
    "Accept": "application/json, text/plain, */*",
}

_SINA_HEADERS = {
    "User-Agent": _UA,
    "Referer": "https://finance.sina.com.cn/",
    "Accept": "application/javascript, */*",
}


def _cache_get(cache: OrderedDict, key: str):
    entry = cache.get(key)
    if entry and (time.time() - entry["ts"]) < entry.get("ttl", 60):
        cache.move_to_end(key)
        return entry["data"]
    if key in cache:
        del cache[key]
    return None


def _cache_set(cache: OrderedDict, key: str, data, ttl: int = 60):
    if key in cache:
        cache.move_to_end(key)
    cache[key] = {"data": data, "ts": time.time(), "ttl": ttl}
    while len(cache) > _MAX_CACHE_SIZE:
        cache.popitem(last=False)


def _http_get(url: str, params: dict = None, headers: dict = None, timeout: int = 8, retries: int = 1) -> Optional[requests.Response]:
    for attempt in range(retries + 1):
        try:
            session = _get_session()
            resp = session.get(url, params=params, headers=headers, timeout=(3, timeout), stream=False)
            if resp.status_code == 200:
                return resp
            elif resp.status_code == 429:
                logger.debug(f"Rate limited for {url}, waiting...")
                time.sleep(min(2 ** attempt, 3))
            elif resp.status_code in (500, 502, 503, 504):
                logger.debug(f"Server error {resp.status_code} for {url}, attempt {attempt+1}")
            else:
                logger.debug(f"HTTP {resp.status_code} from {url}")
                return None
        except requests.exceptions.ConnectionError as e:
            logger.debug(f"Connection error for {url} (attempt {attempt+1}/{retries+1}): {e}")
        except requests.exceptions.Timeout:
            logger.debug(f"Timeout for {url} (attempt {attempt+1}/{retries+1})")
        except Exception as e:
            logger.debug(f"HTTP error for {url} (attempt {attempt+1}/{retries+1}): {e}")
    return None


def _safe_float(val, default=0.0) -> float:
    try:
        if val is None or val == "" or val == "-":
            return default
        v = float(val)
        return v if not np.isnan(v) else default
    except (ValueError, TypeError):
        return default


def _date_to_key(value) -> str:
    if isinstance(value, pd.Timestamp):
        return value.strftime("%Y-%m-%d %H:%M:%S" if value.hour or value.minute or value.second else "%Y-%m-%d")
    if isinstance(value, datetime):
        return value.strftime("%Y-%m-%d %H:%M:%S" if value.hour or value.minute or value.second else "%Y-%m-%d")
    text = str(value)
    if not text:
        return ""
    try:
        ts = pd.to_datetime(text, errors="coerce")
        if pd.notna(ts):
            return ts.strftime("%Y-%m-%d %H:%M:%S" if ts.hour or ts.minute or ts.second else "%Y-%m-%d")
    except Exception:
        pass
    return text


class DataQualityChecker:
    def check_price_continuity(self, df: pd.DataFrame) -> pd.Series:
        if df.empty or "close" not in df.columns:
            return pd.Series(dtype=bool)
        prev_close = df["close"].shift(1)
        pct_change = (df["close"] - prev_close).abs() / prev_close.replace(0, np.nan)
        return pct_change.fillna(0) > 0.2

    def check_volume_zero(self, df: pd.DataFrame) -> pd.Series:
        if "volume" not in df.columns:
            return pd.Series(False, index=df.index)
        return df["volume"].fillna(0) <= 0

    def check_null_fields(self, df: pd.DataFrame) -> pd.Series:
        required = [col for col in ["open", "high", "low", "close"] if col in df.columns]
        if not required:
            return pd.Series(False, index=df.index)
        return df[required].isna().any(axis=1)

    def fill_missing_with_forward(self, df: pd.DataFrame) -> pd.DataFrame:
        if df.empty:
            return df
        df = df.copy()
        if "is_dirty" not in df.columns:
            df["is_dirty"] = 0
        else:
            df["is_dirty"] = df["is_dirty"].fillna(0).astype(int)
        for column in [col for col in ["open", "high", "low", "close", "volume"] if col in df.columns]:
            mask = df[column].isna()
            if not mask.any():
                continue
            isolated = mask & ~mask.shift(1, fill_value=False) & ~mask.shift(-1, fill_value=False)
            if isolated.any():
                df.loc[isolated, column] = df[column].ffill()
                df.loc[isolated, "is_dirty"] = 1
        return df

    def run(self, df: pd.DataFrame) -> pd.DataFrame:
        if df.empty:
            return df
        cleaned = self.fill_missing_with_forward(df)
        if "is_dirty" not in cleaned.columns:
            cleaned["is_dirty"] = 0
        else:
            cleaned["is_dirty"] = cleaned["is_dirty"].fillna(0).astype(int)
        dirty_mask = (
            self.check_price_continuity(cleaned).reindex(cleaned.index, fill_value=False)
            | self.check_volume_zero(cleaned).reindex(cleaned.index, fill_value=False)
            | self.check_null_fields(cleaned).reindex(cleaned.index, fill_value=False)
        )
        cleaned.loc[dirty_mask, "is_dirty"] = 1
        return cleaned


class DataSourceHealthMonitor:
    def __init__(self):
        self._db = get_db()
        self._windows: dict[tuple[str, str], deque] = defaultdict(lambda: deque(maxlen=100))

    def record(self, source_name: str, request_type: str, success: bool, latency_ms: float, error: str = "") -> None:
        self._windows[(source_name, request_type)].append(
            {
                "success": bool(success),
                "latency_ms": round(float(latency_ms or 0), 2),
                "error": error[:300] if error else "",
                "ts": _date_to_key(datetime.now()),
            }
        )
        try:
            self._db.record_source_request(source_name, request_type, success, latency_ms, error)
        except Exception as e:
            logger.debug(f"Health record failed: {e}")

    def get_stats(self) -> list[dict]:
        try:
            return self._db.get_source_stats()
        except Exception:
            return []

    def rank_sources(self, request_type: str, sources: list[tuple[str, callable]]) -> list[tuple[str, callable]]:
        try:
            stats = {
                (row["source_name"], row["request_type"]): row
                for row in self._db.get_source_stats()
            }
        except Exception:
            stats = {}

        def _sort_key(item: tuple[str, callable]):
            name, _ = item
            row = stats.get((name, request_type))
            if not row:
                return (0, 0, 0)
            success_rate = float(row.get("success_rate", 0))
            avg_latency = float(row.get("avg_response_ms", 0))
            degraded = 1 if success_rate < 0.5 and int(row.get("total_requests", 0)) >= 5 else 0
            return (degraded, -success_rate, avg_latency)

        return sorted(sources, key=_sort_key)


def _validate_realtime(data: dict) -> bool:
    if not data:
        return False
    price = data.get("price", 0)
    if price is None or price <= 0:
        return False
    return True


def _validate_history_df(df: pd.DataFrame) -> bool:
    if df is None or df.empty:
        return False
    required = {"date", "close"}
    if not required.issubset(set(df.columns)):
        return False
    if df["close"].isna().all():
        return False
    return True


class TencentSource:
    """腾讯财经 - 中国大陆最稳定的实时数据源之一"""
    NAME = "腾讯财经"

    @staticmethod
    def fetch_realtime(code: str, market: str) -> Optional[dict]:
        try:
            if market == "A":
                prefix = "sh" if code.startswith(("6", "9")) else "sz"
                qt_code = f"{prefix}{code}"
            elif market == "HK":
                qt_code = f"hk{code}"
            elif market == "US":
                qt_code = f"us{code.upper()}"
            else:
                return None

            url = f"http://qt.gtimg.cn/q={qt_code}"
            resp = _http_get(url, headers=_TENCENT_HEADERS, timeout=8)
            if resp and resp.text:
                content = resp.text.strip()
                match = re.search(r'="([^"]*)"', content)
                if match:
                    raw = match.group(1)
                    if not raw:
                        return None
                    fields = raw.split("~")
                    if len(fields) >= 36:
                        price = _safe_float(fields[3])
                        name = fields[1] if len(fields) > 1 else ""
                        prev_close = _safe_float(fields[4])
                        result = {
                            "name": name,
                            "price": price,
                            "change": _safe_float(fields[31]),
                            "pct": _safe_float(fields[32]),
                            "volume": _safe_float(fields[36]),
                            "high": _safe_float(fields[33]),
                            "low": _safe_float(fields[34]),
                            "open": _safe_float(fields[5]),
                            "prev_close": prev_close,
                            "time": fields[30] if fields[30] else datetime.now().strftime("%H:%M:%S"),
                        }
                        if market == "A" and len(fields) >= 43:
                            result["turnover"] = _safe_float(fields[38])
                            result["amplitude"] = _safe_float(fields[43]) if _safe_float(fields[43]) != 0 else None
                        return result
        except Exception as e:
            logger.debug(f"Tencent realtime error for {code}: {e}")
        return None

    @staticmethod
    def fetch_history(code: str, market: str, start: str, end: str, kline_type: str = "daily", adjust: str = "qfq") -> Optional[pd.DataFrame]:
        try:
            if market == "A":
                prefix = "sh" if code.startswith(("6", "9")) else "sz"
                qt_code = f"{prefix}{code}"
            elif market == "HK":
                qt_code = f"hk{code}"
            else:
                return None

            adjust_key = adjust if adjust in ("qfq", "hfq", "") else "qfq"
            url = f"http://web.ifzq.gtimg.cn/appstock/app/fqkline/get?param={qt_code},day,,,500,{adjust_key}"
            resp = _http_get(url, headers=_TENCENT_HEADERS, timeout=12)
            if resp:
                d = resp.json()
                data = d.get("data", {})
                if data:
                    keys = list(data.keys())
                    if keys:
                        kdata = data[keys[0]]
                        day = kdata.get("qfqday") or kdata.get("day")
                        if day and len(day) > 1:
                            rows = []
                            for item in day:
                                if len(item) >= 6:
                                    rows.append({
                                        "date": item[0],
                                        "open": _safe_float(item[1]),
                                        "close": _safe_float(item[2]),
                                        "high": _safe_float(item[3]),
                                        "low": _safe_float(item[4]),
                                        "volume": _safe_float(item[5]),
                                    })
                            if rows:
                                return pd.DataFrame(rows)
        except Exception as e:
            logger.debug(f"Tencent history error for {code}: {e}")
        return None

    @staticmethod
    def fetch_hot_stocks() -> Optional[list]:
        try:
            codes = [
                ("sh000001", "上证指数"), ("sz399001", "深证成指"),
                ("sh600519", "贵州茅台"), ("sz000858", "五粮液"),
                ("sh601318", "中国平安"), ("sz000001", "平安银行"),
                ("sh600036", "招商银行"), ("sz002594", "比亚迪"),
                ("sz000333", "美的集团"), ("sh601012", "隆基绿能"),
            ]
            qt_codes = [c[0] for c in codes]
            url = f"http://qt.gtimg.cn/q={','.join(qt_codes)}"
            resp = _http_get(url, headers=_TENCENT_HEADERS, timeout=8)
            if resp and resp.text:
                result = []
                lines = resp.text.strip().split(";")
                for line in lines:
                    match = re.search(r'="([^"]*)"', line)
                    if match:
                        raw = match.group(1)
                        if not raw:
                            continue
                        fields = raw.split("~")
                        if len(fields) >= 36:
                            code = fields[2] if len(fields) > 2 else ""
                            name = fields[1] if len(fields) > 1 else ""
                            price = _safe_float(fields[3])
                            pct = _safe_float(fields[32])
                            change = _safe_float(fields[31])
                            volume = _safe_float(fields[36])
                            if code and name and price > 0 and not code.endswith(".HK"):
                                result.append({
                                    "code": code,
                                    "name": name,
                                    "price": price,
                                    "pct": pct,
                                    "change": change,
                                    "volume": volume,
                                })
                if result:
                    result.sort(key=lambda x: x["pct"], reverse=True)
                    return result[:8]
        except Exception as e:
            logger.debug(f"Tencent hot stocks error: {e}")
        return None


class SinaSource:
    """新浪财经 - 备用数据源"""
    NAME = "新浪财经"

    @staticmethod
    def fetch_realtime(code: str, market: str) -> Optional[dict]:
        try:
            if market == "A":
                prefix = "sh" if code.startswith(("6", "9")) else "sz"
                sina_code = f"{prefix}{code}"
            elif market == "HK":
                sina_code = f"rt_hk{code}"
            else:
                return None

            url = f"http://hq.sinajs.cn/list={sina_code}"
            resp = _http_get(url, headers=_SINA_HEADERS, timeout=8)
            if resp and resp.text:
                content = resp.text.strip()
                match = re.search(r'="([^"]*)"', content)
                if match:
                    raw = match.group(1)
                    if not raw:
                        return None
                    fields = raw.split(",")
                    if market == "A" and len(fields) >= 32:
                        name = fields[0] if fields[0] else ""
                        return {
                            "name": name,
                            "price": _safe_float(fields[3]),
                            "change": round(_safe_float(fields[3]) - _safe_float(fields[2]), 2),
                            "pct": round((_safe_float(fields[3]) - _safe_float(fields[2])) / _safe_float(fields[2]) * 100, 2) if _safe_float(fields[2]) > 0 else 0,
                            "volume": _safe_float(fields[8]),
                            "high": _safe_float(fields[4]),
                            "low": _safe_float(fields[5]),
                            "open": _safe_float(fields[1]),
                            "prev_close": _safe_float(fields[2]),
                            "time": f"{fields[30]} {fields[31]}" if len(fields) > 31 else datetime.now().strftime("%H:%M:%S"),
                        }
                    elif market == "HK" and len(fields) >= 13:
                        return {
                            "price": _safe_float(fields[6]),
                            "change": _safe_float(fields[7]),
                            "pct": _safe_float(fields[8]),
                            "volume": _safe_float(fields[12]),
                            "high": _safe_float(fields[4]),
                            "low": _safe_float(fields[5]),
                            "open": _safe_float(fields[2]),
                            "prev_close": _safe_float(fields[3]),
                            "time": f"{fields[17]} {fields[18]}" if len(fields) > 18 else datetime.now().strftime("%H:%M:%S"),
                        }
        except Exception as e:
            logger.debug(f"Sina realtime error for {code}: {e}")
        return None

    @staticmethod
    def fetch_history(code: str, market: str, start: str, end: str, kline_type: str = "daily", adjust: str = "qfq") -> Optional[pd.DataFrame]:
        try:
            if market != "A":
                return None
            prefix = "sh" if code.startswith(("6", "9")) else "sz"
            sina_code = f"{prefix}{code}"
            url = "https://money.finance.sina.com.cn/quotes_service/api/json_v2.php/CN_MarketData.getKLineData"
            params = {
                "symbol": sina_code,
                "scale": "240",
                "ma": "no",
                "datalen": "500",
            }
            resp = _http_get(url, params=params, headers=_SINA_HEADERS, timeout=15)
            if resp:
                try:
                    data = resp.json()
                    if isinstance(data, list) and data:
                        rows = []
                        for item in data:
                            rows.append({
                                "date": item.get("day", ""),
                                "open": _safe_float(item.get("open", 0)),
                                "close": _safe_float(item.get("close", 0)),
                                "high": _safe_float(item.get("high", 0)),
                                "low": _safe_float(item.get("low", 0)),
                                "volume": _safe_float(item.get("volume", 0)),
                            })
                        if rows:
                            return pd.DataFrame(rows)
                except (ValueError, KeyError):
                    pass
        except Exception as e:
            logger.debug(f"Sina history error for {code}: {e}")
        return None


class EastMoneySource:
    """东方财富 - 备用数据源，带熔断机制"""
    NAME = "东方财富"

    _circuits = {"realtime": {"open": False, "until": 0, "fail_count": 0, "success_count": 0},
                 "history": {"open": False, "until": 0, "fail_count": 0, "success_count": 0},
                 "hot": {"open": False, "until": 0, "fail_count": 0, "success_count": 0}}

    @classmethod
    def _check_circuit(cls, endpoint: str) -> bool:
        c = cls._circuits.get(endpoint, {"open": False, "until": 0, "fail_count": 0, "success_count": 0})
        if c["open"]:
            if time.time() >= c["until"]:
                c["open"] = False
                c["fail_count"] = 0
                return True
            return False
        return True

    @classmethod
    def _trip_circuit(cls, endpoint: str, cooldown: int = 60):
        c = cls._circuits.setdefault(endpoint, {"open": False, "until": 0, "fail_count": 0, "success_count": 0})
        c["open"] = True
        c["fail_count"] += 1
        c["success_count"] = 0
        dynamic_cooldown = min(300, cooldown * (1 + c["fail_count"] * 0.5))
        c["until"] = time.time() + dynamic_cooldown
        logger.debug(f"EastMoney {endpoint} circuit tripped, cooldown {dynamic_cooldown:.1f}s")

    @classmethod
    def _reset_circuit(cls, endpoint: str):
        c = cls._circuits.get(endpoint, {"open": False, "until": 0, "fail_count": 0, "success_count": 0})
        c["success_count"] += 1
        c["fail_count"] = max(0, c["fail_count"] - 0.5)
        if c["success_count"] >= 3:
            c["fail_count"] = 0
            c["success_count"] = 0

    @staticmethod
    def _a_code_to_secid(code: str) -> str:
        if code.startswith(("6", "9")):
            return f"1.{code}"
        return f"0.{code}"

    @staticmethod
    def _hk_code_to_secid(code: str) -> str:
        return f"116.{code}"

    @staticmethod
    def _us_code_to_secid(code: str) -> str:
        return f"105.{code}"

    @staticmethod
    def fetch_realtime(code: str, market: str) -> Optional[dict]:
        if not EastMoneySource._check_circuit("realtime"):
            return None
        try:
            if market == "A":
                secid = EastMoneySource._a_code_to_secid(code)
            elif market == "HK":
                secid = EastMoneySource._hk_code_to_secid(code)
            elif market == "US":
                secid = EastMoneySource._us_code_to_secid(code)
            else:
                return None

            url = "https://push2.eastmoney.com/api/qt/stock/get"
            params = {
                "secid": secid,
                "fields": "f43,f44,f45,f46,f47,f48,f57,f58,f60,f168,f169,f170,f171",
                "ut": "fa5fd1943c7b386f172d6893dbfba10b",
            }
            resp = _http_get(url, params=params, headers=_EM_HEADERS, timeout=10)
            if resp:
                try:
                    d = resp.json().get("data", {})
                    if d:
                        divisor = 100 if market == "A" else 1000
                        price = _safe_float(d.get("f43", 0)) / divisor if d.get("f43") else 0
                        change = _safe_float(d.get("f169", 0)) / divisor if d.get("f169") else 0
                        pct = _safe_float(d.get("f170", 0)) / 100 if d.get("f170") else 0
                        name = str(d.get("f58", ""))
                        result = {
                            "name": name,
                            "price": price,
                            "change": change,
                            "pct": pct,
                            "volume": _safe_float(d.get("f47", 0)),
                            "high": _safe_float(d.get("f44", 0)) / divisor if d.get("f44") else 0,
                            "low": _safe_float(d.get("f45", 0)) / divisor if d.get("f45") else 0,
                            "open": _safe_float(d.get("f46", 0)) / divisor if d.get("f46") else 0,
                            "prev_close": _safe_float(d.get("f60", 0)) / divisor if d.get("f60") else 0,
                            "time": datetime.now().strftime("%H:%M:%S"),
                        }
                        if market == "A":
                            result["turnover"] = _safe_float(d.get("f168", 0)) / 100 if d.get("f168") else 0
                            result["amplitude"] = _safe_float(d.get("f171", 0)) / 100 if d.get("f171") else 0
                        EastMoneySource._reset_circuit("realtime")
                        return result
                except json.JSONDecodeError:
                    logger.debug(f"EastMoney realtime JSON decode error for {code}")
            EastMoneySource._trip_circuit("realtime", 60)
        except Exception as e:
            logger.debug(f"EastMoney realtime error for {code}: {e}")
            EastMoneySource._trip_circuit("realtime", 60)
        return None

    @staticmethod
    def fetch_history(code: str, market: str, start: str, end: str, kline_type: str = "daily", adjust: str = "qfq") -> Optional[pd.DataFrame]:
        if not EastMoneySource._check_circuit("history"):
            return None
        try:
            if market == "A":
                secid = EastMoneySource._a_code_to_secid(code)
            elif market == "HK":
                secid = EastMoneySource._hk_code_to_secid(code)
            elif market == "US":
                secid = EastMoneySource._us_code_to_secid(code)
            else:
                return None

            url = "https://push2his.eastmoney.com/api/qt/stock/kline/get"
            klt_map = {"daily": "101", "weekly": "102", "monthly": "103"}
            params = {
                "secid": secid,
                "fields1": "f1,f2,f3,f4,f5,f6",
                "fields2": "f51,f52,f53,f54,f55,f56,f57",
                "klt": klt_map.get(kline_type, "101"),
                "fqt": "2" if adjust == "hfq" else "0" if adjust == "" else "1",
                "beg": start,
                "end": end,
                "ut": "fa5fd1943c7b386f172d6893dbfba10b",
            }
            resp = _http_get(url, params=params, headers=_EM_HEADERS, timeout=15)
            if resp:
                try:
                    data = resp.json().get("data", {})
                    klines = data.get("klines", [])
                    if klines:
                        rows = []
                        for line in klines:
                            parts = line.split(",")
                            if len(parts) >= 6:
                                rows.append({
                                    "date": parts[0],
                                    "open": _safe_float(parts[1]),
                                    "close": _safe_float(parts[2]),
                                    "high": _safe_float(parts[3]),
                                    "low": _safe_float(parts[4]),
                                    "volume": _safe_float(parts[5]),
                                })
                        if rows:
                            EastMoneySource._reset_circuit("history")
                            return pd.DataFrame(rows)
                except json.JSONDecodeError:
                    logger.debug(f"EastMoney history JSON decode error for {code}")
            EastMoneySource._trip_circuit("history", 60)
        except Exception as e:
            logger.debug(f"EastMoney history error for {code}: {e}")
            EastMoneySource._trip_circuit("history", 60)
        return None

    @staticmethod
    def fetch_hot_stocks() -> Optional[list]:
        if not EastMoneySource._check_circuit("hot"):
            return None
        try:
            url = "https://push2.eastmoney.com/api/qt/clist/get"
            params = {
                "pn": "1",
                "pz": "10",
                "po": "1",
                "np": "1",
                "fltt": "2",
                "invt": "2",
                "fid": "f3",
                "fs": "m:0+t:6,m:0+t:80,m:1+t:2,m:1+t:23",
                "fields": "f2,f3,f4,f5,f6,f7,f8,f12,f14",
                "ut": "fa5fd1943c7b386f172d6893dbfba10b",
            }
            resp = _http_get(url, params=params, headers=_EM_HEADERS, timeout=10)
            if resp:
                try:
                    data = resp.json().get("data", {})
                    diff = data.get("diff", [])
                    if diff:
                        result = []
                        for item in diff:
                            code = str(item.get("f12", ""))
                            name = str(item.get("f14", ""))
                            price = _safe_float(item.get("f2", 0))
                            pct = _safe_float(item.get("f3", 0))
                            change = _safe_float(item.get("f4", 0))
                            volume = _safe_float(item.get("f5", 0))
                            if code and name and price > 0:
                                result.append({
                                    "code": code,
                                    "name": name,
                                    "price": price,
                                    "pct": pct,
                                    "change": change,
                                    "volume": volume,
                                })
                        if result:
                            EastMoneySource._reset_circuit("hot")
                            return result[:8]
                except json.JSONDecodeError:
                    logger.debug("EastMoney hot stocks JSON decode error")
            EastMoneySource._trip_circuit("hot", 60)
        except Exception as e:
            logger.debug(f"EastMoney hot stocks error: {e}")
            EastMoneySource._trip_circuit("hot", 60)
        return None


class AkshareSource:
    """AkShare - Python库数据源"""
    NAME = "AkShare"

    _fail_until = 0

    @classmethod
    def is_available(cls) -> bool:
        return time.time() >= cls._fail_until

    @classmethod
    def mark_failed(cls, cooldown: int = 30):
        cls._fail_until = time.time() + cooldown

    @staticmethod
    def fetch_realtime(code: str, market: str) -> Optional[dict]:
        if not AkshareSource.is_available():
            return None
        try:
            import akshare as ak
            if market == "A":
                df = _akshare_retry(ak.stock_zh_a_spot_em)
                if df is not None and not df.empty:
                    row = df[df["代码"] == code]
                    if not row.empty:
                        r = row.iloc[0]
                        return {
                            "name": str(r.get("名称", "")),
                            "price": _safe_float(r.get("最新价", 0)),
                            "change": _safe_float(r.get("涨跌额", 0)),
                            "pct": _safe_float(r.get("涨跌幅", 0)),
                            "volume": _safe_float(r.get("成交量", 0)),
                            "high": _safe_float(r.get("最高", 0)),
                            "low": _safe_float(r.get("最低", 0)),
                            "open": _safe_float(r.get("今开", 0)),
                            "prev_close": _safe_float(r.get("昨收", 0)),
                            "turnover": _safe_float(r.get("换手率", 0)),
                            "amplitude": _safe_float(r.get("振幅", 0)),
                            "time": str(r.get("时间", "")),
                        }
            elif market == "HK":
                df = _akshare_retry(ak.stock_hk_spot_em)
                if df is not None and not df.empty:
                    row = df[df["代码"] == code]
                    if not row.empty:
                        r = row.iloc[0]
                        return {
                            "name": str(r.get("名称", "")),
                            "price": _safe_float(r.get("最新价", 0)),
                            "change": _safe_float(r.get("涨跌额", 0)),
                            "pct": _safe_float(r.get("涨跌幅", 0)),
                            "volume": _safe_float(r.get("成交量", 0)),
                            "high": _safe_float(r.get("最高", 0)),
                            "low": _safe_float(r.get("最低", 0)),
                            "open": _safe_float(r.get("今开", 0)),
                            "prev_close": _safe_float(r.get("昨收", 0)),
                            "time": datetime.now().strftime("%H:%M:%S"),
                        }
            elif market == "US":
                df = _akshare_retry(ak.stock_us_spot_em)
                if df is not None and not df.empty:
                    code_upper = code.upper()
                    row = df[df["代码"].str.upper() == code_upper]
                    if row.empty:
                        row = df[df["代码"].str.upper().str.startswith(code_upper)]
                    if not row.empty:
                        r = row.iloc[0]
                        return {
                            "name": str(r.get("名称", "")),
                            "price": _safe_float(r.get("最新价", 0)),
                            "change": _safe_float(r.get("涨跌额", 0)),
                            "pct": _safe_float(r.get("涨跌幅", 0)),
                            "volume": _safe_float(r.get("成交量", 0)),
                            "high": _safe_float(r.get("最高", 0)),
                            "low": _safe_float(r.get("最低", 0)),
                            "open": _safe_float(r.get("今开", 0)),
                            "prev_close": _safe_float(r.get("昨收", 0)),
                            "time": datetime.now().strftime("%H:%M:%S"),
                        }
        except Exception as e:
            logger.debug(f"Akshare realtime error for {code}: {e}")
            AkshareSource.mark_failed(30)
        return None

    @staticmethod
    def fetch_history(code: str, market: str, start: str, end: str, kline_type: str = "daily", adjust: str = "qfq") -> Optional[pd.DataFrame]:
        if not AkshareSource.is_available():
            return None
        try:
            import akshare as ak
            if market == "A":
                ak_period = kline_type if kline_type in ("daily", "weekly", "monthly") else "daily"
                return _akshare_retry(ak.stock_zh_a_hist, symbol=code, period=ak_period,
                                      start_date=start, end_date=end, adjust=adjust)
            elif market == "HK":
                ak_period = kline_type if kline_type in ("daily", "weekly", "monthly") else "daily"
                return _akshare_retry(ak.stock_hk_hist, symbol=code, period=ak_period,
                                      start_date=start, end_date=end, adjust=adjust if adjust in ("qfq", "hfq", "") else "")
            elif market == "US":
                ak_period = "daily"
                return _akshare_retry(ak.stock_us_hist, symbol=code, period=ak_period,
                                      start_date=start, end_date=end, adjust=adjust if adjust in ("qfq", "hfq", "") else "")
        except Exception as e:
            logger.debug(f"Akshare history error for {code}: {e}")
            AkshareSource.mark_failed(30)
        return None

    @staticmethod
    def fetch_hot_stocks() -> Optional[list]:
        if not AkshareSource.is_available():
            return None
        try:
            import akshare as ak
            df = _akshare_retry(ak.stock_zh_a_spot_em)
            if df is None or df.empty:
                return None
            df = df.sort_values(by="涨跌幅", ascending=False)
            top = df.head(8)
            result = []
            for _, r in top.iterrows():
                result.append({
                    "code": str(r.get("代码", "")),
                    "name": str(r.get("名称", "")),
                    "price": _safe_float(r.get("最新价", 0)),
                    "pct": _safe_float(r.get("涨跌幅", 0)),
                    "change": _safe_float(r.get("涨跌额", 0)),
                    "volume": _safe_float(r.get("成交量", 0)),
                })
            return result
        except Exception as e:
            logger.debug(f"Akshare hot stocks error: {e}")
            AkshareSource.mark_failed(30)
        return None


def _akshare_retry(func, *args, **kwargs):
    for i in range(3):
        try:
            _AKSHARE_BUCKET.wait()
            result = func(*args, **kwargs)
            if result is not None and not (isinstance(result, pd.DataFrame) and result.empty):
                return result
        except Exception as e:
            if i < 2:
                time.sleep(0.5 * (i + 1))
            else:
                logger.debug(f"Akshare retry exhausted: {e}")
    return None


class SmartDataFetcher:
    def __init__(self):
        self._db = get_db()
        self._quality_checker = DataQualityChecker()
        self._health_monitor = DataSourceHealthMonitor()
        self._source_stats: dict = {}
        self._major_indices = {
            "000001": {"name": "上证指数", "market": "INDEX"},
            "399001": {"name": "深证成指", "market": "INDEX"},
            "399006": {"name": "创业板指", "market": "INDEX"},
            "000300": {"name": "沪深300", "market": "INDEX"},
            "000905": {"name": "中证500", "market": "INDEX"},
            ".DJI": {"name": "道琼斯工业指数", "market": "US"},
            ".IXIC": {"name": "纳斯达克指数", "market": "US"},
            ".INX": {"name": "标普500", "market": "US"},
        }
        self._bootstrap_reference_assets()

    def _bootstrap_reference_assets(self) -> None:
        rows = []
        for symbol, meta in self._major_indices.items():
            rows.append(
                {
                    "symbol": symbol,
                    "market": meta["market"],
                    "name": meta["name"],
                    "instrument_type": "index",
                    "industry": "指数",
                    "concepts": "",
                    "market_value": 0,
                    "float_market_value": 0,
                    "list_date": "",
                    "extra_json": meta,
                }
            )
        try:
            self._db.upsert_stock_info_rows(rows)
        except Exception as e:
            logger.debug(f"Bootstrap reference assets failed: {e}")

    def _record_source(
        self,
        source: str,
        success: bool,
        request_type: str,
        latency_ms: float = 0,
        error: str = "",
    ) -> None:
        key = f"{request_type}:{source}"
        if key not in self._source_stats:
            self._source_stats[key] = {"ok": 0, "fail": 0}
        if success:
            self._source_stats[key]["ok"] += 1
        else:
            self._source_stats[key]["fail"] += 1
        self._health_monitor.record(source, request_type, success, latency_ms, error)

    def _get_realtime_sources(self, market: str) -> list:
        if market == "A":
            sources = [
                ("tencent", TencentSource.fetch_realtime),
                ("akshare", AkshareSource.fetch_realtime),
                ("sina", SinaSource.fetch_realtime),
                ("eastmoney", EastMoneySource.fetch_realtime),
            ]
        elif market == "HK":
            sources = [
                ("tencent", TencentSource.fetch_realtime),
                ("akshare", AkshareSource.fetch_realtime),
                ("eastmoney", EastMoneySource.fetch_realtime),
            ]
        elif market == "US":
            sources = [
                ("tencent", TencentSource.fetch_realtime),
                ("akshare", AkshareSource.fetch_realtime),
                ("eastmoney", EastMoneySource.fetch_realtime),
            ]
        else:
            sources = [
                ("tencent", TencentSource.fetch_realtime),
                ("akshare", AkshareSource.fetch_realtime),
                ("sina", SinaSource.fetch_realtime),
                ("eastmoney", EastMoneySource.fetch_realtime),
            ]
        return self._health_monitor.rank_sources("realtime", sources)

    def _get_history_sources(self, market: str) -> list:
        if market == "A":
            sources = [
                ("tencent", TencentSource.fetch_history),
                ("akshare", AkshareSource.fetch_history),
                ("sina", SinaSource.fetch_history),
                ("eastmoney", EastMoneySource.fetch_history),
            ]
        elif market == "HK":
            sources = [
                ("tencent", TencentSource.fetch_history),
                ("akshare", AkshareSource.fetch_history),
                ("eastmoney", EastMoneySource.fetch_history),
            ]
        elif market == "US":
            sources = [
                ("akshare", AkshareSource.fetch_history),
                ("eastmoney", EastMoneySource.fetch_history),
            ]
        else:
            sources = [
                ("tencent", TencentSource.fetch_history),
                ("akshare", AkshareSource.fetch_history),
                ("sina", SinaSource.fetch_history),
                ("eastmoney", EastMoneySource.fetch_history),
            ]
        return self._health_monitor.rank_sources("history", sources)

    def _resolve_period_range(self, period: str) -> tuple[str, str]:
        trading_days = PERIOD_MAP.get(period, 370)
        end_date = datetime.now().strftime("%Y%m%d")
        if trading_days is None:
            return "20000101", end_date
        start_date = (datetime.now() - timedelta(days=trading_days)).strftime("%Y%m%d")
        return start_date, end_date

    def _needs_today_refresh(self, symbol: str, market: str, kline_type: str, adjust: str) -> bool:
        today_key = datetime.now().strftime("%Y-%m-%d")
        try:
            updated_at = self._db.get_last_update_time(symbol, market, kline_type, adjust=adjust, trade_date=today_key)
            if not updated_at:
                return True
            age = (datetime.now() - datetime.strptime(updated_at, "%Y-%m-%d %H:%M:%S")).total_seconds()
            return age >= _TODAY_CACHE_TTL_SECONDS
        except Exception:
            return True

    def _prepare_frame_for_storage(self, df: pd.DataFrame, source: str) -> pd.DataFrame:
        result = _normalize(df)
        if result.empty:
            return result
        result = self._quality_checker.run(result)
        result["source"] = source
        if "adjusted_factor" not in result.columns:
            result["adjusted_factor"] = 1.0
        else:
            result["adjusted_factor"] = result["adjusted_factor"].fillna(1.0)
        result["date"] = result["date"].apply(_date_to_key)
        return result

    def _store_history_frame(
        self,
        symbol: str,
        market: str,
        kline_type: str,
        adjust: str,
        df: pd.DataFrame,
        source: str,
        instrument_type: str = "stock",
    ) -> None:
        if df.empty:
            return
        rows = df.to_dict("records")
        conn = None
        try:
            conn = _get_db_connection()
            self._db.upsert_kline_rows(symbol, market, kline_type, rows, adjust=adjust, instrument_type=instrument_type, conn=conn)
        except Exception as e:
            logger.debug(f"Store history frame failed: {e}")
        finally:
            if conn:
                _return_db_connection(conn)

    async def _fetch_history_from_network(
        self,
        symbol: str,
        market: str,
        start_date: str,
        end_date: str,
        kline_type: str,
        adjust: str,
        instrument_type: str = "stock",
    ) -> pd.DataFrame:
        sources = self._get_history_sources(market)

        async def fetch_from_source(name, fetch_fn):
            for attempt in range(2):
                started = time.perf_counter()
                try:
                    df = await asyncio.to_thread(fetch_fn, symbol, market, start_date, end_date, kline_type, adjust)
                    latency_ms = (time.perf_counter() - started) * 1000
                    if df is not None and not df.empty:
                        result = self._prepare_frame_for_storage(df, name)
                        if _validate_history_df(result):
                            self._store_history_frame(symbol, market, kline_type, adjust, result, name, instrument_type)
                            self._record_source(name, True, "history", latency_ms)
                            logger.debug(f"History data for {symbol} from {name}")
                            return result, name
                    if attempt == 0:
                        logger.debug(f"Source {name} attempt {attempt+1} failed for {symbol}, retrying...")
                        await asyncio.sleep(0.5)
                except Exception as e:
                    latency_ms = (time.perf_counter() - started) * 1000
                    logger.debug(f"Source {name} attempt {attempt+1} failed for {symbol}: {e}")
                    if attempt == 1:
                        self._record_source(name, False, "history", latency_ms, str(e))
                    if attempt == 0:
                        await asyncio.sleep(0.5)
            return None, name

        tasks = []
        for name, fetch_fn in sources[:2]:
            tasks.append(fetch_from_source(name, fetch_fn))

        results = await asyncio.gather(*tasks)

        for result, name in results:
            if result is not None:
                return result

        for name, fetch_fn in sources[2:]:
            result, _ = await fetch_from_source(name, fetch_fn)
            if result is not None:
                return result

        logger.debug(f"All history sources failed for {symbol}")
        return pd.DataFrame()

    def _load_cached_history(
        self,
        symbol: str,
        market: str,
        kline_type: str,
        start_date: str,
        end_date: str,
        adjust: str,
    ) -> pd.DataFrame:
        start_key = f"{start_date[:4]}-{start_date[4:6]}-{start_date[6:8]}"
        end_key = f"{end_date[:4]}-{end_date[4:6]}-{end_date[6:8]}"
        conn = None
        try:
            conn = _get_db_connection()
            return self._db.load_kline_rows(symbol, market, kline_type, start_key, end_key, adjust, conn=conn)
        except Exception as e:
            logger.debug(f"Load cached history failed: {e}")
            return pd.DataFrame()
        finally:
            if conn:
                _return_db_connection(conn)

    async def _fetch_index_history(self, symbol: str, start_date: str, end_date: str, kline_type: str) -> pd.DataFrame:
        try:
            import akshare as ak
            period = kline_type if kline_type in ("daily", "weekly", "monthly") else "daily"
            df = await asyncio.to_thread(
                _akshare_retry,
                ak.index_zh_a_hist,
                symbol=symbol,
                period=period,
                start_date=start_date,
                end_date=end_date,
            )
            return df if df is not None else pd.DataFrame()
        except Exception as e:
            logger.debug(f"Index history fetch failed for {symbol}: {e}")
            return pd.DataFrame()

    async def get_history(
        self,
        symbol: str,
        period: str = "1y",
        kline_type: str = "daily",
        adjust: str = "qfq",
        instrument_type: str = "stock",
    ) -> pd.DataFrame:
        if kline_type == "intraday":
            return await self.get_intraday_data(symbol, period=1, adjust="" if adjust == "qfq" else adjust)

        cache_key = f"{symbol}:{period}:{kline_type}:{adjust}:{instrument_type}"
        cached = _cache_get(_history_cache, cache_key)
        if cached is not None:
            return cached.copy()

        market = "INDEX" if instrument_type == "index" else MarketDetector.detect(symbol)
        norm = MarketDetector.normalize_symbol(symbol)
        start_date, end_date = self._resolve_period_range(period)
        today_key = datetime.now().strftime("%Y-%m-%d")
        cached_df = self._load_cached_history(norm, market, kline_type, start_date, end_date, adjust)

        fetch_start = ""
        if cached_df.empty:
            fetch_start = start_date
        else:
            latest_date = cached_df["date"].iloc[-1]
            latest_key = _date_to_key(latest_date)[:10]
            if latest_key < today_key:
                fetch_start = (pd.to_datetime(latest_key) + timedelta(days=1)).strftime("%Y%m%d")
            elif latest_key == today_key and self._needs_today_refresh(norm, market, kline_type, adjust):
                fetch_start = datetime.now().strftime("%Y%m%d")

        if fetch_start:
            if market == "INDEX" and norm in {"000001", "399001", "399006", "000300", "000905"}:
                index_df = await self._fetch_index_history(norm, fetch_start, end_date, kline_type)
                if not index_df.empty:
                    result = self._prepare_frame_for_storage(index_df, "akshare_index")
                    self._store_history_frame(norm, market, kline_type, adjust, result, "akshare_index", "index")
            else:
                await self._fetch_history_from_network(norm, market, fetch_start, end_date, kline_type, adjust, instrument_type)
            cached_df = self._load_cached_history(norm, market, kline_type, start_date, end_date, adjust)

        if not cached_df.empty:
            ttl = _HIST_CACHE_TTL if (cached_df["date"].iloc[-1].strftime("%Y-%m-%d") if hasattr(cached_df["date"].iloc[-1], "strftime") else str(cached_df["date"].iloc[-1])[:10]) != today_key else min(_HIST_CACHE_TTL, _TODAY_CACHE_TTL_SECONDS)
            _cache_set(_history_cache, cache_key, cached_df.copy(), ttl=ttl)
            return cached_df

        logger.debug(f"All history sources failed for {symbol}")
        return pd.DataFrame()

    async def get_realtime(self, symbol: str) -> dict:
        cache_key = symbol
        cached = _cache_get(_realtime_cache, cache_key)
        if cached is not None:
            return cached

        info = self._db.get_stock_info(symbol)
        instrument_type = (info or {}).get("instrument_type", "stock")
        market = (info or {}).get("market") or MarketDetector.detect(symbol)
        norm = MarketDetector.normalize_symbol(symbol)

        if instrument_type == "ETF":
            etf_spot = await self.get_etf_spot(norm)
            if etf_spot:
                _cache_set(_realtime_cache, cache_key, etf_spot, ttl=_RT_CACHE_TTL)
                return etf_spot
        if instrument_type == "bond":
            bond_spot = await self.get_convertible_bond_spot(norm)
            if bond_spot:
                _cache_set(_realtime_cache, cache_key, bond_spot, ttl=_RT_CACHE_TTL)
                return bond_spot
        if instrument_type == "future":
            future_spot = await self.get_futures_spot(norm)
            if future_spot:
                _cache_set(_realtime_cache, cache_key, future_spot, ttl=_RT_CACHE_TTL)
                return future_spot
        if instrument_type == "index" and market == "INDEX":
            index_spot = await self.get_index_spot(norm)
            if index_spot:
                _cache_set(_realtime_cache, cache_key, index_spot, ttl=_RT_CACHE_TTL)
                return index_spot

        sources = self._get_realtime_sources(market)

        async def fetch_from_source(name, fetch_fn):
            for attempt in range(2):
                started = time.perf_counter()
                try:
                    data = await asyncio.to_thread(fetch_fn, norm, market)
                    latency_ms = (time.perf_counter() - started) * 1000
                    if data and _validate_realtime(data):
                        if not data.get("name"):
                            db_name = get_stock_name(symbol)
                            if db_name:
                                data["name"] = db_name
                        self._record_source(name, True, "realtime", latency_ms)
                        logger.debug(f"Realtime data for {symbol} from {name}")
                        return data, name
                    if attempt == 0:
                        logger.debug(f"Source {name} attempt {attempt+1} failed for {symbol}, retrying...")
                        await asyncio.sleep(0.3)
                except Exception as e:
                    latency_ms = (time.perf_counter() - started) * 1000
                    logger.debug(f"Source {name} attempt {attempt+1} failed for {symbol}: {e}")
                    if attempt == 1:
                        self._record_source(name, False, "realtime", latency_ms, str(e))
                    if attempt == 0:
                        await asyncio.sleep(0.3)
            return None, name

        tasks = []
        for name, fetch_fn in sources[:2]:
            tasks.append(fetch_from_source(name, fetch_fn))

        results = await asyncio.gather(*tasks)

        for data, name in results:
            if data:
                _cache_set(_realtime_cache, cache_key, data, ttl=_RT_CACHE_TTL)
                return data

        for name, fetch_fn in sources[2:]:
            data, _ = await fetch_from_source(name, fetch_fn)
            if data:
                _cache_set(_realtime_cache, cache_key, data, ttl=_RT_CACHE_TTL)
                return data

        if cache_key in _realtime_cache:
            return _realtime_cache[cache_key]["data"]

        conn = None
        try:
            conn = _get_db_connection()
            latest_daily = self._db.load_kline_rows(norm, market, "daily", adjust="qfq", conn=conn)
            if not latest_daily.empty:
                last_row = latest_daily.iloc[-1]
                result = {
                    "name": (info or {}).get("name") or get_stock_name(symbol) or symbol,
                    "price": _safe_float(last_row.get("close", 0)),
                    "change": 0,
                    "pct": 0,
                    "volume": _safe_float(last_row.get("volume", 0)),
                    "high": _safe_float(last_row.get("high", 0)),
                    "low": _safe_float(last_row.get("low", 0)),
                    "open": _safe_float(last_row.get("open", 0)),
                    "prev_close": _safe_float(last_row.get("close", 0)),
                    "time": _date_to_key(last_row.get("date")),
                    "offline": True,
                }
                _cache_set(_realtime_cache, cache_key, result, ttl=_RT_CACHE_TTL)
                return result
        except Exception as e:
            logger.debug(f"Fallback to cached history failed: {e}")
        finally:
            if conn:
                _return_db_connection(conn)

        db_name = get_stock_name(symbol)
        fallback = {"name": db_name or symbol, "offline": True}
        _cache_set(_realtime_cache, cache_key, fallback, ttl=_RT_CACHE_TTL)
        logger.debug(f"All realtime sources failed for {symbol}")
        return fallback

    def _pick_frame_value(self, frame: pd.DataFrame, patterns: list[str], default: Any = 0) -> Any:
        if frame is None or frame.empty:
            return default
        text_patterns = [re.compile(pattern, re.I) for pattern in patterns]
        for column in frame.columns:
            for pattern in text_patterns:
                if pattern.search(str(column)):
                    value = frame[column].iloc[0]
                    if isinstance(default, str):
                        return "" if pd.isna(value) else str(value)
                    return _safe_float(value, default)
        return default

    async def get_fundamentals(self, symbol: str, market: str) -> dict:
        if market != "A":
            return {}

        norm = MarketDetector.normalize_symbol(symbol)
        try:
            cached_rows = self._db.get_financials(norm)
            if cached_rows:
                latest_row = cached_rows[0]
                try:
                    updated_at = datetime.strptime(latest_row["updated_at"], "%Y-%m-%d %H:%M:%S")
                    if (datetime.now() - updated_at).days <= 100:
                        payload = json.loads(latest_row.get("payload", "{}")) if latest_row.get("payload") else {}
                        payload.update(
                            {
                                "revenue": latest_row.get("revenue", 0),
                                "net_profit": latest_row.get("net_profit", 0),
                                "gross_margin": latest_row.get("gross_margin", 0),
                                "net_margin": latest_row.get("net_margin", 0),
                                "roe": latest_row.get("roe", 0),
                                "roa": latest_row.get("roa", 0),
                                "debt_ratio": latest_row.get("debt_ratio", 0),
                                "report_date": latest_row.get("report_date", ""),
                            }
                        )
                        return payload
                except Exception:
                    pass
        except Exception:
            pass

        try:
            import akshare as ak

            analysis_df = await asyncio.to_thread(
                _akshare_retry,
                ak.stock_financial_analysis_indicator,
                symbol=norm,
                start_year=str(max(datetime.now().year - 2, 2020)),
            )
            info_df = await asyncio.to_thread(_akshare_retry, ak.stock_individual_info_em, symbol=norm)
            result = {
                "symbol": norm,
                "report_date": "",
                "revenue": self._pick_frame_value(analysis_df, [r"营业总收入", r"营业收入"], 0.0),
                "net_profit": self._pick_frame_value(analysis_df, [r"净利润"], 0.0),
                "gross_margin": self._pick_frame_value(analysis_df, [r"销售毛利率", r"毛利率"], 0.0),
                "net_margin": self._pick_frame_value(analysis_df, [r"销售净利率", r"净利率"], 0.0),
                "roe": self._pick_frame_value(analysis_df, [r"净资产收益率", r"ROE"], 0.0),
                "roa": self._pick_frame_value(analysis_df, [r"总资产净利率", r"ROA"], 0.0),
                "debt_ratio": self._pick_frame_value(analysis_df, [r"资产负债率"], 0.0),
                "industry": self._pick_frame_value(info_df, [r"行业"], ""),
                "market_value": self._pick_frame_value(info_df, [r"总市值"], 0.0),
                "float_market_value": self._pick_frame_value(info_df, [r"流通市值"], 0.0),
                "list_date": self._pick_frame_value(info_df, [r"上市时间", r"上市日期"], ""),
            }
            if analysis_df is not None and not analysis_df.empty:
                date_column = next((col for col in analysis_df.columns if "日期" in str(col) or "报告期" in str(col)), None)
                if date_column:
                    result["report_date"] = str(analysis_df[date_column].iloc[0])
            self._db.upsert_financial_rows(norm, [result])
            await self.refresh_stock_info_for_symbol(norm)
            return result
        except Exception as e:
            logger.debug(f"Fundamentals fetch failed: {e}")
        return {}

    async def refresh_stock_info(self, force: bool = False) -> dict:
        try:
            existing = self._db.fetchone("SELECT COUNT(*) AS total FROM stock_info")
            if not force and existing and int(existing["total"]) >= 500:
                return {"success": True, "count": int(existing["total"]), "cached": True}
        except Exception:
            pass

        try:
            import akshare as ak

            rows: list[dict] = []
            code_name_df = await asyncio.to_thread(_akshare_retry, ak.stock_info_a_code_name)
            if code_name_df is not None and not code_name_df.empty:
                for _, row in code_name_df.iterrows():
                    rows.append(
                        {
                            "symbol": str(row.get("code") or row.get("证券代码") or row.iloc[0]),
                            "market": "A",
                            "name": str(row.get("name") or row.get("证券简称") or row.iloc[1]),
                            "instrument_type": "stock",
                            "industry": "",
                        }
                    )

            etf_df = await asyncio.to_thread(_akshare_retry, ak.fund_etf_spot_em)
            if etf_df is not None and not etf_df.empty:
                for _, row in etf_df.iterrows():
                    rows.append(
                        {
                            "symbol": str(row.get("代码", "")),
                            "market": "A",
                            "name": str(row.get("名称", "")),
                            "instrument_type": "ETF",
                            "industry": "ETF",
                            "market_value": _safe_float(row.get("总市值", 0)),
                            "extra_json": row.to_dict(),
                        }
                    )

            bond_df = await asyncio.to_thread(_akshare_retry, ak.bond_zh_cov)
            if bond_df is not None and not bond_df.empty:
                for _, row in bond_df.iterrows():
                    rows.append(
                        {
                            "symbol": str(row.get("债券代码", row.get("代码", ""))),
                            "market": "A",
                            "name": str(row.get("债券简称", row.get("名称", ""))),
                            "instrument_type": "bond",
                            "industry": "可转债",
                            "extra_json": row.to_dict(),
                        }
                    )

            if rows:
                self._db.upsert_stock_info_rows(rows)
            return {"success": True, "count": len(rows), "cached": False}
        except Exception as e:
            logger.debug(f"Stock info refresh failed: {e}")
            return {"success": False, "error": str(e)}

    async def refresh_stock_info_for_symbol(self, symbol: str) -> dict:
        try:
            import akshare as ak

            info_df = await asyncio.to_thread(_akshare_retry, ak.stock_individual_info_em, symbol=symbol)
            info_map = {}
            if info_df is not None and not info_df.empty:
                for _, row in info_df.iterrows():
                    info_map[str(row.iloc[0])] = row.iloc[1]
            current = self._db.get_stock_info(symbol) or {"code": symbol, "market": "A", "name": get_stock_name(symbol) or symbol}
            row = {
                "symbol": symbol,
                "market": current.get("market", "A"),
                "name": current.get("name", get_stock_name(symbol) or symbol),
                "instrument_type": current.get("instrument_type", "stock"),
                "industry": str(info_map.get("行业", current.get("sector", ""))),
                "market_value": _safe_float(info_map.get("总市值", current.get("market_value", 0))),
                "float_market_value": _safe_float(info_map.get("流通市值", current.get("float_market_value", 0))),
                "list_date": str(info_map.get("上市时间", current.get("list_date", ""))),
                "extra_json": info_map,
            }
            self._db.upsert_stock_info_rows([row])
            return {"success": True, "data": row}
        except Exception as e:
            logger.debug(f"Stock info enrich failed for {symbol}: {e}")
            return {"success": False, "error": str(e)}

    async def get_hot_stocks(self) -> list:
        cache_key = "hot_stocks:default"
        cached = _cache_get(_realtime_cache, cache_key)
        if cached is not None:
            return cached

        try:
            data = await asyncio.to_thread(EastMoneySource.fetch_hot_stocks)
            if data:
                _cache_set(_realtime_cache, cache_key, data, ttl=60)
                return data
        except Exception as e:
            logger.debug(f"EastMoney hot stocks failed: {e}")

        try:
            data = await asyncio.to_thread(TencentSource.fetch_hot_stocks)
            if data:
                _cache_set(_realtime_cache, cache_key, data, ttl=60)
                return data
        except Exception as e:
            logger.debug(f"Tencent hot stocks failed: {e}")

        try:
            data = await asyncio.to_thread(AkshareSource.fetch_hot_stocks)
            if data:
                self._db.upsert_stock_info_rows(
                    [
                        {
                            "symbol": item["code"],
                            "market": "A",
                            "name": item["name"],
                            "instrument_type": "stock",
                        }
                        for item in data
                    ]
                )
                _cache_set(_realtime_cache, cache_key, data, ttl=60)
                return data
        except Exception as e:
            logger.debug(f"Akshare hot stocks failed: {e}")

        return _default_hot_stocks()

    async def get_index_spot(self, symbol: str) -> dict:
        cache_key = f"idx_spot:{symbol}"
        cached = _cache_get(_realtime_cache, cache_key)
        if cached is not None:
            return cached

        if symbol in {".DJI", ".IXIC", ".INX"}:
            try:
                data = await asyncio.to_thread(TencentSource.fetch_realtime, symbol, "US")
                if data and _validate_realtime(data):
                    data["name"] = self._major_indices.get(symbol, {}).get("name", symbol)
                    _cache_set(_realtime_cache, cache_key, data, ttl=_RT_CACHE_TTL)
                    return data
            except Exception:
                pass

        if symbol in {"000001", "399001", "399006", "000300", "000905"}:
            try:
                data = await asyncio.to_thread(TencentSource.fetch_realtime, symbol, "A")
                if data and _validate_realtime(data):
                    data["name"] = self._major_indices.get(symbol, {}).get("name", data.get("name", symbol))
                    _cache_set(_realtime_cache, cache_key, data, ttl=_RT_CACHE_TTL)
                    return data
            except Exception:
                pass

            try:
                data = await asyncio.to_thread(EastMoneySource.fetch_realtime, symbol, "A")
                if data and _validate_realtime(data):
                    data["name"] = self._major_indices.get(symbol, {}).get("name", data.get("name", symbol))
                    _cache_set(_realtime_cache, cache_key, data, ttl=_RT_CACHE_TTL)
                    return data
            except Exception:
                pass

        conn = None
        try:
            conn = _get_db_connection()
            hist = self._db.load_kline_rows(symbol, "INDEX", "daily", adjust="qfq", conn=conn)
            if not hist.empty:
                last = hist.iloc[-1]
                prev_close = _safe_float(hist.iloc[-2]["close"], _safe_float(last["close"])) if len(hist) > 1 else _safe_float(last["close"])
                price = _safe_float(last["close"])
                change = price - prev_close
                pct = change / prev_close * 100 if prev_close else 0
                result = {
                    "name": self._major_indices.get(symbol, {}).get("name", symbol),
                    "price": price,
                    "change": round(change, 2),
                    "pct": round(pct, 2),
                    "open": _safe_float(last["open"]),
                    "high": _safe_float(last["high"]),
                    "low": _safe_float(last["low"]),
                    "prev_close": prev_close,
                    "volume": _safe_float(last.get("volume", 0)),
                    "time": _date_to_key(last["date"]),
                    "offline": True,
                }
                _cache_set(_realtime_cache, cache_key, result, ttl=60)
                return result
        except Exception as e:
            logger.debug(f"Index spot fallback failed: {e}")
        finally:
            if conn:
                _return_db_connection(conn)
        return {}

    async def get_intraday_data(
        self,
        symbol: str,
        period: int = 1,
        market: Optional[str] = None,
        adjust: str = "",
    ) -> pd.DataFrame:
        period = int(period)
        if period not in {1, 5, 15, 30, 60}:
            return pd.DataFrame()

        market = market or (self._db.get_stock_info(symbol) or {}).get("market") or MarketDetector.detect(symbol)
        norm = MarketDetector.normalize_symbol(symbol)
        if market == "US" and not norm.startswith("105."):
            norm = f"105.{norm.upper()}"
        kline_type = f"min{period}"
        cache_key = f"intraday:{market}:{norm}:{period}:{adjust}"
        cached = _cache_get(_history_cache, cache_key)
        if cached is not None:
            return cached.copy()

        today_key = datetime.now().strftime("%Y-%m-%d")
        conn = None
        try:
            conn = _get_db_connection()
            cached_df = self._db.load_kline_rows(norm, market, kline_type, start_date=today_key, adjust=adjust, conn=conn)
            if not cached_df.empty and not self._needs_today_refresh(norm, market, kline_type, adjust):
                _cache_set(_history_cache, cache_key, cached_df.copy(), ttl=_HIST_CACHE_TTL)
                return cached_df
        except Exception:
            cached_df = pd.DataFrame()
        finally:
            if conn:
                _return_db_connection(conn)

        try:
            import akshare as ak

            start_date = (datetime.now() - timedelta(days=5)).strftime("%Y-%m-%d %H:%M:%S")
            end_date = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            if market == "A":
                df = await asyncio.to_thread(
                    _akshare_retry,
                    ak.stock_zh_a_hist_min_em,
                    symbol=norm,
                    start_date=start_date,
                    end_date=end_date,
                    period=str(period),
                    adjust=adjust if adjust in ("qfq", "hfq", "") else "",
                )
            elif market == "HK":
                df = await asyncio.to_thread(
                    _akshare_retry,
                    ak.stock_hk_hist_min_em,
                    symbol=norm,
                    period=str(period),
                    adjust=adjust if adjust in ("qfq", "hfq", "") else "",
                    start_date=start_date,
                    end_date=end_date,
                )
            else:
                df = await asyncio.to_thread(
                    _akshare_retry,
                    ak.stock_us_hist_min_em,
                    symbol=norm,
                    start_date=start_date,
                    end_date=end_date,
                )
            if df is not None and not df.empty:
                result = self._prepare_frame_for_storage(df, "akshare_intraday")
                self._store_history_frame(norm, market, kline_type, adjust, result, "akshare_intraday")
                final_df = self._db.load_kline_rows(norm, market, kline_type, start_date=today_key, adjust=adjust)
                _cache_set(_history_cache, cache_key, final_df.copy(), ttl=_HIST_CACHE_TTL)
                return final_df
        except Exception as e:
            logger.debug(f"Intraday fetch failed for {symbol}: {e}")

        return cached_df

    async def get_etf_spot(self, symbol: str) -> dict:
        try:
            import akshare as ak

            df = await asyncio.to_thread(_akshare_retry, ak.fund_etf_spot_em)
            if df is None or df.empty:
                return {}
            row = df[df["代码"].astype(str) == str(symbol)]
            if row.empty:
                return {}
            item = row.iloc[0]
            self._db.upsert_stock_info_rows(
                [{
                    "symbol": str(symbol),
                    "market": "A",
                    "name": str(item.get("名称", symbol)),
                    "instrument_type": "ETF",
                    "industry": "ETF",
                    "extra_json": item.to_dict(),
                }]
            )
            return {
                "name": str(item.get("名称", symbol)),
                "price": _safe_float(item.get("最新价", 0)),
                "change": _safe_float(item.get("涨跌额", 0)),
                "pct": _safe_float(item.get("涨跌幅", 0)),
                "volume": _safe_float(item.get("成交量", 0)),
                "high": _safe_float(item.get("最高价", item.get("最高", 0))),
                "low": _safe_float(item.get("最低价", item.get("最低", 0))),
                "open": _safe_float(item.get("开盘价", item.get("今开", 0))),
                "prev_close": _safe_float(item.get("昨收", 0)),
                "time": _date_to_key(datetime.now()),
                "instrument_type": "ETF",
            }
        except Exception as e:
            logger.debug(f"ETF spot fetch failed for {symbol}: {e}")
        return {}

    async def get_etf_history(self, symbol: str, period: str = "1y", adjust: str = "qfq") -> pd.DataFrame:
        start_date, end_date = self._resolve_period_range(period)
        conn = None
        try:
            conn = _get_db_connection()
            cached_df = self._db.load_kline_rows(symbol, "A", "daily", start_date=f"{start_date[:4]}-{start_date[4:6]}-{start_date[6:8]}", end_date=f"{end_date[:4]}-{end_date[4:6]}-{end_date[6:8]}", adjust=adjust, conn=conn)
            if not cached_df.empty and not self._needs_today_refresh(symbol, "A", "daily", adjust):
                return cached_df
        except Exception:
            cached_df = pd.DataFrame()
        finally:
            if conn:
                _return_db_connection(conn)
        try:
            import akshare as ak

            df = await asyncio.to_thread(
                _akshare_retry,
                ak.fund_etf_hist_em,
                symbol=symbol,
                period="daily",
                start_date=start_date,
                end_date=end_date,
                adjust=adjust if adjust in ("qfq", "hfq", "") else "",
            )
            if df is not None and not df.empty:
                result = self._prepare_frame_for_storage(df, "akshare_etf")
                self._store_history_frame(symbol, "A", "daily", adjust, result, "akshare_etf", instrument_type="ETF")
                return self._db.load_kline_rows(symbol, "A", "daily", start_date=f"{start_date[:4]}-{start_date[4:6]}-{start_date[6:8]}", end_date=f"{end_date[:4]}-{end_date[4:6]}-{end_date[6:8]}", adjust=adjust)
        except Exception as e:
            logger.debug(f"ETF history fetch failed for {symbol}: {e}")
        return cached_df

    async def get_convertible_bond_spot(self, symbol: str) -> dict:
        try:
            import akshare as ak

            df = await asyncio.to_thread(_akshare_retry, ak.bond_zh_cov)
            if df is None or df.empty:
                return {}
            code_col = next((col for col in df.columns if "代码" in str(col)), df.columns[0])
            row = df[df[code_col].astype(str) == str(symbol)]
            if row.empty:
                return {}
            item = row.iloc[0]
            return {
                "name": str(item.get("债券简称", item.get("名称", symbol))),
                "price": _safe_float(item.get("最新价", item.get("现价", 0))),
                "change": _safe_float(item.get("涨跌额", 0)),
                "pct": _safe_float(item.get("涨跌幅", 0)),
                "volume": _safe_float(item.get("成交量", 0)),
                "time": _date_to_key(datetime.now()),
                "instrument_type": "bond",
            }
        except Exception as e:
            logger.debug(f"Bond spot fetch failed for {symbol}: {e}")
        return {}

    async def get_convertible_bond_detail(self, symbol: str) -> dict:
        try:
            import akshare as ak

            df = await asyncio.to_thread(_akshare_retry, ak.bond_zh_cov_value_analysis, symbol=symbol)
            if df is None or df.empty:
                return {}
            latest = df.iloc[-1].to_dict()
            return {str(k): (float(v) if isinstance(v, (int, float, np.floating)) else v) for k, v in latest.items()}
        except Exception as e:
            logger.debug(f"Bond detail fetch failed for {symbol}: {e}")
        return {}

    async def get_futures_spot(self, symbol: str) -> dict:
        try:
            import akshare as ak

            market_code = "".join(ch for ch in symbol if ch.isalpha()).upper()[:2] or "CF"
            df = await asyncio.to_thread(_akshare_retry, ak.futures_zh_spot, symbol=symbol, market=market_code, adjust="0")
            if df is None or df.empty:
                return {}
            row = df.iloc[0].to_dict()
            return {
                "name": str(row.get("symbol", symbol)),
                "price": _safe_float(row.get("current_price", row.get("最新价", 0))),
                "change": _safe_float(row.get("change", row.get("涨跌", 0))),
                "pct": _safe_float(row.get("change_percent", row.get("涨跌幅", 0))),
                "basis": _safe_float(row.get("basis", row.get("基差", 0))),
                "open_interest": _safe_float(row.get("open_interest", row.get("持仓量", 0))),
                "open_interest_change": _safe_float(row.get("open_interest_change", row.get("仓差", 0))),
                "time": _date_to_key(datetime.now()),
                "instrument_type": "future",
                "raw": row,
            }
        except Exception as e:
            logger.debug(f"Futures spot fetch failed for {symbol}: {e}")
        return {}

    async def get_bid_ask(self, symbol: str) -> dict:
        try:
            import akshare as ak

            df = await asyncio.to_thread(_akshare_retry, ak.stock_bid_ask_em, symbol=symbol)
            if df is None or df.empty:
                return {}
            result = {}
            for _, row in df.iterrows():
                label = str(row.iloc[0])
                result[label] = row.iloc[1]
            return result
        except Exception as e:
            logger.debug(f"Bid/ask fetch failed for {symbol}: {e}")
        return {}

    async def get_zt_pool(self, trade_date: Optional[str] = None) -> dict:
        trade_date = trade_date or datetime.now().strftime("%Y%m%d")
        try:
            cached = self._db.get_zt_pool(trade_date)
            if cached:
                return {
                    "limit_up": [row for row in cached if row["pool_type"] == "limit_up"],
                    "broken_board": [row for row in cached if row["pool_type"] == "broken_board"],
                    "strong": [row for row in cached if row["pool_type"] == "strong"],
                }
        except Exception:
            pass

        try:
            import akshare as ak

            mapping = {
                "limit_up": ak.stock_zt_pool_em,
                "broken_board": ak.stock_zt_pool_dtgc_em,
                "strong": ak.stock_zt_pool_strong_em,
            }
            output = {}
            for pool_type, func in mapping.items():
                df = await asyncio.to_thread(_akshare_retry, func, date=trade_date)
                rows = [] if df is None or df.empty else df.to_dict("records")
                self._db.upsert_zt_pool_rows(trade_date, pool_type, rows)
                output[pool_type] = self._db.get_zt_pool(trade_date, pool_type)
            return output
        except Exception as e:
            logger.debug(f"ZT pool fetch failed: {e}")
        return {"limit_up": [], "broken_board": [], "strong": []}

    async def get_northbound_flow(self, limit: int = 10) -> list[dict]:
        try:
            cached = self._db.get_northbound(limit)
            if cached:
                latest_date = cached[0]["trade_date"]
                if latest_date == datetime.now().strftime("%Y-%m-%d"):
                    return cached
        except Exception:
            pass
        try:
            import akshare as ak

            df = await asyncio.to_thread(_akshare_retry, ak.stock_hsgt_hist_em, symbol="北向资金")
            rows = []
            if df is not None and not df.empty:
                date_col = next((col for col in df.columns if "日期" in str(col)), df.columns[0])
                sh_col = next((col for col in df.columns if "沪股通" in str(col)), None)
                sz_col = next((col for col in df.columns if "深股通" in str(col)), None)
                total_col = next((col for col in df.columns if "当日成交净买额" in str(col) or "净流入" in str(col)), df.columns[-1])
                for _, row in df.tail(max(limit, 20)).iterrows():
                    rows.append(
                        {
                            "trade_date": _date_to_key(row[date_col])[:10],
                            "sh_connect": _safe_float(row[sh_col], 0) if sh_col else 0,
                            "sz_connect": _safe_float(row[sz_col], 0) if sz_col else 0,
                            "total_flow": _safe_float(row[total_col], 0),
                            "net_buy": _safe_float(row[total_col], 0),
                            "top_stocks": [],
                        }
                    )
            self._db.upsert_northbound(rows)
            return self._db.get_northbound(limit)
        except Exception as e:
            logger.debug(f"Northbound flow fetch failed: {e}")
        try:
            return self._db.get_northbound(limit)
        except Exception:
            return []

    async def get_market_temperature(self) -> dict:
        cache_key = "market:temperature"
        cached = _cache_get(_realtime_cache, cache_key)
        if cached is not None:
            return cached

        today_key = datetime.now().strftime("%Y-%m-%d")
        try:
            db_cached = self._db.get_market_sentiment(1)
            if db_cached and db_cached[0].get("trade_date") == today_key:
                _cache_set(_realtime_cache, cache_key, db_cached[0], ttl=120)
                return db_cached[0]
        except Exception:
            pass

        try:
            from core.market_data import _fetch_sina_page
            advancers = 0
            decliners = 0
            total_turnover = 0.0
            for page in range(1, 80):
                batch = await asyncio.to_thread(_fetch_sina_page, page, 80, "changepercent", 0)
                if not batch:
                    break
                for item in batch:
                    pct = item.get("changepercent", 0) or 0
                    if pct > 0:
                        advancers += 1
                    elif pct < 0:
                        decliners += 1
                    total_turnover += float(item.get("turnoverratio", 0) or 0)
                if len(batch) < 80:
                    break
            if advancers + decliners > 0:
                ratio = advancers / max(decliners, 1)
                new_high_low_index = (advancers - decliners) / max(advancers + decliners, 1)
                row = {
                    "trade_date": today_key,
                    "advancers": advancers,
                    "decliners": decliners,
                    "up_down_ratio": round(ratio, 4),
                    "turnover_amount": total_turnover,
                    "margin_balance_change": 0,
                    "new_high_low_ratio": round(new_high_low_index, 4),
                    "mcclellan": 0,
                    "ad_line": advancers - decliners,
                    "new_high_low_index": round(float(new_high_low_index), 4),
                }
                self._db.upsert_market_sentiment(row)
                _cache_set(_realtime_cache, cache_key, row, ttl=120)
                return row
        except Exception as e:
            logger.debug(f"Market temperature sina failed: {e}")

        try:
            import akshare as ak
            spot_df = await asyncio.to_thread(_akshare_retry, ak.stock_zh_a_spot_em)
            if spot_df is None or spot_df.empty:
                return db_cached[0] if db_cached else {}
            advancers = int((pd.to_numeric(spot_df.get("涨跌幅"), errors="coerce").fillna(0) > 0).sum())
            decliners = int((pd.to_numeric(spot_df.get("涨跌幅"), errors="coerce").fillna(0) < 0).sum())
            turnover_amount = float(pd.to_numeric(spot_df.get("成交额"), errors="coerce").fillna(0).sum())
            ratio = advancers / max(decliners, 1)
            history = self._db.get_market_sentiment(39)
            recent_net = [int(item.get("advancers", 0)) - int(item.get("decliners", 0)) for item in reversed(history)]
            recent_net.append(advancers - decliners)
            ema19 = pd.Series(recent_net).ewm(span=19, adjust=False).mean().iloc[-1]
            ema39 = pd.Series(recent_net).ewm(span=39, adjust=False).mean().iloc[-1]
            ad_line = sum(recent_net)
            new_high_low_index = (advancers - decliners) / max(advancers + decliners, 1)
            row = {
                "trade_date": today_key,
                "advancers": advancers,
                "decliners": decliners,
                "up_down_ratio": round(ratio, 4),
                "turnover_amount": turnover_amount,
                "margin_balance_change": 0,
                "new_high_low_ratio": round(new_high_low_index, 4),
                "mcclellan": round(float(ema19 - ema39), 4),
                "ad_line": round(float(ad_line), 4),
                "new_high_low_index": round(float(new_high_low_index), 4),
            }
            self._db.upsert_market_sentiment(row)
            _cache_set(_realtime_cache, cache_key, row, ttl=120)
            return row
        except Exception as e:
            logger.debug(f"Market temperature fetch failed: {e}")
        return db_cached[0] if db_cached else {}

    async def get_market_overview(self) -> dict:
        cache_key = "market:overview:full"
        cached = _cache_get(_realtime_cache, cache_key)
        if cached is not None:
            return cached

        index_tasks = []
        for symbol, meta in self._major_indices.items():
            index_tasks.append(self.get_index_spot(symbol))

        indices_results = await asyncio.gather(*index_tasks, return_exceptions=True)

        overview = []
        for i, (symbol, meta) in enumerate(self._major_indices.items()):
            result = indices_results[i]
            if isinstance(result, Exception) or not result:
                continue
            overview.append({"symbol": symbol, **result})

        try:
            northbound = await self.get_northbound_flow(10)
        except Exception:
            northbound = []

        try:
            temperature = await self.get_market_temperature()
        except Exception:
            temperature = {}

        result = {
            "indices": overview,
            "northbound": northbound,
            "temperature": temperature,
        }

        _cache_set(_realtime_cache, cache_key, result, ttl=30)
        return result

    async def export_history_csv(
        self,
        symbol: str,
        period: str = "1y",
        kline_type: str = "daily",
        adjust: str = "qfq",
    ) -> Path:
        df = await self.get_history(symbol, period=period, kline_type=kline_type, adjust=adjust)
        export_dir = self._db.db_path.parent / "cache"
        export_dir.mkdir(parents=True, exist_ok=True)
        file_path = export_dir / f"{symbol}_{period}_{kline_type}_{adjust or 'raw'}.csv"
        df.to_csv(file_path, index=False, encoding="utf-8-sig")
        return file_path

    def get_data_source_health(self) -> list[dict]:
        return self._health_monitor.get_stats()

    async def get_kline(self, symbol: str, period: str = "daily", start_date: str = None, end_date: str = None, limit: int = 500) -> list:
        kline_type_map = {"daily": "daily", "weekly": "weekly", "monthly": "monthly", "1d": "daily", "1w": "weekly", "1m": "monthly"}
        kline_type = kline_type_map.get(period, "daily")
        market = MarketDetector.detect(symbol)
        df = await self.get_history(symbol, period="1y", kline_type=kline_type, adjust="qfq")
        if df is None or df.empty:
            return []
        if start_date:
            df = df[df["date"] >= start_date]
        if end_date:
            df = df[df["date"] <= end_date]
        if limit and len(df) > limit:
            df = df.iloc[-limit:]
        result = []
        for _, row in df.iterrows():
            d = row.get("date", "")
            if hasattr(d, "strftime"):
                d = d.strftime("%Y-%m-%d")
            result.append({
                "date": str(d),
                "open": float(row.get("open", 0) or 0),
                "high": float(row.get("high", 0) or 0),
                "low": float(row.get("low", 0) or 0),
                "close": float(row.get("close", 0) or 0),
                "volume": float(row.get("volume", 0) or 0),
                "amount": float(row.get("amount", 0) or 0),
            })
        return result

    async def get_sector_data(self) -> list:
        cache_key = "sector:data"
        cached = _cache_get(_realtime_cache, cache_key)
        if cached is not None:
            return cached
        try:
            import akshare as ak
            _AKSHARE_BUCKET.wait()
            df = ak.stock_board_industry_name_em()
            if df is not None and not df.empty:
                sectors = []
                for _, row in df.head(30).iterrows():
                    sectors.append({
                        "name": str(row.get("板块名称", "")),
                        "change_pct": float(row.get("涨跌幅", 0) or 0),
                        "total_market_cap": float(row.get("总市值", 0) or 0),
                        "turnover_rate": float(row.get("换手率", 0) or 0),
                        "advancers": int(row.get("上涨家数", 0) or 0),
                        "decliners": int(row.get("下跌家数", 0) or 0),
                        "lead_stock": str(row.get("领涨股票", "")),
                    })
                _cache_set(_realtime_cache, cache_key, sectors, ttl=120)
                return sectors
        except Exception as e:
            logger.debug(f"Sector data fetch failed: {e}")
        return []

    async def get_financial_data(self, symbol: str) -> list:
        cache_key = f"financial:{symbol}"
        cached = _cache_get(_realtime_cache, cache_key)
        if cached is not None:
            return cached
        try:
            db = get_db()
            db_data = db.get_financials(symbol)
            if db_data:
                _cache_set(_realtime_cache, cache_key, db_data, ttl=3600)
                return db_data
        except Exception:
            pass
        try:
            import akshare as ak
            _AKSHARE_BUCKET.wait()
            market = MarketDetector.detect(symbol)
            if market == "A":
                df = ak.stock_financial_abstract_ths(symbol=symbol, indicator="按年度")
                if df is not None and not df.empty:
                    rows = []
                    for _, row in df.head(5).iterrows():
                        rows.append(dict(row))
                    _cache_set(_realtime_cache, cache_key, rows, ttl=3600)
                    return rows
        except Exception as e:
            logger.debug(f"Financial data fetch failed for {symbol}: {e}")
        return []

    async def refresh_stock_info(self):
        try:
            from core.market_data import get_stock_list
            for market in ("A",):
                get_stock_list(market, force_refresh=True)
        except Exception:
            pass


def _normalize(df: pd.DataFrame, market: str = "A") -> pd.DataFrame:
    col_map = {
        "日期": "date", "时间": "date", "date": "date", "datetime": "date", "day": "date",
        "开盘": "open", "open": "open",
        "收盘": "close", "close": "close",
        "最高": "high", "high": "high",
        "最低": "low", "low": "low",
        "成交量": "volume", "volume": "volume",
        "成交额": "amount",
    }
    df = df.rename(columns={k: v for k, v in col_map.items() if k in df.columns})
    keep_cols = [c for c in ["date", "open", "high", "low", "close", "volume", "amount"] if c in df.columns]
    df = df[keep_cols]
    for c in ["open", "high", "low", "close", "volume"]:
        if c in df.columns:
            df[c] = pd.to_numeric(df[c], errors="coerce")
    if "date" in df.columns:
        df["date"] = pd.to_datetime(df["date"], errors="coerce")
        df = df.dropna(subset=["date"])
        df = df.sort_values("date").reset_index(drop=True)
    for c in ["open", "high", "low", "close", "volume"]:
        if c in df.columns:
            df[c] = df[c].replace([None, ""], np.nan)
    df = df.dropna(subset=["close"])
    df = df[df["close"] != 0]
    df = df[~df["close"].isna()]
    return df


def _default_hot_stocks() -> list:
    return [
        {"code": "000001", "name": "平安银行", "price": 0, "pct": 0, "change": 0, "volume": 0},
        {"code": "600519", "name": "贵州茅台", "price": 0, "pct": 0, "change": 0, "volume": 0},
        {"code": "000858", "name": "五粮液", "price": 0, "pct": 0, "change": 0, "volume": 0},
        {"code": "601318", "name": "中国平安", "price": 0, "pct": 0, "change": 0, "volume": 0},
        {"code": "600036", "name": "招商银行", "price": 0, "pct": 0, "change": 0, "volume": 0},
        {"code": "000333", "name": "美的集团", "price": 0, "pct": 0, "change": 0, "volume": 0},
        {"code": "002594", "name": "比亚迪", "price": 0, "pct": 0, "change": 0, "volume": 0},
        {"code": "601012", "name": "隆基绿能", "price": 0, "pct": 0, "change": 0, "volume": 0},
    ]
