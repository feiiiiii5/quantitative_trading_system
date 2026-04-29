"""
QuantCore 策略模块
提供多种量化策略实现
"""
import logging
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional

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
    strength: float = 0.0
    reason: str = ""
    bar_index: int = -1
    position_pct: float = 0.0
    stop_loss: float = 0.0
    take_profit: float = 0.0


@dataclass
class StrategyResult:
    strategy_name: str
    total_return: float = 0.0
    annual_return: float = 0.0
    sharpe_ratio: float = 0.0
    max_drawdown: float = 0.0
    win_rate: float = 0.0
    profit_factor: float = 0.0
    total_trades: int = 0
    win_trades: int = 0
    loss_trades: int = 0
    avg_profit: float = 0.0
    avg_loss: float = 0.0
    benchmark_return: float = 0.0
    alpha: float = 0.0
    beta: float = 1.0
    equity_curve: list = field(default_factory=list)
    drawdown_curve: list = field(default_factory=list)
    dates: list = field(default_factory=list)
    signals: list = field(default_factory=list)


class BaseStrategy:
    """策略基类"""

    def __init__(self):
        self.name = self.__class__.__name__

    def generate_signal(self, df: pd.DataFrame) -> TradeSignal:
        raise NotImplementedError

    def generate_score(self, df: pd.DataFrame) -> float:
        signal = self.generate_signal(df)
        if signal.signal_type == SignalType.BUY:
            return round(float(np.clip(signal.strength, 0, 1)), 2)
        elif signal.signal_type == SignalType.SELL:
            return round(float(-np.clip(signal.strength, 0, 1)), 2)
        return 0.0

    def generate_signals(self, df: pd.DataFrame) -> StrategyResult:
        signals = []
        if df is None or len(df) < 2:
            return StrategyResult(strategy_name=self.name, signals=signals)

        min_bars = int(getattr(self, "min_bars", 2))
        start = max(1, min(min_bars - 1, len(df) - 1))
        for i in range(start, len(df)):
            try:
                signal = self.generate_signal(df.iloc[:i + 1].copy())
            except Exception as e:
                logger.debug(f"{self.name} generate_signal failed at {i}: {e}")
                continue
            if not signal or signal.signal_type == SignalType.HOLD:
                continue
            signal.strength = round(float(np.clip(signal.strength, 0, 1)), 2)
            signal.bar_index = i
            if signal.position_pct <= 0:
                signal.position_pct = round(float(np.clip(signal.strength * 0.55, 0.2, 0.65)), 2)
            signals.append(signal)

        return StrategyResult(strategy_name=self.name, signals=signals)

    def get_info(self) -> dict:
        return {"name": self.name, "type": self.__class__.__base__.__name__}

    @staticmethod
    def get_param_space() -> dict:
        return {}


def _safe_float(value, default: float = 0.0) -> float:
    try:
        value = float(value)
        return value if np.isfinite(value) else default
    except (TypeError, ValueError):
        return default


def _signal(signal_type: SignalType, strength: float = 0.0, reason: str = "",
            position_pct: float = 0.0) -> TradeSignal:
    return TradeSignal(
        signal_type=signal_type,
        strength=round(float(np.clip(strength, 0, 1)), 2),
        reason=reason,
        position_pct=position_pct,
    )


def _rsi_series(c: pd.Series, period: int = 14) -> pd.Series:
    delta = c.diff()
    gain = delta.clip(lower=0)
    loss = (-delta.clip(upper=0))
    avg_gain = gain.ewm(alpha=1 / period, min_periods=period, adjust=False).mean()
    avg_loss = loss.ewm(alpha=1 / period, min_periods=period, adjust=False).mean()
    rs = avg_gain / avg_loss.replace(0, np.nan)
    return (100 - 100 / (1 + rs)).fillna(50)


class DualMAStrategy(BaseStrategy):
    """双均线策略"""

    def __init__(self, short_period: int = 5, long_period: int = 20):
        super().__init__()
        self._short = short_period
        self._long = long_period

    def generate_signal(self, df: pd.DataFrame) -> TradeSignal:
        if len(df) < self._long + 1:
            return TradeSignal(SignalType.HOLD)
        c = df["close"].astype(float)
        ma_short = c.rolling(self._short).mean()
        ma_long = c.rolling(self._long).mean()
        if ma_short.iloc[-1] > ma_long.iloc[-1] and ma_short.iloc[-2] <= ma_long.iloc[-2]:
            return TradeSignal(SignalType.BUY, 0.7, f"MA{self._short}上穿MA{self._long}")
        if ma_short.iloc[-1] < ma_long.iloc[-1] and ma_short.iloc[-2] >= ma_long.iloc[-2]:
            return TradeSignal(SignalType.SELL, 0.7, f"MA{self._short}下穿MA{self._long}")
        if ma_short.iloc[-1] > ma_long.iloc[-1]:
            return TradeSignal(SignalType.BUY, 0.3, f"MA{self._short}>MA{self._long}")
        return TradeSignal(SignalType.SELL, 0.3, f"MA{self._short}<MA{self._long}")


class MACDStrategy(BaseStrategy):
    """MACD策略"""

    def generate_signal(self, df: pd.DataFrame) -> TradeSignal:
        if len(df) < 35:
            return TradeSignal(SignalType.HOLD)
        c = df["close"].astype(float)
        ema12 = c.ewm(span=12, adjust=False).mean()
        ema26 = c.ewm(span=26, adjust=False).mean()
        dif = ema12 - ema26
        dea = dif.ewm(span=9, adjust=False).mean()
        hist = (dif - dea) * 2
        if dif.iloc[-1] > dea.iloc[-1] and dif.iloc[-2] <= dea.iloc[-2]:
            return TradeSignal(SignalType.BUY, 0.8, "MACD金叉")
        if dif.iloc[-1] < dea.iloc[-1] and dif.iloc[-2] >= dea.iloc[-2]:
            return TradeSignal(SignalType.SELL, 0.8, "MACD死叉")
        if hist.iloc[-1] > 0 and hist.iloc[-1] > hist.iloc[-2]:
            return TradeSignal(SignalType.BUY, 0.4, "MACD柱增长")
        if hist.iloc[-1] < 0 and hist.iloc[-1] < hist.iloc[-2]:
            return TradeSignal(SignalType.SELL, 0.4, "MACD柱缩短")
        return TradeSignal(SignalType.HOLD)


class KDJStrategy(BaseStrategy):
    """KDJ策略"""

    def generate_signal(self, df: pd.DataFrame) -> TradeSignal:
        if len(df) < 12:
            return TradeSignal(SignalType.HOLD)
        h = df["high"].astype(float)
        l = df["low"].astype(float)
        c = df["close"].astype(float)
        n = 9
        hh = h.rolling(n).max()
        ll = l.rolling(n).min()
        rsv = (c - ll) / (hh - ll) * 100
        rsv = rsv.fillna(50)
        k = rsv.ewm(alpha=1/3, adjust=False).mean()
        d = k.ewm(alpha=1/3, adjust=False).mean()
        j = 3 * k - 2 * d
        if k.iloc[-1] > d.iloc[-1] and k.iloc[-2] <= d.iloc[-2] and k.iloc[-1] < 30:
            return TradeSignal(SignalType.BUY, 0.8, "KDJ低位金叉")
        if k.iloc[-1] < d.iloc[-1] and k.iloc[-2] >= d.iloc[-2] and k.iloc[-1] > 70:
            return TradeSignal(SignalType.SELL, 0.8, "KDJ高位死叉")
        if j.iloc[-1] < 0:
            return TradeSignal(SignalType.BUY, 0.5, "J值超卖")
        if j.iloc[-1] > 100:
            return TradeSignal(SignalType.SELL, 0.5, "J值超买")
        return TradeSignal(SignalType.HOLD)


class BollingerBreakoutStrategy(BaseStrategy):
    """布林带突破策略"""

    def generate_signal(self, df: pd.DataFrame) -> TradeSignal:
        if len(df) < 22:
            return TradeSignal(SignalType.HOLD)
        c = df["close"].astype(float)
        mid = c.rolling(20).mean()
        std = c.rolling(20).std()
        upper = mid + 2 * std
        lower = mid - 2 * std
        if c.iloc[-1] <= lower.iloc[-1]:
            return TradeSignal(SignalType.BUY, 0.7, "触及布林下轨")
        if c.iloc[-1] >= upper.iloc[-1]:
            return TradeSignal(SignalType.SELL, 0.7, "触及布林上轨")
        return TradeSignal(SignalType.HOLD)


class MomentumStrategy(BaseStrategy):
    """动量策略"""

    def __init__(self, period: int = 20):
        super().__init__()
        self._period = period

    def generate_signal(self, df: pd.DataFrame) -> TradeSignal:
        if len(df) < self._period + 1:
            return TradeSignal(SignalType.HOLD)
        c = df["close"].astype(float)
        ret = (c.iloc[-1] / c.iloc[-self._period] - 1) * 100
        if ret > 5:
            return TradeSignal(SignalType.BUY, min(0.9, ret / 10), f"动量上涨{ret:.1f}%")
        if ret < -5:
            return TradeSignal(SignalType.SELL, min(0.9, abs(ret) / 10), f"动量下跌{ret:.1f}%")
        return TradeSignal(SignalType.HOLD)


class MultiFactorConfluenceStrategy(BaseStrategy):
    """多因子共振策略"""

    def generate_signal(self, df: pd.DataFrame) -> TradeSignal:
        if len(df) < 60:
            return TradeSignal(SignalType.HOLD)
        c = df["close"].astype(float)
        score = 0
        reasons = []
        ma5 = c.rolling(5).mean().iloc[-1]
        ma20 = c.rolling(20).mean().iloc[-1]
        ma60 = c.rolling(60).mean().iloc[-1]
        if ma5 > ma20 > ma60:
            score += 0.3
            reasons.append("多头排列")
        elif ma5 < ma20 < ma60:
            score -= 0.3
            reasons.append("空头排列")
        ema12 = c.ewm(span=12, adjust=False).mean()
        ema26 = c.ewm(span=26, adjust=False).mean()
        dif = ema12 - ema26
        dea = dif.ewm(span=9, adjust=False).mean()
        if dif.iloc[-1] > dea.iloc[-1]:
            score += 0.2
            reasons.append("MACD多头")
        else:
            score -= 0.2
            reasons.append("MACD空头")
        delta = c.diff()
        gain = delta.where(delta > 0, 0)
        loss = -delta.where(delta < 0, 0)
        avg_gain = gain.rolling(14).mean()
        avg_loss = loss.rolling(14).mean()
        rs = avg_gain / avg_loss.replace(0, np.nan)
        rsi = (100 - 100 / (1 + rs)).iloc[-1]
        if rsi < 30:
            score += 0.3
            reasons.append(f"RSI超卖({rsi:.0f})")
        elif rsi > 70:
            score -= 0.3
            reasons.append(f"RSI超买({rsi:.0f})")
        elif rsi < 50:
            score += 0.1
        else:
            score -= 0.1
        if score >= 0.5:
            return TradeSignal(SignalType.BUY, min(1.0, score), "+".join(reasons))
        if score <= -0.5:
            return TradeSignal(SignalType.SELL, min(1.0, abs(score)), "+".join(reasons))
        return TradeSignal(SignalType.HOLD, abs(score), "多因子中性")


class AdaptiveTrendFollowingStrategy(BaseStrategy):
    """自适应趋势跟踪策略"""

    def generate_signal(self, df: pd.DataFrame) -> TradeSignal:
        if len(df) < 30:
            return TradeSignal(SignalType.HOLD)
        c = df["close"].astype(float)
        h = df["high"].astype(float)
        l = df["low"].astype(float)
        tr = pd.concat([h - l, (h - c.shift(1)).abs(), (l - c.shift(1)).abs()], axis=1).max(axis=1)
        atr = tr.rolling(14).mean().iloc[-1]
        if atr <= 0 or np.isnan(atr):
            return TradeSignal(SignalType.HOLD)
        hl2 = (h + l) / 2
        upper = hl2 + 3 * tr.rolling(14).mean()
        lower = hl2 - 3 * tr.rolling(14).mean()
        supertrend = lower.copy()
        direction = pd.Series(1, index=df.index)
        for i in range(1, len(df)):
            if c.iloc[i] > supertrend.iloc[i - 1]:
                direction.iloc[i] = 1
                supertrend.iloc[i] = max(lower.iloc[i], supertrend.iloc[i - 1])
            else:
                direction.iloc[i] = -1
                supertrend.iloc[i] = min(upper.iloc[i], supertrend.iloc[i - 1])
        if direction.iloc[-1] == 1 and direction.iloc[-2] == -1:
            return TradeSignal(SignalType.BUY, 0.8, "SuperTrend翻多")
        if direction.iloc[-1] == -1 and direction.iloc[-2] == 1:
            return TradeSignal(SignalType.SELL, 0.8, "SuperTrend翻空")
        if direction.iloc[-1] == 1:
            return TradeSignal(SignalType.BUY, 0.4, "SuperTrend多头")
        return TradeSignal(SignalType.SELL, 0.4, "SuperTrend空头")


class MeanReversionProStrategy(BaseStrategy):
    """均值回归增强策略"""

    def generate_signal(self, df: pd.DataFrame) -> TradeSignal:
        if len(df) < 30:
            return TradeSignal(SignalType.HOLD)
        c = df["close"].astype(float)
        ma = c.rolling(20).mean()
        std = c.rolling(20).std()
        z_score = (c - ma) / std.replace(0, np.nan)
        z = z_score.iloc[-1]
        if np.isnan(z):
            return TradeSignal(SignalType.HOLD)
        if z < -2.0:
            return TradeSignal(SignalType.BUY, min(0.9, abs(z) / 3), f"Z-score超卖({z:.2f})")
        if z > 2.0:
            return TradeSignal(SignalType.SELL, min(0.9, z / 3), f"Z-score超买({z:.2f})")
        return TradeSignal(SignalType.HOLD)


class VolatilitySqueezeBreakoutStrategy(BaseStrategy):
    """波动率收缩突破策略"""

    def generate_signal(self, df: pd.DataFrame) -> TradeSignal:
        if len(df) < 25:
            return TradeSignal(SignalType.HOLD)
        c = df["close"].astype(float)
        h = df["high"].astype(float)
        l = df["low"].astype(float)
        tr = pd.concat([h - l, (h - c.shift(1)).abs(), (l - c.shift(1)).abs()], axis=1).max(axis=1)
        atr = tr.rolling(14).mean()
        bb_width = c.rolling(20).std() * 4 / c.rolling(20).mean().replace(0, np.nan)
        squeeze = bb_width.iloc[-1] < bb_width.rolling(20).mean().iloc[-1] * 0.6
        if squeeze and c.iloc[-1] > c.rolling(20).mean().iloc[-1]:
            return TradeSignal(SignalType.BUY, 0.7, "波动率收缩向上突破")
        if squeeze and c.iloc[-1] < c.rolling(20).mean().iloc[-1]:
            return TradeSignal(SignalType.SELL, 0.7, "波动率收缩向下突破")
        return TradeSignal(SignalType.HOLD)


class RSIMeanReversionStrategy(BaseStrategy):
    """RSI均值回归策略"""

    def generate_signal(self, df: pd.DataFrame) -> TradeSignal:
        if len(df) < 20:
            return TradeSignal(SignalType.HOLD)
        c = df["close"].astype(float)
        delta = c.diff()
        gain = delta.where(delta > 0, 0)
        loss = -delta.where(delta < 0, 0)
        avg_gain = gain.rolling(14).mean()
        avg_loss = loss.rolling(14).mean()
        rs = avg_gain / avg_loss.replace(0, np.nan)
        rsi = 100 - 100 / (1 + rs)
        rsi_val = rsi.iloc[-1]
        if np.isnan(rsi_val):
            return TradeSignal(SignalType.HOLD)
        if rsi_val < 25:
            return TradeSignal(SignalType.BUY, 0.8, f"RSI深度超卖({rsi_val:.0f})")
        if rsi_val > 75:
            return TradeSignal(SignalType.SELL, 0.8, f"RSI深度超买({rsi_val:.0f})")
        if rsi_val < 35 and rsi.iloc[-2] < rsi.iloc[-1]:
            return TradeSignal(SignalType.BUY, 0.5, "RSI超卖回升")
        if rsi_val > 65 and rsi.iloc[-2] > rsi.iloc[-1]:
            return TradeSignal(SignalType.SELL, 0.5, "RSI超买回落")
        return TradeSignal(SignalType.HOLD)


class SuperTrendStrategy(BaseStrategy):
    """SuperTrend策略"""

    def generate_signal(self, df: pd.DataFrame) -> TradeSignal:
        if len(df) < 30:
            return TradeSignal(SignalType.HOLD)
        c = df["close"].astype(float)
        h = df["high"].astype(float)
        l = df["low"].astype(float)
        tr = pd.concat([h - l, (h - c.shift(1)).abs(), (l - c.shift(1)).abs()], axis=1).max(axis=1)
        atr = tr.rolling(10).mean()
        hl2 = (h + l) / 2
        upper_band = hl2 + 3.0 * atr
        lower_band = hl2 - 3.0 * atr
        n = len(df)
        supertrend = pd.Series(0.0, index=df.index)
        direction = pd.Series(1, index=df.index)
        for i in range(1, n):
            if lower_band.iloc[i] > lower_band.iloc[i - 1] or c.iloc[i - 1] < lower_band.iloc[i - 1]:
                pass
            else:
                lower_band.iloc[i] = lower_band.iloc[i - 1]
            if upper_band.iloc[i] < upper_band.iloc[i - 1] or c.iloc[i - 1] > upper_band.iloc[i - 1]:
                pass
            else:
                upper_band.iloc[i] = upper_band.iloc[i - 1]
            if direction.iloc[i - 1] == 1:
                if c.iloc[i] < lower_band.iloc[i]:
                    direction.iloc[i] = -1
                    supertrend.iloc[i] = upper_band.iloc[i]
                else:
                    direction.iloc[i] = 1
                    supertrend.iloc[i] = lower_band.iloc[i]
            else:
                if c.iloc[i] > upper_band.iloc[i]:
                    direction.iloc[i] = 1
                    supertrend.iloc[i] = lower_band.iloc[i]
                else:
                    direction.iloc[i] = -1
                    supertrend.iloc[i] = upper_band.iloc[i]
        if direction.iloc[-1] == 1 and direction.iloc[-2] == -1:
            return TradeSignal(SignalType.BUY, 0.85, "SuperTrend翻多")
        if direction.iloc[-1] == -1 and direction.iloc[-2] == 1:
            return TradeSignal(SignalType.SELL, 0.85, "SuperTrend翻空")
        return TradeSignal(SignalType.HOLD)


class IchimokuCloudStrategy(BaseStrategy):
    """一目均衡表策略"""

    min_bars = 80

    def __init__(self, tenkan_period: int = 9, kijun_period: int = 26, senkou_b_period: int = 52):
        super().__init__()
        self._tenkan = int(tenkan_period)
        self._kijun = int(kijun_period)
        self._senkou_b = int(senkou_b_period)

    def generate_signal(self, df: pd.DataFrame) -> TradeSignal:
        if df is None or len(df) < self._senkou_b + self._kijun + 2:
            return TradeSignal(SignalType.HOLD)

        h = df["high"].astype(float)
        l = df["low"].astype(float)
        c = df["close"].astype(float)
        v = df["volume"].astype(float) if "volume" in df.columns else pd.Series(0, index=df.index)

        def mid_line(high, low, period):
            return (high.rolling(period).max() + low.rolling(period).min()) / 2

        tenkan = mid_line(h, l, self._tenkan)
        kijun = mid_line(h, l, self._kijun)
        senkou_a = ((tenkan + kijun) / 2).shift(self._kijun)
        senkou_b = mid_line(h, l, self._senkou_b).shift(self._kijun)

        last_c = _safe_float(c.iloc[-1])
        prev_c = _safe_float(c.iloc[-2])
        cloud_top = max(_safe_float(senkou_a.iloc[-1]), _safe_float(senkou_b.iloc[-1]))
        cloud_bot = min(_safe_float(senkou_a.iloc[-1]), _safe_float(senkou_b.iloc[-1]))
        prev_cloud_top = max(_safe_float(senkou_a.iloc[-2]), _safe_float(senkou_b.iloc[-2]))

        if cloud_top <= 0 or cloud_bot <= 0:
            return TradeSignal(SignalType.HOLD)

        tk_cross_up = (
            _safe_float(tenkan.iloc[-1]) > _safe_float(kijun.iloc[-1])
            and _safe_float(tenkan.iloc[-2]) <= _safe_float(kijun.iloc[-2])
        )
        chikou_above_price = len(c) > self._kijun and last_c > _safe_float(c.iloc[-self._kijun])
        price_above_cloud = last_c > cloud_top
        price_below_cloud = last_c < cloud_bot

        # 云层变厚且上移，说明趋势支撑正在增强。
        cloud_thickness = abs(_safe_float(senkou_a.iloc[-1]) - _safe_float(senkou_b.iloc[-1]))
        prev_thickness = abs(_safe_float(senkou_a.iloc[-6]) - _safe_float(senkou_b.iloc[-6])) if len(df) > 6 else cloud_thickness
        cloud_confirm = cloud_thickness > prev_thickness and cloud_top > prev_cloud_top

        vol_ma = _safe_float(v.rolling(20).mean().iloc[-1])
        vol_expand = vol_ma > 0 and _safe_float(v.iloc[-1]) > vol_ma * 1.5

        if tk_cross_up and price_above_cloud and chikou_above_price:
            strength = 0.9 + (0.05 if cloud_confirm else 0)
            return _signal(SignalType.BUY, strength, "一目均衡金叉+云上+迟行线确认", 0.55)
        if prev_c <= prev_cloud_top and last_c > cloud_top and vol_expand:
            return _signal(SignalType.BUY, 0.75, "收盘价放量突破云层上沿", 0.45)
        if price_below_cloud:
            return _signal(SignalType.SELL, 0.8, "收盘价跌破云层下沿")
        if price_above_cloud and cloud_confirm:
            return _signal(SignalType.BUY, 0.45, "云层上移且趋势确认", 0.30)
        return TradeSignal(SignalType.HOLD)

    @staticmethod
    def get_param_space() -> dict:
        return {
            "tenkan_period": {"min": 7, "max": 15, "step": 1},
            "kijun_period": {"min": 20, "max": 32, "step": 2},
        }


class VWAPDeviationStrategy(BaseStrategy):
    """VWAP偏离均值回归策略"""

    min_bars = 35

    def __init__(self, vwap_window: int = 20, sigma_mult: float = 2.5):
        super().__init__()
        self._window = int(vwap_window)
        self._sigma_mult = float(sigma_mult)

    def generate_signal(self, df: pd.DataFrame) -> TradeSignal:
        if df is None or len(df) < self._window + 15:
            return TradeSignal(SignalType.HOLD)
        c = df["close"].astype(float)
        h = df["high"].astype(float)
        l = df["low"].astype(float)
        v = df["volume"].astype(float) if "volume" in df.columns else pd.Series(1, index=df.index)
        typical = (h + l + c) / 3
        vol_sum = v.rolling(self._window).sum().replace(0, np.nan)
        vwap = (typical * v).rolling(self._window).sum() / vol_sum
        spread = c - vwap
        sigma = spread.rolling(self._window).std().replace(0, np.nan)
        z = _safe_float((spread / sigma).iloc[-1])
        rsi = _safe_float(_rsi_series(c, 14).iloc[-1], 50)
        vol_ma = _safe_float(v.rolling(self._window).mean().iloc[-1])
        vol_not_expand = vol_ma <= 0 or _safe_float(v.iloc[-1]) <= vol_ma * 1.2

        if z < -self._sigma_mult and rsi < 35 and vol_not_expand:
            return _signal(SignalType.BUY, 0.8, f"价格低于VWAP {abs(z):.1f}σ且RSI超卖", 0.45)
        if z > self._sigma_mult and rsi > 65:
            return _signal(SignalType.SELL, 0.8, f"价格高于VWAP {z:.1f}σ且RSI超买")
        if abs(z) <= 0.3:
            return TradeSignal(SignalType.HOLD, 0.6, "价格回归VWAP附近")
        return TradeSignal(SignalType.HOLD)

    @staticmethod
    def get_param_space() -> dict:
        return {
            "vwap_window": {"min": 10, "max": 30, "step": 5},
            "sigma_mult": {"min": 1.5, "max": 3.0, "step": 0.25},
        }


class OrderFlowImbalanceStrategy(BaseStrategy):
    """订单流失衡策略（日线近似）"""

    min_bars = 25

    def __init__(self, ofi_window: int = 10):
        super().__init__()
        self._window = int(ofi_window)

    def generate_signal(self, df: pd.DataFrame) -> TradeSignal:
        if df is None or len(df) < 15:
            return TradeSignal(SignalType.HOLD)
        o = df["open"].astype(float) if "open" in df.columns else df["close"].astype(float)
        h = df["high"].astype(float)
        l = df["low"].astype(float)
        c = df["close"].astype(float)
        v = df["volume"].astype(float) if "volume" in df.columns else pd.Series(1, index=df.index)
        spread = (h - l).replace(0, np.nan)

        buy_pressure = np.where(c > o, v * (c - l) / spread, v * (h - c) / spread * 0.5)
        sell_pressure = np.where(c < o, v * (h - c) / spread, v * (c - l) / spread * 0.5)
        buy_pressure = pd.Series(np.nan_to_num(buy_pressure, nan=0.0), index=df.index)
        sell_pressure = pd.Series(np.nan_to_num(sell_pressure, nan=0.0), index=df.index)
        total_vol = v.rolling(self._window).sum().replace(0, np.nan)
        ofi = ((buy_pressure - sell_pressure).rolling(self._window).sum() / total_vol).fillna(0)
        ofi_diff = ofi.diff().fillna(0)
        price_ret_3 = _safe_float(c.iloc[-1] / c.iloc[-4] - 1) if len(c) >= 4 and c.iloc[-4] > 0 else 0

        if _safe_float(ofi.iloc[-1]) > 0.3 and _safe_float(ofi_diff.iloc[-1]) > _safe_float(ofi_diff.iloc[-2]):
            return _signal(SignalType.BUY, 0.7, "订单流失衡向买方加速", 0.40)
        if _safe_float(ofi.iloc[-1]) < -0.3 and _safe_float(ofi_diff.iloc[-1]) < _safe_float(ofi_diff.iloc[-2]):
            return _signal(SignalType.SELL, 0.7, "订单流失衡向卖方加速")
        if price_ret_3 > 0.02 and _safe_float(ofi.iloc[-1]) < _safe_float(ofi.iloc[-4]):
            return _signal(SignalType.SELL, 0.5, "价涨但订单流转弱，反转预警")
        return TradeSignal(SignalType.HOLD)

    @staticmethod
    def get_param_space() -> dict:
        return {"ofi_window": {"min": 6, "max": 14, "step": 2}}


class RegimeSwitchingStrategy(BaseStrategy):
    """简化马尔科夫机制转换策略"""

    min_bars = 90

    def __init__(self, window: int = 120, max_iter: int = 50, tol: float = 1e-6):
        super().__init__()
        self._window = int(window)
        self._max_iter = int(max_iter)
        self._tol = float(tol)

    @staticmethod
    def _normal_pdf(x: np.ndarray, mean: float, std: float) -> np.ndarray:
        std = max(float(std), 1e-6)
        z = (x - mean) / std
        return np.exp(-0.5 * z * z) / (std * np.sqrt(2 * np.pi)) + 1e-12

    def _fit_hmm(self, returns: np.ndarray) -> tuple[int, np.ndarray, np.ndarray, np.ndarray]:
        x = np.asarray(returns, dtype=float)
        x = x[np.isfinite(x)]
        if len(x) < 30:
            return 0, np.array([[0.9, 0.1], [0.1, 0.9]]), np.zeros((len(x), 2)), np.array([0.0, 0.0])

        q25, q75 = np.quantile(x, [0.25, 0.75])
        means = np.array([q75, q25], dtype=float)
        stds = np.array([max(np.std(x[x >= np.median(x)]), 1e-4), max(np.std(x[x < np.median(x)]), 1e-4)])
        trans = np.array([[0.92, 0.08], [0.12, 0.88]], dtype=float)
        pi = np.array([0.5, 0.5], dtype=float)
        prev_ll = -np.inf

        for _ in range(self._max_iter):
            emit = np.column_stack([
                self._normal_pdf(x, means[0], stds[0]),
                self._normal_pdf(x, means[1], stds[1]),
            ])
            alpha = np.zeros_like(emit)
            scale = np.zeros(len(x))
            alpha[0] = pi * emit[0]
            scale[0] = max(alpha[0].sum(), 1e-12)
            alpha[0] /= scale[0]
            for t in range(1, len(x)):
                alpha[t] = (alpha[t - 1] @ trans) * emit[t]
                scale[t] = max(alpha[t].sum(), 1e-12)
                alpha[t] /= scale[t]

            beta = np.ones_like(emit)
            for t in range(len(x) - 2, -1, -1):
                beta[t] = trans @ (emit[t + 1] * beta[t + 1])
                beta[t] /= max(scale[t + 1], 1e-12)

            gamma = alpha * beta
            gamma /= np.maximum(gamma.sum(axis=1, keepdims=True), 1e-12)

            xi_sum = np.zeros((2, 2))
            for t in range(len(x) - 1):
                xi = alpha[t][:, None] * trans * emit[t + 1][None, :] * beta[t + 1][None, :]
                xi_sum += xi / max(xi.sum(), 1e-12)

            pi = gamma[0]
            trans = xi_sum / np.maximum(gamma[:-1].sum(axis=0)[:, None], 1e-12)
            trans = np.nan_to_num(trans, nan=0.5)
            trans /= np.maximum(trans.sum(axis=1, keepdims=True), 1e-12)
            weights = np.maximum(gamma.sum(axis=0), 1e-12)
            means = (gamma * x[:, None]).sum(axis=0) / weights
            vars_ = (gamma * (x[:, None] - means) ** 2).sum(axis=0) / weights
            stds = np.sqrt(np.maximum(vars_, 1e-8))

            ll = float(np.sum(np.log(scale + 1e-12)))
            if abs(ll - prev_ll) < self._tol:
                break
            prev_ll = ll

        state_score = means - 0.5 * stds
        bull_state = int(np.argmax(state_score))
        current_state = int(np.argmax(gamma[-1]))
        return current_state, trans, gamma, means

    def generate_signal(self, df: pd.DataFrame) -> TradeSignal:
        if df is None or len(df) < 60:
            return TradeSignal(SignalType.HOLD)
        c = df["close"].astype(float)
        returns = c.pct_change().replace([np.inf, -np.inf], np.nan).dropna().tail(self._window).values
        if len(returns) < 40:
            return TradeSignal(SignalType.HOLD)
        current_state, trans, gamma, means = self._fit_hmm(np.clip(returns, -0.12, 0.12))
        state_score = means - 0.5 * np.std(returns)
        bull_state = int(np.argmax(state_score))
        bear_state = 1 - bull_state
        p_bull_stay = _safe_float(trans[bull_state, bull_state])
        p_bull_to_bear = _safe_float(trans[bull_state, bear_state])

        if current_state == bull_state and p_bull_stay > 0.8:
            return _signal(SignalType.BUY, 0.7, f"低波动牛市状态延续(P={p_bull_stay:.2f})", 0.40)
        if current_state == bear_state or p_bull_to_bear > 0.22:
            return _signal(SignalType.SELL, 0.75, f"高波动熊市/转熊概率上升(P={p_bull_to_bear:.2f})")
        if len(gamma) > 5 and gamma[-1, bull_state] < gamma[-5, bull_state] - 0.2:
            return _signal(SignalType.SELL, 0.6, "牛市状态概率快速下降")
        return TradeSignal(SignalType.HOLD)

    @staticmethod
    def get_param_space() -> dict:
        return {"window": {"min": 80, "max": 160, "step": 20}}


class FractalBreakoutStrategy(BaseStrategy):
    """Bill Williams分形突破策略"""

    min_bars = 35

    def __init__(self, lookback: int = 20):
        super().__init__()
        self._lookback = int(lookback)

    def generate_signal(self, df: pd.DataFrame) -> TradeSignal:
        if df is None or len(df) < 25:
            return TradeSignal(SignalType.HOLD)
        h = df["high"].astype(float).reset_index(drop=True)
        l = df["low"].astype(float).reset_index(drop=True)
        c = df["close"].astype(float).reset_index(drop=True)
        v = df["volume"].astype(float).reset_index(drop=True) if "volume" in df.columns else pd.Series(1, index=c.index)

        highs = h.values
        lows = l.values
        up_fractal = np.zeros(len(df), dtype=bool)
        down_fractal = np.zeros(len(df), dtype=bool)
        if len(df) >= 5:
            mid_high = highs[2:-2]
            mid_low = lows[2:-2]
            up_fractal[2:-2] = (
                (mid_high > highs[:-4]) & (mid_high > highs[1:-3])
                & (mid_high > highs[3:-1]) & (mid_high > highs[4:])
            )
            down_fractal[2:-2] = (
                (mid_low < lows[:-4]) & (mid_low < lows[1:-3])
                & (mid_low < lows[3:-1]) & (mid_low < lows[4:])
            )

        start = max(0, len(df) - self._lookback - 2)
        recent_up = h.iloc[start:-1][up_fractal[start:-1]]
        recent_down = l.iloc[start:-1][down_fractal[start:-1]]
        top_fractal = _safe_float(recent_up.max()) if len(recent_up) else 0
        bot_fractal = _safe_float(recent_down.min()) if len(recent_down) else 0
        vol_ma = _safe_float(v.rolling(20).mean().iloc[-1])
        vol_confirm = vol_ma > 0 and _safe_float(v.iloc[-1]) > vol_ma * 1.5

        ma5 = c.rolling(5).mean()
        ma8 = c.rolling(8).mean()
        ma13 = c.rolling(13).mean()
        alligator_open = (
            _safe_float(ma5.iloc[-1]) > _safe_float(ma8.iloc[-1]) > _safe_float(ma13.iloc[-1])
            and (_safe_float(ma5.iloc[-1]) - _safe_float(ma13.iloc[-1])) / max(_safe_float(c.iloc[-1]), 1) > 0.01
        )

        if top_fractal > 0 and _safe_float(c.iloc[-1]) > top_fractal and vol_confirm:
            strength = 0.75 + (0.1 if alligator_open else 0)
            return _signal(SignalType.BUY, strength, "向上分形被放量突破，鳄鱼线确认" if alligator_open else "向上分形被放量突破", 0.45)
        if bot_fractal > 0 and _safe_float(c.iloc[-1]) < bot_fractal:
            return _signal(SignalType.SELL, 0.75, "向下分形被跌破")
        if alligator_open and top_fractal > 0 and _safe_float(c.iloc[-1]) > top_fractal * 0.98:
            return _signal(SignalType.BUY, 0.45, "价格贴近向上分形且鳄鱼线张口", 0.30)
        return TradeSignal(SignalType.HOLD)

    @staticmethod
    def get_param_space() -> dict:
        return {"lookback": {"min": 15, "max": 30, "step": 5}}


class WyckoffAccumulationStrategy(BaseStrategy):
    """威科夫积累阶段策略 - 识别PS/SC/AR/ST/SOS五个阶段"""

    min_bars = 65

    def generate_signal(self, df: pd.DataFrame) -> TradeSignal:
        if df is None or len(df) < 60:
            return TradeSignal(SignalType.HOLD)
        c = df["close"].astype(float)
        h = df["high"].astype(float)
        l = df["low"].astype(float)
        v = df["volume"].astype(float) if "volume" in df.columns else pd.Series(1, index=df.index)

        window = min(60, len(df) - 1)
        recent_c = c.iloc[-window:]
        recent_l = l.iloc[-window:]
        recent_h = h.iloc[-window:]
        recent_v = v.iloc[-window:]

        vol_ma = _safe_float(recent_v.rolling(20).mean().iloc[-1])
        last_vol = _safe_float(recent_v.iloc[-1])
        vol_ratio = last_vol / vol_ma if vol_ma > 0 else 1.0

        # SC阶段：价格创新低+成交量暴增+下影线>实体2倍
        last_close = _safe_float(recent_c.iloc[-1])
        last_low = _safe_float(recent_l.iloc[-1])
        last_high = _safe_float(recent_h.iloc[-1])
        body = abs(last_close - _safe_float(recent_c.iloc[-2]))
        lower_shadow = _safe_float(min(recent_c.iloc[-1], recent_c.iloc[-2])) - last_low
        is_sc = (
            last_close <= _safe_float(recent_c.rolling(20).min().iloc[-1])
            and vol_ratio > 3.0
            and lower_shadow > body * 2
        )

        # AR高点：SC后反弹的最高价
        low_20 = _safe_float(recent_l.rolling(20).min().iloc[-1])
        ar_high = _safe_float(recent_h.iloc[-5:].max())

        # SOS阶段：价格突破AR高点+成交量确认
        is_sos = last_close > ar_high and vol_ratio > 1.2

        # 跌破SC低点
        if last_close < low_20:
            return _signal(SignalType.SELL, 0.9, "价格跌破SC低点，威科夫派发")

        if is_sos:
            return _signal(SignalType.BUY, 0.85, "威科夫SOS阶段：力量显现，突破AR高点")

        if is_sc:
            return _signal(SignalType.BUY, 0.7, "威科夫SC阶段：抛售高潮，关注买入")

        return TradeSignal(SignalType.HOLD)

    @staticmethod
    def get_param_space() -> dict:
        return {"window": {"min": 40, "max": 80, "step": 10}}


class ElliottWaveAIStrategy(BaseStrategy):
    """简化艾略特波浪策略 - 用波峰波谷识别5浪/ABC结构"""

    min_bars = 130

    def generate_signal(self, df: pd.DataFrame) -> TradeSignal:
        if df is None or len(df) < 120:
            return TradeSignal(SignalType.HOLD)
        c = df["close"].astype(float).reset_index(drop=True)
        v = df["volume"].astype(float).reset_index(drop=True) if "volume" in df.columns else pd.Series(1, index=c.index)
        prices = c.values

        try:
            from scipy.signal import find_peaks
            peaks, _ = find_peaks(prices, distance=5, prominence=prices.std() * 0.3)
            troughs, _ = find_peaks(-prices, distance=5, prominence=prices.std() * 0.3)
        except (ImportError, ValueError):
            return TradeSignal(SignalType.HOLD)

        if len(peaks) < 3 or len(troughs) < 3:
            return TradeSignal(SignalType.HOLD)

        # 合并波峰波谷并按位置排序
        pivots = sorted(
            [(int(p), float(prices[p]), "peak") for p in peaks[-6:]] +
            [(int(t), float(prices[t]), "trough") for t in troughs[-6:]],
            key=lambda x: x[0],
        )

        if len(pivots) < 5:
            return TradeSignal(SignalType.HOLD)

        # 检查5浪上升结构
        last_5 = pivots[-5:]
        is_impulse_up = (
            last_5[0][2] == "trough" and last_5[1][2] == "peak" and
            last_5[2][2] == "trough" and last_5[3][2] == "peak" and
            last_5[4][2] == "trough" and
            last_5[1][1] > last_5[0][1] and
            last_5[3][1] > last_5[1][1] and
            last_5[2][1] > last_5[0][1]
        )

        # 检查第3浪初期（最强上升浪）
        if is_impulse_up and len(pivots) >= 3:
            last_pivot = pivots[-1]
            prev_pivot = pivots[-2]
            if last_pivot[2] == "trough" and prev_pivot[2] == "peak":
                wave3_ratio = prev_pivot[1] / max(last_5[0][1], 1e-9)
                if 1.618 < wave3_ratio < 4.236:
                    return _signal(SignalType.BUY, 0.9, "艾略特第3浪初期，最强上升浪")

        # 第5浪末期：RSI背离+成交量萎缩
        rsi = _safe_float(_rsi_series(c, 14).iloc[-1], 50)
        vol_ma = _safe_float(v.rolling(20).mean().iloc[-1])
        vol_shrink = vol_ma > 0 and _safe_float(v.iloc[-1]) < vol_ma * 0.7

        if is_impulse_up and rsi > 70 and vol_shrink:
            return _signal(SignalType.SELL, 0.85, "艾略特第5浪末期，RSI背离+量缩")

        # ABC调整浪C浪末端
        if len(pivots) >= 3:
            last_3 = pivots[-3:]
            if (last_3[0][2] == "peak" and last_3[1][2] == "trough" and
                    last_3[2][2] == "peak" and rsi < 35):
                return _signal(SignalType.BUY, 0.7, "ABC调整浪C浪末端，超卖买入")

        return TradeSignal(SignalType.HOLD)

    @staticmethod
    def get_param_space() -> dict:
        return {"min_bars": {"min": 100, "max": 160, "step": 20}}


class MarketMicrostructureStrategy(BaseStrategy):
    """市场微观结构策略 - 用日线近似Amihud非流动性和价格冲击"""

    min_bars = 30

    def generate_signal(self, df: pd.DataFrame) -> TradeSignal:
        if df is None or len(df) < 25:
            return TradeSignal(SignalType.HOLD)
        c = df["close"].astype(float)
        h = df["high"].astype(float)
        l = df["low"].astype(float)
        v = df["volume"].astype(float) if "volume" in df.columns else pd.Series(1, index=df.index)
        o = df["open"].astype(float) if "open" in df.columns else c

        # Amihud非流动性比率：|收益率|/成交额，滚动20日均值
        returns = c.pct_change().replace([np.inf, -np.inf], np.nan).fillna(0)
        amount = v * c
        illiq = (returns.abs() / amount.replace(0, np.nan)).rolling(20).mean().fillna(0)
        illiq_mean = _safe_float(illiq.rolling(60).mean().iloc[-1]) if len(illiq) >= 60 else _safe_float(illiq.mean())
        illiq_current = _safe_float(illiq.iloc[-1])

        # 非流动性突然下降（流动性改善）且价格上涨
        liquidity_improve = illiq_mean > 0 and illiq_current < illiq_mean * 0.7
        price_up = _safe_float(returns.iloc[-1]) > 0

        if liquidity_improve and price_up:
            return _signal(SignalType.BUY, 0.65, "流动性改善且价格上涨")

        # 价格冲击系数：大成交量对应的价格变动幅度
        spread = h - l
        impact = (spread / v.replace(0, np.nan)).rolling(10).mean().fillna(0)
        impact_diff = impact.diff().fillna(0)

        # 连续3日冲击系数下降+价格上行 → 机构吸筹
        if len(impact_diff) >= 3:
            impact_declining = all(_safe_float(impact_diff.iloc[-i]) < 0 for i in range(1, 4))
            if impact_declining and price_up:
                return _signal(SignalType.BUY, 0.75, "冲击系数连续下降+价格上行，机构吸筹信号")

        return TradeSignal(SignalType.HOLD)

    @staticmethod
    def get_param_space() -> dict:
        return {"illiq_window": {"min": 15, "max": 30, "step": 5}}


class CopulaCorrelationStrategy(BaseStrategy):
    """Copula相关性策略 - 用秩相关检测与基准的偏离"""

    min_bars = 75

    def __init__(self, corr_window: int = 60, threshold: float = 0.3):
        super().__init__()
        self._window = int(corr_window)
        self._threshold = float(threshold)

    def generate_signal(self, df: pd.DataFrame) -> TradeSignal:
        if df is None or len(df) < self._window + 5:
            return TradeSignal(SignalType.HOLD)
        c = df["close"].astype(float)

        # 若无基准列，用沪深300近似（用大盘动量代替）
        if "benchmark_close" in df.columns:
            bench = df["benchmark_close"].astype(float)
        else:
            # 用自身长期均线偏移作为替代基准
            bench = c.rolling(60).mean()

        stock_ret = c.pct_change().dropna()
        bench_ret = bench.pct_change().dropna()
        n = min(len(stock_ret), len(bench_ret))
        if n < self._window:
            return TradeSignal(SignalType.HOLD)

        stock_recent = stock_ret.iloc[-self._window:].values
        bench_recent = bench_ret.iloc[-self._window:].values

        try:
            from scipy.stats import spearmanr
            corr, _ = spearmanr(stock_recent, bench_recent)
            if not np.isfinite(corr):
                corr = 0.0
        except Exception:
            corr = 0.0

        # 历史相关性均值
        hist_corrs = []
        step = max(20, self._window // 3)
        for i in range(step, n, step):
            try:
                seg_corr, _ = spearmanr(stock_recent[:i], bench_recent[:i])
                if np.isfinite(seg_corr):
                    hist_corrs.append(seg_corr)
            except Exception:
                pass
        hist_mean = np.mean(hist_corrs) if hist_corrs else 0.0

        # 个股相对强弱
        stock_cum = (1 + stock_recent).prod()
        bench_cum = (1 + bench_recent).prod()
        stock_stronger = stock_cum > bench_cum

        # 相关性骤降且个股强于基准
        if abs(corr - hist_mean) > self._threshold and stock_stronger:
            return _signal(SignalType.BUY, 0.75, f"相关性骤降(Δ={abs(corr - hist_mean):.2f})且个股强于基准")

        # 相关性骤升+个股弱于基准
        if (corr - hist_mean) > self._threshold and not stock_stronger:
            return _signal(SignalType.SELL, 0.7, f"相关性骤升且个股弱于基准")

        return TradeSignal(SignalType.HOLD)

    @staticmethod
    def get_param_space() -> dict:
        return {"corr_window": {"min": 40, "max": 80, "step": 10}}


class QuantileRegressionStrategy(BaseStrategy):
    """分位数回归策略 - 用τ=0.1/0.5/0.9分位线识别超买超卖"""

    min_bars = 75

    def __init__(self, window: int = 60):
        super().__init__()
        self._window = int(window)

    def generate_signal(self, df: pd.DataFrame) -> TradeSignal:
        if df is None or len(df) < self._window + 5:
            return TradeSignal(SignalType.HOLD)
        c = df["close"].astype(float).reset_index(drop=True)
        prices = c.values
        n = len(prices)

        # 手写分位数回归：用滚动窗口的分位数近似
        def rolling_quantile(arr, window, q):
            result = np.full(len(arr), np.nan)
            for i in range(window - 1, len(arr)):
                segment = arr[i - window + 1:i + 1]
                finite = segment[np.isfinite(segment)]
                if len(finite) >= 10:
                    result[i] = np.quantile(finite, q)
            return result

        q10 = rolling_quantile(prices, self._window, 0.1)
        q50 = rolling_quantile(prices, self._window, 0.5)
        q90 = rolling_quantile(prices, self._window, 0.9)

        last_price = _safe_float(prices[-1])
        last_q10 = _safe_float(q10[-1])
        last_q50 = _safe_float(q50[-1])
        last_q90 = _safe_float(q90[-1])

        if last_q10 <= 0 or last_q50 <= 0 or last_q90 <= 0:
            return TradeSignal(SignalType.HOLD)

        # 中位数线斜率（趋势方向）
        if len(q50) > 5 and not np.isnan(q50[-5]):
            slope = (q50[-1] - q50[-5]) / max(abs(q50[-5]), 1e-9)
        else:
            slope = 0.0

        # 价格跌破τ=0.1分位线且斜率为正 → 超跌买入
        if last_price < last_q10 and slope > 0:
            return _signal(SignalType.BUY, 0.8, "价格跌破10%分位线且趋势向上，超跌买入")

        # 价格超过τ=0.9分位线且斜率放缓 → 超买卖出
        if last_price > last_q90 and slope < 0.01:
            return _signal(SignalType.SELL, 0.75, "价格超过90%分位线且斜率放缓，超买卖出")

        # 中位数线方向代表趋势强度
        if slope > 0.02 and last_price > last_q50:
            return _signal(SignalType.BUY, 0.35, "分位数趋势向上且价格在中位数上方")

        if slope < -0.02 and last_price < last_q50:
            return _signal(SignalType.SELL, 0.35, "分位数趋势向下且价格在中位数下方")

        return TradeSignal(SignalType.HOLD)

    @staticmethod
    def get_param_space() -> dict:
        return {"window": {"min": 40, "max": 80, "step": 10}}


class CompositeStrategy:
    """组合策略"""

    def __init__(self):
        self.strategies = [
            IchimokuCloudStrategy(),
            VWAPDeviationStrategy(),
            OrderFlowImbalanceStrategy(),
            FractalBreakoutStrategy(),
            DualMAStrategy(),
            MACDStrategy(),
            KDJStrategy(),
            BollingerBreakoutStrategy(),
            MomentumStrategy(),
            MultiFactorConfluenceStrategy(),
            WyckoffAccumulationStrategy(),
            ElliottWaveAIStrategy(),
            MarketMicrostructureStrategy(),
            CopulaCorrelationStrategy(),
            QuantileRegressionStrategy(),
        ]

    def get_strategy_info(self) -> list[dict]:
        return [s.get_info() for s in self.strategies]


STRATEGY_REGISTRY = {
    "ma_cross": DualMAStrategy,
    "dual_ma": DualMAStrategy,
    "DualMAStrategy": DualMAStrategy,
    "macd": MACDStrategy,
    "MACDStrategy": MACDStrategy,
    "kdj": KDJStrategy,
    "KDJStrategy": KDJStrategy,
    "bollinger": BollingerBreakoutStrategy,
    "bollinger_breakout": BollingerBreakoutStrategy,
    "BollingerBreakoutStrategy": BollingerBreakoutStrategy,
    "momentum": MomentumStrategy,
    "MomentumStrategy": MomentumStrategy,
    "multi_factor": MultiFactorConfluenceStrategy,
    "MultiFactorConfluenceStrategy": MultiFactorConfluenceStrategy,
    "adaptive_trend": AdaptiveTrendFollowingStrategy,
    "AdaptiveTrendFollowingStrategy": AdaptiveTrendFollowingStrategy,
    "mean_reversion_pro": MeanReversionProStrategy,
    "MeanReversionProStrategy": MeanReversionProStrategy,
    "vol_squeeze": VolatilitySqueezeBreakoutStrategy,
    "volatility_squeeze": VolatilitySqueezeBreakoutStrategy,
    "VolatilitySqueezeBreakoutStrategy": VolatilitySqueezeBreakoutStrategy,
    "rsi": RSIMeanReversionStrategy,
    "rsi_mean_reversion": RSIMeanReversionStrategy,
    "RSIMeanReversionStrategy": RSIMeanReversionStrategy,
    "supertrend": SuperTrendStrategy,
    "SuperTrendStrategy": SuperTrendStrategy,
    "ichimoku": IchimokuCloudStrategy,
    "ichimoku_cloud": IchimokuCloudStrategy,
    "IchimokuCloudStrategy": IchimokuCloudStrategy,
    "vwap_deviation": VWAPDeviationStrategy,
    "VWAPDeviationStrategy": VWAPDeviationStrategy,
    "order_flow": OrderFlowImbalanceStrategy,
    "order_flow_imbalance": OrderFlowImbalanceStrategy,
    "OrderFlowImbalanceStrategy": OrderFlowImbalanceStrategy,
    "regime_switching": RegimeSwitchingStrategy,
    "RegimeSwitchingStrategy": RegimeSwitchingStrategy,
    "fractal_breakout": FractalBreakoutStrategy,
    "FractalBreakoutStrategy": FractalBreakoutStrategy,
    "wyckoff": WyckoffAccumulationStrategy,
    "wyckoff_accumulation": WyckoffAccumulationStrategy,
    "WyckoffAccumulationStrategy": WyckoffAccumulationStrategy,
    "elliott_wave": ElliottWaveAIStrategy,
    "ElliottWaveAIStrategy": ElliottWaveAIStrategy,
    "microstructure": MarketMicrostructureStrategy,
    "market_microstructure": MarketMicrostructureStrategy,
    "MarketMicrostructureStrategy": MarketMicrostructureStrategy,
    "copula": CopulaCorrelationStrategy,
    "copula_correlation": CopulaCorrelationStrategy,
    "CopulaCorrelationStrategy": CopulaCorrelationStrategy,
    "quantile": QuantileRegressionStrategy,
    "quantile_regression": QuantileRegressionStrategy,
    "QuantileRegressionStrategy": QuantileRegressionStrategy,
}
