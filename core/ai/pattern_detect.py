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

    def detect(self, prices: np.ndarray, volumes: Optional[np.ndarray] = None, timestamps: Optional[List[str]] = None) -> List[PatternMatch]:
        results = []
        symbol = ""

        if len(prices) >= 20 and volumes is not None and len(volumes) >= 20:
            vp = self.detect_volume_price_anomaly(symbol, volumes, prices)
            if vp:
                results.append(vp)

        if len(prices) >= 5:
            tail = self.detect_tail_manipulation(symbol, prices)
            if tail:
                results.append(tail)

        if timestamps and len(prices) >= 2:
            opening = self.detect_opening_anomaly(symbol, prices[:-1], prices[1:])
            if opening:
                results.append(opening)

        return results

    def check_volume_price_anomaly(
        self, symbol: str, current_volume: float, avg_volume: float,
        current_price: float, prev_price: float = 0,
    ) -> dict:
        vol_ratio = current_volume / avg_volume if avg_volume > 0 else 0
        price_change = (current_price / prev_price - 1) if prev_price > 0 else 0

        is_anomaly = False
        anomaly_type = ""
        confidence = 0.0

        if vol_ratio > 2.0 and abs(price_change) > 0.03:
            is_anomaly = True
            anomaly_type = "放量突破" if price_change > 0 else "放量下跌"
            confidence = min(vol_ratio / 5, 1.0)
        elif vol_ratio < 0.3 and abs(price_change) > 0.02:
            is_anomaly = True
            anomaly_type = "缩量异动"
            confidence = 0.6
        elif vol_ratio > 3.0:
            is_anomaly = True
            anomaly_type = "异常放量"
            confidence = min(vol_ratio / 5, 1.0)

        result = {
            "symbol": symbol,
            "is_anomaly": is_anomaly,
            "anomaly_type": anomaly_type,
            "confidence": round(confidence, 4),
            "vol_ratio": round(vol_ratio, 2),
            "price_change": round(price_change, 4),
        }

        if is_anomaly:
            match = PatternMatch(
                pattern_type=anomaly_type, symbol=symbol,
                confidence=confidence,
                details={"vol_ratio": round(vol_ratio, 2), "price_change": round(price_change, 4)},
                timestamp=time.strftime("%Y-%m-%d %H:%M:%S"),
            )
            self._patterns.append(match)

        return result

    def detect_manipulation(
        self, symbol: str, prices: np.ndarray, vols: np.ndarray,
        timestamps: Optional[List[str]] = None,
    ) -> List[PatternMatch]:
        results = []
        if len(prices) < 5 or len(vols) < 5:
            return results

        consecutive_anomaly = 0
        avg_vol = np.mean(vols[-20:]) if len(vols) >= 20 else np.mean(vols)

        for i in range(max(0, len(vols) - 10), len(vols)):
            if avg_vol > 0 and vols[i] > avg_vol * 3:
                consecutive_anomaly += 1
            else:
                consecutive_anomaly = 0

            if consecutive_anomaly >= 3:
                price_change = (prices[i] / prices[max(0, i - consecutive_anomaly)] - 1) if i >= consecutive_anomaly else 0
                pattern_type = "连续大单拉升" if price_change > 0 else "连续大单打压"
                match = PatternMatch(
                    pattern_type=pattern_type, symbol=symbol,
                    confidence=min(consecutive_anomaly / 5, 1.0),
                    details={
                        "consecutive_anomaly": consecutive_anomaly,
                        "price_change": round(price_change, 4),
                        "vol_ratio": round(vols[i] / avg_vol, 2) if avg_vol > 0 else 0,
                    },
                    timestamp=timestamps[i] if timestamps and i < len(timestamps) else time.strftime("%Y-%m-%d %H:%M:%S"),
                )
                results.append(match)
                self._patterns.append(match)
                break

        tail = self.detect_tail_manipulation(symbol, prices)
        if tail:
            results.append(tail)

        return results

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

    def find_similar_historical(self, pattern_type: str, symbol: str = "", limit: int = 10) -> List[str]:
        similars = []
        for p in self._patterns[-200:]:
            if p.pattern_type == pattern_type and p.symbol != symbol:
                similars.append(f"{p.symbol}@{p.timestamp}")
        return similars[:limit]

    def get_recent_patterns(self, limit: int = 50) -> List[dict]:
        return [p.to_dict() for p in self._patterns[-limit:]]

    def get_pattern_stats(self) -> dict:
        type_counts = {}
        for p in self._patterns:
            type_counts[p.pattern_type] = type_counts.get(p.pattern_type, 0) + 1
        return {"total_patterns": len(self._patterns), "by_type": type_counts}
