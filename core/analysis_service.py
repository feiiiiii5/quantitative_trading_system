from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Iterable

import numpy as np
import pandas as pd

from core.database import get_db
from core.indicators import IndicatorAnalysis, KLinePatternRecognizer, TechnicalIndicators


@dataclass
class SignalVerificationResult:
    signal_type: str
    total_signals: int
    avg_return_5d: float
    avg_return_10d: float
    avg_return_20d: float
    win_rate_5d: float
    win_rate_10d: float
    win_rate_20d: float

    def to_dict(self) -> dict:
        return {
            "signal_type": self.signal_type,
            "total_signals": self.total_signals,
            "avg_return_5d": round(self.avg_return_5d, 4),
            "avg_return_10d": round(self.avg_return_10d, 4),
            "avg_return_20d": round(self.avg_return_20d, 4),
            "win_rate_5d": round(self.win_rate_5d, 4),
            "win_rate_10d": round(self.win_rate_10d, 4),
            "win_rate_20d": round(self.win_rate_20d, 4),
        }


class AnalysisService:
    def __init__(self):
        self._db = get_db()

    def ma_alignment(self, df: pd.DataFrame) -> dict:
        return IndicatorAnalysis.ma_alignment(df)

    def kline_patterns(self, df: pd.DataFrame) -> list[dict]:
        return KLinePatternRecognizer.recognize(df)

    def support_resistance(self, df: pd.DataFrame) -> dict:
        return IndicatorAnalysis.support_resistance(df)

    def vpvr(self, df: pd.DataFrame, bins: int = 24, lookback: int = 120) -> dict:
        return IndicatorAnalysis.vpvr(df, bins=bins, lookback=lookback)

    def trend_lines(self, df: pd.DataFrame, lookback: int = 120) -> dict:
        return IndicatorAnalysis.trend_lines(df, lookback=lookback)

    def volatility_range(self, df: pd.DataFrame) -> dict:
        return IndicatorAnalysis.volatility_range(df)

    def volume_price_analysis(self, df: pd.DataFrame) -> dict:
        return IndicatorAnalysis.volume_price_analysis(df)

    def boll_squeeze(self, df: pd.DataFrame) -> dict:
        return IndicatorAnalysis.boll_squeeze(df)

    def rsi_divergence(self, df: pd.DataFrame) -> dict:
        return IndicatorAnalysis.rsi_divergence(df)

    def relative_strength(self, df: pd.DataFrame, benchmark_df: pd.DataFrame) -> dict:
        return IndicatorAnalysis.relative_strength(df, benchmark_df)

    def signal_verify(self, df: pd.DataFrame, signal_type: str) -> SignalVerificationResult:
        if df is None or len(df) < 60:
            return SignalVerificationResult(signal_type, 0, 0, 0, 0, 0, 0, 0)
        signal_type = signal_type.lower()
        closes = df["close"].astype(float).values
        signals = self._locate_signals(df, signal_type)
        forward_5 = []
        forward_10 = []
        forward_20 = []
        for idx in signals:
            if idx + 5 < len(closes):
                forward_5.append((closes[idx + 5] - closes[idx]) / closes[idx] * 100)
            if idx + 10 < len(closes):
                forward_10.append((closes[idx + 10] - closes[idx]) / closes[idx] * 100)
            if idx + 20 < len(closes):
                forward_20.append((closes[idx + 20] - closes[idx]) / closes[idx] * 100)

        return SignalVerificationResult(
            signal_type=signal_type,
            total_signals=len(signals),
            avg_return_5d=float(np.mean(forward_5)) if forward_5 else 0,
            avg_return_10d=float(np.mean(forward_10)) if forward_10 else 0,
            avg_return_20d=float(np.mean(forward_20)) if forward_20 else 0,
            win_rate_5d=float(np.mean(np.array(forward_5) > 0) * 100) if forward_5 else 0,
            win_rate_10d=float(np.mean(np.array(forward_10) > 0) * 100) if forward_10 else 0,
            win_rate_20d=float(np.mean(np.array(forward_20) > 0) * 100) if forward_20 else 0,
        )

    def _locate_signals(self, df: pd.DataFrame, signal_type: str) -> list[int]:
        closes = df["close"].astype(float).values
        highs = df["high"].astype(float).values
        lows = df["low"].astype(float).values
        if signal_type in {"macd金叉", "macd_golden_cross", "macd"}:
            macd = TechnicalIndicators._macd(closes)
            hist = np.array(macd["hist"])
            return [i for i in range(1, len(hist)) if hist[i - 1] <= 0 < hist[i]]
        if signal_type in {"ma金叉", "ma5_ma20", "ma"}:
            ma5 = pd.Series(closes).rolling(5).mean().values
            ma20 = pd.Series(closes).rolling(20).mean().values
            return [i for i in range(20, len(closes)) if ma5[i - 1] <= ma20[i - 1] and ma5[i] > ma20[i]]
        if signal_type in {"rsi超卖", "rsi_oversold", "rsi"}:
            rsi = TechnicalIndicators._rsi(closes)[6]
            rsi_arr = np.array(rsi)
            return [i for i in range(1, len(rsi_arr)) if rsi_arr[i - 1] < 30 <= rsi_arr[i]]
        atr = TechnicalIndicators._atr(highs, lows, closes)
        return [i for i in range(20, len(atr)) if atr[i] > np.nanmean(atr[max(0, i - 20):i])]

    def calendar_effect(self, df: pd.DataFrame) -> dict:
        if df is None or df.empty:
            return {"monthly": [], "weekday": []}
        data = df.copy()
        data["date"] = pd.to_datetime(data["date"])
        data["return"] = data["close"].astype(float).pct_change() * 100
        data = data.dropna(subset=["return"])
        data["month"] = data["date"].dt.month
        data["weekday"] = data["date"].dt.dayofweek
        monthly = (
            data.groupby("month")["return"].agg(["mean", "count"])
            .reset_index()
            .rename(columns={"mean": "avg_return", "count": "samples"})
            .to_dict("records")
        )
        weekday = (
            data.groupby("weekday")["return"].agg(["mean", "count"])
            .reset_index()
            .rename(columns={"mean": "avg_return", "count": "samples"})
            .to_dict("records")
        )
        return {"monthly": monthly, "weekday": weekday}

    def holding_period_analysis(self, df: pd.DataFrame, entry_condition: str = "macd_golden_cross") -> dict:
        signals = self._locate_signals(df, entry_condition)
        closes = df["close"].astype(float).values
        horizons = [1, 5, 10, 20, 60]
        stats = []
        for horizon in horizons:
            returns = []
            for idx in signals:
                if idx + horizon < len(closes):
                    returns.append((closes[idx + horizon] - closes[idx]) / closes[idx] * 100)
            stats.append(
                {
                    "holding_days": horizon,
                    "avg_return": round(float(np.mean(returns)), 4) if returns else 0,
                    "win_rate": round(float(np.mean(np.array(returns) > 0) * 100), 4) if returns else 0,
                    "samples": len(returns),
                }
            )
        best = max(stats, key=lambda item: item["avg_return"]) if stats else {}
        return {"signals": len(signals), "stats": stats, "best_holding_period": best}

    def correlation_matrix(self, datasets: dict[str, pd.DataFrame]) -> dict:
        returns = {}
        for symbol, df in datasets.items():
            if df is None or df.empty:
                continue
            returns[symbol] = df["close"].astype(float).pct_change().dropna()
        if not returns:
            return {"symbols": [], "matrix": []}
        merged = pd.DataFrame(returns).dropna(how="all")
        corr = merged.corr().fillna(0)
        return {"symbols": corr.columns.tolist(), "matrix": corr.round(4).values.tolist()}

    def industry_comparison(self, symbol: str, base_df: pd.DataFrame, peers: Iterable[dict]) -> list[dict]:
        if base_df is None or base_df.empty:
            return []
        base_return = self._window_return(base_df, 20)
        results = []
        for peer in peers:
            peer_symbol = peer.get("code") or peer.get("symbol")
            peer_df = self._db.load_kline_rows(peer_symbol, peer.get("market", "A"), "daily", adjust="qfq")
            results.append(
                {
                    "symbol": peer_symbol,
                    "name": peer.get("name", peer_symbol),
                    "sector": peer.get("sector", ""),
                    "return_20d": round(self._window_return(peer_df, 20), 4),
                    "pe_ttm": round(float(peer.get("pe_ttm", 0) or 0), 4),
                    "pb": round(float(peer.get("pb", 0) or 0), 4),
                    "relative_to_base": round(self._window_return(peer_df, 20) - base_return, 4),
                }
            )
        return sorted(results, key=lambda item: item["return_20d"], reverse=True)

    def _window_return(self, df: pd.DataFrame, window: int) -> float:
        if df is None or len(df) <= window:
            return 0.0
        closes = df["close"].astype(float)
        return float((closes.iloc[-1] - closes.iloc[-window]) / closes.iloc[-window] * 100)
