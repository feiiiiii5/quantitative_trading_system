"""
QuantCore 内置策略集 - 8+策略
涵盖: 趋势跟踪、均值回归、动量、多因子、网格交易、配对交易
所有策略参数通过YAML配置文件调整, 不硬编码
"""
import logging
from dataclasses import dataclass
from typing import Dict, List, Optional, Any

import numpy as np
import pandas as pd

from core.strategies import BaseStrategy, StrategyResult, TradeSignal, SignalType

logger = logging.getLogger(__name__)


class DualMACrossStrategy(BaseStrategy):
    """双均线交叉策略 - 趋势跟踪"""

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
                signals.append(TradeSignal(signal_type=SignalType.BUY, strength=0.7,
                    reason=f"MA{self.fast}上穿MA{self.slow}", price=c[i],
                    stop_loss=sl, take_profit=c[i] + 3 * (c[i] - sl), position_pct=pos, bar_index=i))
            elif prev_diff >= 0 and curr_diff < 0:
                signals.append(TradeSignal(signal_type=SignalType.SELL, strength=0.7,
                    reason=f"MA{self.fast}下穿MA{self.slow}", price=c[i], bar_index=i))
        current_signal = None
        score = 0.0
        if len(c) > self.slow and not np.isnan(ma_fast[-1]) and not np.isnan(ma_slow[-1]):
            diff = ma_fast[-1] - ma_slow[-1]
            score = min(80, 40 + abs(diff / c[-1]) * 1000) if diff > 0 else max(-80, -40 - abs(diff / c[-1]) * 1000)
        return StrategyResult(name=self.name, signals=signals, current_signal=current_signal,
                              score=score, params=self.get_default_params(), description=self.description)


class MACDStrategy(BaseStrategy):
    """MACD策略 - 趋势跟踪"""

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
        hist_vals = hist.values
        dif_vals = dif.values
        signals = []
        for i in range(self.slow, len(c)):
            if np.isnan(hist_vals[i]) or np.isnan(hist_vals[i - 1]):
                continue
            if hist_vals[i - 1] < 0 and hist_vals[i] > 0:
                sl = c[i] - 2 * atr[i] if not np.isnan(atr[i]) else c[i] * 0.95
                pos = self._calc_position_size(atr[i] if not np.isnan(atr[i]) else c[i] * 0.02)
                strength = 0.6 if dif_vals[i] < 0 else 0.8
                signals.append(TradeSignal(signal_type=SignalType.BUY, strength=strength,
                    reason="MACD金叉" + ("(零轴上方)" if dif_vals[i] > 0 else "(零轴下方)"),
                    price=c[i], stop_loss=sl, take_profit=c[i] + 3 * (c[i] - sl), position_pct=pos, bar_index=i))
            elif hist_vals[i - 1] > 0 and hist_vals[i] < 0:
                strength = 0.6 if dif_vals[i] > 0 else 0.8
                signals.append(TradeSignal(signal_type=SignalType.SELL, strength=strength,
                    reason="MACD死叉" + ("(零轴下方)" if dif_vals[i] < 0 else "(零轴上方)"),
                    price=c[i], bar_index=i))
        score = 0.0
        if not np.isnan(dif_vals[-1]) and not np.isnan(dea.values[-1]):
            score = min(70, 30 + abs(dif_vals[-1] / c[-1]) * 500) if dif_vals[-1] > dea.values[-1] else max(-70, -30 - abs(dif_vals[-1] / c[-1]) * 500)
        return StrategyResult(name=self.name, signals=signals, score=score,
                              params=self.get_default_params(), description=self.description)


class RSIMeanReversionStrategy(BaseStrategy):
    """RSI均值回归策略 - 均值回归"""

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
                signals.append(TradeSignal(signal_type=SignalType.BUY, strength=0.75,
                    reason=f"RSI={rsi[i]:.1f}超卖+布林下轨支撑", price=c[i],
                    stop_loss=sl, take_profit=boll_mid[i] if not np.isnan(boll_mid[i]) else c[i] * 1.05,
                    position_pct=pos, bar_index=i))
            elif rsi[i] > self.overbought and c[i] > boll_upper[i]:
                signals.append(TradeSignal(signal_type=SignalType.SELL, strength=0.75,
                    reason=f"RSI={rsi[i]:.1f}超买+布林上轨压力", price=c[i], bar_index=i))
        score = 0.0
        if not np.isnan(rsi[-1]):
            score = (rsi[-1] - 50) * 0.8
        return StrategyResult(name=self.name, signals=signals, score=score,
                              params=self.get_default_params(), description=self.description)


class SuperTrendStrategy(BaseStrategy):
    """SuperTrend趋势跟踪策略 - 趋势跟踪"""

    def __init__(self, period: int = 10, multiplier: float = 3.0):
        super().__init__("SuperTrend趋势跟踪策略", "基于SuperTrend指标的趋势跟踪系统")
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
        direction = np.ones(n)
        hl2 = (h + l) / 2
        upper_band = hl2 + self.multiplier * atr
        lower_band = hl2 - self.multiplier * atr
        for i in range(1, n):
            if np.isnan(atr[i]):
                continue
            if not (lower_band[i] > lower_band[i - 1] or c[i - 1] < lower_band[i - 1]):
                lower_band[i] = lower_band[i - 1]
            if not (upper_band[i] < upper_band[i - 1] or c[i - 1] > upper_band[i - 1]):
                upper_band[i] = upper_band[i - 1]
            if direction[i - 1] == 1:
                direction[i] = -1 if c[i] < lower_band[i] else 1
            else:
                direction[i] = 1 if c[i] > upper_band[i] else -1
        signals = []
        for i in range(self.period + 1, len(c)):
            if np.isnan(direction[i]) or np.isnan(direction[i - 1]):
                continue
            if direction[i - 1] == -1 and direction[i] == 1:
                sl = lower_band[i] if not np.isnan(lower_band[i]) else c[i] * 0.95
                pos = self._calc_position_size(atr[i] if not np.isnan(atr[i]) else c[i] * 0.02)
                signals.append(TradeSignal(signal_type=SignalType.BUY, strength=0.8,
                    reason="SuperTrend翻多", price=c[i], stop_loss=sl,
                    take_profit=c[i] + 4 * atr[i] if not np.isnan(atr[i]) else c[i] * 1.12,
                    position_pct=pos, bar_index=i))
            elif direction[i - 1] == 1 and direction[i] == -1:
                signals.append(TradeSignal(signal_type=SignalType.SELL, strength=0.8,
                    reason="SuperTrend翻空", price=c[i], bar_index=i))
        score = 65 if not np.isnan(direction[-1]) and direction[-1] == 1 else -65
        return StrategyResult(name=self.name, signals=signals, score=score,
                              params=self.get_default_params(), description=self.description)


class KDJStrategy(BaseStrategy):
    """KDJ随机策略 - 动量"""

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
        rsv = np.where(np.isfinite(hh) & np.isfinite(ll) & (hh != ll), (c - ll) / (hh - ll) * 100, 50.0)
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
                signals.append(TradeSignal(signal_type=SignalType.BUY, strength=0.75,
                    reason=f"KDJ超卖(J={j[i]:.1f})", price=c[i], stop_loss=sl,
                    take_profit=c[i] + 3 * (c[i] - sl), position_pct=pos, bar_index=i))
            elif k[i] > 80 and d[i] > 80 and j[i] > 100:
                signals.append(TradeSignal(signal_type=SignalType.SELL, strength=0.75,
                    reason=f"KDJ超买(J={j[i]:.1f})", price=c[i], bar_index=i))
        score = 0.0
        if not np.isnan(k[-1]) and not np.isnan(d[-1]):
            score = 20 + (k[-1] - d[-1]) if k[-1] > d[-1] else -20 + (k[-1] - d[-1])
        return StrategyResult(name=self.name, signals=signals, score=score,
                              params=self.get_default_params(), description=self.description)


class BollingerBreakoutStrategy(BaseStrategy):
    """布林带突破策略 - 突破"""

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
        signals = []
        for i in range(self.period + 1, len(c)):
            if np.isnan(upper[i]) or np.isnan(lower[i]):
                continue
            if c[i] > upper[i]:
                sl = mid[i] if not np.isnan(mid[i]) else c[i] * 0.95
                pos = self._calc_position_size(atr[i] if not np.isnan(atr[i]) else c[i] * 0.02)
                signals.append(TradeSignal(signal_type=SignalType.BUY, strength=0.7,
                    reason="突破布林上轨", price=c[i], stop_loss=sl,
                    take_profit=c[i] + 3 * (c[i] - sl), position_pct=pos, bar_index=i))
            elif c[i] < lower[i]:
                signals.append(TradeSignal(signal_type=SignalType.SELL, strength=0.7,
                    reason="跌破布林下轨", price=c[i], bar_index=i))
        score = 0.0
        if not np.isnan(upper[-1]) and not np.isnan(lower[-1]):
            bb_pos = (c[-1] - lower[-1]) / (upper[-1] - lower[-1]) if (upper[-1] - lower[-1]) != 0 else 0.5
            score = (bb_pos - 0.5) * 100
        return StrategyResult(name=self.name, signals=signals, score=score,
                              params=self.get_default_params(), description=self.description)


class MomentumStrategy(BaseStrategy):
    """动量策略 - 动量"""

    def __init__(self, lookback: int = 20, holding: int = 10):
        super().__init__("动量策略", "基于价格动量排名的趋势跟踪策略")
        self.lookback = lookback
        self.holding = holding

    def get_default_params(self) -> dict:
        return {"lookback": self.lookback, "holding": self.holding}

    def generate_signals(self, df: pd.DataFrame) -> StrategyResult:
        if not self._validate_df(df, self.lookback + 10):
            return StrategyResult(name=self.name, description=self.description)
        c = df["close"].values.astype(float)
        h = df["high"].values.astype(float)
        l = df["low"].values.astype(float)
        atr = self._calc_atr(h, l, c)
        momentum = np.zeros(len(c))
        for i in range(self.lookback, len(c)):
            momentum[i] = (c[i] - c[i - self.lookback]) / c[i - self.lookback] * 100
        ma20 = pd.Series(c).rolling(20).mean().values
        signals = []
        for i in range(self.lookback + 1, len(c)):
            if np.isnan(momentum[i]) or np.isnan(ma20[i]):
                continue
            if momentum[i] > 5 and c[i] > ma20[i]:
                sl = c[i] - 2 * atr[i] if not np.isnan(atr[i]) else c[i] * 0.93
                pos = self._calc_position_size(atr[i] if not np.isnan(atr[i]) else c[i] * 0.02)
                signals.append(TradeSignal(signal_type=SignalType.BUY, strength=min(0.9, 0.5 + momentum[i] / 50),
                    reason=f"动量={momentum[i]:.1f}%强势", price=c[i], stop_loss=sl,
                    take_profit=c[i] + 3 * (c[i] - sl), position_pct=pos, bar_index=i))
            elif momentum[i] < -5 and c[i] < ma20[i]:
                signals.append(TradeSignal(signal_type=SignalType.SELL, strength=min(0.9, 0.5 + abs(momentum[i]) / 50),
                    reason=f"动量={momentum[i]:.1f}%弱势", price=c[i], bar_index=i))
        score = max(-80, min(80, momentum[-1] * 3)) if not np.isnan(momentum[-1]) else 0
        return StrategyResult(name=self.name, signals=signals, score=score,
                              params=self.get_default_params(), description=self.description)


class VolumeBreakoutStrategy(BaseStrategy):
    """成交量突破策略 - 量价"""

    def __init__(self, vol_period: int = 20, vol_mult: float = 2.0):
        super().__init__("成交量突破策略", "基于成交量异动和价格突破的短线策略")
        self.vol_period = vol_period
        self.vol_mult = vol_mult

    def get_default_params(self) -> dict:
        return {"vol_period": self.vol_period, "vol_mult": self.vol_mult}

    def generate_signals(self, df: pd.DataFrame) -> StrategyResult:
        if not self._validate_df(df, self.vol_period + 10):
            return StrategyResult(name=self.name, description=self.description)
        c = df["close"].values.astype(float)
        h = df["high"].values.astype(float)
        l = df["low"].values.astype(float)
        v = df["volume"].values.astype(float) if "volume" in df.columns else np.ones(len(c))
        atr = self._calc_atr(h, l, c)
        vol_ma = pd.Series(v).rolling(self.vol_period).mean().values
        vol_ratio = np.where(vol_ma > 0, v / vol_ma, 1.0)
        hh20 = pd.Series(h).rolling(20).max().values
        ll20 = pd.Series(l).rolling(20).min().values
        signals = []
        for i in range(self.vol_period + 1, len(c)):
            if np.isnan(vol_ratio[i]) or np.isnan(hh20[i]) or np.isnan(ll20[i]):
                continue
            is_vol_surge = vol_ratio[i] >= self.vol_mult
            if c[i] > hh20[i - 1] and is_vol_surge:
                sl = c[i] - 2 * atr[i] if not np.isnan(atr[i]) else c[i] * 0.94
                pos = self._calc_position_size(atr[i] if not np.isnan(atr[i]) else c[i] * 0.02)
                signals.append(TradeSignal(signal_type=SignalType.BUY, strength=0.85,
                    reason=f"放量突破20日高点(量比={vol_ratio[i]:.1f})", price=c[i],
                    stop_loss=sl, take_profit=c[i] + 3 * (c[i] - sl), position_pct=pos, bar_index=i))
            elif c[i] < ll20[i - 1] and is_vol_surge:
                signals.append(TradeSignal(signal_type=SignalType.SELL, strength=0.85,
                    reason=f"放量跌破20日低点(量比={vol_ratio[i]:.1f})", price=c[i], bar_index=i))
        score = 0.0
        if not np.isnan(vol_ratio[-1]):
            score = max(-80, min(80, (vol_ratio[-1] - 1) * 30))
        return StrategyResult(name=self.name, signals=signals, score=score,
                              params=self.get_default_params(), description=self.description)


class GridTradingStrategy(BaseStrategy):
    """网格交易策略 - 网格交易"""

    def __init__(self, grid_num: int = 10, grid_pct: float = 0.03):
        super().__init__("网格交易策略", "在价格区间内等分网格，低买高卖赚取价差")
        self.grid_num = grid_num
        self.grid_pct = grid_pct

    def get_default_params(self) -> dict:
        return {"grid_num": self.grid_num, "grid_pct": self.grid_pct}

    def generate_signals(self, df: pd.DataFrame) -> StrategyResult:
        if not self._validate_df(df, 30):
            return StrategyResult(name=self.name, description=self.description)
        c = df["close"].values.astype(float)
        h = df["high"].values.astype(float)
        l = df["low"].values.astype(float)
        atr = self._calc_atr(h, l, c)
        window = c[-60:] if len(c) >= 60 else c
        price_high = np.max(window)
        price_low = np.min(window)
        grid_step = (price_high - price_low) / self.grid_num
        if grid_step <= 0:
            return StrategyResult(name=self.name, description=self.description)
        current_price = c[-1]
        grid_position = (current_price - price_low) / grid_step
        signals = []
        if grid_position < 3:
            sl = current_price - 2 * atr[-1] if not np.isnan(atr[-1]) else current_price * 0.93
            pos = self._calc_position_size(atr[-1] if not np.isnan(atr[-1]) else current_price * 0.02)
            signals.append(TradeSignal(signal_type=SignalType.BUY, strength=0.7,
                reason=f"网格低位(位置={grid_position:.1f}/{self.grid_num})", price=current_price,
                stop_loss=sl, take_profit=current_price + grid_step * 2, position_pct=pos, bar_index=len(c) - 1))
        elif grid_position > self.grid_num - 3:
            signals.append(TradeSignal(signal_type=SignalType.SELL, strength=0.7,
                reason=f"网格高位(位置={grid_position:.1f}/{self.grid_num})", price=current_price, bar_index=len(c) - 1))
        score = (grid_position / self.grid_num - 0.5) * -100
        return StrategyResult(name=self.name, signals=signals, score=score,
                              params=self.get_default_params(), description=self.description)


class MultiFactorStrategy(BaseStrategy):
    """多因子策略 - 多因子"""

    def __init__(self, momentum_weight: float = 0.3, volatility_weight: float = 0.2,
                 volume_weight: float = 0.2, trend_weight: float = 0.3):
        super().__init__("多因子策略", "综合动量、波动率、成交量、趋势四个因子评分")
        self.momentum_weight = momentum_weight
        self.volatility_weight = volatility_weight
        self.volume_weight = volume_weight
        self.trend_weight = trend_weight

    def get_default_params(self) -> dict:
        return {"momentum_weight": self.momentum_weight, "volatility_weight": self.volatility_weight,
                "volume_weight": self.volume_weight, "trend_weight": self.trend_weight}

    def generate_signals(self, df: pd.DataFrame) -> StrategyResult:
        if not self._validate_df(df, 60):
            return StrategyResult(name=self.name, description=self.description)
        c = df["close"].values.astype(float)
        h = df["high"].values.astype(float)
        l = df["low"].values.astype(float)
        v = df["volume"].values.astype(float) if "volume" in df.columns else np.ones(len(c))
        atr = self._calc_atr(h, l, c)
        # 动量因子
        mom_20 = (c[-1] / c[-21] - 1) * 100 if len(c) > 20 else 0
        mom_score = min(100, max(-100, mom_20 * 5))
        # 波动率因子 (低波动率得分高)
        rets = np.diff(c[-20:]) / c[-20:-1] if len(c) > 20 else np.array([0.0])
        vol = np.std(rets) * np.sqrt(252) * 100
        vol_score = max(-100, min(100, (30 - vol) * 5))
        # 成交量因子
        vol_ma = np.mean(v[-20:]) if len(v) >= 20 else v[-1]
        vol_ratio = v[-1] / vol_ma if vol_ma > 0 else 1
        volume_score = min(100, max(-100, (vol_ratio - 1) * 50))
        # 趋势因子
        ma5 = np.mean(c[-5:])
        ma20 = np.mean(c[-20:])
        trend_score = 80 if ma5 > ma20 else -80
        # 综合评分
        composite = (mom_score * self.momentum_weight + vol_score * self.volatility_weight +
                     volume_score * self.volume_weight + trend_score * self.trend_weight)
        signals = []
        if composite > 30:
            sl = c[-1] - 2 * atr[-1] if not np.isnan(atr[-1]) else c[-1] * 0.93
            pos = self._calc_position_size(atr[-1] if not np.isnan(atr[-1]) else c[-1] * 0.02)
            signals.append(TradeSignal(signal_type=SignalType.BUY, strength=min(0.9, composite / 100),
                reason=f"多因子综合={composite:.1f}(动量={mom_score:.0f},趋势={trend_score:.0f})",
                price=c[-1], stop_loss=sl, take_profit=c[-1] + 3 * (c[-1] - sl),
                position_pct=pos, bar_index=len(c) - 1))
        elif composite < -30:
            signals.append(TradeSignal(signal_type=SignalType.SELL, strength=min(0.9, abs(composite) / 100),
                reason=f"多因子综合={composite:.1f}(动量={mom_score:.0f},趋势={trend_score:.0f})",
                price=c[-1], bar_index=len(c) - 1))
        return StrategyResult(name=self.name, signals=signals, score=composite,
                              params=self.get_default_params(), description=self.description)


class PairTradingStrategy(BaseStrategy):
    """配对交易策略 - 配对交易 (需两个标的)"""

    def __init__(self, lookback: int = 60, entry_z: float = 2.0, exit_z: float = 0.5):
        super().__init__("配对交易策略", "基于价差均值回归的配对交易，需两个相关性高的标的")
        self.lookback = lookback
        self.entry_z = entry_z
        self.exit_z = exit_z

    def get_default_params(self) -> dict:
        return {"lookback": self.lookback, "entry_z": self.entry_z, "exit_z": self.exit_z}

    def generate_signals(self, df: pd.DataFrame) -> StrategyResult:
        if not self._validate_df(df, self.lookback + 10):
            return StrategyResult(name=self.name, description=self.description)
        c = df["close"].values.astype(float)
        h = df["high"].values.astype(float)
        l = df["low"].values.astype(float)
        atr = self._calc_atr(h, l, c)
        # 简化: 使用价格与自身均值的偏离度模拟价差
        ma = pd.Series(c).rolling(self.lookback).mean().values
        std = pd.Series(c).rolling(self.lookback).std().values
        spread = np.where(std > 0, (c - ma) / std, 0)
        signals = []
        for i in range(self.lookback + 1, len(c)):
            if np.isnan(spread[i]):
                continue
            if spread[i] < -self.entry_z:
                sl = c[i] - 2 * atr[i] if not np.isnan(atr[i]) else c[i] * 0.93
                pos = self._calc_position_size(atr[i] if not np.isnan(atr[i]) else c[i] * 0.02)
                signals.append(TradeSignal(signal_type=SignalType.BUY, strength=0.7,
                    reason=f"价差Z={spread[i]:.2f}低于-{self.entry_z}", price=c[i],
                    stop_loss=sl, take_profit=ma[i] if not np.isnan(ma[i]) else c[i] * 1.05,
                    position_pct=pos, bar_index=i))
            elif spread[i] > self.entry_z:
                signals.append(TradeSignal(signal_type=SignalType.SELL, strength=0.7,
                    reason=f"价差Z={spread[i]:.2f}高于{self.entry_z}", price=c[i], bar_index=i))
        score = float(spread[-1]) * -30 if not np.isnan(spread[-1]) else 0
        return StrategyResult(name=self.name, signals=signals, score=score,
                              params=self.get_default_params(), description=self.description)


def get_all_strategies() -> list:
    return [
        DualMACrossStrategy(),
        MACDStrategy(),
        RSIMeanReversionStrategy(),
        SuperTrendStrategy(),
        KDJStrategy(),
        BollingerBreakoutStrategy(),
        MomentumStrategy(),
        VolumeBreakoutStrategy(),
        GridTradingStrategy(),
        MultiFactorStrategy(),
        PairTradingStrategy(),
    ]
