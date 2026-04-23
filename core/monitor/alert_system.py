import logging
import time
from collections import deque
from dataclasses import dataclass, field
from enum import Enum
from typing import Callable, Dict, List, Optional

logger = logging.getLogger(__name__)


class AlertLevel(Enum):
    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"
    EMERGENCY = "emergency"


class AlertChannel(Enum):
    LOG = "log"
    EMAIL = "email"
    DINGTALK = "dingtalk"
    WECHAT = "wechat"
    TELEGRAM = "telegram"


@dataclass
class Alert:
    id: str
    level: AlertLevel
    title: str
    message: str
    source: str = ""
    channel: AlertChannel = AlertChannel.LOG
    created_at: float = 0.0
    acknowledged: bool = False
    aggregated: bool = False
    group_key: str = ""

    def to_dict(self) -> dict:
        return {
            "id": self.id, "level": self.level.value,
            "title": self.title, "message": self.message,
            "source": self.source, "channel": self.channel.value,
            "created_at": time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(self.created_at)),
            "acknowledged": self.acknowledged, "aggregated": self.aggregated,
        }


class SmartAlertSystem:
    def __init__(self, aggregation_window: float = 300.0):
        self.aggregation_window = aggregation_window
        self._alerts: deque = deque(maxlen=1000)
        self._channels: Dict[AlertChannel, Callable] = {}
        self._alert_counter = 0
        self._group_tracker: Dict[str, List[Alert]] = {}

    def register_channel(self, channel: AlertChannel, handler: Callable):
        self._channels[channel] = handler

    def send_alert(
        self,
        level: AlertLevel,
        title: str,
        message: str,
        source: str = "",
        channel: AlertChannel = AlertChannel.LOG,
        group_key: str = "",
    ) -> Alert:
        self._alert_counter += 1
        alert = Alert(
            id=f"alert_{self._alert_counter:06d}",
            level=level, title=title, message=message,
            source=source, channel=channel,
            created_at=time.time(),
            group_key=group_key or f"{source}:{title}",
        )

        if group_key:
            now = time.time()
            group = self._group_tracker.get(alert.group_key, [])
            recent = [a for a in group if now - a.created_at < self.aggregation_window]
            if recent:
                alert.aggregated = True
            recent.append(alert)
            self._group_tracker[alert.group_key] = recent

        self._alerts.append(alert)
        self._dispatch(alert)
        return alert

    def _dispatch(self, alert: Alert):
        handler = self._channels.get(alert.channel)
        if handler:
            try:
                handler(alert)
            except Exception as e:
                logger.error(f"Alert dispatch error: {e}")
        else:
            level_emoji = {"info": "ℹ️", "warning": "⚠️", "critical": "🔴", "emergency": "🚨"}
            logger.log(
                logging.INFO if alert.level == AlertLevel.INFO else
                logging.WARNING if alert.level == AlertLevel.WARNING else
                logging.ERROR if alert.level == AlertLevel.CRITICAL else
                logging.CRITICAL,
                f"{level_emoji.get(alert.level.value, '')} [{alert.level.value.upper()}] {alert.title}: {alert.message}",
            )

    def acknowledge(self, alert_id: str) -> bool:
        for alert in self._alerts:
            if alert.id == alert_id:
                alert.acknowledged = True
                return True
        return False

    def get_alerts(
        self, level: Optional[AlertLevel] = None,
        unacknowledged_only: bool = False, limit: int = 50,
    ) -> List[dict]:
        result = []
        for alert in reversed(self._alerts):
            if level and alert.level != level:
                continue
            if unacknowledged_only and alert.acknowledged:
                continue
            result.append(alert.to_dict())
            if len(result) >= limit:
                break
        return result

    def get_stats(self) -> dict:
        level_counts = {}
        for alert in self._alerts:
            level_counts[alert.level.value] = level_counts.get(alert.level.value, 0) + 1
        return {
            "total_alerts": len(self._alerts),
            "unacknowledged": sum(1 for a in self._alerts if not a.acknowledged),
            "by_level": level_counts,
            "active_groups": len(self._group_tracker),
        }
