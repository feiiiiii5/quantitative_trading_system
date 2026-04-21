#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
示例策略：双均线交叉策略

这是最简单的趋势跟踪策略之一：
- 当短期均线上穿长期均线时买入（金叉）
- 当短期均线下穿长期均线时卖出（死叉）

适合新手理解策略的基本结构
"""

import pandas as pd
import numpy as np
from typing import Dict

from strategies.base_strategy import BaseStrategy
from utils.logger import get_logger

logger = get_logger(__name__)


class MACrossStrategy(BaseStrategy):
    """
    双均线交叉策略
    
    参数:
    - fast_period: 短期均线周期（默认5日）
    - slow_period: 长期均线周期（默认20日）
    """
    
    def __init__(self, parameters: Dict = None):
        """
        初始化双均线策略
        
        Args:
            parameters: 策略参数
                - fast_period: 短期均线周期
                - slow_period: 长期均线周期
        """
        default_params = {
            'fast_period': 5,
            'slow_period': 20
        }
        
        if parameters:
            default_params.update(parameters)
        
        super().__init__(name="MA_Cross", parameters=default_params)
        
        # 指标数据
        self.fast_ma = None
        self.slow_ma = None
    
    def init(self, data: pd.DataFrame):
        """
        初始化指标计算
        
        Args:
            data: 历史数据
        """
        fast_period = self.parameters['fast_period']
        slow_period = self.parameters['slow_period']
        
        # 计算移动平均线
        self.fast_ma = data['close'].rolling(window=fast_period).mean()
        self.slow_ma = data['close'].rolling(window=slow_period).mean()
        
        # 计算交叉信号
        self.cross_above = (self.fast_ma > self.slow_ma) & (
            self.fast_ma.shift(1) <= self.slow_ma.shift(1)
        )
        self.cross_below = (self.fast_ma < self.slow_ma) & (
            self.fast_ma.shift(1) >= self.slow_ma.shift(1)
        )
        
        logger.info(f"MA指标计算完成: 快线{fast_period}日, 慢线{slow_period}日")
    
    def next(self, index: int, current_data: pd.Series) -> Dict:
        """
        每个周期的交易逻辑
        
        Args:
            index: 当前索引
            current_data: 当前数据
            
        Returns:
            交易信号
        """
        # 跳过初始阶段（均线未计算完成）
        if index < self.parameters['slow_period']:
            return self.hold(reason="指标计算中")
        
        # 获取当前交叉状态
        is_cross_above = self.cross_above.iloc[index]
        is_cross_below = self.cross_below.iloc[index]
        
        # 金叉买入
        if is_cross_above and self.position <= 0:
            return self.buy(
                weight=1.0,
                reason=f"金叉: {self.parameters['fast_period']}日均线上穿{self.parameters['slow_period']}日均线"
            )
        
        # 死叉卖出
        elif is_cross_below and self.position > 0:
            return self.sell(
                weight=1.0,
                reason=f"死叉: {self.parameters['fast_period']}日均线下穿{self.parameters['slow_period']}日均线"
            )
        
        # 无信号，持有
        return self.hold(reason="无交叉信号")


class RSIStrategy(BaseStrategy):
    """
    RSI相对强弱指标策略
    
    参数:
    - period: RSI计算周期
    - overbought: 超买阈值（默认70）
    - oversold: 超卖阈值（默认30）
    """
    
    def __init__(self, parameters: Dict = None):
        default_params = {
            'period': 14,
            'overbought': 70,
            'oversold': 30
        }
        
        if parameters:
            default_params.update(parameters)
        
        super().__init__(name="RSI_Strategy", parameters=default_params)
        self.rsi = None
    
    def init(self, data: pd.DataFrame):
        """计算RSI指标"""
        period = self.parameters['period']
        
        # 计算价格变化
        delta = data['close'].diff()
        
        # 分离上涨和下跌
        gain = delta.where(delta > 0, 0)
        loss = -delta.where(delta < 0, 0)
        
        # 计算平均上涨和下跌
        avg_gain = gain.rolling(window=period).mean()
        avg_loss = loss.rolling(window=period).mean()
        
        # 计算RSI
        rs = avg_gain / avg_loss
        self.rsi = 100 - (100 / (1 + rs))
        
        logger.info(f"RSI指标计算完成: 周期{period}")
    
    def next(self, index: int, current_data: pd.Series) -> Dict:
        """RSI交易逻辑"""
        if index < self.parameters['period']:
            return self.hold(reason="RSI计算中")
        
        current_rsi = self.rsi.iloc[index]
        
        # 超卖买入
        if current_rsi < self.parameters['oversold'] and self.position <= 0:
            return self.buy(
                weight=1.0,
                reason=f"RSI超卖: {current_rsi:.2f} < {self.parameters['oversold']}"
            )
        
        # 超买卖出
        elif current_rsi > self.parameters['overbought'] and self.position > 0:
            return self.sell(
                weight=1.0,
                reason=f"RSI超买: {current_rsi:.2f} > {self.parameters['overbought']}"
            )
        
        return self.hold(reason=f"RSI正常区间: {current_rsi:.2f}")


class BollingerBandsStrategy(BaseStrategy):
    """
    布林带策略
    
    参数:
    - period: 均线周期（默认20）
    - std_dev: 标准差倍数（默认2）
    """
    
    def __init__(self, parameters: Dict = None):
        default_params = {
            'period': 20,
            'std_dev': 2
        }
        
        if parameters:
            default_params.update(parameters)
        
        super().__init__(name="Bollinger_Bands", parameters=default_params)
        self.upper_band = None
        self.middle_band = None
        self.lower_band = None
    
    def init(self, data: pd.DataFrame):
        """计算布林带"""
        period = self.parameters['period']
        std_dev = self.parameters['std_dev']
        
        # 中轨（移动平均线）
        self.middle_band = data['close'].rolling(window=period).mean()
        
        # 标准差
        rolling_std = data['close'].rolling(window=period).std()
        
        # 上轨和下轨
        self.upper_band = self.middle_band + (rolling_std * std_dev)
        self.lower_band = self.middle_band - (rolling_std * std_dev)
        
        logger.info(f"布林带计算完成: 周期{period}, 标准差{std_dev}")
    
    def next(self, index: int, current_data: pd.Series) -> Dict:
        """布林带交易逻辑"""
        if index < self.parameters['period']:
            return self.hold(reason="布林带计算中")
        
        close_price = current_data['close']
        upper = self.upper_band.iloc[index]
        lower = self.lower_band.iloc[index]
        
        # 价格触及下轨买入（超卖反弹）
        if close_price <= lower and self.position <= 0:
            return self.buy(
                weight=1.0,
                reason=f"价格触及布林带下轨: {close_price:.2f} <= {lower:.2f}"
            )
        
        # 价格触及上轨卖出（超买回调）
        elif close_price >= upper and self.position > 0:
            return self.sell(
                weight=1.0,
                reason=f"价格触及布林带上轨: {close_price:.2f} >= {upper:.2f}"
            )
        
        return self.hold(reason=f"价格在布林带区间内")
