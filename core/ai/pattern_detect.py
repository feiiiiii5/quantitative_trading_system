import logging
import time
from dataclasses import dataclass, field
from typing import Dict, List, Optional

import numpy as np

logger = logging.getLogger(__name__)


@dataclass
class PatternMatch:
    pattern_type: str
    symbol: str
    confidence: float = 0.0
    details: dict = field(default_factory=dict)
    historical_similars: List[str] = field(default_factory=list)
    timestamp: str = ""

    def to_dict(self) -> dict:
        return {
            "pattern_type": self.pattern_type, "symbol": self.symbol,
            "confidence": round(self.confidence, 4), "details": self.details,
            "historical_similars": self.historical_similars,
            "timestamp": self.timestamp,
        }


class AnomalyPatternDetector:
    def __init__(self):
        self._patterns: List[PatternMatch] = []
        self._historical_patterns: Dict[str, List[dict]] = {}

    def detect_volume_price_anomaly(
        self, symbol: str, volumes: np.ndarray, prices: np.ndarray,
    ) -> Optional[PatternMatch]:
        if len(volumes) < 20 or len(prices) < 20:
            return None

        recent_vol = volumes[-5:]
        avg_vol = np.mean(volumes[-20:])
        recent_ret = (prices[-1] / prices[-5] - 1)

        vol_ratio = np.mean(recent_vol) / avg_vol if avg_vol > 0 else 0

        if vol_ratio > 2.0 and abs(recent_ret) > 0.03:
            pattern_type = "放量突破" if recent_ret > 0 else "放量下跌"
            confidence = min(vol_ratio / 5, 1.0)
            match = PatternMatch(
                pattern_type=pattern_type, symbol=symbol,
                confidence=confidence,
                details={"vol_ratio": round(vol_ratio, 2), "price_change": round(recent_ret, 4)},
                timestamp=time.strftime("%Y-%m-%d %H:%M:%S"),
            )
            self._patterns.append(match)
            return match

        if vol_ratio < 0.3 and abs(recent_ret) > 0.02:
            match = PatternMatch(
                pattern_type="缩量异动", symbol=symbol,
                confidence=0.6,
                details={"vol_ratio": round(vol_ratio, 2), "price_change": round(recent_ret, 4)},
                timestamp=time.strftime("%Y-%m-%d %H:%M:%S"),
            )
            self._patterns.append(match)
            return match

        return None

    def detect_tail_manipulation(
        self, symbol: str, close_prices: np.ndarray, vwap: Optional[np.ndarray] = None,
    ) -> Optional[PatternMatch]:
        if len(close_prices) < 5:
            return None

        last_price = close_prices[-1]
        prev_price = close_prices[-2]
        tail_change = (last_price / prev_price - 1)

        if abs(tail_change) > 0.02:
            pattern_type = "尾盘拉升" if tail_change > 0 else "尾盘打压"
            match = PatternMatch(
                pattern_type=pattern_type, symbol=symbol,
                confidence=min(abs(tail_change) * 20, 1.0),
                details={"tail_change": round(tail_change * 100, 2)},
                timestamp=time.strftime("%Y-%m-%d %H:%M:%S"),
            )
            self._patterns.append(match)
            return match

        return None

    def detect_opening_anomaly(
        self, symbol: str, open_prices: np.ndarray, prev_closes: np.ndarray,
    ) -> Optional[PatternMatch]:
        if len(open_prices) < 2 or len(prev_closes) < 2:
            return None

        gap = (open_prices[-1] / prev_closes[-1] - 1)
        if abs(gap) > 0.03:
            pattern_type = "开盘跳空高开" if gap > 0 else "开盘跳空低开"
            match = PatternMatch(
                pattern_type=pattern_type, symbol=symbol,
                confidence=min(abs(gap) * 15, 1.0),
                details={"gap_pct": round(gap * 100, 2)},
                timestamp=time.strftime("%Y-%m-%d %H:%M:%S"),
            )
            self._patterns.append(match)
            return match

        return None

    def find_similar_historical(self, current_pattern: PatternMatch, lookback: int = 100) -> List[str]:
        similars = []
        for p in self._patterns[-lookback:]:
            if p.pattern_type == current_pattern.pattern_type and p.symbol != current_pattern.symbol:
                similars.append(f"{p.symbol}@{p.timestamp}")
        return similars[:5]

    def get_recent_patterns(self, limit: int = 50) -> List[dict]:
        return [p.to_dict() for p in self._patterns[-limit:]]

    def get_pattern_stats(self) -> dict:
        type_counts = {}
        for p in self._patterns:
            type_counts[p.pattern_type] = type_counts.get(p.pattern_type, 0) + 1
        return {"total_patterns": len(self._patterns), "by_type": type_counts}
