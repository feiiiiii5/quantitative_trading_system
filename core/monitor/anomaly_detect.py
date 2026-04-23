import logging
import time
from dataclasses import dataclass, field
from typing import Dict, List, Optional

import numpy as np

logger = logging.getLogger(__name__)


@dataclass
class AnomalyEvent:
    event_type: str
    symbol: str = ""
    severity: str = "medium"
    details: dict = field(default_factory=dict)
    timestamp: str = ""
    similar_historical: List[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "event_type": self.event_type, "symbol": self.symbol,
            "severity": self.severity, "details": self.details,
            "timestamp": self.timestamp,
            "similar_historical": self.similar_historical,
        }


class AnomalyDetector:
    def __init__(
        self,
        volume_z_threshold: float = 3.0,
        price_z_threshold: float = 3.0,
        large_order_threshold: float = 1000000.0,
        daily_loss_limit: float = 0.05,
        high_freq_threshold: int = 10,
    ):
        self.volume_z_threshold = volume_z_threshold
        self.price_z_threshold = price_z_threshold
        self.large_order_threshold = large_order_threshold
        self.daily_loss_limit = daily_loss_limit
        self.high_freq_threshold = high_freq_threshold
        self._volume_history: Dict[str, List[float]] = {}
        self._price_history: Dict[str, List[float]] = {}
        self._order_timestamps: Dict[str, List[float]] = {}
        self._anomalies: List[AnomalyEvent] = []
        self._max_anomalies = 10000
        self._max_history = 60

    def check_volume_anomaly(self, symbol: str, current_volume: float) -> Optional[AnomalyEvent]:
        if symbol not in self._volume_history:
            self._volume_history[symbol] = []
        self._volume_history[symbol].append(current_volume)
        if len(self._volume_history[symbol]) > self._max_history:
            self._volume_history[symbol] = self._volume_history[symbol][-self._max_history:]
        if len(self._volume_history[symbol]) < 20:
            return None

        history = self._volume_history[symbol][-60:]
        mean = np.mean(history)
        std = np.std(history)
        if std <= 0:
            return None

        z_score = (current_volume - mean) / std
        if abs(z_score) > self.volume_z_threshold:
            event = AnomalyEvent(
                event_type="volume_anomaly", symbol=symbol,
                severity="high" if abs(z_score) > 5 else "medium",
                details={"z_score": round(z_score, 2), "current": current_volume,
                         "mean": round(mean, 2), "std": round(std, 2)},
                timestamp=time.strftime("%Y-%m-%d %H:%M:%S"),
            )
            self._anomalies.append(event)
            self._trim_anomalies()
            return event
        return None

    def check_price_anomaly(self, symbol: str, current_return: float) -> Optional[AnomalyEvent]:
        if symbol not in self._price_history:
            self._price_history[symbol] = []
        self._price_history[symbol].append(current_return)
        if len(self._price_history[symbol]) > self._max_history:
            self._price_history[symbol] = self._price_history[symbol][-self._max_history:]
        if len(self._price_history[symbol]) < 20:
            return None

        history = self._price_history[symbol][-60:]
        mean = np.mean(history)
        std = np.std(history)
        if std <= 0:
            return None

        z_score = (current_return - mean) / std
        if abs(z_score) > self.price_z_threshold:
            event = AnomalyEvent(
                event_type="price_anomaly", symbol=symbol,
                severity="high" if abs(z_score) > 5 else "medium",
                details={"z_score": round(z_score, 2), "current_return": round(current_return, 4),
                         "mean": round(mean, 4), "std": round(std, 4)},
                timestamp=time.strftime("%Y-%m-%d %H:%M:%S"),
            )
            self._anomalies.append(event)
            self._trim_anomalies()
            return event
        return None

    def check_large_order(self, symbol: str, order_value: float) -> Optional[AnomalyEvent]:
        if order_value >= self.large_order_threshold:
            event = AnomalyEvent(
                event_type="large_order", symbol=symbol,
                severity="high",
                details={"order_value": order_value, "threshold": self.large_order_threshold},
                timestamp=time.strftime("%Y-%m-%d %H:%M:%S"),
            )
            self._anomalies.append(event)
            self._trim_anomalies()
            return event
        return None

    def check_daily_loss(self, symbol: str, daily_pnl_pct: float) -> Optional[AnomalyEvent]:
        if daily_pnl_pct < -self.daily_loss_limit:
            event = AnomalyEvent(
                event_type="daily_loss_limit", symbol=symbol,
                severity="critical",
                details={"daily_pnl_pct": round(daily_pnl_pct, 4), "limit": self.daily_loss_limit},
                timestamp=time.strftime("%Y-%m-%d %H:%M:%S"),
            )
            self._anomalies.append(event)
            self._trim_anomalies()
            return event
        return None

    def check_high_frequency(self, symbol: str) -> Optional[AnomalyEvent]:
        now = time.time()
        if symbol not in self._order_timestamps:
            self._order_timestamps[symbol] = []

        self._order_timestamps[symbol].append(now)
        recent = [t for t in self._order_timestamps[symbol] if now - t < 60]
        self._order_timestamps[symbol] = recent

        if len(recent) > self.high_freq_threshold:
            event = AnomalyEvent(
                event_type="high_frequency", symbol=symbol,
                severity="warning",
                details={"orders_per_minute": len(recent), "threshold": self.high_freq_threshold},
                timestamp=time.strftime("%Y-%m-%d %H:%M:%S"),
            )
            self._anomalies.append(event)
            self._trim_anomalies()
            return event
        return None

    def detect_opening_anomaly(self, symbol: str, open_price: float, prev_close: float) -> Optional[AnomalyEvent]:
        if prev_close <= 0:
            return None
        gap_pct = (open_price / prev_close - 1)
        if abs(gap_pct) > 0.05:
            event = AnomalyEvent(
                event_type="opening_gap", symbol=symbol,
                severity="high" if abs(gap_pct) > 0.08 else "medium",
                details={"gap_pct": round(gap_pct * 100, 2), "open": open_price, "prev_close": prev_close},
                timestamp=time.strftime("%Y-%m-%d %H:%M:%S"),
            )
            self._anomalies.append(event)
            self._trim_anomalies()
            return event
        return None

    def get_recent_anomalies(self, limit: int = 50) -> List[dict]:
        return [a.to_dict() for a in self._anomalies[-limit:]]

    def get_anomaly_stats(self) -> dict:
        type_counts = {}
        for a in self._anomalies:
            type_counts[a.event_type] = type_counts.get(a.event_type, 0) + 1
        return {
            "total_anomalies": len(self._anomalies),
            "by_type": type_counts,
        }

    def _trim_anomalies(self):
        if len(self._anomalies) > self._max_anomalies:
            self._anomalies = self._anomalies[-self._max_anomalies:]
