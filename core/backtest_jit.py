"""
core/backtest_jit.py — Numba JIT-accelerated backtest computations.

This module provides drop-in JIT replacements for hot-path functions
in the backtesting engine. When numba is unavailable (e.g. CI without
LLVM), all functions fall back to pure NumPy equivalents.

Key hot paths accelerated:
  - Vectorized equity curve computation
  - Drawdown envelope computation
  - Max drawdown
  - Rolling Sharpe ratio

Usage:
    from core.backtest_jit import compute_equity_curve, compute_drawdowns

    equity = compute_equity_curve(equity, entry_indices, exit_indices, pnl_array, n_bars)
"""
from __future__ import annotations

import logging

logger = logging.getLogger(__name__)

try:
    from numba import njit
    _NUMBA_AVAILABLE = True
except ImportError:
    _NUMBA_AVAILABLE = False
    logger.debug("numba not available — using NumPy fallbacks for backtest_jit")


if _NUMBA_AVAILABLE:
    @njit(cache=True, fastmath=True)
    def _jit_equity_loop(
        n_bars: int,
        equity: float,
        entry_indices,
        exit_indices,
        pnl_array,
    ):
        equity_curve = [0.0] * (n_bars + 1)
        equity_curve[0] = equity

        for bar in range(1, n_bars + 1):
            cumulative = 0.0
            for t in range(len(entry_indices)):
                entry = entry_indices[t]
                exit_bar = exit_indices[t]
                pnl = pnl_array[t]
                if entry < bar <= exit_bar:
                    cumulative += pnl
            equity_curve[bar] = equity + cumulative

        return equity_curve


    @njit(cache=True, fastmath=True)
    def _jit_drawdown_envelope(equity_curve):
        n = len(equity_curve)
        drawdown = [0.0] * n
        peak = [0.0] * n
        peak_idx = [0] * n

        peak_equity = equity_curve[0]
        peak_index = 0

        for i in range(n):
            if equity_curve[i] > peak_equity:
                peak_equity = equity_curve[i]
                peak_index = i

            peak[i] = peak_equity
            peak_idx[i] = peak_index

            if peak_equity > 0:
                drawdown[i] = (equity_curve[i] - peak_equity) / peak_equity
            else:
                drawdown[i] = 0.0

        return drawdown, peak, peak_idx


    @njit(cache=True, fastmath=True)
    def _jit_max_drawdown(equity_curve):
        if len(equity_curve) < 2:
            return 0.0

        peak = equity_curve[0]
        max_dd = 0.0

        for i in range(len(equity_curve)):
            if equity_curve[i] > peak:
                peak = equity_curve[i]
            dd = (equity_curve[i] - peak) / peak if peak > 0 else 0.0
            if dd < max_dd:
                max_dd = dd

        return max_dd


    @njit(cache=True, fastmath=True)
    def _jit_rolling_sharpe(
        returns,
        window: int,
        risk_free: float,
    ):
        n = len(returns)
        result = [0.0] * n

        if n < window:
            return result

        for i in range(window, n):
            window_returns = returns[i - window:i]
            mean_ret = 0.0
            var_ret = 0.0
            for j in range(window):
                mean_ret += window_returns[j]
            mean_ret /= window

            for j in range(window):
                diff = window_returns[j] - mean_ret
                var_ret += diff * diff
            std_ret = var_ret ** 0.5

            if std_ret > 1e-12:
                excess = mean_ret - risk_free / 252
                result[i] = excess / std_ret * (252 ** 0.5)
            else:
                result[i] = 0.0

        return result
else:
    _jit_equity_loop = None
    _jit_drawdown_envelope = None
    _jit_max_drawdown = None
    _jit_rolling_sharpe = None


def compute_equity_curve(
    equity: float,
    entry_indices: list[int],
    exit_indices: list[int],
    pnl_array: list[float],
    n_bars: int,
) -> list[float]:
    """Drop-in JIT-accelerated equity curve computation.

    Falls back to pure NumPy if numba unavailable.
    """
    import numpy as np

    if not _NUMBA_AVAILABLE or len(entry_indices) == 0:
        return _numpy_equity_fallback(equity, entry_indices, exit_indices, pnl_array, n_bars)

    entry_arr = np.array(entry_indices, dtype=np.int32)
    exit_arr = np.array(exit_indices, dtype=np.int32)
    pnl_arr = np.array(pnl_array, dtype=np.float64)

    return list(_jit_equity_loop(n_bars, equity, entry_arr, exit_arr, pnl_arr))


def compute_drawdowns(equity_curve: list[float]) -> tuple[list[float], list[float], list[int]]:
    """Drop-in JIT-accelerated drawdown envelope computation.

    Falls back to pure NumPy if numba unavailable.
    """
    import numpy as np

    eq_arr = np.array(equity_curve, dtype=np.float64)

    if not _NUMBA_AVAILABLE:
        return _numpy_drawdown_fallback(eq_arr)

    dd, peak, peak_idx = _jit_drawdown_envelope(eq_arr)
    return list(dd), list(peak), list(peak_idx)


def max_drawdown(equity_curve: list[float]) -> float:
    """Drop-in JIT-accelerated max drawdown computation."""
    import numpy as np

    eq_arr = np.array(equity_curve, dtype=np.float64)

    if not _NUMBA_AVAILABLE:
        return _numpy_max_dd_fallback(eq_arr)

    return float(_jit_max_drawdown(eq_arr))


def rolling_sharpe(
    returns: list[float],
    window: int = 60,
    risk_free: float = 0.03,
) -> list[float]:
    """Drop-in JIT-accelerated rolling Sharpe ratio."""
    import numpy as np

    ret_arr = np.array(returns, dtype=np.float64)

    if not _NUMBA_AVAILABLE:
        return _numpy_rolling_sharpe_fallback(ret_arr, window, risk_free)

    result = _jit_rolling_sharpe(ret_arr, window, risk_free)
    return list(result)


def _numpy_equity_fallback(
    equity: float,
    entry_indices: list[int],
    exit_indices: list[int],
    pnl_array: list[float],
    n_bars: int,
) -> list[float]:
    """Pure NumPy fallback when numba is unavailable."""
    if n_bars <= 0:
        return [equity]

    import numpy as np

    equity_curve = np.zeros(n_bars + 1, dtype=np.float64)
    equity_curve[0] = equity

    for entry, exit_bar, pnl in zip(entry_indices, exit_indices, pnl_array, strict=True):
        if 0 <= entry < n_bars and entry < exit_bar:
            for bar in range(entry + 1, min(exit_bar + 1, n_bars + 1)):
                equity_curve[bar] += pnl

    return list(equity_curve + equity)


def _numpy_drawdown_fallback(equity_curve) -> tuple[list[float], list[float], list[int]]:
    """Pure NumPy drawdown fallback."""
    import numpy as np

    eq_arr = np.asarray(equity_curve, dtype=np.float64)
    peak = np.maximum.accumulate(eq_arr)
    drawdown = (eq_arr - peak) / np.where(peak > 0, peak, 1.0)

    peak_indices = [0] * len(eq_arr)
    current_max_idx = 0
    for i in range(len(eq_arr)):
        if eq_arr[i] > eq_arr[current_max_idx]:
            current_max_idx = i
        peak_indices[i] = current_max_idx

    return (
        [float(d) for d in drawdown],
        [float(p) for p in peak],
        peak_indices,
    )


def _numpy_max_dd_fallback(equity_curve) -> float:
    """Pure NumPy max drawdown fallback."""
    import numpy as np

    eq_arr = np.asarray(equity_curve, dtype=np.float64)
    peak = np.maximum.accumulate(eq_arr)
    drawdown = (eq_arr - peak) / np.where(peak > 0, peak, 1.0)
    return float(drawdown.min())


def _numpy_rolling_sharpe_fallback(
    returns,
    window: int,
    risk_free: float,
) -> list[float]:
    """Pure NumPy rolling Sharpe fallback using pandas rolling."""
    import pandas as pd

    ret_series = pd.Series(returns)
    rolling_mean = ret_series.rolling(window).mean()
    rolling_std = ret_series.rolling(window).std()
    excess = rolling_mean - risk_free / 252
    sharpe = excess / rolling_std * (252 ** 0.5)
    result = sharpe.fillna(0.0).to_numpy()
    return [float(x) for x in result]
