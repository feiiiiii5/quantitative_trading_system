import logging
from dataclasses import dataclass, field
from typing import List, Optional

import numpy as np

logger = logging.getLogger(__name__)


@dataclass
class RegimeState:
    name: str
    volatility: float = 0.0
    trend: str = "neutral"
    duration_days: int = 0
    optimal_params: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "name": self.name, "volatility": round(self.volatility, 4),
            "trend": self.trend, "duration_days": self.duration_days,
            "optimal_params": self.optimal_params,
        }


REGIME_PARAMS = {
    "bull_low_vol": {"fast": 10, "slow": 30, "rsi_period": 14, "stop_pct": 0.05},
    "bull_high_vol": {"fast": 5, "slow": 20, "rsi_period": 10, "stop_pct": 0.08},
    "bear_low_vol": {"fast": 15, "slow": 40, "rsi_period": 20, "stop_pct": 0.03},
    "bear_high_vol": {"fast": 20, "slow": 50, "rsi_period": 25, "stop_pct": 0.02},
    "sideways": {"fast": 7, "slow": 25, "rsi_period": 14, "stop_pct": 0.04},
}


class AdaptiveParamOptimizer:
    def __init__(self, reoptimize_interval: int = 20, window: int = 60):
        self.reoptimize_interval = reoptimize_interval
        self.window = window
        self._current_regime: Optional[RegimeState] = None
        self._current_params: dict = {}
        self._last_optimize: int = 0
        self._regime_history: List[RegimeState] = []

    def detect_regime(self, returns: np.ndarray, window: int = 60) -> RegimeState:
        effective_window = min(window, len(returns))
        if effective_window < 10:
            return RegimeState("unknown")

        recent_ret = returns[-effective_window:]

        rolling_vol = np.array([
            np.std(returns[max(0, i - 20):i + 1])
            for i in range(len(returns))
        ])
        recent_vol = rolling_vol[-effective_window:]

        avg_ret = np.mean(recent_ret)
        avg_vol = np.mean(recent_vol) if len(recent_vol) > 0 else np.std(recent_ret)

        if avg_ret > 0.001:
            trend = "bull"
        elif avg_ret < -0.001:
            trend = "bear"
        else:
            trend = "sideways"

        vol_median = np.median(rolling_vol) if len(rolling_vol) > 0 else avg_vol
        vol_level = "high" if avg_vol > vol_median * 1.5 else "low"

        if trend == "bull":
            name = f"bull_{vol_level}_vol"
        elif trend == "bear":
            name = f"bear_{vol_level}_vol"
        else:
            name = "sideways"

        optimal_params = REGIME_PARAMS.get(name, REGIME_PARAMS["sideways"])

        regime = RegimeState(
            name=name, volatility=avg_vol, trend=trend,
            duration_days=effective_window, optimal_params=optimal_params,
        )

        if self._current_regime and self._current_regime.name != name:
            self._regime_history.append(self._current_regime)

        self._current_regime = regime
        self._current_params = optimal_params
        return regime

    def get_optimal_params(self, strategy_name: str, regime_name: str = "") -> dict:
        if regime_name:
            base_params = REGIME_PARAMS.get(regime_name, REGIME_PARAMS["sideways"])
        elif self._current_regime:
            base_params = self._current_params or REGIME_PARAMS.get(
                self._current_regime.name, REGIME_PARAMS["sideways"]
            )
        else:
            base_params = REGIME_PARAMS["sideways"]

        return {
            "strategy": strategy_name,
            "regime": regime_name or (self._current_regime.name if self._current_regime else "sideways"),
            "params": base_params,
        }

    def rolling_optimize(self, strategy_name: str, returns: np.ndarray, window: int = 60, step: int = 20) -> List[dict]:
        results = []
        n = len(returns)
        if n < window:
            regime = self.detect_regime(returns, window)
            results.append({
                "start": 0, "end": n,
                "regime": regime.name,
                "params": self.get_optimal_params(strategy_name, regime.name),
            })
            return results

        for start in range(0, n - window + 1, step):
            segment = returns[start:start + window]
            regime = self.detect_regime(segment, window)
            results.append({
                "start": start, "end": start + window,
                "regime": regime.name,
                "params": self.get_optimal_params(strategy_name, regime.name),
            })

        return results

    def get_regime_param_map(self, strategy_name: str = "") -> dict:
        result = {}
        for regime_name, params in REGIME_PARAMS.items():
            result[regime_name] = {
                "strategy": strategy_name,
                "regime": regime_name,
                "params": params,
            }
        return result

    def should_reoptimize(self, bar_count: int) -> bool:
        if bar_count - self._last_optimize >= self.reoptimize_interval:
            return True
        if self._current_regime and self._regime_history and self._current_regime.name != self._regime_history[-1].name:
            return True
        return False

    def update_with_rolling_window(self, returns: np.ndarray, bar_count: int) -> dict:
        if not self.should_reoptimize(bar_count):
            return {"regime": self._current_regime.to_dict() if self._current_regime else {},
                    "params": self._current_params, "reoptimized": False}

        regime = self.detect_regime(returns, self.window)
        self._last_optimize = bar_count

        return {"regime": regime.to_dict(), "params": self._current_params, "reoptimized": True}

    def get_regime_history(self) -> List[dict]:
        return [r.to_dict() for r in self._regime_history[-20:]]

    def get_info(self) -> dict:
        return {
            "current_regime": self._current_regime.to_dict() if self._current_regime else None,
            "current_params": self._current_params,
            "reoptimize_interval": self.reoptimize_interval,
            "window": self.window,
            "available_regimes": list(REGIME_PARAMS.keys()),
        }
