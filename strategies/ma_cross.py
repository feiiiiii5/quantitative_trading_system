#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
均线交叉策略 - 兼容core.engine.BaseStrategy接口
"""

from core.engine import BaseStrategy, Order
from utils.logger import get_logger

logger = get_logger(__name__)


class MACrossStrategy(BaseStrategy):
    """均线交叉策略"""

    def __init__(self, fast_period=5, slow_period=20, **kwargs):
        super().__init__(name="MA_Cross", parameters={
            'fast_period': fast_period,
            'slow_period': slow_period
        })
        self.fast_ma = None
        self.slow_ma = None

    def init(self):
        fast = self.parameters['fast_period']
        slow = self.parameters['slow_period']
        self.fast_ma = self.data.close.rolling(fast).mean()
        self.slow_ma = self.data.close.rolling(slow).mean()
        self.data.add_indicator('fast_ma', self.fast_ma)
        self.data.add_indicator('slow_ma', self.slow_ma)

    def next(self, index: int) -> Order:
        if index < self.parameters['slow_period']:
            return None
        if self.fast_ma.iloc[index] > self.slow_ma.iloc[index] and \
           self.fast_ma.iloc[index-1] <= self.slow_ma.iloc[index-1]:
            return self.buy(quantity=100, reason="金叉买入")
        elif self.fast_ma.iloc[index] < self.slow_ma.iloc[index] and \
             self.fast_ma.iloc[index-1] >= self.slow_ma.iloc[index-1]:
            return self.sell(quantity=100, reason="死叉卖出")
        return None
