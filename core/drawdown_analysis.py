import logging
from dataclasses import dataclass, field
from typing import Any

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)


@dataclass
class DrawdownPeriod:
    peak_idx: int
    trough_idx: int
    recovery_idx: int | None
    peak_value: float
    trough_value: float
    depth: float
    duration: int
    recovery_duration: int | None

    def to_dict(self) -> dict[str, Any]:
        return {
            "peak_idx": self.peak_idx,
            "trough_idx": self.trough_idx,
            "recovery_idx": self.recovery_idx,
            "peak_value": round(self.peak_value, 4),
            "trough_value": round(self.trough_value, 4),
            "depth": round(self.depth, 6),
            "duration": self.duration,
            "recovery_duration": self.recovery_duration,
        }


@dataclass
class DrawdownReport:
    max_drawdown: float
    max_drawdown_duration: int
    max_drawdown_recovery: int | None
    current_drawdown: float
    avg_drawdown: float
    avg_drawdown_duration: float
    drawdown_periods: list[DrawdownPeriod] = field(default_factory=list)
    underwater_curve: list[float] = field(default_factory=list)
    drawdown_distribution: dict[str, Any] = field(default_factory=dict)
    calmar_ratio: float = 0.0
    sterling_ratio: float = 0.0
    burke_ratio: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        return {
            "max_drawdown": round(self.max_drawdown, 6),
            "max_drawdown_duration": self.max_drawdown_duration,
            "max_drawdown_recovery": self.max_drawdown_recovery,
            "current_drawdown": round(self.current_drawdown, 6),
            "avg_drawdown": round(self.avg_drawdown, 6),
            "avg_drawdown_duration": round(self.avg_drawdown_duration, 2),
            "drawdown_periods": [p.to_dict() for p in self.drawdown_periods],
            "underwater_curve": [round(v, 6) for v in self.underwater_curve],
            "drawdown_distribution": self.drawdown_distribution,
            "calmar_ratio": round(self.calmar_ratio, 4),
            "sterling_ratio": round(self.sterling_ratio, 4),
            "burke_ratio": round(self.burke_ratio, 4),
        }


def compute_underwater_curve(equity: np.ndarray | pd.Series) -> np.ndarray:
    if len(equity) == 0:
        return np.array([])
    arr = np.asarray(equity, dtype=float)
    peak = np.maximum.accumulate(arr)
    with np.errstate(divide="ignore", invalid="ignore"):
        dd = np.where(peak > 0, (arr - peak) / peak, 0.0)
    return dd


def _extract_drawdown_periods(
    underwater: np.ndarray,
    equity: np.ndarray,
    min_depth: float = 0.001,
) -> list[DrawdownPeriod]:
    if len(underwater) == 0:
        return []

    periods: list[DrawdownPeriod] = []
    in_drawdown = False
    peak_idx = 0
    trough_idx = 0

    for i in range(len(underwater)):
        if underwater[i] < -min_depth:
            if not in_drawdown:
                in_drawdown = True
                peak_idx = i - 1 if i > 0 else 0
                while peak_idx > 0 and underwater[peak_idx] >= 0:
                    peak_idx -= 1
                peak_idx = max(0, peak_idx)
                if underwater[peak_idx] < 0 and peak_idx > 0:
                    peak_idx -= 1
                trough_idx = i
            else:
                if underwater[i] < underwater[trough_idx]:
                    trough_idx = i
        else:
            if in_drawdown:
                recovery_idx = i
                depth = abs(underwater[trough_idx])
                duration = trough_idx - peak_idx
                recovery_duration = recovery_idx - trough_idx
                periods.append(
                    DrawdownPeriod(
                        peak_idx=int(peak_idx),
                        trough_idx=int(trough_idx),
                        recovery_idx=int(recovery_idx),
                        peak_value=float(equity[peak_idx]),
                        trough_value=float(equity[trough_idx]),
                        depth=depth,
                        duration=int(duration),
                        recovery_duration=int(recovery_duration),
                    )
                )
                in_drawdown = False

    if in_drawdown:
        depth = abs(underwater[trough_idx])
        duration = len(underwater) - 1 - peak_idx
        periods.append(
            DrawdownPeriod(
                peak_idx=int(peak_idx),
                trough_idx=int(trough_idx),
                recovery_idx=None,
                peak_value=float(equity[peak_idx]),
                trough_value=float(equity[trough_idx]),
                depth=depth,
                duration=int(duration),
                recovery_duration=None,
            )
        )

    return periods


def _compute_drawdown_distribution(
    periods: list[DrawdownPeriod],
) -> dict[str, Any]:
    if not periods:
        return {"count": 0}

    depths = [p.depth for p in periods]
    durations = [p.duration for p in periods]
    recoveries = [p.recovery_duration for p in periods if p.recovery_duration is not None]

    dist: dict[str, Any] = {
        "count": len(periods),
        "depth": {
            "min": round(float(min(depths)), 6),
            "max": round(float(max(depths)), 6),
            "mean": round(float(np.mean(depths)), 6),
            "median": round(float(np.median(depths)), 6),
            "std": round(float(np.std(depths)), 6) if len(depths) > 1 else 0.0,
        },
        "duration": {
            "min": int(min(durations)),
            "max": int(max(durations)),
            "mean": round(float(np.mean(durations)), 2),
            "median": round(float(np.median(durations)), 2),
        },
    }

    if recoveries:
        dist["recovery"] = {
            "min": int(min(recoveries)),
            "max": int(max(recoveries)),
            "mean": round(float(np.mean(recoveries)), 2),
            "median": round(float(np.median(recoveries)), 2),
        }
    else:
        dist["recovery"] = None

    return dist


def analyze_drawdown(
    equity: np.ndarray | pd.Series | list[float],
    returns: np.ndarray | pd.Series | None = None,
    risk_free_rate: float = 0.0,
    annualize_factor: int = 252,
    min_depth: float = 0.001,
) -> DrawdownReport:
    if isinstance(equity, list):
        equity = np.array(equity, dtype=float)
    arr = np.asarray(equity, dtype=float)

    if len(arr) < 2:
        return DrawdownReport(
            max_drawdown=0.0,
            max_drawdown_duration=0,
            max_drawdown_recovery=None,
            current_drawdown=0.0,
            avg_drawdown=0.0,
            avg_drawdown_duration=0.0,
        )

    underwater = compute_underwater_curve(arr)
    periods = _extract_drawdown_periods(underwater, arr, min_depth=min_depth)

    if not periods:
        return DrawdownReport(
            max_drawdown=0.0,
            max_drawdown_duration=0,
            max_drawdown_recovery=None,
            current_drawdown=float(underwater[-1]) if len(underwater) > 0 else 0.0,
            avg_drawdown=0.0,
            avg_drawdown_duration=0.0,
            underwater_curve=underwater.tolist(),
        )

    max_dd_period = max(periods, key=lambda p: p.depth)
    depths = [p.depth for p in periods]
    durations = [p.duration for p in periods]

    max_recovery = None
    if max_dd_period.recovery_duration is not None:
        max_recovery = max_dd_period.recovery_duration

    distribution = _compute_drawdown_distribution(periods)

    annualized_return = 0.0
    if returns is not None:
        ret_arr = np.asarray(returns, dtype=float)
        if len(ret_arr) > 0:
            annualized_return = float(np.mean(ret_arr)) * annualize_factor

    calmar = 0.0
    if max_dd_period.depth > 1e-12:
        calmar = annualized_return / max_dd_period.depth

    avg_dd = float(np.mean(depths))
    sterling = 0.0
    if avg_dd > 1e-12:
        sterling = (annualized_return - risk_free_rate) / avg_dd

    burke = 0.0
    dd_squared_sum = float(np.sum(np.array(depths) ** 2))
    if dd_squared_sum > 1e-12:
        burke = (annualized_return - risk_free_rate) / np.sqrt(dd_squared_sum / len(depths))

    return DrawdownReport(
        max_drawdown=max_dd_period.depth,
        max_drawdown_duration=max_dd_period.duration,
        max_drawdown_recovery=max_recovery,
        current_drawdown=float(abs(underwater[-1])) if len(underwater) > 0 else 0.0,
        avg_drawdown=avg_dd,
        avg_drawdown_duration=float(np.mean(durations)),
        drawdown_periods=periods,
        underwater_curve=underwater.tolist(),
        drawdown_distribution=distribution,
        calmar_ratio=calmar,
        sterling_ratio=sterling,
        burke_ratio=burke,
    )


def rolling_max_drawdown(
    equity: np.ndarray | pd.Series,
    window: int = 252,
) -> np.ndarray:
    arr = np.asarray(equity, dtype=float)
    n = len(arr)
    if n < 2 or window < 2:
        return np.zeros(n)

    result = np.zeros(n)
    for i in range(window - 1, n):
        window_equity = arr[i - window + 1 : i + 1]
        peak = np.maximum.accumulate(window_equity)
        with np.errstate(divide="ignore", invalid="ignore"):
            dd = np.where(peak > 0, (window_equity - peak) / peak, 0.0)
        result[i] = float(np.min(dd))

    return result
