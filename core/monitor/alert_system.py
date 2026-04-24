import logging
import time
import httpx
from collections import deque
from dataclasses import dataclass, field
from enum import Enum
from typing import Callable, Dict, List, Optional, Any

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
    SMS = "sms"
    SLACK = "slack"


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
    metadata: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "id": self.id, "level": self.level.value,
            "title": self.title, "message": self.message,
            "source": self.source, "channel": self.channel.value,
            "created_at": time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(self.created_at)),
            "acknowledged": self.acknowledged, "aggregated": self.aggregated,
            "metadata": self.metadata,
        }


class SmartAlertSystem:
    def __init__(self, aggregation_window: float = 300.0):
        self.aggregation_window = aggregation_window
        self._alerts: deque = deque(maxlen=1000)
        self._channels: Dict[AlertChannel, Callable] = {}
        self._alert_counter = 0
        self._group_tracker: Dict[str, List[Alert]] = {}
        self._channel_config: Dict[str, Any] = {}
        self._initialized = False
        self._init_default_channels()

    def _init_default_channels(self):
        """初始化默认告警通道"""
        self._channels[AlertChannel.LOG] = self._log_handler
        self._initialized = True

    def _log_handler(self, alert: Alert):
        """默认日志处理程序"""
        level_emoji = {"info": "ℹ️", "warning": "⚠️", "critical": "🔴", "emergency": "🚨"}
        logger.log(
            logging.INFO if alert.level == AlertLevel.INFO else
            logging.WARNING if alert.level == AlertLevel.WARNING else
            logging.ERROR if alert.level == AlertLevel.CRITICAL else
            logging.CRITICAL,
            f"{level_emoji.get(alert.level.value, '')} [{alert.level.value.upper()}] {alert.title}: {alert.message}",
            extra={"alert_id": alert.id, "source": alert.source, "metadata": alert.metadata}
        )

    def _dingtalk_handler(self, alert: Alert):
        """钉钉告警处理程序"""
        webhook = self._channel_config.get("dingtalk_webhook")
        if not webhook:
            return
        
        level_color = {"info": "#007FFF", "warning": "#FFA500", "critical": "#FF0000", "emergency": "#8B0000"}
        color = level_color.get(alert.level.value, "#007FFF")
        
        data = {
            "msgtype": "markdown",
            "markdown": {
                "title": f"{alert.level.value.upper()}: {alert.title}",
                "text": f"### {alert.title}\n" +
                        f"> 级别: **{alert.level.value.upper()}**\n" +
                        f"> 来源: {alert.source}\n" +
                        f"> 时间: {time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(alert.created_at))}\n" +
                        f"> 内容: {alert.message}\n" +
                        (f"> 详情: {alert.metadata}\n" if alert.metadata else "")
            }
        }
        
        try:
            httpx.post(webhook, json=data, timeout=5.0)
        except Exception as e:
            logger.error(f"DingTalk alert dispatch error: {e}")

    def _wechat_handler(self, alert: Alert):
        """企业微信告警处理程序"""
        webhook = self._channel_config.get("wechat_webhook")
        if not webhook:
            return
        
        data = {
            "msgtype": "text",
            "text": {
                "content": f"【{alert.level.value.upper()}】{alert.title}\n" +
                          f"来源: {alert.source}\n" +
                          f"内容: {alert.message}\n" +
                          f"时间: {time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(alert.created_at))}"
            }
        }
        
        try:
            httpx.post(webhook, json=data, timeout=5.0)
        except Exception as e:
            logger.error(f"WeChat alert dispatch error: {e}")

    def register_channel(self, channel: AlertChannel, handler: Callable):
        self._channels[channel] = handler

    def send_alert(
        self,
        title: str,
        message: str,
        level: AlertLevel = AlertLevel.WARNING,
        source: str = "",
        channels: Optional[List[AlertChannel]] = None,
        metadata: Optional[dict] = None,
    ) -> Alert:
        self._alert_counter += 1
        primary_channel = channels[0] if channels else AlertChannel.LOG
        alert = Alert(
            id=f"alert_{self._alert_counter:06d}",
            level=level, title=title, message=message,
            source=source, channel=primary_channel,
            created_at=time.time(),
            group_key=f"{source}:{title}",
            metadata=metadata or {},
        )

        # 告警聚合
        if alert.group_key:
            now = time.time()
            group = self._group_tracker.get(alert.group_key, [])
            recent = [a for a in group if now - a.created_at < self.aggregation_window]
            if recent:
                alert.aggregated = True
                # 更新聚合信息
                alert.metadata["aggregated_count"] = len(recent) + 1
            recent.append(alert)
            self._group_tracker[alert.group_key] = recent

        self._alerts.append(alert)

        # 分发告警
        if channels:
            for ch in channels:
                handler = self._channels.get(ch)
                if handler:
                    try:
                        handler(alert)
                    except Exception as e:
                        logger.error(f"Alert dispatch error for {ch}: {e}")
        else:
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
            self._log_handler(alert)

    def acknowledge(self, alert_id: str) -> dict:
        for alert in self._alerts:
            if alert.id == alert_id:
                alert.acknowledged = True
                return {"success": True, "alert_id": alert_id, "acknowledged": True}
        return {"success": False, "alert_id": alert_id, "acknowledged": False, "error": "告警未找到"}

    def get_alerts(self, filters: Optional[dict] = None, limit: int = 50) -> List[Alert]:
        result = []
        level_filter = filters.get("level") if filters else None
        ack_filter = filters.get("acknowledged") if filters else None
        source_filter = filters.get("source") if filters else None

        for alert in reversed(self._alerts):
            if level_filter and alert.level != level_filter:
                continue
            if ack_filter is not None and alert.acknowledged != ack_filter:
                continue
            if source_filter and alert.source != source_filter:
                continue
            result.append(alert)
            if len(result) >= limit:
                break
        return result

    def configure_channels(self, config: dict):
        self._channel_config.update(config)
        
        # 自动注册通道处理程序
        if config.get("dingtalk_webhook"):
            self.register_channel(AlertChannel.DINGTALK, self._dingtalk_handler)
        if config.get("wechat_webhook"):
            self.register_channel(AlertChannel.WECHAT, self._wechat_handler)

    def get_stats(self) -> dict:
        level_counts = {}
        source_counts = {}
        for alert in self._alerts:
            level_counts[alert.level.value] = level_counts.get(alert.level.value, 0) + 1
            source_counts[alert.source] = source_counts.get(alert.source, 0) + 1
        
        return {
            "total_alerts": len(self._alerts),
            "unacknowledged": sum(1 for a in self._alerts if not a.acknowledged),
            "by_level": level_counts,
            "by_source": source_counts,
            "active_groups": len(self._group_tracker),
            "configured_channels": list(self._channel_config.keys()),
            "registered_channels": [ch.value for ch in self._channels.keys()],
        }

    def clear_old_alerts(self, hours: int = 24):
        """清理指定小时数之前的告警"""
        cutoff = time.time() - (hours * 3600)
        self._alerts = deque([a for a in self._alerts if a.created_at >= cutoff], maxlen=1000)
        
        # 清理过期的告警组
        now = time.time()
        self._group_tracker = {
            k: v for k, v in self._group_tracker.items()
            if any(a.created_at >= cutoff for a in v)
        }

    def send_heartbeat(self, source: str = "system"):
        """发送心跳告警"""
        self.send_alert(
            title="系统心跳",
            message="系统运行正常",
            level=AlertLevel.INFO,
            source=source,
            metadata={"timestamp": time.time()}
        )
