import asyncio
import logging
import re
import time
from collections import OrderedDict
from datetime import datetime, timedelta
from typing import Optional

import numpy as np
import pandas as pd
import requests

from core.market_detector import MarketDetector
from core.stock_search import get_stock_name

logger = logging.getLogger(__name__)

PERIOD_MAP = {
    "1d": timedelta(days=5),
    "1w": timedelta(weeks=2),
    "1m": timedelta(days=35),
    "3m": timedelta(days=95),
    "6m": timedelta(days=185),
    "1y": timedelta(days=370),
    "all": None,
}

_MAX_CACHE_SIZE = 200
_history_cache: OrderedDict = OrderedDict()
_realtime_cache: OrderedDict = OrderedDict()
_HIST_CACHE_TTL = 120
_RT_CACHE_TTL = 15

_UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"

_global_session = None

def _get_session() -> requests.Session:
    global _global_session
    if _global_session is None:
        from requests.adapters import HTTPAdapter
        from urllib3.util.retry import Retry
        _global_session = requests.Session()
        retry_strategy = Retry(
            total=3,
            backoff_factor=1,
            status_forcelist=[429, 500, 502, 503, 504],
        )
        adapter = HTTPAdapter(max_retries=retry_strategy)
        _global_session.mount("http://", adapter)
        _global_session.mount("https://", adapter)
    return _global_session

_EM_HEADERS = {
    "User-Agent": _UA,
    "Referer": "https://quote.eastmoney.com/",
    "Accept": "*/*",
}

_SINA_HEADERS = {
    "User-Agent": _UA,
    "Referer": "https://finance.sina.com.cn/",
}

_TENCENT_HEADERS = {
    "User-Agent": _UA,
    "Referer": "https://guojijj.com/",
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


def _http_get(url: str, params: dict = None, headers: dict = None, timeout: int = 8) -> Optional[requests.Response]:
    try:
        session = _get_session()
        resp = session.get(url, params=params, headers=headers, timeout=timeout)
        if resp.status_code == 200:
            return resp
        logger.debug(f"HTTP {resp.status_code} from {url}")
    except requests.exceptions.ConnectionError as e:
        logger.debug(f"Connection error for {url}: {e}")
    except requests.exceptions.Timeout:
        logger.debug(f"Timeout for {url}")
    except requests.exceptions.ChunkedEncodingError:
        logger.debug(f"Chunked encoding error for {url}")
    except Exception as e:
        logger.debug(f"HTTP error for {url}: {e}")
    return None


def _safe_float(val, default=0.0) -> float:
    try:
        if val is None or val == "" or val == "-":
            return default
        v = float(val)
        return v if not np.isnan(v) else default
    except (ValueError, TypeError):
        return default


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


class SinaSource:
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
    def fetch_history(code: str, market: str, start: str, end: str) -> Optional[pd.DataFrame]:
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


class TencentSource:
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
    def fetch_history(code: str, market: str, start: str, end: str) -> Optional[pd.DataFrame]:
        try:
            if market == "A":
                prefix = "sh" if code.startswith(("6", "9")) else "sz"
                qt_code = f"{prefix}{code}"
            elif market == "HK":
                qt_code = f"hk{code}"
            else:
                return None

            url = f"http://web.ifzq.gtimg.cn/appstock/app/fqkline/get?param={qt_code},day,,,500,qfq"
            resp = _http_get(url, headers=_TENCENT_HEADERS, timeout=10)
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


class EastMoneySource:
    NAME = "东方财富"

    _circuits = {"realtime": {"open": False, "until": 0},
                 "history": {"open": False, "until": 0},
                 "hot": {"open": False, "until": 0}}

    @classmethod
    def _check_circuit(cls, endpoint: str) -> bool:
        c = cls._circuits.get(endpoint, {"open": False, "until": 0})
        if c["open"]:
            if time.time() >= c["until"]:
                c["open"] = False
                return True
            return False
        return True

    @classmethod
    def _trip_circuit(cls, endpoint: str, cooldown: int = 60):
        c = cls._circuits.setdefault(endpoint, {"open": False, "until": 0})
        c["open"] = True
        c["until"] = time.time() + cooldown
        logger.info(f"EastMoney {endpoint} circuit tripped, cooldown {cooldown}s")

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
            resp = _http_get(url, params=params, headers=_EM_HEADERS, timeout=5)
            if resp:
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
                    return result
            EastMoneySource._trip_circuit("realtime", 60)
        except Exception as e:
            logger.debug(f"EastMoney realtime error for {code}: {e}")
            EastMoneySource._trip_circuit("realtime", 60)
        return None

    @staticmethod
    def fetch_history(code: str, market: str, start: str, end: str) -> Optional[pd.DataFrame]:
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
            params = {
                "secid": secid,
                "fields1": "f1,f2,f3,f4,f5,f6",
                "fields2": "f51,f52,f53,f54,f55,f56,f57",
                "klt": "101",
                "fqt": "1",
                "beg": start,
                "end": end,
                "ut": "fa5fd1943c7b386f172d6893dbfba10b",
            }
            resp = _http_get(url, params=params, headers=_EM_HEADERS, timeout=10)
            if resp:
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
                        return pd.DataFrame(rows)
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
            resp = _http_get(url, params=params, headers=_EM_HEADERS, timeout=8)
            if resp:
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
                        return result[:8]
            EastMoneySource._trip_circuit("hot", 60)
        except Exception as e:
            logger.debug(f"EastMoney hot stocks error: {e}")
            EastMoneySource._trip_circuit("hot", 60)
        return None


class AkshareSource:
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
        except Exception as e:
            logger.debug(f"Akshare realtime error for {code}: {e}")
            AkshareSource.mark_failed(30)
        return None

    @staticmethod
    def fetch_history(code: str, market: str, start: str, end: str) -> Optional[pd.DataFrame]:
        if not AkshareSource.is_available():
            return None
        try:
            import akshare as ak
            if market == "A":
                return _akshare_retry(ak.stock_zh_a_hist, symbol=code, period="daily",
                                      start_date=start, end_date=end, adjust="qfq")
            elif market == "HK":
                return _akshare_retry(ak.stock_hk_hist, symbol=code, period="daily",
                                      start_date=start, end_date=end, adjust="qfq")
            elif market == "US":
                return _akshare_retry(ak.stock_us_hist, symbol=code, period="daily",
                                      start_date=start, end_date=end, adjust="qfq")
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


class BaostockSource:
    NAME = "Baostock"

    def __init__(self):
        self._connected = False

    def _ensure_connected(self):
        if self._connected:
            return True
        try:
            import baostock as bs
            lg = bs.login()
            if lg.error_code == "0":
                self._connected = True
                return True
            logger.debug(f"Baostock login failed: {lg.error_msg}")
        except Exception as e:
            logger.debug(f"Baostock login error: {e}")
        return False

    def fetch_realtime(self, code: str, market: str) -> Optional[dict]:
        if market != "A":
            return None
        try:
            if not self._ensure_connected():
                return None
            import baostock as bs
            prefix = "sh" if code.startswith("6") else "sz"
            end = datetime.now().strftime("%Y-%m-%d")
            start = (datetime.now() - timedelta(days=10)).strftime("%Y-%m-%d")
            rs = bs.query_history_k_data_plus(
                f"{prefix}.{code}",
                "date,open,high,low,close,volume",
                start_date=start,
                end_date=end,
                frequency="d",
                adjustflag="3",
            )
            if rs is None:
                return None
            rows = []
            while rs.next():
                rows.append(rs.get_row_data())
            if not rows:
                return None
            r = rows[-1]
            close = float(r[4]) if r[4] else 0
            open_ = float(r[1]) if r[1] else 0
            prev_close = float(rows[-2][4]) if len(rows) >= 2 and rows[-2][4] else open_
            change = round(close - prev_close, 2)
            pct = round(change / prev_close * 100, 2) if prev_close else 0
            return {
                "price": close,
                "change": change,
                "pct": pct,
                "volume": float(r[5]) if r[5] else 0,
                "high": float(r[2]) if r[2] else 0,
                "low": float(r[3]) if r[3] else 0,
                "open": open_,
                "prev_close": prev_close,
                "time": r[0] if r[0] else "",
            }
        except Exception as e:
            logger.debug(f"Baostock realtime error: {e}")
        return None

    def fetch_history(self, code: str, market: str, start: str, end: str) -> Optional[pd.DataFrame]:
        if market != "A":
            return None
        try:
            if not self._ensure_connected():
                return None
            import baostock as bs
            prefix = "sh" if code.startswith("6") else "sz"
            bs_code = f"{prefix}.{code}"
            start_fmt = f"{start[:4]}-{start[4:6]}-{start[6:8]}"
            end_fmt = f"{end[:4]}-{end[4:6]}-{end[6:8]}"
            rs = bs.query_history_k_data_plus(
                bs_code,
                "date,open,high,low,close,volume",
                start_date=start_fmt,
                end_date=end_fmt,
                frequency="d",
                adjustflag="2",
            )
            if rs is None:
                return None
            rows = []
            while rs.next():
                rows.append(rs.get_row_data())
            if rows:
                df = pd.DataFrame(rows, columns=rs.fields)
                for c in ["open", "high", "low", "close", "volume"]:
                    df[c] = pd.to_numeric(df[c], errors="coerce")
                return df
        except Exception as e:
            logger.debug(f"Baostock history error: {e}")
        return None


def _akshare_retry(func, *args, **kwargs):
    for i in range(3):
        try:
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
        self._bs = BaostockSource()
        self._source_stats: dict = {}

    def _record_source(self, source: str, success: bool):
        key = source
        if key not in self._source_stats:
            self._source_stats[key] = {"ok": 0, "fail": 0}
        if success:
            self._source_stats[key]["ok"] += 1
        else:
            self._source_stats[key]["fail"] += 1

    def _get_realtime_sources(self, market: str) -> list:
        sources = [
            ("tencent", TencentSource.fetch_realtime),
            ("eastmoney", EastMoneySource.fetch_realtime),
            ("sina", SinaSource.fetch_realtime),
            ("akshare", AkshareSource.fetch_realtime),
        ]
        if market == "A":
            sources.append(("baostock", self._bs.fetch_realtime))
        return sources

    def _get_history_sources(self, market: str) -> list:
        sources = [
            ("tencent", TencentSource.fetch_history),
            ("eastmoney", EastMoneySource.fetch_history),
            ("sina", SinaSource.fetch_history),
            ("akshare", AkshareSource.fetch_history),
        ]
        if market == "A":
            sources.append(("baostock", self._bs.fetch_history))
        return sources

    async def get_history(self, symbol: str, period: str = "1y") -> pd.DataFrame:
        cache_key = f"{symbol}:{period}"
        cached = _cache_get(_history_cache, cache_key)
        if cached is not None:
            return cached.copy()

        market = MarketDetector.detect(symbol)
        norm = MarketDetector.normalize_symbol(symbol)
        delta = PERIOD_MAP.get(period, timedelta(days=370))
        end_date = datetime.now().strftime("%Y%m%d")
        start_date = (datetime.now() - delta).strftime("%Y%m%d") if delta else "19900101"

        sources = self._get_history_sources(market)
        for name, fetch_fn in sources:
            try:
                df = await asyncio.to_thread(fetch_fn, norm, market, start_date, end_date)
                if df is not None and not df.empty:
                    result = _normalize(df)
                    if _validate_history_df(result):
                        _cache_set(_history_cache, cache_key, result.copy(), ttl=_HIST_CACHE_TTL)
                        self._record_source(name, True)
                        logger.info(f"History data for {symbol} from {name}")
                        return result
            except Exception as e:
                logger.debug(f"Source {name} history failed for {symbol}: {e}")
                self._record_source(name, False)

        logger.warning(f"All history sources failed for {symbol}")
        return pd.DataFrame()

    async def get_realtime(self, symbol: str) -> dict:
        cache_key = symbol
        cached = _cache_get(_realtime_cache, cache_key)
        if cached is not None:
            return cached

        market = MarketDetector.detect(symbol)
        norm = MarketDetector.normalize_symbol(symbol)

        sources = self._get_realtime_sources(market)
        for name, fetch_fn in sources:
            try:
                data = await asyncio.to_thread(fetch_fn, norm, market)
                if data and _validate_realtime(data):
                    if not data.get("name"):
                        db_name = get_stock_name(symbol)
                        if db_name:
                            data["name"] = db_name
                    _cache_set(_realtime_cache, cache_key, data, ttl=_RT_CACHE_TTL)
                    self._record_source(name, True)
                    logger.info(f"Realtime data for {symbol} from {name}")
                    return data
            except Exception as e:
                logger.debug(f"Source {name} realtime failed for {symbol}: {e}")
                self._record_source(name, False)

        if cache_key in _realtime_cache:
            return _realtime_cache[cache_key]["data"]

        db_name = get_stock_name(symbol)
        fallback = {"name": db_name or symbol}
        logger.warning(f"All realtime sources failed for {symbol}")
        return fallback

    async def get_fundamentals(self, symbol: str, market: str) -> dict:
        if market != "A":
            return {}
        try:
            import akshare as ak
            norm = MarketDetector.normalize_symbol(symbol)
            df = _akshare_retry(ak.stock_individual_info_em, symbol=norm)
            if df is not None and not df.empty:
                result = {}
                for _, row in df.iterrows():
                    result[str(row.iloc[0])] = str(row.iloc[1])
                return result
        except Exception as e:
            logger.debug(f"Fundamentals fetch failed: {e}")
        return {}

    async def get_hot_stocks(self) -> list:
        try:
            data = await asyncio.to_thread(EastMoneySource.fetch_hot_stocks)
            if data:
                return data
        except Exception as e:
            logger.debug(f"EastMoney hot stocks failed: {e}")

        try:
            data = await asyncio.to_thread(AkshareSource.fetch_hot_stocks)
            if data:
                return data
        except Exception as e:
            logger.debug(f"Akshare hot stocks failed: {e}")

        try:
            data = await asyncio.to_thread(TencentSource.fetch_hot_stocks)
            if data:
                return data
        except Exception as e:
            logger.debug(f"Tencent hot stocks failed: {e}")

        return _default_hot_stocks()


def _normalize(df: pd.DataFrame) -> pd.DataFrame:
    col_map = {
        "日期": "date", "date": "date",
        "开盘": "open", "open": "open",
        "收盘": "close", "close": "close",
        "最高": "high", "high": "high",
        "最低": "low", "low": "low",
        "成交量": "volume", "volume": "volume",
    }
    df = df.rename(columns={k: v for k, v in col_map.items() if k in df.columns})
    for c in ["open", "high", "low", "close", "volume"]:
        if c in df.columns:
            df[c] = pd.to_numeric(df[c], errors="coerce")
    if "date" in df.columns:
        df["date"] = pd.to_datetime(df["date"])
        df = df.sort_values("date").reset_index(drop=True)
    df = df.dropna(subset=["close"])
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
