"""
实时告警系统 - Real-time Alert System
多渠道、多类型、可配置阈值的告警框架

支持告警类型:
- 价格告警 (突破/跌破)
- 盈亏告警 (达到目标/止损)
- 回撤告警 (超过阈值)
- 状态切换告警 (市场状态变化)
- 自定义告警 (可扩展)

支持渠道:
- 日志 (内置)
- Webhook (可扩展)
- Email (可扩展)
"""
import contextlib
import logging
import threading
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

logger = logging.getLogger(__name__)


class AlertType(Enum):
    PRICE_ABOVE = "price_above"
    PRICE_BELOW = "price_below"
    PNL_TARGET = "pnl_target"
    PNL_STOP_LOSS = "pnl_stop_loss"
    DRAWDOWN = "drawdown"
    REGIME_CHANGE = "regime_change"
    VOLUME_SPIKE = "volume_spike"
    CUSTOM = "custom"


class AlertSeverity(Enum):
    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"


class AlertChannel(Enum):
    LOG = "log"
    WEBHOOK = "webhook"
    EMAIL = "email"


@dataclass
class Alert:
    alert_id: str
    alert_type: AlertType
    severity: AlertSeverity
    symbol: str
    message: str
    value: float
    threshold: float
    timestamp: float = field(default_factory=time.time)
    channel: AlertChannel = AlertChannel.LOG
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "alert_id": self.alert_id,
            "alert_type": self.alert_type.value,
            "severity": self.severity.value,
            "symbol": self.symbol,
            "message": self.message,
            "value": round(self.value, 4),
            "threshold": round(self.threshold, 4),
            "timestamp": self.timestamp,
            "channel": self.channel.value,
            "metadata": self.metadata,
        }


@dataclass
class AlertRule:
    name: str
    alert_type: AlertType
    symbol: str | None
    threshold: float
    severity: AlertSeverity
    channel: AlertChannel = AlertChannel.LOG
    enabled: bool = True
    cooldown_seconds: float = 60.0
    message_template: str = ""


@dataclass
class AlertConfig:
    enabled: bool = True
    default_cooldown: float = 60.0
    max_alerts_per_minute: int = 10
    store_history: bool = True
    max_history: int = 1000


class AlertManager:
    def __init__(self, config: AlertConfig | None = None):
        self._config = config or AlertConfig()
        self._lock = threading.RLock()
        self._rules: dict[str, AlertRule] = {}
        self._history: list[Alert] = []
        self._last_triggered: dict[str, float] = {}
        self._minute_counts: list[tuple[float, int]] = []
        self._subscribers: list[callable] = []
        self._counter = 0

    def add_rule(self, rule: AlertRule) -> str:
        with self._lock:
            rule_id = f"{rule.alert_type.value}_{rule.name}_{rule.symbol or 'global'}"
            self._rules[rule_id] = rule
            return rule_id

    def remove_rule(self, rule_id: str) -> bool:
        with self._lock:
            if rule_id in self._rules:
                del self._rules[rule_id]
                return True
            return False

    def enable_rule(self, rule_id: str) -> bool:
        with self._lock:
            if rule_id in self._rules:
                self._rules[rule_id].enabled = True
                return True
            return False

    def disable_rule(self, rule_id: str) -> bool:
        with self._lock:
            if rule_id in self._rules:
                self._rules[rule_id].enabled = False
                return True
            return False

    def trigger(
        self,
        alert_type: AlertType,
        severity: AlertSeverity,
        symbol: str,
        message: str,
        value: float,
        threshold: float,
        channel: AlertChannel = AlertChannel.LOG,
        metadata: dict | None = None,
    ) -> Alert | None:
        with self._lock:
            if not self._config.enabled:
                return None

            now = time.time()
            if self._should_throttle(now):
                return None

            rule_id = f"{alert_type.value}_{symbol}"
            if rule_id in self._last_triggered:
                last = self._last_triggered[rule_id]
                rule = self._rules.get(rule_id)
                cooldown = (
                    rule.cooldown_seconds
                    if rule
                    else self._config.default_cooldown
                )
                if now - last < cooldown:
                    return None

            self._counter += 1
            alert = Alert(
                alert_id=f"ALT_{self._counter:08d}",
                alert_type=alert_type,
                severity=severity,
                symbol=symbol,
                message=message,
                value=value,
                threshold=threshold,
                timestamp=now,
                channel=channel,
                metadata=metadata or {},
            )

            self._dispatch(alert)
            self._last_triggered[rule_id] = now

            if self._config.store_history:
                self._history.append(alert)
                if len(self._history) > self._config.max_history:
                    self._history = self._history[-self._config.max_history :]

            self._minute_counts.append((now, 1))
            cutoff = now - 60
            self._minute_counts = [(t, c) for t, c in self._minute_counts if t > cutoff]

            return alert

    def _should_throttle(self, now: float) -> bool:
        cutoff = now - 60
        self._minute_counts = [(t, c) for t, c in self._minute_counts if t > cutoff]
        total = sum(c for _, c in self._minute_counts)
        return total >= self._config.max_alerts_per_minute

    def _dispatch(self, alert: Alert) -> None:
        self._log_alert(alert)
        for subscriber in self._subscribers:
            with contextlib.suppress(Exception):
                subscriber(alert)

    def _log_alert(self, alert: Alert) -> None:
        level_map = {
            AlertSeverity.INFO: logger.info,
            AlertSeverity.WARNING: logger.warning,
            AlertSeverity.CRITICAL: logger.critical,
        }
        log_fn = level_map.get(alert.severity, logger.info)
        log_fn(
            f"[{alert.alert_type.value}] {alert.symbol}: {alert.message} "
            f"(value={alert.value:.4f}, threshold={alert.threshold:.4f})"
        )

    def subscribe(self, callback: callable) -> None:
        with self._lock:
            self._subscribers.append(callback)

    def unsubscribe(self, callback: callable) -> None:
        with self._lock:
            if callback in self._subscribers:
                self._subscribers.remove(callback)

    def get_history(
        self,
        alert_type: AlertType | None = None,
        symbol: str | None = None,
        limit: int = 100,
    ) -> list[Alert]:
        with self._lock:
            history = self._history
            if alert_type:
                history = [a for a in history if a.alert_type == alert_type]
            if symbol:
                history = [a for a in history if a.symbol == symbol]
            return history[-limit:]

    def get_active_rules(self) -> list[AlertRule]:
        with self._lock:
            return [r for r in self._rules.values() if r.enabled]

    def check_price_alert(
        self,
        symbol: str,
        current_price: float,
        upper_threshold: float | None = None,
        lower_threshold: float | None = None,
    ) -> Alert | None:
        if upper_threshold and current_price >= upper_threshold:
            return self.trigger(
                AlertType.PRICE_ABOVE,
                AlertSeverity.WARNING,
                symbol,
                f"Price above threshold: {current_price:.4f} >= {upper_threshold:.4f}",
                current_price,
                upper_threshold,
            )
        if lower_threshold and current_price <= lower_threshold:
            return self.trigger(
                AlertType.PRICE_BELOW,
                AlertSeverity.WARNING,
                symbol,
                f"Price below threshold: {current_price:.4f} <= {lower_threshold:.4f}",
                current_price,
                lower_threshold,
            )
        return None

    def check_pnl_alert(
        self,
        symbol: str,
        pnl: float,
        target: float,
        stop_loss: float | None = None,
    ) -> Alert | None:
        if pnl >= target:
            return self.trigger(
                AlertType.PNL_TARGET,
                AlertSeverity.INFO,
                symbol,
                f"PnL target reached: {pnl:.2f} >= {target:.2f}",
                pnl,
                target,
            )
        if stop_loss is not None and pnl <= stop_loss:
            return self.trigger(
                AlertType.PNL_STOP_LOSS,
                AlertSeverity.CRITICAL,
                symbol,
                f"Stop loss triggered: {pnl:.2f} <= {stop_loss:.2f}",
                pnl,
                stop_loss,
            )
        return None

    def check_drawdown_alert(
        self,
        symbol: str,
        current_drawdown: float,
        threshold: float,
    ) -> Alert | None:
        if current_drawdown >= threshold:
            return self.trigger(
                AlertType.DRAWDOWN,
                AlertSeverity.CRITICAL,
                symbol,
                f"Drawdown threshold breached: {current_drawdown:.2%} >= {threshold:.2%}",
                current_drawdown,
                threshold,
            )
        return None

    def check_regime_change(
        self,
        symbol: str,
        old_regime: str,
        new_regime: str,
    ) -> Alert | None:
        if old_regime == new_regime:
            return None
        severity = (
            AlertSeverity.CRITICAL
            if new_regime in ("bear_distribution", "bear_rally")
            else AlertSeverity.WARNING
        )
        return self.trigger(
            AlertType.REGIME_CHANGE,
            severity,
            symbol,
            f"Market regime changed: {old_regime} → {new_regime}",
            0.0,
            0.0,
            metadata={"old_regime": old_regime, "new_regime": new_regime},
        )

    def check_volume_spike(
        self,
        symbol: str,
        current_volume: float,
        avg_volume: float,
        spike_threshold: float = 3.0,
    ) -> Alert | None:
        if avg_volume <= 0:
            return None
        ratio = current_volume / avg_volume
        if ratio >= spike_threshold:
            return self.trigger(
                AlertType.VOLUME_SPIKE,
                AlertSeverity.INFO,
                symbol,
                f"Volume spike: {ratio:.1f}x average ({current_volume:.0f} vs avg {avg_volume:.0f})",
                ratio,
                spike_threshold,
                metadata={
                    "current_volume": current_volume,
                    "avg_volume": avg_volume,
                },
            )
        return None

    def get_alert_summary(self) -> dict:
        with self._lock:
            now = time.time()
            cutoff = now - 3600
            recent = [a for a in self._history if a.timestamp > cutoff]
            by_severity = {}
            for s in AlertSeverity:
                by_severity[s.value] = len([a for a in recent if a.severity == s])
            by_type = {}
            for t in AlertType:
                by_type[t.value] = len([a for a in recent if a.alert_type == t])
            return {
                "total_alerts": len(self._history),
                "active_rules": len(self.get_active_rules()),
                "last_hour": len(recent),
                "by_severity": by_severity,
                "by_type": by_type,
            }


_alert_manager: AlertManager | None = None


def get_alert_manager(config: AlertConfig | None = None) -> AlertManager:
    global _alert_manager
    if _alert_manager is None or config is not None:
        _alert_manager = AlertManager(config)
    return _alert_manager
