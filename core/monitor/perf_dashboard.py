import logging
import time
from dataclasses import dataclass, field
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)


@dataclass
class MetricPoint:
    name: str
    value: float
    timestamp: float = 0.0
    labels: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {"name": self.name, "value": self.value, "timestamp": self.timestamp, "labels": self.labels}


class PerformanceDashboard:
    def __init__(self, retention_seconds: float = 3600):
        self.retention_seconds = retention_seconds
        self._metrics: Dict[str, List[MetricPoint]] = {}
        self._api_latencies: Dict[str, List[float]] = {}
        self._start_time = time.time()

    def record_metric(self, name: str, value: float, labels: Optional[dict] = None):
        if name not in self._metrics:
            self._metrics[name] = []
        point = MetricPoint(name=name, value=value, timestamp=time.time(), labels=labels or {})
        self._metrics[name].append(point)
        self._cleanup(name)

    def record_api_latency(self, endpoint: str, latency_ms: float):
        if endpoint not in self._api_latencies:
            self._api_latencies[endpoint] = []
        self._api_latencies[endpoint].append(latency_ms)
        if len(self._api_latencies[endpoint]) > 1000:
            self._api_latencies[endpoint] = self._api_latencies[endpoint][-500:]

    def get_system_metrics(self) -> dict:
        import psutil
        try:
            cpu = psutil.cpu_percent(interval=0.1)
            mem = psutil.virtual_memory()
            disk = psutil.disk_usage("/")
            net = psutil.net_io_counters()
            return {
                "cpu_percent": cpu,
                "memory": {"total_gb": round(mem.total / 1e9, 2), "used_pct": mem.percent, "available_gb": round(mem.available / 1e9, 2)},
                "disk": {"total_gb": round(disk.total / 1e9, 2), "used_pct": disk.percent},
                "network": {"bytes_sent": net.bytes_sent, "bytes_recv": net.bytes_recv},
                "uptime_seconds": round(time.time() - self._start_time, 1),
            }
        except ImportError:
            return {"cpu_percent": 0, "memory": {}, "disk": {}, "note": "psutil not installed"}

    def get_api_latency_stats(self) -> dict:
        stats = {}
        for endpoint, latencies in self._api_latencies.items():
            if not latencies:
                continue
            arr = sorted(latencies)
            n = len(arr)
            stats[endpoint] = {
                "p50": round(arr[n // 2], 2),
                "p95": round(arr[int(n * 0.95)], 2) if n > 20 else round(arr[-1], 2),
                "p99": round(arr[int(n * 0.99)], 2) if n > 100 else round(arr[-1], 2),
                "avg": round(sum(arr) / n, 2),
                "count": n,
            }
        return stats

    def get_data_latency_heatmap(self) -> dict:
        heatmap = {}
        for name, points in self._metrics.items():
            if "latency" in name.lower() or "delay" in name.lower():
                if points:
                    latest = points[-1].value
                    heatmap[name] = round(latest, 2)
        return heatmap

    def get_dashboard(self) -> dict:
        return {
            "system": self.get_system_metrics(),
            "api_latencies": self.get_api_latency_stats(),
            "data_latency_heatmap": self.get_data_latency_heatmap(),
            "custom_metrics": {name: points[-1].value if points else 0 for name, points in self._metrics.items()},
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        }

    def _cleanup(self, name: str):
        now = time.time()
        if name in self._metrics:
            self._metrics[name] = [
                p for p in self._metrics[name]
                if now - p.timestamp < self.retention_seconds
            ]
