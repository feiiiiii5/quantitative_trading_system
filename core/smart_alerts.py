import logging
import threading
import time
from collections import deque
from dataclasses import dataclass, field

import numpy as np

logger = logging.getLogger(__name__)


@dataclass
class AnomalyAlert:
    symbol: str
    name: str
    alert_type: str
    z_score: float
    current_value: float
    mean_value: float
    std_value: float
    timestamp: float = 0.0


@dataclass
class SymbolStats:
    returns: deque = field(default_factory=lambda: deque(maxlen=60))
    volumes: deque = field(default_factory=lambda: deque(maxlen=60))
    last_price: float = 0.0
    last_volume: float = 0.0
    last_alert_time: float = 0.0


class SmartAlertEngine:
    """基于Z-score的实时异常检测引擎

    检测价格变动和成交量异常，通过WebSocket推送告警。
    使用滚动窗口统计，O(1)每bar更新成本。
    """

    PRICE_Z_THRESHOLD = 2.5
    VOLUME_Z_THRESHOLD = 3.0
    MIN_SAMPLES = 10
    COOLDOWN_SECONDS = 300
    MAX_ALERTS_PER_CYCLE = 5

    def __init__(
        self,
        price_z_threshold: float = 2.5,
        volume_z_threshold: float = 3.0,
        cooldown_seconds: float = 300,
    ):
        self._price_z_threshold = price_z_threshold
        self._volume_z_threshold = volume_z_threshold
        self._cooldown_seconds = cooldown_seconds
        self._stats: dict[str, SymbolStats] = {}
        self._lock = threading.Lock()
        self._alert_history: deque = deque(maxlen=200)

    def update(self, symbol: str, name: str, price: float, volume: float = 0.0) -> list[AnomalyAlert]:
        """更新价格/成交量数据并检测异常

        Args:
            symbol: 股票代码
            name: 股票名称
            price: 当前价格
            volume: 当前成交量

        Returns:
            本轮检测到的异常告警列表
        """
        if price <= 0:
            return []

        alerts = []

        with self._lock:
            stats = self._stats.get(symbol)
            if stats is None:
                stats = SymbolStats()
                self._stats[symbol] = stats

            if stats.last_price > 0:
                ret = (price - stats.last_price) / stats.last_price
                if np.isfinite(ret):
                    stats.returns.append(ret)

            if volume > 0:
                stats.volumes.append(volume)

            stats.last_price = price
            stats.last_volume = volume

            now = time.time()
            if now - stats.last_alert_time < self._cooldown_seconds:
                return []

            price_alert = self._check_price_anomaly(symbol, name, stats, now)
            if price_alert:
                alerts.append(price_alert)

            volume_alert = self._check_volume_anomaly(symbol, name, stats, now)
            if volume_alert:
                alerts.append(volume_alert)

            if alerts:
                stats.last_alert_time = now
                for a in alerts:
                    self._alert_history.append(a)

        return alerts[:self.MAX_ALERTS_PER_CYCLE]

    def _check_price_anomaly(self, symbol: str, name: str, stats: SymbolStats, now: float) -> AnomalyAlert | None:
        if len(stats.returns) < self.MIN_SAMPLES:
            return None

        ret_arr = np.array(stats.returns)
        mean_ret = float(np.mean(ret_arr))
        std_ret = float(np.std(ret_arr))

        if std_ret < 1e-10:
            return None

        latest_ret = stats.returns[-1]
        z_score = abs(latest_ret - mean_ret) / std_ret

        if z_score >= self._price_z_threshold:
            return AnomalyAlert(
                symbol=symbol,
                name=name,
                alert_type="price_anomaly",
                z_score=round(z_score, 2),
                current_value=round(latest_ret * 100, 4),
                mean_value=round(mean_ret * 100, 4),
                std_value=round(std_ret * 100, 4),
                timestamp=now,
            )
        return None

    def _check_volume_anomaly(self, symbol: str, name: str, stats: SymbolStats, now: float) -> AnomalyAlert | None:
        if len(stats.volumes) < self.MIN_SAMPLES:
            return None

        vol_arr = np.array(stats.volumes)
        mean_vol = float(np.mean(vol_arr))
        std_vol = float(np.std(vol_arr))

        if std_vol < 1e-10 or mean_vol < 1e-10:
            return None

        latest_vol = stats.volumes[-1]
        z_score = (latest_vol - mean_vol) / std_vol

        if z_score >= self._volume_z_threshold:
            return AnomalyAlert(
                symbol=symbol,
                name=name,
                alert_type="volume_spike",
                z_score=round(z_score, 2),
                current_value=round(latest_vol, 2),
                mean_value=round(mean_vol, 2),
                std_value=round(std_vol, 2),
                timestamp=now,
            )
        return None

    def get_alert_history(self, limit: int = 50) -> list[dict]:
        with self._lock:
            alerts = list(self._alert_history)[-limit:]
            return [
                {
                    "symbol": a.symbol,
                    "name": a.name,
                    "alert_type": a.alert_type,
                    "z_score": a.z_score,
                    "current_value": a.current_value,
                    "mean_value": a.mean_value,
                    "std_value": a.std_value,
                    "timestamp": a.timestamp,
                }
                for a in alerts
            ]

    def get_stats(self, symbol: str) -> dict | None:
        with self._lock:
            stats = self._stats.get(symbol)
            if stats is None:
                return None
            return {
                "symbol": symbol,
                "return_count": len(stats.returns),
                "volume_count": len(stats.volumes),
                "last_price": stats.last_price,
                "last_volume": stats.last_volume,
            }

    def cleanup_stale(self, max_age: float = 3600) -> int:
        now = time.time()
        removed = 0
        with self._lock:
            stale = [
                s for s, stats in self._stats.items()
                if now - stats.last_alert_time > max_age and len(stats.returns) == 0
            ]
            for s in stale:
                del self._stats[s]
                removed += 1
        return removed


_engine: SmartAlertEngine | None = None


def get_smart_alert_engine() -> SmartAlertEngine:
    global _engine
    if _engine is None:
        _engine = SmartAlertEngine()
    return _engine
