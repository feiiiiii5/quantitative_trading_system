import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from typing import List, Optional, Tuple

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)


class SignalType(Enum):
    BUY = "buy"
    SELL = "sell"
    HOLD = "hold"


@dataclass
class TradeSignal:
    signal_type: SignalType
    strength: float
    reason: str
    price: float = 0.0
    stop_loss: float = 0.0
    take_profit: float = 0.0
    position_pct: float = 0.0
    bar_index: int = -1


@dataclass
class StrategyResult:
    name: str
    signals: List[TradeSignal] = field(default_factory=list)
    current_signal: Optional[TradeSignal] = None
    score: float = 0.0
    params: dict = field(default_factory=dict)
    description: str = ""


class BaseStrategy(ABC):
    def __init__(self, name: str, description: str = ""):
        self.name = name
        self.description = description

    @abstractmethod
    def generate_signals(self, df: pd.DataFrame) -> StrategyResult:
        pass

    @abstractmethod
    def get_default_params(self) -> dict:
        pass

    def _validate_df(self, df: pd.DataFrame, min_len: int = 30) -> bool:
        if df is None or len(df) < min_len:
            return False
        required = {"close", "high", "low"}
        return required.issubset(set(df.columns))

    def _calc_atr(self, h: np.ndarray, l: np.ndarray, c: np.ndarray, period: int = 14) -> np.ndarray:
        tr = np.maximum(h - l, np.maximum(np.abs(h - np.roll(c, 1)), np.abs(l - np.roll(c, 1))))
        tr[0] = h[0] - l[0]
        atr = pd.Series(tr).ewm(alpha=1 / period, min_periods=period).mean().values
        return atr

    def _calc_position_size(self, atr_val: float, capital: float = 100000.0,
                            risk_pct: float = 0.02, max_position: float = 0.3) -> float:
        if atr_val <= 0:
            return max_position
        risk_amount = capital * risk_pct
        position_value = risk_amount / (atr_val * 2)
        position_pct = min(position_value / capital, max_position)
        return max(0.05, position_pct)


class DualMAStrategy(BaseStrategy):
    def __init__(self, fast: int = 5, slow: int = 20, atr_period: int = 14):
        super().__init__("双均线交叉策略", "基于快慢均线交叉产生买卖信号，配合ATR动态止损")
        self.fast = fast
        self.slow = slow
        self.atr_period = atr_period

    def get_default_params(self) -> dict:
        return {"fast": self.fast, "slow": self.slow, "atr_period": self.atr_period}

    def generate_signals(self, df: pd.DataFrame) -> StrategyResult:
        if not self._validate_df(df, self.slow + 5):
            return StrategyResult(name=self.name, description=self.description)

        c = df["close"].values.astype(float)
        h = df["high"].values.astype(float)
        l = df["low"].values.astype(float)

        ma_fast = pd.Series(c).rolling(self.fast).mean().values
        ma_slow = pd.Series(c).rolling(self.slow).mean().values
        atr = self._calc_atr(h, l, c, self.atr_period)

        signals = []
        for i in range(self.slow + 1, len(c)):
            if np.isnan(ma_fast[i]) or np.isnan(ma_slow[i]):
                continue
            prev_diff = ma_fast[i - 1] - ma_slow[i - 1]
            curr_diff = ma_fast[i] - ma_slow[i]

            if prev_diff <= 0 and curr_diff > 0:
                sl = c[i] - 2 * atr[i] if not np.isnan(atr[i]) else c[i] * 0.95
                pos = self._calc_position_size(atr[i] if not np.isnan(atr[i]) else c[i] * 0.02)
                signals.append(TradeSignal(
                    signal_type=SignalType.BUY, strength=0.7,
                    reason=f"MA{self.fast}上穿MA{self.slow}",
                    price=c[i], stop_loss=sl,
                    take_profit=c[i] + 3 * (c[i] - sl),
                    position_pct=pos, bar_index=i,
                ))
            elif prev_diff >= 0 and curr_diff < 0:
                signals.append(TradeSignal(
                    signal_type=SignalType.SELL, strength=0.7,
                    reason=f"MA{self.fast}下穿MA{self.slow}",
                    price=c[i], bar_index=i,
                ))

        current_signal = None
        score = 0.0
        if len(c) > self.slow and not np.isnan(ma_fast[-1]) and not np.isnan(ma_slow[-1]):
            diff = ma_fast[-1] - ma_slow[-1]
            prev_diff = ma_fast[-2] - ma_slow[-2] if len(ma_fast) > 1 else 0
            if diff > 0:
                score = min(80, 40 + abs(diff / c[-1]) * 1000)
                if prev_diff <= 0 and diff > 0:
                    current_signal = TradeSignal(
                        signal_type=SignalType.BUY, strength=0.8,
                        reason=f"MA{self.fast}金叉MA{self.slow}",
                        price=c[-1],
                        stop_loss=c[-1] - 2 * atr[-1] if not np.isnan(atr[-1]) else c[-1] * 0.95,
                        take_profit=c[-1] + 3 * 2 * atr[-1] if not np.isnan(atr[-1]) else c[-1] * 1.1,
                        position_pct=self._calc_position_size(atr[-1] if not np.isnan(atr[-1]) else c[-1] * 0.02),
                    )
            else:
                score = max(-80, -40 - abs(diff / c[-1]) * 1000)
                if prev_diff >= 0 and diff < 0:
                    current_signal = TradeSignal(
                        signal_type=SignalType.SELL, strength=0.8,
                        reason=f"MA{self.fast}死叉MA{self.slow}",
                        price=c[-1],
                    )

        return StrategyResult(
            name=self.name, signals=signals, current_signal=current_signal,
            score=score, params=self.get_default_params(), description=self.description,
        )


class MACDStrategy(BaseStrategy):
    def __init__(self, fast: int = 12, slow: int = 26, signal: int = 9):
        super().__init__("MACD策略", "基于MACD金叉死叉信号，配合零轴判断多空趋势")
        self.fast = fast
        self.slow = slow
        self.signal = signal

    def get_default_params(self) -> dict:
        return {"fast": self.fast, "slow": self.slow, "signal": self.signal}

    def generate_signals(self, df: pd.DataFrame) -> StrategyResult:
        if not self._validate_df(df, self.slow + self.signal + 5):
            return StrategyResult(name=self.name, description=self.description)

        c = df["close"].values.astype(float)
        h = df["high"].values.astype(float)
        l = df["low"].values.astype(float)
        atr = self._calc_atr(h, l, c)

        s = pd.Series(c)
        ema_fast = s.ewm(span=self.fast, adjust=False).mean()
        ema_slow = s.ewm(span=self.slow, adjust=False).mean()
        dif = ema_fast - ema_slow
        dea = dif.ewm(span=self.signal, adjust=False).mean()
        hist = (dif - dea) * 2

        dif_vals = dif.values
        dea_vals = dea.values
        hist_vals = hist.values

        signals = []
        for i in range(self.slow, len(c)):
            if np.isnan(hist_vals[i]) or np.isnan(hist_vals[i - 1]):
                continue
            if hist_vals[i - 1] < 0 and hist_vals[i] > 0:
                sl = c[i] - 2 * atr[i] if not np.isnan(atr[i]) else c[i] * 0.95
                pos = self._calc_position_size(atr[i] if not np.isnan(atr[i]) else c[i] * 0.02)
                strength = 0.6 if dif_vals[i] < 0 else 0.8
                signals.append(TradeSignal(
                    signal_type=SignalType.BUY, strength=strength,
                    reason="MACD金叉" + ("(零轴上方)" if dif_vals[i] > 0 else "(零轴下方)"),
                    price=c[i], stop_loss=sl,
                    take_profit=c[i] + 3 * (c[i] - sl),
                    position_pct=pos,
                ))
            elif hist_vals[i - 1] > 0 and hist_vals[i] < 0:
                strength = 0.6 if dif_vals[i] > 0 else 0.8
                signals.append(TradeSignal(
                    signal_type=SignalType.SELL, strength=strength,
                    reason="MACD死叉" + ("(零轴下方)" if dif_vals[i] < 0 else "(零轴上方)"),
                    price=c[i],
                ))

        current_signal = None
        score = 0.0
        if not np.isnan(dif_vals[-1]) and not np.isnan(dea_vals[-1]):
            if dif_vals[-1] > dea_vals[-1]:
                score = min(70, 30 + abs(dif_vals[-1] / c[-1]) * 500)
            else:
                score = max(-70, -30 - abs(dif_vals[-1] / c[-1]) * 500)
            if len(hist_vals) >= 2 and not np.isnan(hist_vals[-1]) and not np.isnan(hist_vals[-2]):
                if hist_vals[-2] < 0 and hist_vals[-1] > 0:
                    current_signal = TradeSignal(
                        signal_type=SignalType.BUY, strength=0.8,
                        reason="MACD金叉", price=c[-1],
                        stop_loss=c[-1] - 2 * atr[-1] if not np.isnan(atr[-1]) else c[-1] * 0.95,
                        take_profit=c[-1] + 6 * atr[-1] if not np.isnan(atr[-1]) else c[-1] * 1.1,
                        position_pct=self._calc_position_size(atr[-1] if not np.isnan(atr[-1]) else c[-1] * 0.02),
                    )
                elif hist_vals[-2] > 0 and hist_vals[-1] < 0:
                    current_signal = TradeSignal(
                        signal_type=SignalType.SELL, strength=0.8,
                        reason="MACD死叉", price=c[-1],
                    )

        return StrategyResult(
            name=self.name, signals=signals, current_signal=current_signal,
            score=score, params=self.get_default_params(), description=self.description,
        )


class RSIMeanReversionStrategy(BaseStrategy):
    def __init__(self, period: int = 14, oversold: float = 30, overbought: float = 70):
        super().__init__("RSI均值回归策略", "RSI超卖买入超买卖出，配合布林带确认价格位置")
        self.period = period
        self.oversold = oversold
        self.overbought = overbought

    def get_default_params(self) -> dict:
        return {"period": self.period, "oversold": self.oversold, "overbought": self.overbought}

    def generate_signals(self, df: pd.DataFrame) -> StrategyResult:
        if not self._validate_df(df, self.period + 10):
            return StrategyResult(name=self.name, description=self.description)

        c = df["close"].values.astype(float)
        h = df["high"].values.astype(float)
        l = df["low"].values.astype(float)
        atr = self._calc_atr(h, l, c)

        delta = np.diff(c, prepend=c[0])
        gain = np.where(delta > 0, delta, 0)
        loss = np.where(delta < 0, -delta, 0)
        avg_gain = pd.Series(gain).ewm(alpha=1 / self.period, min_periods=self.period).mean().values
        avg_loss = pd.Series(loss).ewm(alpha=1 / self.period, min_periods=self.period).mean().values
        rs = np.where(avg_loss != 0, avg_gain / avg_loss, 100)
        rsi = 100 - 100 / (1 + rs)

        boll_mid = pd.Series(c).rolling(20).mean().values
        boll_std = pd.Series(c).rolling(20).std().values
        boll_lower = boll_mid - 2 * boll_std
        boll_upper = boll_mid + 2 * boll_std

        signals = []
        for i in range(self.period + 1, len(c)):
            if np.isnan(rsi[i]):
                continue
            if rsi[i] < self.oversold and c[i] < boll_lower[i]:
                sl = c[i] - 2 * atr[i] if not np.isnan(atr[i]) else c[i] * 0.93
                pos = self._calc_position_size(atr[i] if not np.isnan(atr[i]) else c[i] * 0.02)
                signals.append(TradeSignal(
                    signal_type=SignalType.BUY, strength=0.75,
                    reason=f"RSI={rsi[i]:.1f}超卖+布林下轨支撑",
                    price=c[i], stop_loss=sl,
                    take_profit=boll_mid[i] if not np.isnan(boll_mid[i]) else c[i] * 1.05,
                    position_pct=pos,
                ))
            elif rsi[i] > self.overbought and c[i] > boll_upper[i]:
                signals.append(TradeSignal(
                    signal_type=SignalType.SELL, strength=0.75,
                    reason=f"RSI={rsi[i]:.1f}超买+布林上轨压力",
                    price=c[i],
                ))

        current_signal = None
        score = 0.0
        if not np.isnan(rsi[-1]):
            if rsi[-1] < self.oversold:
                score = 60 + (self.oversold - rsi[-1]) * 2
                current_signal = TradeSignal(
                    signal_type=SignalType.BUY, strength=0.7,
                    reason=f"RSI={rsi[-1]:.1f}超卖区域",
                    price=c[-1],
                    stop_loss=c[-1] - 2 * atr[-1] if not np.isnan(atr[-1]) else c[-1] * 0.93,
                    take_profit=boll_mid[-1] if not np.isnan(boll_mid[-1]) else c[-1] * 1.05,
                    position_pct=self._calc_position_size(atr[-1] if not np.isnan(atr[-1]) else c[-1] * 0.02),
                )
            elif rsi[-1] > self.overbought:
                score = -60 - (rsi[-1] - self.overbought) * 2
                current_signal = TradeSignal(
                    signal_type=SignalType.SELL, strength=0.7,
                    reason=f"RSI={rsi[-1]:.1f}超买区域",
                    price=c[-1],
                )
            else:
                score = (rsi[-1] - 50) * 0.8

        return StrategyResult(
            name=self.name, signals=signals, current_signal=current_signal,
            score=score, params=self.get_default_params(), description=self.description,
        )


class SuperTrendStrategy(BaseStrategy):
    def __init__(self, period: int = 10, multiplier: float = 3.0):
        super().__init__("SuperTrend趋势跟踪策略", "基于SuperTrend指标的趋势跟踪系统，适合捕捉中长期趋势")
        self.period = period
        self.multiplier = multiplier

    def get_default_params(self) -> dict:
        return {"period": self.period, "multiplier": self.multiplier}

    def generate_signals(self, df: pd.DataFrame) -> StrategyResult:
        if not self._validate_df(df, self.period + 10):
            return StrategyResult(name=self.name, description=self.description)

        c = df["close"].values.astype(float)
        h = df["high"].values.astype(float)
        l = df["low"].values.astype(float)

        tr = np.maximum(h - l, np.maximum(np.abs(h - np.roll(c, 1)), np.abs(l - np.roll(c, 1))))
        tr[0] = h[0] - l[0]
        atr = pd.Series(tr).rolling(self.period).mean().values

        n = len(c)
        upper_band = np.zeros(n)
        lower_band = np.zeros(n)
        st = np.zeros(n)
        direction = np.ones(n)

        hl2 = (h + l) / 2
        upper_band = hl2 + self.multiplier * atr
        lower_band = hl2 - self.multiplier * atr

        for i in range(1, n):
            if np.isnan(atr[i]):
                st[i] = np.nan
                continue
            if lower_band[i] > lower_band[i - 1] or c[i - 1] < lower_band[i - 1]:
                pass
            else:
                lower_band[i] = lower_band[i - 1]
            if upper_band[i] < upper_band[i - 1] or c[i - 1] > upper_band[i - 1]:
                pass
            else:
                upper_band[i] = upper_band[i - 1]
            if direction[i - 1] == 1:
                if c[i] < lower_band[i]:
                    direction[i] = -1
                    st[i] = upper_band[i]
                else:
                    direction[i] = 1
                    st[i] = lower_band[i]
            else:
                if c[i] > upper_band[i]:
                    direction[i] = 1
                    st[i] = lower_band[i]
                else:
                    direction[i] = -1
                    st[i] = upper_band[i]

        signals = []
        for i in range(self.period + 1, len(c)):
            if np.isnan(direction[i]) or np.isnan(direction[i - 1]):
                continue
            if direction[i - 1] == -1 and direction[i] == 1:
                sl = lower_band[i] if not np.isnan(lower_band[i]) else c[i] * 0.95
                pos = self._calc_position_size(atr[i] if not np.isnan(atr[i]) else c[i] * 0.02)
                signals.append(TradeSignal(
                    signal_type=SignalType.BUY, strength=0.8,
                    reason="SuperTrend翻多",
                    price=c[i], stop_loss=sl,
                    take_profit=c[i] + 4 * atr[i] if not np.isnan(atr[i]) else c[i] * 1.12,
                    position_pct=pos,
                ))
            elif direction[i - 1] == 1 and direction[i] == -1:
                signals.append(TradeSignal(
                    signal_type=SignalType.SELL, strength=0.8,
                    reason="SuperTrend翻空",
                    price=c[i],
                ))

        current_signal = None
        score = 0.0
        if not np.isnan(direction[-1]):
            if direction[-1] == 1:
                score = 65
                if len(direction) >= 2 and direction[-2] == -1:
                    current_signal = TradeSignal(
                        signal_type=SignalType.BUY, strength=0.85,
                        reason="SuperTrend刚翻多", price=c[-1],
                        stop_loss=lower_band[-1] if not np.isnan(lower_band[-1]) else c[-1] * 0.95,
                        take_profit=c[-1] + 4 * atr[-1] if not np.isnan(atr[-1]) else c[-1] * 1.12,
                        position_pct=self._calc_position_size(atr[-1] if not np.isnan(atr[-1]) else c[-1] * 0.02),
                    )
            else:
                score = -65
                if len(direction) >= 2 and direction[-2] == 1:
                    current_signal = TradeSignal(
                        signal_type=SignalType.SELL, strength=0.85,
                        reason="SuperTrend刚翻空", price=c[-1],
                    )

        return StrategyResult(
            name=self.name, signals=signals, current_signal=current_signal,
            score=score, params=self.get_default_params(), description=self.description,
        )


class KDJStrategy(BaseStrategy):
    def __init__(self, n: int = 9, m1: int = 3, m2: int = 3):
        super().__init__("KDJ随机策略", "基于KDJ指标的买卖信号，J值极端区域反转信号更强")
        self.n = n
        self.m1 = m1
        self.m2 = m2

    def get_default_params(self) -> dict:
        return {"n": self.n, "m1": self.m1, "m2": self.m2}

    def generate_signals(self, df: pd.DataFrame) -> StrategyResult:
        if not self._validate_df(df, self.n + 10):
            return StrategyResult(name=self.name, description=self.description)

        c = df["close"].values.astype(float)
        h = df["high"].values.astype(float)
        l = df["low"].values.astype(float)
        atr = self._calc_atr(h, l, c)

        hh = pd.Series(h).rolling(self.n).max().values
        ll = pd.Series(l).rolling(self.n).min().values
        rsv = np.where(
            np.isfinite(hh) & np.isfinite(ll) & (hh != ll),
            (c - ll) / (hh - ll) * 100, 50.0,
        )
        k = np.full(len(c), 50.0)
        d = np.full(len(c), 50.0)
        for i in range(1, len(c)):
            k[i] = (2 / self.m1) * k[i - 1] + (1 / self.m1) * rsv[i]
            d[i] = (2 / self.m2) * d[i - 1] + (1 / self.m2) * k[i]
        j = 3 * k - 2 * d

        signals = []
        for i in range(self.n + 1, len(c)):
            if k[i] < 20 and d[i] < 20 and j[i] < 0:
                sl = c[i] - 2 * atr[i] if not np.isnan(atr[i]) else c[i] * 0.93
                pos = self._calc_position_size(atr[i] if not np.isnan(atr[i]) else c[i] * 0.02)
                signals.append(TradeSignal(
                    signal_type=SignalType.BUY, strength=0.75,
                    reason=f"KDJ超卖(J={j[i]:.1f})",
                    price=c[i], stop_loss=sl,
                    take_profit=c[i] + 3 * (c[i] - sl),
                    position_pct=pos,
                ))
            elif k[i] > 80 and d[i] > 80 and j[i] > 100:
                signals.append(TradeSignal(
                    signal_type=SignalType.SELL, strength=0.75,
                    reason=f"KDJ超买(J={j[i]:.1f})",
                    price=c[i],
                ))
            elif k[i - 1] < d[i - 1] and k[i] > d[i] and k[i] < 50:
                sl = c[i] - 2 * atr[i] if not np.isnan(atr[i]) else c[i] * 0.95
                signals.append(TradeSignal(
                    signal_type=SignalType.BUY, strength=0.6,
                    reason="KDJ低位金叉",
                    price=c[i], stop_loss=sl,
                    take_profit=c[i] + 3 * (c[i] - sl),
                    position_pct=self._calc_position_size(atr[i] if not np.isnan(atr[i]) else c[i] * 0.02),
                ))
            elif k[i - 1] > d[i - 1] and k[i] < d[i] and k[i] > 50:
                signals.append(TradeSignal(
                    signal_type=SignalType.SELL, strength=0.6,
                    reason="KDJ高位死叉",
                    price=c[i],
                ))

        current_signal = None
        score = 0.0
        if not np.isnan(k[-1]) and not np.isnan(d[-1]):
            if k[-1] > d[-1]:
                score = 20 + (k[-1] - d[-1])
            else:
                score = -20 + (k[-1] - d[-1])
            if j[-1] < 0:
                score = max(score, 50)
                current_signal = TradeSignal(
                    signal_type=SignalType.BUY, strength=0.7,
                    reason=f"J值极端超卖({j[-1]:.1f})", price=c[-1],
                    stop_loss=c[-1] - 2 * atr[-1] if not np.isnan(atr[-1]) else c[-1] * 0.93,
                    take_profit=c[-1] + 6 * atr[-1] if not np.isnan(atr[-1]) else c[-1] * 1.08,
                    position_pct=self._calc_position_size(atr[-1] if not np.isnan(atr[-1]) else c[-1] * 0.02),
                )
            elif j[-1] > 100:
                score = min(score, -50)
                current_signal = TradeSignal(
                    signal_type=SignalType.SELL, strength=0.7,
                    reason=f"J值极端超买({j[-1]:.1f})", price=c[-1],
                )

        return StrategyResult(
            name=self.name, signals=signals, current_signal=current_signal,
            score=score, params=self.get_default_params(), description=self.description,
        )


class BollingerBreakoutStrategy(BaseStrategy):
    def __init__(self, period: int = 20, nbdev: float = 2.0):
        super().__init__("布林带突破策略", "价格突破布林带上下轨产生信号，收窄后突破更可靠")
        self.period = period
        self.nbdev = nbdev

    def get_default_params(self) -> dict:
        return {"period": self.period, "nbdev": self.nbdev}

    def generate_signals(self, df: pd.DataFrame) -> StrategyResult:
        if not self._validate_df(df, self.period + 10):
            return StrategyResult(name=self.name, description=self.description)

        c = df["close"].values.astype(float)
        h = df["high"].values.astype(float)
        l = df["low"].values.astype(float)
        atr = self._calc_atr(h, l, c)

        s = pd.Series(c)
        mid = s.rolling(self.period).mean().values
        std = s.rolling(self.period).std().values
        upper = mid + self.nbdev * std
        lower = mid - self.nbdev * std
        width = np.where(mid != 0, (upper - lower) / mid * 100, 0)

        avg_width = pd.Series(width).rolling(20).mean().values

        signals = []
        for i in range(self.period + 1, len(c)):
            if np.isnan(upper[i]) or np.isnan(lower[i]):
                continue
            is_squeeze = not np.isnan(avg_width[i]) and width[i] < avg_width[i] * 0.7

            if c[i] > upper[i]:
                strength = 0.8 if is_squeeze else 0.6
                sl = mid[i] if not np.isnan(mid[i]) else c[i] * 0.95
                pos = self._calc_position_size(atr[i] if not np.isnan(atr[i]) else c[i] * 0.02)
                signals.append(TradeSignal(
                    signal_type=SignalType.BUY, strength=strength,
                    reason="突破布林上轨" + ("(收窄突破)" if is_squeeze else ""),
                    price=c[i], stop_loss=sl,
                    take_profit=c[i] + 3 * (c[i] - sl),
                    position_pct=pos,
                ))
            elif c[i] < lower[i]:
                strength = 0.8 if is_squeeze else 0.6
                signals.append(TradeSignal(
                    signal_type=SignalType.SELL, strength=strength,
                    reason="跌破布林下轨" + ("(收窄突破)" if is_squeeze else ""),
                    price=c[i],
                ))

        current_signal = None
        score = 0.0
        if not np.isnan(upper[-1]) and not np.isnan(lower[-1]):
            bb_pos = (c[-1] - lower[-1]) / (upper[-1] - lower[-1]) if (upper[-1] - lower[-1]) != 0 else 0.5
            score = (bb_pos - 0.5) * 100
            if c[-1] > upper[-1]:
                current_signal = TradeSignal(
                    signal_type=SignalType.BUY, strength=0.7,
                    reason="当前突破布林上轨", price=c[-1],
                    stop_loss=mid[-1] if not np.isnan(mid[-1]) else c[-1] * 0.95,
                    take_profit=c[-1] + 3 * (c[-1] - mid[-1]) if not np.isnan(mid[-1]) else c[-1] * 1.1,
                    position_pct=self._calc_position_size(atr[-1] if not np.isnan(atr[-1]) else c[-1] * 0.02),
                )
            elif c[-1] < lower[-1]:
                current_signal = TradeSignal(
                    signal_type=SignalType.SELL, strength=0.7,
                    reason="当前跌破布林下轨", price=c[-1],
                )

        return StrategyResult(
            name=self.name, signals=signals, current_signal=current_signal,
            score=score, params=self.get_default_params(), description=self.description,
        )


class CompositeStrategy:
    def __init__(self):
        self.strategies = [
            DualMAStrategy(),
            MACDStrategy(),
            RSIMeanReversionStrategy(),
            SuperTrendStrategy(),
            KDJStrategy(),
            BollingerBreakoutStrategy(),
        ]
        self.weights = {
            "双均线交叉策略": 0.15,
            "MACD策略": 0.20,
            "RSI均值回归策略": 0.15,
            "SuperTrend趋势跟踪策略": 0.25,
            "KDJ随机策略": 0.10,
            "布林带突破策略": 0.15,
        }

    def run_all(self, df: pd.DataFrame) -> dict:
        results = {}
        for strategy in self.strategies:
            try:
                result = strategy.generate_signals(df)
                results[strategy.name] = result
            except Exception as e:
                logger.debug(f"Strategy {strategy.name} failed: {e}")
                results[strategy.name] = StrategyResult(
                    name=strategy.name, description=strategy.description
                )
        return results

    def composite_score(self, results: dict) -> dict:
        total_score = 0.0
        total_weight = 0.0
        buy_count = 0
        sell_count = 0
        hold_count = 0
        best_signal = None
        best_strength = 0.0

        for name, result in results.items():
            w = self.weights.get(name, 0.1)
            total_score += result.score * w
            total_weight += w

            if result.current_signal:
                if result.current_signal.signal_type == SignalType.BUY:
                    buy_count += 1
                    if result.current_signal.strength > best_strength:
                        best_strength = result.current_signal.strength
                        best_signal = result.current_signal
                elif result.current_signal.signal_type == SignalType.SELL:
                    sell_count += 1
                    if result.current_signal.strength > best_strength:
                        best_strength = result.current_signal.strength
                        best_signal = result.current_signal
                else:
                    hold_count += 1

        if total_weight > 0:
            total_score /= total_weight

        if buy_count > sell_count and buy_count >= 2:
            composite_signal = "buy"
        elif sell_count > buy_count and sell_count >= 2:
            composite_signal = "sell"
        else:
            composite_signal = "neutral"

        return {
            "score": round(total_score, 2),
            "signal": composite_signal,
            "buy_count": buy_count,
            "sell_count": sell_count,
            "hold_count": hold_count,
            "best_signal": best_signal,
            "individual_results": {
                name: {
                    "score": r.score,
                    "signal": r.current_signal.signal_type.value if r.current_signal else "hold",
                    "reason": r.current_signal.reason if r.current_signal else "",
                    "strength": r.current_signal.strength if r.current_signal else 0,
                }
                for name, r in results.items()
            },
        }

    def get_strategy_info(self) -> list:
        info = []
        for s in self.strategies:
            info.append({
                "name": s.name,
                "description": s.description,
                "params": s.get_default_params(),
                "weight": self.weights.get(s.name, 0),
            })
        return info
