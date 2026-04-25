"""
趋势跟踪策略 - 均线/MACD/布林带
"""
import numpy as np
from typing import Optional, List, Dict, Any

from strategy.base import Strategy, Bar, Signal, SignalType


class MovingAverageCrossStrategy(Strategy):
    """
    双均线交叉策略
    短期均线上穿长期均线买入，下穿卖出
    """

    name = "双均线交叉"
    description = "基于短期和长期移动平均线的交叉信号"
    risk_level = "medium"

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.params = {
            "short_window": 5,
            "long_window": 20,
            **self.params
        }

    async def on_bar(self, bar: Bar) -> Optional[Signal]:
        await super().on_bar(bar)

        if len(self._data_buffer) < self.params["long_window"]:
            return None

        closes = [b.close for b in self._data_buffer[-self.params["long_window"]:]]
        short_ma = np.mean(closes[-self.params["short_window"]:])
        long_ma = np.mean(closes)

        # 需要至少两根K线才能判断交叉
        if len(self._data_buffer) < self.params["long_window"] + 1:
            return None

        prev_closes = [b.close for b in self._data_buffer[-self.params["long_window"]-1:-1]]
        prev_short_ma = np.mean(prev_closes[-self.params["short_window"]:])
        prev_long_ma = np.mean(prev_closes)

        # 金叉: 短均线上穿长均线
        if prev_short_ma <= prev_long_ma and short_ma > long_ma:
            strength = min(100, abs(short_ma - long_ma) / long_ma * 1000)
            return Signal(
                type=SignalType.BUY,
                symbol=bar.symbol,
                strength=strength,
                reason=f"金叉: MA{self.params['short_window']}({short_ma:.2f}) 上穿 MA{self.params['long_window']}({long_ma:.2f})"
            )

        # 死叉: 短均线下穿长均线
        if prev_short_ma >= prev_long_ma and short_ma < long_ma:
            strength = min(100, abs(short_ma - long_ma) / long_ma * 1000)
            return Signal(
                type=SignalType.SELL,
                symbol=bar.symbol,
                strength=strength,
                reason=f"死叉: MA{self.params['short_window']}({short_ma:.2f}) 下穿 MA{self.params['long_window']}({long_ma:.2f})"
            )

        return None

    def get_indicators(self) -> Dict[str, Any]:
        if len(self._data_buffer) < self.params["long_window"]:
            return {}
        closes = [b.close for b in self._data_buffer[-self.params["long_window"]:]]
        return {
            f"MA{self.params['short_window']}": round(np.mean(closes[-self.params["short_window"]:]), 2),
            f"MA{self.params['long_window']}": round(np.mean(closes), 2),
        }


class MACDStrategy(Strategy):
    """
    MACD策略
    DIF上穿DEA买入，下穿卖出
    """

    name = "MACD趋势"
    description = "基于MACD指标的趋势跟踪策略"
    risk_level = "medium"

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.params = {
            "fast": 12,
            "slow": 26,
            "signal": 9,
            **self.params
        }
        self._macd_history: List[tuple] = []

    def _calculate_ema(self, data: List[float], period: int) -> List[float]:
        """计算EMA"""
        if len(data) < period:
            return []
        multiplier = 2 / (period + 1)
        ema = [sum(data[:period]) / period]
        for price in data[period:]:
            ema.append((price - ema[-1]) * multiplier + ema[-1])
        return ema

    async def on_bar(self, bar: Bar) -> Optional[Signal]:
        await super().on_bar(bar)

        min_periods = self.params["slow"] + self.params["signal"]
        if len(self._data_buffer) < min_periods:
            return None

        closes = [b.close for b in self._data_buffer[-min_periods:]]
        ema_fast = self._calculate_ema(closes, self.params["fast"])
        ema_slow = self._calculate_ema(closes, self.params["slow"])

        if len(ema_fast) < len(ema_slow):
            ema_fast = [ema_fast[0]] * (len(ema_slow) - len(ema_fast)) + ema_fast

        dif = [f - s for f, s in zip(ema_fast[-self.params["signal"]:], ema_slow[-self.params["signal"]:])]
        dea = self._calculate_ema(dif, self.params["signal"])

        if len(dif) < 2 or len(dea) < 2:
            return None

        macd = [(d - e) * 2 for d, e in zip(dif, dea)]

        # 金叉
        if dif[-2] <= dea[-2] and dif[-1] > dea[-1]:
            return Signal(
                type=SignalType.BUY,
                symbol=bar.symbol,
                strength=min(100, abs(macd[-1]) * 10),
                reason=f"MACD金叉: DIF({dif[-1]:.3f}) 上穿 DEA({dea[-1]:.3f})"
            )

        # 死叉
        if dif[-2] >= dea[-2] and dif[-1] < dea[-1]:
            return Signal(
                type=SignalType.SELL,
                symbol=bar.symbol,
                strength=min(100, abs(macd[-1]) * 10),
                reason=f"MACD死叉: DIF({dif[-1]:.3f}) 下穿 DEA({dea[-1]:.3f})"
            )

        return None

    def get_indicators(self) -> Dict[str, Any]:
        min_periods = self.params["slow"] + self.params["signal"]
        if len(self._data_buffer) < min_periods:
            return {}
        closes = [b.close for b in self._data_buffer[-min_periods:]]
        ema_fast = self._calculate_ema(closes, self.params["fast"])
        ema_slow = self._calculate_ema(closes, self.params["slow"])
        if len(ema_fast) < len(ema_slow):
            ema_fast = [ema_fast[0]] * (len(ema_slow) - len(ema_fast)) + ema_fast
        dif = [f - s for f, s in zip(ema_fast[-self.params["signal"]:], ema_slow[-self.params["signal"]:])]
        dea = self._calculate_ema(dif, self.params["signal"])
        macd = [(d - e) * 2 for d, e in zip(dif, dea)]
        return {
            "DIF": round(dif[-1], 3) if dif else 0,
            "DEA": round(dea[-1], 3) if dea else 0,
            "MACD": round(macd[-1], 3) if macd else 0,
        }


class BollingerBandsStrategy(Strategy):
    """
    布林带策略
    价格触及下轨买入，触及上轨卖出
    """

    name = "布林带"
    description = "基于布林带通道的均值回归策略"
    risk_level = "medium"

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.params = {
            "period": 20,
            "std_dev": 2.0,
            **self.params
        }

    async def on_bar(self, bar: Bar) -> Optional[Signal]:
        await super().on_bar(bar)

        period = self.params["period"]
        if len(self._data_buffer) < period:
            return None

        closes = [b.close for b in self._data_buffer[-period:]]
        ma = np.mean(closes)
        std = np.std(closes)
        upper = ma + self.params["std_dev"] * std
        lower = ma - self.params["std_dev"] * std

        price = bar.close

        # 触及下轨买入
        if price <= lower:
            strength = min(100, (lower - price) / std * 50 + 50)
            return Signal(
                type=SignalType.BUY,
                symbol=bar.symbol,
                strength=strength,
                reason=f"触及下轨: 价格{price:.2f} <= 下轨{lower:.2f}"
            )

        # 触及上轨卖出
        if price >= upper:
            strength = min(100, (price - upper) / std * 50 + 50)
            return Signal(
                type=SignalType.SELL,
                symbol=bar.symbol,
                strength=strength,
                reason=f"触及上轨: 价格{price:.2f} >= 上轨{upper:.2f}"
            )

        return None

    def get_indicators(self) -> Dict[str, Any]:
        period = self.params["period"]
        if len(self._data_buffer) < period:
            return {}
        closes = [b.close for b in self._data_buffer[-period:]]
        ma = np.mean(closes)
        std = np.std(closes)
        return {
            "中轨(MA)": round(ma, 2),
            "上轨": round(ma + self.params["std_dev"] * std, 2),
            "下轨": round(ma - self.params["std_dev"] * std, 2),
            "带宽": round(2 * self.params["std_dev"] * std / ma * 100, 2),
        }
