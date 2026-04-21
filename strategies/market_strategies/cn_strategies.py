#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
A股专用策略

- 龙头股效应：行业龙头超额收益
- 机构持股跟踪：北向资金/机构持仓变化
"""

import numpy as np
import pandas as pd
from typing import Optional

from core.engine import BaseStrategy, Order


class DragonHeadStrategy(BaseStrategy):
    """
    A股龙头股效应策略

    逻辑：行业龙头在市场反弹时涨幅更大，下跌时更抗跌
    信号：价格突破20日高点 + 成交量放大
    """

    def __init__(self, **kwargs):
        default_params = {
            'lookback': 20,
            'volume_mult': 1.5,
            'stop_loss': 0.08,
        }
        if kwargs:
            default_params.update(kwargs)
        super().__init__(name="DragonHead", parameters=default_params)
        self.high_ma = None
        self.vol_ma = None

    def init(self):
        data = self._data.data
        lb = self.parameters['lookback']
        self.high_ma = data['high'].rolling(lb).max()
        self.vol_ma = data['volume'].rolling(lb).mean()

    def next(self, index: int) -> Optional[Order]:
        if index < self.parameters['lookback']:
            return None

        close = self._data.close.iloc[index]
        high = self._data.high.iloc[index]
        volume = self._data.volume.iloc[index]

        # 突破20日高点且放量
        if high >= self.high_ma.iloc[index] and volume >= self.vol_ma.iloc[index] * self.parameters['volume_mult']:
            if self._position <= 0:
                return self.buy(symbol=self._data.name, quantity=100, reason="龙头突破买入")

        # 止损
        if self._position > 0 and close < self.high_ma.iloc[index] * (1 - self.parameters['stop_loss']):
            return self.sell(symbol=self._data.name, quantity=100, reason="龙头止损卖出")

        return None


class NorthBoundFlowStrategy(BaseStrategy):
    """
    北向资金跟踪策略（简化版）

    逻辑：北向资金（沪深港通）净流入时做多
    信号：近5日北向净流入为正 + 价格站上10日均线
    """

    def __init__(self, **kwargs):
        default_params = {
            'flow_ma': 5,
            'price_ma': 10,
        }
        if kwargs:
            default_params.update(kwargs)
        super().__init__(name="NorthBoundFlow", parameters=default_params)
        self.price_ma = None

    def init(self):
        data = self._data.data
        self.price_ma = data['close'].rolling(self.parameters['price_ma']).mean()
        # 实际需接入北向资金数据，这里用价格动量代理
        self.flow_proxy = data['close'].diff(5)  # 5日价格变化代理资金流入

    def next(self, index: int) -> Optional[Order]:
        if index < max(self.parameters['flow_ma'], self.parameters['price_ma']):
            return None

        close = self._data.close.iloc[index]
        flow = self.flow_proxy.iloc[index]

        if flow > 0 and close > self.price_ma.iloc[index] and self._position <= 0:
            return self.buy(symbol=self._data.name, quantity=100, reason="北向流入信号买入")

        if flow < 0 and self._position > 0:
            return self.sell(symbol=self._data.name, quantity=100, reason="北向流出信号卖出")

        return None
