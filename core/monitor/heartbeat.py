import logging
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Callable, Dict, List, Optional

logger = logging.getLogger(__name__)


class StrategyStatus(Enum):
    RUNNING = "running"
    WARNING = "warning"
    STOPPED = "stopped"
    ERROR = "error"


@dataclass
class HeartbeatRecord:
    strategy_name: str
    status: StrategyStatus = StrategyStatus.RUNNING
    last_heartbeat: float = 0.0
    latency_ms: float = 0.0
    error_count: int = 0
    last_error: str = ""
    auto_action: str = ""
    timeout_seconds: float = 60.0
    history: List[dict] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "strategy_name": self.strategy_name,
            "status": self.status.value,
            "last_heartbeat": self.last_heartbeat,
            "latency_ms": round(self.latency_ms, 2),
            "error_count": self.error_count,
            "last_error": self.last_error,
            "auto_action": self.auto_action,
            "seconds_since_hb": round(time.time() - self.last_heartbeat, 1) if self.last_heartbeat > 0 else -1,
        }


class StrategyHeartbeatMonitor:
    def __init__(self, timeout_seconds: float = 60.0, max_errors: int = 5):
        self.timeout_seconds = timeout_seconds
        self.max_errors = max_errors
        self._strategies: Dict[str, HeartbeatRecord] = {}
        self._callbacks: Dict[str, List[Callable]] = {}

    def register(self, strategy_name: str, timeout_seconds: float = 30.0):
        self._strategies[strategy_name] = HeartbeatRecord(
            strategy_name=strategy_name, last_heartbeat=time.time(),
            timeout_seconds=timeout_seconds,
        )

    def heartbeat(self, strategy_name: str, latency_ms: float = 0.0):
        if strategy_name not in self._strategies:
            self.register(strategy_name)
        record = self._strategies[strategy_name]
        record.last_heartbeat = time.time()
        record.latency_ms = latency_ms
        if record.status == StrategyStatus.ERROR:
            record.status = StrategyStatus.RUNNING
            record.error_count = 0
        record.history.append({
            "time": time.time(), "status": "heartbeat", "latency_ms": latency_ms,
        })
        if len(record.history) > 1000:
            record.history = record.history[-500:]

    def report(self, strategy_name: str) -> dict:
        if strategy_name not in self._strategies:
            self.register(strategy_name)
        record = self._strategies[strategy_name]
        record.last_heartbeat = time.time()
        if record.status == StrategyStatus.ERROR:
            record.status = StrategyStatus.RUNNING
            record.error_count = 0
        record.history.append({
            "time": time.time(), "status": "report",
        })
        if len(record.history) > 1000:
            record.history = record.history[-500:]
        return {"success": True, **record.to_dict()}

    def report_error(self, strategy_name: str, error: str = ""):
        if strategy_name not in self._strategies:
            self.register(strategy_name)
        record = self._strategies[strategy_name]
        record.error_count += 1
        record.last_error = error
        record.history.append({
            "time": time.time(), "status": "error", "error": error,
        })
        if record.error_count >= self.max_errors:
            record.status = StrategyStatus.ERROR
            record.auto_action = "暂停策略"
            self._fire_callback(strategy_name, "error")

    def check_all(self) -> List[dict]:
        now = time.time()
        results = []
        for name, record in self._strategies.items():
            if record.status == StrategyStatus.STOPPED:
                continue
            elapsed = now - record.last_heartbeat if record.last_heartbeat > 0 else 0
            timeout = record.timeout_seconds or self.timeout_seconds
            if elapsed > timeout:
                record.status = StrategyStatus.WARNING
                record.auto_action = "降仓"
                self._fire_callback(name, "timeout")
            elif record.status != StrategyStatus.ERROR:
                record.status = StrategyStatus.RUNNING
                record.auto_action = ""
            results.append(record.to_dict())
        return results

    def add_callback(self, event_type: str, callback: Callable):
        if event_type not in self._callbacks:
            self._callbacks[event_type] = []
        self._callbacks[event_type].append(callback)

    def _fire_callback(self, strategy_name: str, event_type: str):
        for cb in self._callbacks.get(event_type, []):
            try:
                cb(strategy_name, event_type)
            except Exception as e:
                logger.debug(f"Heartbeat callback error: {e}")

    def get_status(self, strategy_name: str) -> Optional[dict]:
        record = self._strategies.get(strategy_name)
        return record.to_dict() if record else None

    def get_all_status(self) -> Dict[str, dict]:
        return {name: record.to_dict() for name, record in self._strategies.items()}

    def get_history(self, strategy_name: str, limit: int = 100) -> List[dict]:
        record = self._strategies.get(strategy_name)
        if not record:
            return []
        return record.history[-limit:]
