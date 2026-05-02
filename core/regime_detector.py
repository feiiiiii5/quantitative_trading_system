import logging
from dataclasses import dataclass
from enum import Enum
from typing import Dict, List, Optional, Tuple

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)


class MarketRegime(Enum):
    TRENDING_UP = "trending_up"
    TRENDING_DOWN = "trending_down"
    MEAN_REVERTING = "mean_reverting"
    HIGH_VOLATILITY = "high_volatility"
    LOW_VOLATILITY = "low_volatility"
    SIDEWAYS = "sideways"
    UNKNOWN = "unknown"


@dataclass
class RegimeResult:
    current_regime: MarketRegime
    confidence: float
    trend_strength: float
    volatility_level: float
    mean_reversion_score: float
    regime_history: List[MarketRegime]
    transition_probabilities: Dict[str, float]


class RegimeDetector:
    def __init__(
        self,
        trend_window: int = 60,
        vol_window: int = 20,
        adx_threshold: float = 25.0,
        high_vol_threshold: float = 0.30,
        low_vol_threshold: float = 0.10,
        mr_zscore_threshold: float = 1.5,
    ):
        self._trend_window = trend_window
        self._vol_window = vol_window
        self._adx_threshold = adx_threshold
        self._high_vol_threshold = high_vol_threshold
        self._low_vol_threshold = low_vol_threshold
        self._mr_zscore_threshold = mr_zscore_threshold
        self._regime_history: List[MarketRegime] = []

    def _calc_adx(self, high: pd.Series, low: pd.Series, close: pd.Series, period: int = 14) -> pd.Series:
        tr1 = high - low
        tr2 = (high - close.shift(1)).abs()
        tr3 = (low - close.shift(1)).abs()
        tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)

        plus_dm = high.diff()
        minus_dm = -low.diff()
        plus_dm = plus_dm.where((plus_dm > minus_dm) & (plus_dm > 0), 0)
        minus_dm = minus_dm.where((minus_dm > plus_dm) & (minus_dm > 0), 0)

        atr = tr.ewm(alpha=1 / period, min_periods=period, adjust=False).mean()
        plus_di = 100 * (plus_dm.ewm(alpha=1 / period, min_periods=period, adjust=False).mean() / atr.replace(0, np.nan))
        minus_di = 100 * (minus_dm.ewm(alpha=1 / period, min_periods=period, adjust=False).mean() / atr.replace(0, np.nan))

        dx = 100 * ((plus_di - minus_di).abs() / (plus_di + minus_di).replace(0, np.nan))
        adx = dx.ewm(alpha=1 / period, min_periods=period, adjust=False).mean()
        return adx

    def _calc_trend_strength(self, close: pd.Series) -> float:
        if len(close) < self._trend_window:
            return 0.0
        window = close.iloc[-self._trend_window:]
        x = np.arange(len(window))
        y = window.values
        valid = np.isfinite(y)
        if valid.sum() < 5:
            return 0.0
        x_v = x[valid].astype(float)
        y_v = y[valid]
        x_mean = x_v.mean()
        y_mean = y_v.mean()
        ss_tot = np.sum((y_v - y_mean) ** 2)
        if ss_tot < 1e-12:
            return 0.0
        ss_res = np.sum((y_v - (np.polyval(np.polyfit(x_v, y_v, 1), x_v))) ** 2)
        r2 = 1 - ss_res / ss_tot
        slope = np.polyfit(x_v, y_v, 1)[0]
        direction = 1.0 if slope > 0 else -1.0
        return float(r2 * direction)

    def _calc_volatility_level(self, close: pd.Series) -> float:
        if len(close) < self._vol_window:
            return 0.0
        returns = close.pct_change().dropna()
        if len(returns) < self._vol_window:
            return 0.0
        vol = returns.iloc[-self._vol_window:].std() * np.sqrt(252)
        return float(vol)

    def _calc_mean_reversion_score(self, close: pd.Series) -> float:
        if len(close) < 30:
            return 0.0
        window = close.iloc[-30:]
        ma = window.mean()
        std = window.std()
        if std < 1e-12:
            return 0.0
        zscore = (window.iloc[-1] - ma) / std
        returns = window.pct_change().dropna()
        if len(returns) < 5:
            return 0.0
        autocorr = returns.autocorr(lag=1)
        if np.isnan(autocorr):
            return 0.0
        mr_score = -autocorr * (1 + abs(zscore) / self._mr_zscore_threshold)
        return float(mr_score)

    def _calc_hurst_exponent(self, close: pd.Series, max_lag: int = 20) -> float:
        if len(close) < max_lag * 2:
            return 0.5
        returns = np.log(close / close.shift(1)).dropna().values
        if len(returns) < max_lag * 2:
            return 0.5
        lags = range(2, min(max_lag, len(returns) // 2))
        tau = []
        for lag in lags:
            diff = np.diff(returns, lag)
            if len(diff) < 2:
                continue
            tau.append(np.std(diff))
        if len(tau) < 3:
            return 0.5
        log_lags = np.log(np.arange(2, 2 + len(tau)))
        log_tau = np.log(np.array(tau))
        valid = np.isfinite(log_lags) & np.isfinite(log_tau)
        if valid.sum() < 3:
            return 0.5
        try:
            hurst = np.polyfit(log_lags[valid], log_tau[valid], 1)[0]
            return float(np.clip(hurst, 0, 2))
        except Exception:
            return 0.5

    def detect(self, df: pd.DataFrame) -> RegimeResult:
        if df is None or len(df) < 30:
            return RegimeResult(
                current_regime=MarketRegime.UNKNOWN,
                confidence=0.0,
                trend_strength=0.0,
                volatility_level=0.0,
                mean_reversion_score=0.0,
                regime_history=self._regime_history[-10:],
                transition_probabilities={},
            )

        close = df["close"]
        high = df["high"] if "high" in df.columns else close
        low = df["low"] if "low" in df.columns else close

        trend_strength = self._calc_trend_strength(close)
        vol_level = self._calc_volatility_level(close)
        mr_score = self._calc_mean_reversion_score(close)
        hurst = self._calc_hurst_exponent(close)

        adx = self._calc_adx(high, low, close)
        current_adx = float(adx.iloc[-1]) if len(adx) > 0 and not pd.isna(adx.iloc[-1]) else 20.0

        scores = {}

        if trend_strength > 0.3 and current_adx > self._adx_threshold:
            scores[MarketRegime.TRENDING_UP] = abs(trend_strength) * (current_adx / 50)
        elif trend_strength > 0.1:
            scores[MarketRegime.TRENDING_UP] = abs(trend_strength) * 0.5

        if trend_strength < -0.3 and current_adx > self._adx_threshold:
            scores[MarketRegime.TRENDING_DOWN] = abs(trend_strength) * (current_adx / 50)
        elif trend_strength < -0.1:
            scores[MarketRegime.TRENDING_DOWN] = abs(trend_strength) * 0.5

        if mr_score > 0.3:
            scores[MarketRegime.MEAN_REVERTING] = mr_score
        elif hurst < 0.45:
            scores[MarketRegime.MEAN_REVERTING] = (0.5 - hurst) * 2

        if vol_level > self._high_vol_threshold:
            scores[MarketRegime.HIGH_VOLATILITY] = (vol_level - self._high_vol_threshold) / self._high_vol_threshold

        if vol_level < self._low_vol_threshold and vol_level > 0:
            scores[MarketRegime.LOW_VOLATILITY] = (self._low_vol_threshold - vol_level) / self._low_vol_threshold

        if abs(trend_strength) < 0.1 and vol_level < self._high_vol_threshold:
            scores[MarketRegime.SIDEWAYS] = (1 - abs(trend_strength)) * 0.5

        if not scores:
            regime = MarketRegime.SIDEWAYS
            confidence = 0.3
        else:
            regime = max(scores, key=scores.get)
            max_score = scores[regime]
            total_score = sum(scores.values())
            confidence = min(max_score / max(total_score, 1e-10), 1.0)

        self._regime_history.append(regime)
        if len(self._regime_history) > 100:
            self._regime_history = self._regime_history[-100:]

        transition_probs = self._calc_transition_probabilities()

        return RegimeResult(
            current_regime=regime,
            confidence=round(confidence, 4),
            trend_strength=round(trend_strength, 4),
            volatility_level=round(vol_level, 4),
            mean_reversion_score=round(mr_score, 4),
            regime_history=self._regime_history[-10:],
            transition_probabilities=transition_probs,
        )

    def _calc_transition_probabilities(self) -> Dict[str, float]:
        if len(self._regime_history) < 5:
            return {}
        current = self._regime_history[-1]
        transitions = {}
        for i in range(len(self._regime_history) - 1):
            if self._regime_history[i] == current:
                next_regime = self._regime_history[i + 1].value
                transitions[next_regime] = transitions.get(next_regime, 0) + 1
        total = sum(transitions.values())
        if total == 0:
            return {}
        return {k: round(v / total, 4) for k, v in transitions.items()}

    def get_regime_summary(self, result: RegimeResult) -> Dict:
        return {
            "current_regime": result.current_regime.value,
            "confidence": result.confidence,
            "trend_strength": result.trend_strength,
            "volatility_level": result.volatility_level,
            "mean_reversion_score": result.mean_reversion_score,
            "transition_probabilities": result.transition_probabilities,
            "recommended_strategy_type": self._recommend_strategy(result),
        }

    def _recommend_strategy(self, result: RegimeResult) -> str:
        regime = result.current_regime
        if regime == MarketRegime.TRENDING_UP:
            return "momentum"
        elif regime == MarketRegime.TRENDING_DOWN:
            return "short_momentum"
        elif regime == MarketRegime.MEAN_REVERTING:
            return "mean_reversion"
        elif regime == MarketRegime.HIGH_VOLATILITY:
            return "volatility_breakout"
        elif regime == MarketRegime.LOW_VOLATILITY:
            return "carry"
        elif regime == MarketRegime.SIDEWAYS:
            return "mean_reversion"
        else:
            return "balanced"
