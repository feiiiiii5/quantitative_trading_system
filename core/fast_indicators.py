"""
QuantCore 技术指标引擎 - 高性能版
numpy向量化 + Numba JIT加速
10万根K线指标计算 < 100ms
"""
import logging
from typing import Dict, Tuple

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)

_NUMBA_AVAILABLE = False
try:
    from numba import jit
    _NUMBA_AVAILABLE = True
except ImportError:
    pass


def _jit(func):
    if _NUMBA_AVAILABLE:
        return jit(nopython=True, cache=True, fastmath=True)(func)
    return func


@_jit
def _ema_numba(arr: np.ndarray, span: int) -> np.ndarray:
    n = len(arr)
    result = np.empty(n)
    alpha = 2.0 / (span + 1)
    result[0] = arr[0]
    for i in range(1, n):
        result[i] = alpha * arr[i] + (1 - alpha) * result[i - 1]
    return result


@_jit
def _sma_numba(arr: np.ndarray, period: int) -> np.ndarray:
    n = len(arr)
    result = np.empty(n)
    result[:period] = np.nan
    s = 0.0
    for i in range(period):
        s += arr[i]
    result[period - 1] = s / period
    for i in range(period, n):
        s += arr[i] - arr[i - period]
        result[i] = s / period
    return result


@_jit
def _atr_numba(h: np.ndarray, low_arr: np.ndarray, c: np.ndarray, period: int) -> np.ndarray:
    n = len(h)
    tr = np.empty(n)
    tr[0] = h[0] - low_arr[0]
    for i in range(1, n):
        a = h[i] - low_arr[i]
        b = abs(h[i] - c[i - 1])
        d = abs(low_arr[i] - c[i - 1])
        tr[i] = max(a, max(b, d))
    return _ema_numba(tr, period)


@_jit
def _rsi_numba(c: np.ndarray, period: int) -> np.ndarray:
    n = len(c)
    result = np.empty(n)
    result[:period] = np.nan
    avg_gain = 0.0
    avg_loss = 0.0
    for i in range(1, period + 1):
        diff = c[i] - c[i - 1]
        if diff > 0:
            avg_gain += diff
        else:
            avg_loss += abs(diff)
    avg_gain /= period
    avg_loss /= period
    if avg_loss == 0:
        result[period] = 100.0
    else:
        result[period] = 100 - 100 / (1 + avg_gain / avg_loss)
    for i in range(period + 1, n):
        diff = c[i] - c[i - 1]
        gain = diff if diff > 0 else 0.0
        loss = abs(diff) if diff < 0 else 0.0
        avg_gain = (avg_gain * (period - 1) + gain) / period
        avg_loss = (avg_loss * (period - 1) + loss) / period
        if avg_loss == 0:
            result[i] = 100.0
        else:
            result[i] = 100 - 100 / (1 + avg_gain / avg_loss)
    return result


@_jit
def _macd_numba(c: np.ndarray, fast: int, slow: int, signal: int) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
    ema_fast = _ema_numba(c, fast)
    ema_slow = _ema_numba(c, slow)
    dif = ema_fast - ema_slow
    dea = _ema_numba(dif, signal)
    hist = (dif - dea) * 2
    return dif, dea, hist


@_jit
def _kdj_numba(h: np.ndarray, low_arr: np.ndarray, c: np.ndarray, n: int, m1: int, m2: int) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
    length = len(c)
    k = np.full(length, 50.0)
    d = np.full(length, 50.0)
    for i in range(n - 1, length):
        hh = h[i]
        ll = low_arr[i]
        for j in range(i - n + 1, i):
            if h[j] > hh:
                hh = h[j]
            if low_arr[j] < ll:
                ll = low_arr[j]
        rsv = (c[i] - ll) / (hh - ll) * 100 if hh != ll else 50.0
        k[i] = (2.0 / m1) * k[i - 1] + (1.0 / m1) * rsv
        d[i] = (2.0 / m2) * d[i - 1] + (1.0 / m2) * k[i]
    j = 3 * k - 2 * d
    return k, d, j


@_jit
def _boll_numba(c: np.ndarray, period: int, nbdev: float) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
    n = len(c)
    mid = _sma_numba(c, period)
    upper = np.empty(n)
    lower = np.empty(n)
    for i in range(period - 1, n):
        s = 0.0
        for j in range(i - period + 1, i + 1):
            s += (c[j] - mid[i]) ** 2
        std = (s / period) ** 0.5
        upper[i] = mid[i] + nbdev * std
        lower[i] = mid[i] - nbdev * std
    upper[:period - 1] = np.nan
    lower[:period - 1] = np.nan
    return mid, upper, lower


@_jit
def _williams_r_numba(h: np.ndarray, low_arr: np.ndarray, c: np.ndarray, period: int) -> np.ndarray:
    n = len(c)
    result = np.empty(n)
    result[:period - 1] = np.nan
    for i in range(period - 1, n):
        hh = h[i]
        ll = low_arr[i]
        for j in range(i - period + 1, i):
            if h[j] > hh:
                hh = h[j]
            if low_arr[j] < ll:
                ll = low_arr[j]
        result[i] = (hh - c[i]) / (hh - ll) * -100 if hh != ll else -50.0
    return result


@_jit
def _cci_numba(h: np.ndarray, low_arr: np.ndarray, c: np.ndarray, period: int) -> np.ndarray:
    n = len(c)
    tp = (h + low_arr + c) / 3
    result = np.empty(n)
    result[:period - 1] = np.nan
    for i in range(period - 1, n):
        ma = 0.0
        for j in range(i - period + 1, i + 1):
            ma += tp[j]
        ma /= period
        md = 0.0
        for j in range(i - period + 1, i + 1):
            md += abs(tp[j] - ma)
        md /= period
        result[i] = (tp[i] - ma) / (0.015 * md) if md != 0 else 0.0
    return result


@_jit
def _obv_numba(c: np.ndarray, v: np.ndarray) -> np.ndarray:
    n = len(c)
    result = np.empty(n)
    result[0] = v[0]
    for i in range(1, n):
        if c[i] > c[i - 1]:
            result[i] = result[i - 1] + v[i]
        elif c[i] < c[i - 1]:
            result[i] = result[i - 1] - v[i]
        else:
            result[i] = result[i - 1]
    return result


@_jit
def _vwap_numba(h: np.ndarray, low_arr: np.ndarray, c: np.ndarray, v: np.ndarray) -> np.ndarray:
    n = len(c)
    tp = (h + low_arr + c) / 3
    cum_tp_v = np.empty(n)
    cum_v = np.empty(n)
    cum_tp_v[0] = tp[0] * v[0]
    cum_v[0] = v[0]
    for i in range(1, n):
        cum_tp_v[i] = cum_tp_v[i - 1] + tp[i] * v[i]
        cum_v[i] = cum_v[i - 1] + v[i]
    result = np.empty(n)
    for i in range(n):
        result[i] = cum_tp_v[i] / cum_v[i] if cum_v[i] != 0 else c[i]
    return result


@_jit
def _supertrend_numba(h: np.ndarray, low_arr: np.ndarray, c: np.ndarray,
                      period: int, multiplier: float) -> Tuple[np.ndarray, np.ndarray]:
    n = len(c)
    atr = _atr_numba(h, low_arr, c, period)
    hl2 = (h + low_arr) / 2
    upper = hl2 + multiplier * atr
    lower = hl2 - multiplier * atr
    direction = np.ones(n)
    for i in range(1, n):
        if np.isnan(atr[i]):
            direction[i] = direction[i - 1]
            continue
        if not (lower[i] > lower[i - 1] or c[i - 1] < lower[i - 1]):
            lower[i] = lower[i - 1]
        if not (upper[i] < upper[i - 1] or c[i - 1] > upper[i - 1]):
            upper[i] = upper[i - 1]
        if direction[i - 1] == 1:
            direction[i] = -1 if c[i] < lower[i] else 1
        else:
            direction[i] = 1 if c[i] > upper[i] else -1
    st = np.where(direction == 1, lower, upper)
    return st, direction


class FastIndicators:
    """高性能技术指标计算引擎"""

    @staticmethod
    def ma(close: np.ndarray, period: int) -> np.ndarray:
        return _sma_numba(close.astype(np.float64), period)

    @staticmethod
    def ema(close: np.ndarray, span: int) -> np.ndarray:
        return _ema_numba(close.astype(np.float64), span)

    @staticmethod
    def macd(close: np.ndarray, fast: int = 12, slow: int = 26, signal: int = 9) -> Dict[str, np.ndarray]:
        dif, dea, hist = _macd_numba(close.astype(np.float64), fast, slow, signal)
        return {"dif": dif, "dea": dea, "hist": hist}

    @staticmethod
    def rsi(close: np.ndarray, period: int = 14) -> np.ndarray:
        return _rsi_numba(close.astype(np.float64), period)

    @staticmethod
    def kdj(high: np.ndarray, low: np.ndarray, close: np.ndarray,
            n: int = 9, m1: int = 3, m2: int = 3) -> Dict[str, np.ndarray]:
        k, d, j = _kdj_numba(high.astype(np.float64), low.astype(np.float64),
                              close.astype(np.float64), n, m1, m2)
        return {"k": k, "d": d, "j": j}

    @staticmethod
    def boll(close: np.ndarray, period: int = 20, nbdev: float = 2.0) -> Dict[str, np.ndarray]:
        mid, upper, lower = _boll_numba(close.astype(np.float64), period, nbdev)
        return {"mid": mid, "upper": upper, "lower": lower}

    @staticmethod
    def atr(high: np.ndarray, low: np.ndarray, close: np.ndarray, period: int = 14) -> np.ndarray:
        return _atr_numba(high.astype(np.float64), low.astype(np.float64),
                          close.astype(np.float64), period)

    @staticmethod
    def williams_r(high: np.ndarray, low: np.ndarray, close: np.ndarray,
                   period: int = 14) -> np.ndarray:
        return _williams_r_numba(high.astype(np.float64), low.astype(np.float64),
                                 close.astype(np.float64), period)

    @staticmethod
    def cci(high: np.ndarray, low: np.ndarray, close: np.ndarray,
            period: int = 14) -> np.ndarray:
        return _cci_numba(high.astype(np.float64), low.astype(np.float64),
                          close.astype(np.float64), period)

    @staticmethod
    def obv(close: np.ndarray, volume: np.ndarray) -> np.ndarray:
        return _obv_numba(close.astype(np.float64), volume.astype(np.float64))

    @staticmethod
    def vwap(high: np.ndarray, low: np.ndarray, close: np.ndarray,
             volume: np.ndarray) -> np.ndarray:
        return _vwap_numba(high.astype(np.float64), low.astype(np.float64),
                           close.astype(np.float64), volume.astype(np.float64))

    @staticmethod
    def supertrend(high: np.ndarray, low: np.ndarray, close: np.ndarray,
                   period: int = 10, multiplier: float = 3.0) -> Dict[str, np.ndarray]:
        st, direction = _supertrend_numba(high.astype(np.float64), low.astype(np.float64),
                                          close.astype(np.float64), period, multiplier)
        return {"supertrend": st, "direction": direction}

    @staticmethod
    def compute_all(df: pd.DataFrame) -> Dict[str, np.ndarray]:
        """一次性计算所有常用指标"""
        c = df["close"].values.astype(np.float64)
        h = df["high"].values.astype(np.float64) if "high" in df.columns else c
        low_arr = df["low"].values.astype(np.float64) if "low" in df.columns else c
        v = df["volume"].values.astype(np.float64) if "volume" in df.columns else np.ones(len(c))

        result = {}
        for p in [5, 10, 20, 60, 120, 250]:
            if len(c) >= p:
                result[f"ma{p}"] = _sma_numba(c, p)
        result["ema12"] = _ema_numba(c, 12)
        result["ema26"] = _ema_numba(c, 26)

        macd_data = FastIndicators.macd(c)
        result["macd_dif"] = macd_data["dif"]
        result["macd_dea"] = macd_data["dea"]
        result["macd_hist"] = macd_data["hist"]

        result["rsi14"] = _rsi_numba(c, 14)
        result["rsi6"] = _rsi_numba(c, 6)

        kdj_data = FastIndicators.kdj(h, low_arr, c)
        result["kdj_k"] = kdj_data["k"]
        result["kdj_d"] = kdj_data["d"]
        result["kdj_j"] = kdj_data["j"]

        boll_data = FastIndicators.boll(c)
        result["boll_mid"] = boll_data["mid"]
        result["boll_upper"] = boll_data["upper"]
        result["boll_lower"] = boll_data["lower"]

        result["atr14"] = _atr_numba(h, low_arr, c, 14)
        result["willr"] = _williams_r_numba(h, low_arr, c, 14)
        result["cci"] = _cci_numba(h, low_arr, c, 14)
        result["obv"] = _obv_numba(c, v)
        result["vwap"] = _vwap_numba(h, low_arr, c, v)

        st_data = FastIndicators.supertrend(h, low_arr, c)
        result["supertrend"] = st_data["supertrend"]
        result["st_direction"] = st_data["direction"]

        return result
