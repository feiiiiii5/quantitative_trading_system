import logging
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional

import numpy as np

logger = logging.getLogger(__name__)


class CircuitState(Enum):
    NORMAL = "normal"
    COOLING = "cooling"
    TRIPPED = "tripped"


@dataclass
class CircuitBreakerConfig:
    max_drawdown_pct: float = 0.15
    max_daily_loss_pct: float = 0.05
    max_consecutive_losses: int = 5
    cooldown_seconds: int = 300
    volatility_threshold: float = 0.03
    min_volume_ratio: float = 0.3
    enable_circuit_breaker: bool = True


@dataclass
class CircuitEvent:
    timestamp: float
    trigger_type: str
    value: float
    threshold: float
    action: str


class RiskCircuitBreaker:
    def __init__(self, config: Optional[CircuitBreakerConfig] = None):
        self.config = config or CircuitBreakerConfig()
        self._state = CircuitState.NORMAL
        self._tripped_at: Optional[float] = None
        self._events: List[CircuitEvent] = []
        self._daily_losses: List[float] = []
        self._consecutive_losses = 0
        self._peak_equity = 0
        self._last_reset_date: Optional[str] = None

    @property
    def state(self) -> str:
        return self._state.value

    @property
    def is_open(self) -> bool:
        if self._state == CircuitState.TRIPPED:
            if time.time() - self._tripped_at >= self.config.cooldown_seconds:
                self._state = CircuitState.COOLING
                logger.info("Circuit breaker cooling period ended, entering cooling state")
        return self._state == CircuitState.TRIPPED

    def record_trade(self, pnl: float, equity: float, timestamp: Optional[float] = None):
        ts = timestamp or time.time()
        if pnl < 0:
            self._consecutive_losses += 1
        else:
            self._consecutive_losses = 0

        if equity > self._peak_equity:
            self._peak_equity = equity

        current_drawdown = (self._peak_equity - equity) / self._peak_equity if self._peak_equity > 0 else 0
        if self._peak_equity > 0 and current_drawdown >= self.config.max_drawdown_pct:
            self._trip(f"drawdown_{current_drawdown:.2%}", current_drawdown, self.config.max_drawdown_pct, "max_drawdown")
            return

        if self._consecutive_losses >= self.config.max_consecutive_losses:
            self._trip(f"consecutive_losses_{self._consecutive_losses}", self._consecutive_losses, self.config.max_consecutive_losses, "max_losses")
            return

        event = CircuitEvent(
            timestamp=ts, trigger_type="trade", value=pnl,
            threshold=0, action="recorded"
        )
        self._events.append(event)
        self._trim_events()

    def record_daily_loss(self, loss_pct: float, timestamp: Optional[float] = None):
        ts = timestamp or time.time()
        self._daily_losses.append(loss_pct)
        if len(self._daily_losses) > 30:
            self._daily_losses = self._daily_losses[-30:]

        if loss_pct >= self.config.max_daily_loss_pct:
            self._trip(f"daily_loss_{loss_pct:.2%}", loss_pct, self.config.max_daily_loss_pct, "max_daily_loss")

        event = CircuitEvent(
            timestamp=ts, trigger_type="daily_loss", value=loss_pct,
            threshold=self.config.max_daily_loss_pct, action="recorded"
        )
        self._events.append(event)
        self._trim_events()

    def check_volatility(self, returns: List[float]) -> bool:
        if len(returns) < 5:
            return True

        vol = np.std(returns) if len(returns) > 1 else 0
        if vol >= self.config.volatility_threshold:
            self._trip(f"high_volatility_{vol:.4f}", vol, self.config.volatility_threshold, "volatility")
            return False
        return True

    def check_volume(self, current_volume: float, avg_volume: float) -> bool:
        if avg_volume <= 0:
            return True
        ratio = current_volume / avg_volume
        if ratio < self.config.min_volume_ratio:
            self._trip(f"low_volume_{ratio:.2f}", ratio, self.config.min_volume_ratio, "volume")
            return False
        return True

    def can_trade(self) -> bool:
        if not self.config.enable_circuit_breaker:
            return True

        if self._state == CircuitState.TRIPPED:
            if time.time() - self._tripped_at >= self.config.cooldown_seconds:
                self._state = CircuitState.COOLING
                logger.info("Circuit breaker entering cooling state")
                return True
            logger.warning(f"Circuit breaker tripped, trading disabled for {self.config.cooldown_seconds}s")
            return False

        if self._state == CircuitState.COOLING:
            if time.time() - self._tripped_at >= self.config.cooldown_seconds * 2:
                self._state = CircuitState.NORMAL
                logger.info("Circuit breaker reset to normal")
            return True

        return True

    def _trip(self, reason: str, value: float, threshold: float, trigger_type: str):
        if self._state == CircuitState.TRIPPED:
            return

        self._state = CircuitState.TRIPPED
        self._tripped_at = time.time()
        logger.critical(f"CIRCUIT BREAKER TRIPPED: {reason}, value={value:.4f}, threshold={threshold:.4f}")

        event = CircuitEvent(
            timestamp=self._tripped_at, trigger_type=trigger_type,
            value=value, threshold=threshold, action="tripped"
        )
        self._events.append(event)

    def reset(self, full_reset: bool = True):
        if full_reset:
            self._state = CircuitState.NORMAL
            self._tripped_at = None
            self._events.clear()
            self._daily_losses.clear()
            self._consecutive_losses = 0
            self._peak_equity = 0
            logger.info("Circuit breaker fully reset")
        else:
            self._state = CircuitState.NORMAL
            self._tripped_at = None
            logger.info("Circuit breaker reset to cooling")

    def get_status(self) -> dict:
        return {
            "state": self._state.value,
            "is_open": self.is_open,
            "can_trade": self.can_trade(),
            "tripped_at": self._tripped_at,
            "cooldown_remaining": max(0, self.config.cooldown_seconds - (time.time() - self._tripped_at)) if self._tripped_at else 0,
            "consecutive_losses": self._consecutive_losses,
            "peak_equity": self._peak_equity,
            "recent_events": len(self._events[-10:]),
            "config": {
                "max_drawdown_pct": self.config.max_drawdown_pct,
                "max_daily_loss_pct": self.config.max_daily_loss_pct,
                "max_consecutive_losses": self.config.max_consecutive_losses,
                "cooldown_seconds": self.config.cooldown_seconds,
                "enable_circuit_breaker": self.config.enable_circuit_breaker,
            },
        }

    def get_events(self, limit: int = 50) -> List[dict]:
        events = self._events[-limit:]
        return [
            {
                "timestamp": e.timestamp,
                "trigger_type": e.trigger_type,
                "value": round(e.value, 4) if isinstance(e.value, float) else e.value,
                "threshold": round(e.threshold, 4) if isinstance(e.threshold, float) else e.threshold,
                "action": e.action,
            }
            for e in reversed(events)
        ]

    def _trim_events(self):
        max_events = 1000
        if len(self._events) > max_events:
            self._events = self._events[-max_events:]
