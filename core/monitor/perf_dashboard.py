import logging
import time
import threading
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
        self._api_status_codes: Dict[str, List[int]] = {}
        self._data_latencies: Dict[str, Dict[str, List[float]]] = {}
        self._connection_metrics: Dict[str, List[dict]] = {}
        self._start_time = time.time()
        self._lock = threading.Lock()
        self._last_cleanup = time.time()

    def record_metric(self, name: str, value: float, labels: Optional[dict] = None):
        with self._lock:
            if name not in self._metrics:
                self._metrics[name] = []
            point = MetricPoint(name=name, value=value, timestamp=time.time(), labels=labels or {})
            self._metrics[name].append(point)
            self._cleanup(name)

    def record_api_latency(self, endpoint: str, latency_ms: float, status_code: int = 200):
        with self._lock:
            if endpoint not in self._api_latencies:
                self._api_latencies[endpoint] = []
                self._api_status_codes[endpoint] = []
            self._api_latencies[endpoint].append(latency_ms)
            self._api_status_codes[endpoint].append(status_code)
            if len(self._api_latencies[endpoint]) > 1000:
                self._api_latencies[endpoint] = self._api_latencies[endpoint][-500:]
                self._api_status_codes[endpoint] = self._api_status_codes[endpoint][-500:]

    def record_data_latency(self, source: str, symbol: str, latency_ms: float):
        with self._lock:
            key = source
            if key not in self._data_latencies:
                self._data_latencies[key] = {}
            if symbol not in self._data_latencies[key]:
                self._data_latencies[key][symbol] = []
            self._data_latencies[key][symbol].append(latency_ms)
            if len(self._data_latencies[key][symbol]) > 500:
                self._data_latencies[key][symbol] = self._data_latencies[key][symbol][-250:]

    def record_connection_status(self, source: str, status: str, latency_ms: float = 0):
        """记录连接状态"""
        with self._lock:
            if source not in self._connection_metrics:
                self._connection_metrics[source] = []
            self._connection_metrics[source].append({
                "status": status,
                "latency_ms": latency_ms,
                "timestamp": time.time()
            })
            if len(self._connection_metrics[source]) > 100:
                self._connection_metrics[source] = self._connection_metrics[source][-50:]

    def get_system_metrics(self) -> dict:
        try:
            import psutil
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
        with self._lock:
            stats = {}
            for endpoint, latencies in self._api_latencies.items():
                if not latencies:
                    continue
                arr = sorted(latencies)
                n = len(arr)
                status_codes = self._api_status_codes.get(endpoint, [])
                error_count = sum(1 for s in status_codes if s >= 400) if status_codes else 0
                stats[endpoint] = {
                    "p50": round(arr[n // 2], 2),
                    "p95": round(arr[int(n * 0.95)], 2) if n > 20 else round(arr[-1], 2),
                    "p99": round(arr[int(n * 0.99)], 2) if n > 100 else round(arr[-1], 2),
                    "avg": round(sum(arr) / n, 2),
                    "count": n,
                    "error_count": error_count,
                }
            return stats

    def get_data_latency_heatmap(self) -> dict:
        with self._lock:
            heatmap = {}
            for source, symbols in self._data_latencies.items():
                for symbol, latencies in symbols.items():
                    if latencies:
                        key = f"{source}:{symbol}"
                        heatmap[key] = round(sum(latencies) / len(latencies), 2)
            for name, points in self._metrics.items():
                if "latency" in name.lower() or "delay" in name.lower():
                    if points:
                        latest = points[-1].value
                        heatmap[name] = round(latest, 2)
            return heatmap

    def get_connection_status(self) -> dict:
        """获取连接状态"""
        with self._lock:
            status = {}
            for source, metrics in self._connection_metrics.items():
                if metrics:
                    latest = metrics[-1]
                    status[source] = {
                        "status": latest["status"],
                        "latency_ms": latest["latency_ms"],
                        "last_updated": time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(latest["timestamp"]))
                    }
            return status

    def get_summary(self) -> dict:
        return {
            "system": self.get_system_metrics(),
            "api_latencies": self.get_api_latency_stats(),
            "data_latency_heatmap": self.get_data_latency_heatmap(),
            "connection_status": self.get_connection_status(),
            "custom_metrics": {name: points[-1].value if points else 0 for name, points in self._metrics.items()},
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        }

    def get_dashboard(self) -> dict:
        return self.get_summary()

    def _cleanup(self, name: str):
        """清理过期的指标数据（调用方已持锁，不可再获取锁）"""
        now = time.time()

        # 定期清理所有指标
        if now - self._last_cleanup > 300:  # 每5分钟清理一次
            self._last_cleanup = now
            for metric_name in list(self._metrics.keys()):
                self._metrics[metric_name] = [
                    p for p in self._metrics[metric_name]
                    if now - p.timestamp < self.retention_seconds
                ]
                if not self._metrics[metric_name]:
                    del self._metrics[metric_name]
        else:
            # 只清理指定的指标
            if name in self._metrics:
                self._metrics[name] = [
                    p for p in self._metrics[name]
                    if now - p.timestamp < self.retention_seconds
                ]

    def get_metric_series(self, metric_name: str, limit: int = 100) -> list[dict]:
        """获取指标时间序列"""
        with self._lock:
            if metric_name not in self._metrics:
                return []
            points = self._metrics[metric_name][-limit:]
            return [p.to_dict() for p in points]

    def get_health_score(self) -> float:
        score = 100.0

        system = self.get_system_metrics()
        if system.get("cpu_percent", 0) > 80:
            score -= 20
        if system.get("memory", {}).get("used_pct", 0) > 85:
            score -= 20
        if system.get("disk", {}).get("used_pct", 0) > 90:
            score -= 20

        api_stats = self.get_api_latency_stats()
        for endpoint, stats in api_stats.items():
            if stats.get("avg", 0) > 500:
                score -= 5
            if stats.get("error_count", 0) > 0:
                score -= 10

        conn_status = self.get_connection_status()
        for source, status in conn_status.items():
            if status.get("status", "") != "connected":
                score -= 15
            if status.get("latency_ms", 0) > 1000:
                score -= 10

        return max(0, min(100, score))
