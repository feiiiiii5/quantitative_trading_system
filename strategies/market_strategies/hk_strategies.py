#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
港股专用策略

- AH溢价套利：A/H股溢价率均值回归
- 南向资金跟踪：港股通资金流向
"""

import numpy as np
import pandas as pd
from typing import Optional

from core.engine import BaseStrategy, Order


class AHPremiumStrategy(BaseStrategy):
    """
    AH溢价套利策略（简化版）

    逻辑：AH溢价率过高时做空H股/做多A股，过低时反向
    信号：H股相对A股折价超过阈值时买入H股
    """

    def __init__(self, **kwargs):
        default_params = {
            'premium_threshold': 1.15,  # 溢价率阈值
            'discount_threshold': 1.05,  # 折价率阈值
            'lookback': 60,
        }
        if kwargs:
            default_params.update(kwargs)
        super().__init__(name="AHPremium", parameters=default_params)
        self.premium_ma = None

    def init(self):
        data = self._data.data
        # 实际需接入A股对应价格计算溢价率，这里用价格相对60日均值代理
        self.price_ma = data['close'].rolling(self.parameters['lookback']).mean()

    def next(self, index: int) -> Optional[Order]:
        if index < self.parameters['lookback']:
            return None

        close = self._data.close.iloc[index]
        ma = self.price_ma.iloc[index]

        # 价格低于均线5%（代理H股折价）→ 买入
        if close < ma * 0.95 and self._position <= 0:
            return self.buy(symbol=self._data.name, quantity=100, reason="H股折价买入")

        # 价格高于均线15%（代理H股溢价）→ 卖出
        if close > ma * 1.15 and self._position > 0:
            return self.sell(symbol=self._data.name, quantity=100, reason="H股溢价卖出")

        return None


class SouthBoundFlowStrategy(BaseStrategy):
    """
    南向资金跟踪策略

    逻辑：港股通资金持续净流入时做多港股
    """

    def __init__(self, **kwargs):
        default_params = {
            'flow_window': 10,
            'momentum_window': 20,
        }
        if kwargs:
            default_params.update(kwargs)
        super().__init__(name="SouthBoundFlow", parameters=default_params)

    def init(self):
        data = self._data.data
        # 用价格动量代理南向资金流入
        self.momentum = data['close'].pct_change(self.parameters['momentum_window'])

    def next(self, index: int) -> Optional[Order]:
        if index < self.parameters['momentum_window']:
            return None

        mom = self.momentum.iloc[index]

        if mom > 0.05 and self._position <= 0:
            return self.buy(symbol=self._data.name, quantity=100, reason="南向资金流入买入")

        if mom < -0.05 and self._position > 0:
            return self.sell(symbol=self._data.name, quantity=100, reason="南向资金流出卖出")

        return None
