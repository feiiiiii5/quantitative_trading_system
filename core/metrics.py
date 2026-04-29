"""
QuantCore 性能指标收集器
收集API响应时间、策略命中率、数据源可用性等运行指标
"""
import logging
import threading
import time
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)


@dataclass
class MetricPoint:
    timestamp: float
    value: float
    tags: Dict[str, str] = field(default_factory=dict)


class MetricsCollector:
    """线程安全的指标收集器"""

    def __init__(self, max_points: int = 1000):
        self._max_points = max_points
        self._lock = threading.Lock()
        self._counters: Dict[str, float] = defaultdict(float)
        self._gauges: Dict[str, float] = defaultdict(float)
        self._histories: Dict[str, List[MetricPoint]] = defaultdict(list)
        self._timers: Dict[str, List[float]] = defaultdict(list)
        self._start_time = time.time()

    def increment(self, name: str, value: float = 1.0, tags: Optional[Dict[str, str]] = None):
        with self._lock:
            self._counters[name] += value
            self._record(name, self._counters[name], tags)

    def gauge(self, name: str, value: float, tags: Optional[Dict[str, str]] = None):
        with self._lock:
            self._gauges[name] = value
            self._record(name, value, tags)

    def timer(self, name: str, elapsed_seconds: float, tags: Optional[Dict[str, str]] = None):
        with self._lock:
            self._timers[name].append(elapsed_seconds)
            if len(self._timers[name]) > 200:
                self._timers[name] = self._timers[name][-200:]
            self._record(name, elapsed_seconds, tags)

    def _record(self, name: str, value: float, tags: Optional[Dict[str, str]] = None):
        point = MetricPoint(timestamp=time.time(), value=value, tags=tags or {})
        history = self._histories[name]
        history.append(point)
        if len(history) > self._max_points:
            self._histories[name] = history[-self._max_points:]

    def get_counter(self, name: str) -> float:
        return self._counters.get(name, 0.0)

    def get_gauge(self, name: str) -> float:
        return self._gauges.get(name, 0.0)

    def get_timer_stats(self, name: str) -> dict:
        values = self._timers.get(name, [])
        if not values:
            return {"count": 0, "avg": 0, "p50": 0, "p95": 0, "p99": 0}
        sorted_v = sorted(values)
        return {
            "count": len(sorted_v),
            "avg": round(sum(sorted_v) / len(sorted_v), 4),
            "p50": round(sorted_v[int(len(sorted_v) * 0.5)], 4),
            "p95": round(sorted_v[int(len(sorted_v) * 0.95)], 4),
            "p99": round(sorted_v[min(int(len(sorted_v) * 0.99), len(sorted_v) - 1)], 4),
        }

    def get_history(self, name: str, last_n: int = 100) -> List[dict]:
        history = self._histories.get(name, [])
        points = history[-last_n:]
        return [{"timestamp": p.timestamp, "value": p.value, "tags": p.tags} for p in points]

    def get_summary(self) -> dict:
        uptime = time.time() - self._start_time
        timer_stats = {}
        for name in self._timers:
            timer_stats[name] = self.get_timer_stats(name)
        return {
            "uptime_seconds": round(uptime, 1),
            "counters": dict(self._counters),
            "gauges": dict(self._gauges),
            "timers": timer_stats,
        }

    def reset(self):
        with self._lock:
            self._counters.clear()
            self._gauges.clear()
            self._histories.clear()
            self._timers.clear()


class TimerContext:
    """计时上下文管理器"""

    def __init__(self, collector: MetricsCollector, name: str, tags: Optional[Dict[str, str]] = None):
        self._collector = collector
        self._name = name
        self._tags = tags
        self._start = 0.0

    def __enter__(self):
        self._start = time.time()
        return self

    def __exit__(self, *args):
        elapsed = time.time() - self._start
        self._collector.timer(self._name, elapsed, self._tags)


metrics = MetricsCollector()


def record_api_call(endpoint: str, elapsed: float, success: bool = True):
    metrics.increment("api.calls.total")
    if success:
        metrics.increment("api.calls.success")
    else:
        metrics.increment("api.calls.error")
    metrics.timer(f"api.latency.{endpoint}", elapsed)


def record_strategy_signal(strategy_name: str, signal_type: str, confidence: float):
    metrics.increment(f"strategy.signal.{strategy_name}.{signal_type}")
    metrics.gauge(f"strategy.confidence.{strategy_name}", confidence)


def record_data_fetch(source: str, elapsed: float, success: bool = True):
    metrics.increment(f"data.fetch.{source}.total")
    if success:
        metrics.increment(f"data.fetch.{source}.success")
    else:
        metrics.increment(f"data.fetch.{source}.error")
    metrics.timer(f"data.latency.{source}", elapsed)


def record_backtest(strategy_name: str, sharpe: float, total_return: float):
    metrics.increment("backtest.runs.total")
    metrics.gauge(f"backtest.sharpe.{strategy_name}", sharpe)
    metrics.gauge(f"backtest.return.{strategy_name}", total_return)
