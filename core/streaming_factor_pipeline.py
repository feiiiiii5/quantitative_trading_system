import logging
import math
import threading
from abc import ABC, abstractmethod
from collections import defaultdict, deque
from dataclasses import dataclass
from datetime import datetime

import pandas as pd

from core.database import SQLiteStore

logger = logging.getLogger(__name__)

__all__ = [
    "BarData",
    "Factor",
    "EMAFactor",
    "SMAFactor",
    "RSIFactor",
    "MACDFactor",
    "BollingerBandFactor",
    "ATRFactor",
    "VWAPFactor",
    "OBVFactor",
    "FactorRegistry",
    "FactorDAG",
    "LatencyMonitor",
    "LatencyStats",
    "FactorPersistence",
]


@dataclass
class BarData:
    symbol: str
    timestamp: datetime
    open: float
    high: float
    low: float
    close: float
    volume: float
    amount: float = 0.0


class Factor(ABC):
    @abstractmethod
    def update(self, bar: BarData) -> None: ...

    @property
    @abstractmethod
    def value(self) -> float: ...

    @property
    @abstractmethod
    def name(self) -> str: ...

    @property
    def is_ready(self) -> bool:
        return True


class EMAFactor(Factor):
    def __init__(self, period: int) -> None:
        self._period = period
        self._alpha: float = 2.0 / (period + 1)
        self._ema: float | None = None
        self._count: int = 0

    @property
    def name(self) -> str:
        return f"EMA_{self._period}"

    @property
    def value(self) -> float:
        return self._ema if self._ema is not None else float("nan")

    @property
    def is_ready(self) -> bool:
        return self._ema is not None

    def update(self, bar: BarData) -> None:
        self._count += 1
        if self._ema is None:
            self._ema = bar.close
        else:
            self._ema = self._alpha * bar.close + (1.0 - self._alpha) * self._ema


class SMAFactor(Factor):
    def __init__(self, period: int) -> None:
        self._period = period
        self._ring: list[float] = [0.0] * period
        self._head: int = 0
        self._count: int = 0
        self._sum: float = 0.0
        self._sma: float | None = None

    @property
    def name(self) -> str:
        return f"SMA_{self._period}"

    @property
    def value(self) -> float:
        return self._sma if self._sma is not None else float("nan")

    @property
    def is_ready(self) -> bool:
        return self._count >= self._period

    def update(self, bar: BarData) -> None:
        if self._count >= self._period:
            self._sum -= self._ring[self._head]
        self._ring[self._head] = bar.close
        self._sum += bar.close
        self._head = (self._head + 1) % self._period
        self._count += 1
        if self._count >= self._period:
            self._sma = self._sum / self._period


class RSIFactor(Factor):
    def __init__(self, period: int) -> None:
        self._period = period
        self._alpha: float = 1.0 / period
        self._avg_gain: float | None = None
        self._avg_loss: float | None = None
        self._prev_close: float | None = None
        self._count: int = 0
        self._rsi: float | None = None
        self._init_gains: list[float] = []
        self._init_losses: list[float] = []

    @property
    def name(self) -> str:
        return f"RSI_{self._period}"

    @property
    def value(self) -> float:
        return self._rsi if self._rsi is not None else float("nan")

    @property
    def is_ready(self) -> bool:
        return self._rsi is not None

    def update(self, bar: BarData) -> None:
        self._count += 1
        if self._prev_close is None:
            self._prev_close = bar.close
            return
        change = bar.close - self._prev_close
        self._prev_close = bar.close
        gain = max(change, 0.0)
        loss = max(-change, 0.0)

        if self._avg_gain is None:
            self._init_gains.append(gain)
            self._init_losses.append(loss)
            if len(self._init_gains) == self._period:
                self._avg_gain = sum(self._init_gains) / self._period
                self._avg_loss = sum(self._init_losses) / self._period
                self._compute_rsi()
            return

        if self._avg_gain is not None and self._avg_loss is not None:
            self._avg_gain = self._alpha * gain + (1.0 - self._alpha) * self._avg_gain
            self._avg_loss = self._alpha * loss + (1.0 - self._alpha) * self._avg_loss
        self._compute_rsi()

    def _compute_rsi(self) -> None:
        if self._avg_loss is not None and self._avg_loss < 1e-12:
            self._rsi = 100.0
        elif self._avg_gain is not None and self._avg_loss is not None:
            rs = self._avg_gain / self._avg_loss
            self._rsi = 100.0 - 100.0 / (1.0 + rs)


class MACDFactor(Factor):
    def __init__(self, fast: int = 12, slow: int = 26, signal: int = 9) -> None:
        self._fast = fast
        self._slow = slow
        self._signal = signal
        self._fast_ema: float | None = None
        self._slow_ema: float | None = None
        self._signal_ema: float | None = None
        self._fast_alpha: float = 2.0 / (fast + 1)
        self._slow_alpha: float = 2.0 / (slow + 1)
        self._signal_alpha: float = 2.0 / (signal + 1)
        self._macd_value: float | None = None
        self._signal_value: float | None = None
        self._histogram: float | None = None

    @property
    def name(self) -> str:
        return f"MACD_{self._fast}_{self._slow}_{self._signal}"

    @property
    def value(self) -> float:
        return self._histogram if self._histogram is not None else float("nan")

    @property
    def is_ready(self) -> bool:
        return self._histogram is not None

    @property
    def macd_line(self) -> float:
        return self._macd_value if self._macd_value is not None else float("nan")

    @property
    def signal_line(self) -> float:
        return self._signal_value if self._signal_value is not None else float("nan")

    @property
    def histogram(self) -> float:
        return self._histogram if self._histogram is not None else float("nan")

    def update(self, bar: BarData) -> None:
        if self._fast_ema is None:
            self._fast_ema = bar.close
        else:
            self._fast_ema = self._fast_alpha * bar.close + (1.0 - self._fast_alpha) * self._fast_ema

        if self._slow_ema is None:
            self._slow_ema = bar.close
        else:
            self._slow_ema = self._slow_alpha * bar.close + (1.0 - self._slow_alpha) * self._slow_ema

        self._macd_value = self._fast_ema - self._slow_ema

        if self._signal_ema is None:
            self._signal_ema = self._macd_value
        else:
            self._signal_ema = self._signal_alpha * self._macd_value + (1.0 - self._signal_alpha) * self._signal_ema

        self._signal_value = self._signal_ema
        self._histogram = self._macd_value - self._signal_value


class BollingerBandFactor(Factor):
    def __init__(self, period: int = 20, num_std: float = 2.0) -> None:
        self._period = period
        self._num_std = num_std
        self._ring: list[float] = [0.0] * period
        self._head: int = 0
        self._count: int = 0
        self._sum: float = 0.0
        self._sum_sq: float = 0.0
        self._middle: float | None = None
        self._upper: float | None = None
        self._lower: float | None = None

    @property
    def name(self) -> str:
        return f"BOLL_{self._period}_{self._num_std}"

    @property
    def value(self) -> float:
        return self._middle if self._middle is not None else float("nan")

    @property
    def is_ready(self) -> bool:
        return self._middle is not None

    @property
    def upper(self) -> float:
        return self._upper if self._upper is not None else float("nan")

    @property
    def lower(self) -> float:
        return self._lower if self._lower is not None else float("nan")

    @property
    def middle(self) -> float:
        return self._middle if self._middle is not None else float("nan")

    def update(self, bar: BarData) -> None:
        old_val = self._ring[self._head] if self._count >= self._period else 0.0
        if self._count >= self._period:
            self._sum -= old_val
            self._sum_sq -= old_val * old_val

        self._ring[self._head] = bar.close
        self._sum += bar.close
        self._sum_sq += bar.close * bar.close
        self._head = (self._head + 1) % self._period
        self._count += 1

        if self._count >= self._period:
            self._middle = self._sum / self._period
            variance = self._sum_sq / self._period - self._middle * self._middle
            std = math.sqrt(max(variance, 0.0))
            self._upper = self._middle + self._num_std * std
            self._lower = self._middle - self._num_std * std


class ATRFactor(Factor):
    def __init__(self, period: int = 14) -> None:
        self._period = period
        self._alpha: float = 1.0 / period
        self._atr: float | None = None
        self._prev_close: float | None = None
        self._count: int = 0
        self._init_trs: list[float] = []

    @property
    def name(self) -> str:
        return f"ATR_{self._period}"

    @property
    def value(self) -> float:
        return self._atr if self._atr is not None else float("nan")

    @property
    def is_ready(self) -> bool:
        return self._atr is not None

    def _true_range(self, bar: BarData) -> float:
        if self._prev_close is None:
            return bar.high - bar.low
        tr1 = bar.high - bar.low
        tr2 = abs(bar.high - self._prev_close)
        tr3 = abs(bar.low - self._prev_close)
        return max(tr1, tr2, tr3)

    def update(self, bar: BarData) -> None:
        self._count += 1
        tr = self._true_range(bar)

        if self._atr is None:
            self._init_trs.append(tr)
            if len(self._init_trs) == self._period:
                self._atr = sum(self._init_trs) / self._period
        else:
            self._atr = self._alpha * tr + (1.0 - self._alpha) * self._atr

        self._prev_close = bar.close


class VWAPFactor(Factor):
    def __init__(self) -> None:
        self._cum_tp_vol: float = 0.0
        self._cum_vol: float = 0.0
        self._vwap: float | None = None

    @property
    def name(self) -> str:
        return "VWAP"

    @property
    def value(self) -> float:
        return self._vwap if self._vwap is not None else float("nan")

    @property
    def is_ready(self) -> bool:
        return self._vwap is not None

    def update(self, bar: BarData) -> None:
        tp = (bar.high + bar.low + bar.close) / 3.0
        vol = bar.volume if bar.volume > 0 else bar.amount
        self._cum_tp_vol += tp * vol
        self._cum_vol += vol
        if self._cum_vol > 0:
            self._vwap = self._cum_tp_vol / self._cum_vol


class OBVFactor(Factor):
    def __init__(self) -> None:
        self._obv: float = 0.0
        self._prev_close: float | None = None

    @property
    def name(self) -> str:
        return "OBV"

    @property
    def value(self) -> float:
        return self._obv

    @property
    def is_ready(self) -> bool:
        return self._prev_close is not None

    def update(self, bar: BarData) -> None:
        if self._prev_close is None:
            self._prev_close = bar.close
            return
        if bar.close > self._prev_close:
            self._obv += bar.volume
        elif bar.close < self._prev_close:
            self._obv -= bar.volume
        self._prev_close = bar.close


class FactorRegistry:
    def __init__(self) -> None:
        self._factors: dict[str, Factor] = {}

    def register(self, factor: Factor) -> None:
        if factor.name in self._factors:
            logger.warning("Overwriting existing factor: %s", factor.name)
        self._factors[factor.name] = factor

    def get(self, name: str) -> Factor | None:
        return self._factors.get(name)

    def unregister(self, name: str) -> None:
        self._factors.pop(name, None)

    def update_all(self, bar: BarData) -> dict[str, float]:
        result: dict[str, float] = {}
        for fname, factor in self._factors.items():
            factor.update(bar)
            result[fname] = factor.value
        return result

    def get_ready_factors(self) -> dict[str, float]:
        return {
            fname: factor.value
            for fname, factor in self._factors.items()
            if factor.is_ready
        }

    @property
    def factor_names(self) -> list[str]:
        return list(self._factors.keys())


class FactorDAG:
    def __init__(self) -> None:
        self._factors: dict[str, Factor] = {}
        self._dependencies: dict[str, list[str]] = {}
        self._execution_order: list[str] | None = None

    def add_factor(self, factor: Factor, dependencies: list[str] | None = None) -> None:
        self._factors[factor.name] = factor
        self._dependencies[factor.name] = dependencies or []
        self._execution_order = None

    def remove_factor(self, name: str) -> None:
        self._factors.pop(name, None)
        self._dependencies.pop(name, None)
        for deps in self._dependencies.values():
            if name in deps:
                deps.remove(name)
        self._execution_order = None

    def _topological_sort(self) -> list[str]:
        in_degree: dict[str, int] = dict.fromkeys(self._factors, 0)
        adj: dict[str, list[str]] = defaultdict(list)
        for name, deps in self._dependencies.items():
            for dep in deps:
                if dep in self._factors:
                    adj[dep].append(name)
                    in_degree[name] += 1

        queue: deque[str] = deque(
            name for name, deg in in_degree.items() if deg == 0
        )
        order: list[str] = []
        while queue:
            node = queue.popleft()
            order.append(node)
            for neighbor in adj[node]:
                in_degree[neighbor] -= 1
                if in_degree[neighbor] == 0:
                    queue.append(neighbor)

        return order

    def _ensure_order(self) -> list[str]:
        if self._execution_order is None:
            self._execution_order = self._topological_sort()
        return self._execution_order

    def compute(self, bar: BarData) -> dict[str, float]:
        order = self._ensure_order()
        result: dict[str, float] = {}
        for name in order:
            factor = self._factors[name]
            factor.update(bar)
            result[name] = factor.value
        return result

    def validate(self) -> list[str]:
        errors: list[str] = []
        for name, deps in self._dependencies.items():
            for dep in deps:
                if dep not in self._factors:
                    errors.append(f"Factor '{name}' depends on unknown factor '{dep}'")

        order = self._topological_sort()
        if len(order) != len(self._factors):
            errors.append("Cycle detected in factor dependency graph")

        return errors


@dataclass
class LatencyStats:
    count: int = 0
    p50_us: int = 0
    p95_us: int = 0
    p99_us: int = 0
    max_us: int = 0
    avg_us: float = 0.0


class LatencyMonitor:
    def __init__(self, max_samples: int = 10000) -> None:
        self._max_samples = max_samples
        self._latencies: dict[str, deque[int]] = defaultdict(
            lambda: deque(maxlen=max_samples)
        )
        self._lock = threading.Lock()

    def record(self, factor_name: str, latency_us: int) -> None:
        with self._lock:
            self._latencies[factor_name].append(latency_us)

    def get_stats(self) -> dict[str, LatencyStats]:
        with self._lock:
            result: dict[str, LatencyStats] = {}
            for name, samples in self._latencies.items():
                if not samples:
                    result[name] = LatencyStats()
                    continue
                sorted_vals = sorted(samples)
                n = len(sorted_vals)
                result[name] = LatencyStats(
                    count=n,
                    p50_us=sorted_vals[int(n * 0.50)],
                    p95_us=sorted_vals[int(n * 0.95)],
                    p99_us=sorted_vals[min(int(n * 0.99), n - 1)],
                    max_us=sorted_vals[-1],
                    avg_us=sum(sorted_vals) / n,
                )
            return result

    def check_sla(self, p99_threshold_us: int = 100000) -> list[str]:
        stats = self.get_stats()
        return [
            name
            for name, s in stats.items()
            if s.p99_us > p99_threshold_us
        ]

    def reset(self, factor_name: str | None = None) -> None:
        with self._lock:
            if factor_name is None:
                self._latencies.clear()
            else:
                self._latencies.pop(factor_name, None)


class FactorPersistence:
    def __init__(
        self,
        db: SQLiteStore,
        hot_factor_names: set[str] | None = None,
    ) -> None:
        self._db = db
        self._hot_factor_names: set[str] = hot_factor_names or set()
        self._hot_cache: dict[str, dict[str, dict[str, float]]] = defaultdict(
            lambda: defaultdict(dict)
        )
        self._lock = threading.Lock()

    def save_factor_value(
        self, symbol: str, factor_name: str, date: str, value: float
    ) -> None:
        if factor_name in self._hot_factor_names:
            with self._lock:
                self._hot_cache[symbol][factor_name][date] = value
            return
        self._db.buffered_write(
            "INSERT OR REPLACE INTO factor_cache (symbol, factor_name, date, value) VALUES (?, ?, ?, ?)",
            (symbol, factor_name, date, value),
        )

    def load_factor_history(
        self,
        symbol: str,
        factor_name: str,
        start_date: str,
        end_date: str,
    ) -> pd.DataFrame:
        if factor_name in self._hot_factor_names:
            with self._lock:
                factor_data = self._hot_cache.get(symbol, {}).get(factor_name, {})
                rows = [
                    {"date": d, "value": v}
                    for d, v in factor_data.items()
                    if start_date <= d <= end_date
                ]
                if rows:
                    df = pd.DataFrame(rows)
                    df = df.sort_values("date").reset_index(drop=True)
                    return df
                return pd.DataFrame(columns=["date", "value"])

        return self._db.get_factor_cache(symbol, factor_name, start_date, end_date)

    def flush_hot_to_db(self, symbol: str | None = None) -> int:
        count = 0
        with self._lock:
            symbols_to_flush = (
                {symbol: self._hot_cache[symbol]}
                if symbol and symbol in self._hot_cache
                else dict(self._hot_cache)
            )
            for sym, factors in symbols_to_flush.items():
                for fname, date_vals in factors.items():
                    for dt, val in date_vals.items():
                        self._db.buffered_write(
                            "INSERT OR REPLACE INTO factor_cache (symbol, factor_name, date, value) VALUES (?, ?, ?, ?)",
                            (sym, fname, dt, val),
                        )
                        count += 1
            if symbol:
                self._hot_cache.pop(symbol, None)
            else:
                self._hot_cache.clear()
        return count
