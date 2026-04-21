#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
美股专用策略

- 季报效应：财报发布前后超额收益
- 期权链分析：Put/Call比率情绪指标
"""

import numpy as np
import pandas as pd
from typing import Optional

from core.engine import BaseStrategy, Order


class EarningsMomentumStrategy(BaseStrategy):
    """
    美股季报效应策略（简化版）

    逻辑：财报超预期后股价动量延续
    信号：价格突破前期高点 + 成交量放大（代理财报利好）
    """

    def __init__(self, **kwargs):
        default_params = {
            'lookback': 60,
            'volume_mult': 1.8,
            'hold_days': 20,
        }
        if kwargs:
            default_params.update(kwargs)
        super().__init__(name="EarningsMomentum", parameters=default_params)
        self.entry_day = None

    def init(self):
        data = self._data.data
        self.high_60 = data['high'].rolling(self.parameters['lookback']).max()
        self.vol_ma = data['volume'].rolling(20).mean()

    def next(self, index: int) -> Optional[Order]:
        if index < self.parameters['lookback']:
            return None

        close = self._data.close.iloc[index]
        high = self._data.high.iloc[index]
        volume = self._data.volume.iloc[index]

        # 突破60日高点且放量（代理财报超预期）
        if high >= self.high_60.iloc[index] and volume >= self.vol_ma.iloc[index] * self.parameters['volume_mult']:
            if self._position <= 0:
                self.entry_day = index
                return self.buy(symbol=self._data.name, quantity=10, reason="季报突破买入")

        # 持有期满卖出
        if self._position > 0 and self.entry_day is not None:
            if index - self.entry_day >= self.parameters['hold_days']:
                self.entry_day = None
                return self.sell(symbol=self._data.name, quantity=10, reason="季报持有期满卖出")

        return None


class PutCallSentimentStrategy(BaseStrategy):
    """
    期权情绪策略（简化版）

    逻辑：Put/Call比率极端值时反向操作（恐惧时买入，贪婪时卖出）
    信号：VIX代理指标（价格波动率）极端时反向
    """

    def __init__(self, **kwargs):
        default_params = {
            'vol_window': 20,
            'vol_percentile': 80,
        }
        if kwargs:
            default_params.update(kwargs)
        super().__init__(name="PutCallSentiment", parameters=default_params)
        self.vol_percentile_high = None
        self.vol_percentile_low = None

    def init(self):
        data = self._data.data
        returns = data['close'].pct_change()
        vol = returns.rolling(self.parameters['vol_window']).std() * np.sqrt(252)
        self.vol_percentile_high = vol.rolling(252).quantile(self.parameters['vol_percentile'] / 100)
        self.vol_percentile_low = vol.rolling(252).quantile((100 - self.parameters['vol_percentile']) / 100)
        self.current_vol = vol

    def next(self, index: int) -> Optional[Order]:
        if index < 252:
            return None

        vol = self.current_vol.iloc[index]
        high = self.vol_percentile_high.iloc[index]
        low = self.vol_percentile_low.iloc[index]

        # 波动率极高（恐惧）→ 买入
        if vol > high and self._position <= 0:
            return self.buy(symbol=self._data.name, quantity=10, reason="极端恐惧买入")

        # 波动率极低（贪婪）→ 卖出
        if vol < low and self._position > 0:
            return self.sell(symbol=self._data.name, quantity=10, reason="极端贪婪卖出")

        return None
