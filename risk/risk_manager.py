#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
风险控制模块
提供全面的风险管理功能，包括：
- 仓位控制
- 止损止盈
- 回撤控制
- 风险指标监控
"""

import pandas as pd
import numpy as np
from datetime import datetime
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass

from utils.logger import get_logger

logger = get_logger(__name__)


@dataclass
class RiskConfig:
    """风控配置数据类"""
    max_position_per_stock: float = 0.2      # 单只股票最大仓位
    max_total_position: float = 0.8          # 总仓位上限
    stop_loss: float = 0.05                  # 止损比例
    take_profit: float = 0.15                # 止盈比例
    max_drawdown: float = 0.2                # 最大回撤容忍度
    max_daily_loss: float = 0.03             # 单日最大亏损
    min_cash_ratio: float = 0.1              # 最小现金比例


class RiskManager:
    """
    风险管理器
    
    功能：
    - 交易前风险评估
    - 仓位控制
    - 止损止盈检查
    - 回撤监控
    """
    
    def __init__(self, config: Dict = None):
        """
        初始化风险管理器
        
        Args:
            config: 风控配置字典
        """
        if config is None:
            config = {}
        
        self.config = RiskConfig(**config)
        
        # 状态跟踪
        self.positions = {}           # 持仓信息
        self.daily_pnl = []           # 每日盈亏
        self.peak_value = 0           # 历史最高资产
        self.current_drawdown = 0     # 当前回撤
        self.is_trading_allowed = True  # 是否允许交易
        
        # 风险事件记录
        self.risk_events = []
        
        logger.info("风险管理器初始化完成")
    
    def check_trade(
        self,
        action: str,
        stock_code: str,
        price: float,
        quantity: float,
        portfolio_value: float,
        cash: float
    ) -> Tuple[bool, str]:
        """
        检查交易是否允许
        
        Args:
            action: 交易动作 ('buy' 或 'sell')
            stock_code: 股票代码
            price: 交易价格
            quantity: 交易数量
            portfolio_value: 组合总价值
            cash: 可用现金
            
        Returns:
            (是否允许, 原因)
        """
        # 检查是否被禁止交易
        if not self.is_trading_allowed:
            return False, "交易已被暂停（风险控制）"
        
        trade_value = price * quantity
        
        if action == 'buy':
            # 检查现金是否充足
            if trade_value > cash:
                return False, f"现金不足: 需要{trade_value:.2f}, 可用{cash:.2f}"
            
            # 检查单只股票仓位上限
            current_position_value = self.positions.get(stock_code, {}).get('value', 0)
            new_position_value = current_position_value + trade_value
            position_ratio = new_position_value / portfolio_value
            
            if position_ratio > self.config.max_position_per_stock:
                return False, (
                    f"单只股票仓位超限: "
                    f"{stock_code} 仓位将达到{position_ratio*100:.1f}%, "
                    f"上限{self.config.max_position_per_stock*100:.1f}%"
                )
            
            # 检查总仓位上限
            total_position = sum(p.get('value', 0) for p in self.positions.values())
            new_total_position = total_position + trade_value
            total_ratio = new_total_position / portfolio_value
            
            if total_ratio > self.config.max_total_position:
                return False, (
                    f"总仓位超限: "
                    f"将达到{total_ratio*100:.1f}%, "
                    f"上限{self.config.max_total_position*100:.1f}%"
                )
            
            # 检查最小现金比例
            remaining_cash = cash - trade_value
            cash_ratio = remaining_cash / portfolio_value
            
            if cash_ratio < self.config.min_cash_ratio:
                return False, (
                    f"现金比例过低: "
                    f"将降至{cash_ratio*100:.1f}%, "
                    f"最低要求{self.config.min_cash_ratio*100:.1f}%"
                )
        
        elif action == 'sell':
            # 检查是否有持仓可卖
            current_quantity = self.positions.get(stock_code, {}).get('quantity', 0)
            if quantity > current_quantity:
                return False, f"持仓不足: 持有{current_quantity}, 卖出{quantity}"
        
        return True, "通过"
    
    def update_position(self, stock_code: str, quantity: float, price: float, action: str):
        """
        更新持仓信息
        
        Args:
            stock_code: 股票代码
            quantity: 数量
            price: 价格
            action: 交易动作
        """
        if stock_code not in self.positions:
            self.positions[stock_code] = {
                'quantity': 0,
                'avg_price': 0,
                'value': 0,
                'entry_date': None
            }
        
        position = self.positions[stock_code]
        
        if action == 'buy':
            # 计算新的平均成本
            total_cost = position['quantity'] * position['avg_price'] + quantity * price
            total_quantity = position['quantity'] + quantity
            
            if total_quantity > 0:
                position['avg_price'] = total_cost / total_quantity
            
            position['quantity'] = total_quantity
            position['value'] = total_quantity * price
            
            if position['entry_date'] is None:
                position['entry_date'] = datetime.now()
        
        elif action == 'sell':
            position['quantity'] -= quantity
            position['value'] = position['quantity'] * price
            
            if position['quantity'] <= 0:
                position['avg_price'] = 0
                position['entry_date'] = None
    
    def check_stop_loss_take_profit(
        self,
        stock_code: str,
        current_price: float
    ) -> Tuple[Optional[str], str]:
        """
        检查止损止盈
        
        Args:
            stock_code: 股票代码
            current_price: 当前价格
            
        Returns:
            (动作, 原因)
        """
        if stock_code not in self.positions:
            return None, "无持仓"
        
        position = self.positions[stock_code]
        
        if position['quantity'] <= 0:
            return None, "无持仓"
        
        avg_price = position['avg_price']
        
        if avg_price <= 0:
            return None, "无成本价"
        
        # 计算收益率
        return_ratio = (current_price - avg_price) / avg_price
        
        # 检查止损
        if return_ratio <= -self.config.stop_loss:
            self._record_risk_event(
                'stop_loss',
                stock_code,
                f"止损触发: 亏损{return_ratio*100:.2f}%"
            )
            return 'sell', f"止损: 亏损{return_ratio*100:.2f}%"
        
        # 检查止盈
        if return_ratio >= self.config.take_profit:
            self._record_risk_event(
                'take_profit',
                stock_code,
                f"止盈触发: 盈利{return_ratio*100:.2f}%"
            )
            return 'sell', f"止盈: 盈利{return_ratio*100:.2f}%"
        
        return None, "正常"
    
    def update_portfolio_value(self, portfolio_value: float):
        """
        更新组合价值并检查回撤
        
        Args:
            portfolio_value: 当前组合价值
        """
        # 更新历史最高值
        if portfolio_value > self.peak_value:
            self.peak_value = portfolio_value
        
        # 计算当前回撤
        if self.peak_value > 0:
            self.current_drawdown = (self.peak_value - portfolio_value) / self.peak_value
        
        # 检查最大回撤
        if self.current_drawdown > self.config.max_drawdown:
            self.is_trading_allowed = False
            self._record_risk_event(
                'max_drawdown',
                'portfolio',
                f"最大回撤超限: {self.current_drawdown*100:.2f}%"
            )
            logger.warning(f"触发最大回撤限制，暂停交易: {self.current_drawdown*100:.2f}%")
    
    def check_daily_loss(self, daily_pnl: float, portfolio_value: float) -> bool:
        """
        检查单日亏损
        
        Args:
            daily_pnl: 当日盈亏
            portfolio_value: 组合价值
            
        Returns:
            是否超过限制
        """
        daily_return = daily_pnl / portfolio_value if portfolio_value > 0 else 0
        
        if daily_return < -self.config.max_daily_loss:
            self._record_risk_event(
                'daily_loss_limit',
                'portfolio',
                f"单日亏损超限: {daily_return*100:.2f}%"
            )
            return False
        
        return True
    
    def _record_risk_event(self, event_type: str, stock_code: str, message: str):
        """
        记录风险事件
        
        Args:
            event_type: 事件类型
            stock_code: 股票代码
            message: 事件描述
        """
        event = {
            'timestamp': datetime.now(),
            'type': event_type,
            'stock_code': stock_code,
            'message': message
        }
        self.risk_events.append(event)
        logger.warning(f"风险事件: [{event_type}] {stock_code} - {message}")
    
    def get_risk_report(self) -> Dict:
        """
        获取风险报告
        
        Returns:
            风险报告字典
        """
        return {
            'current_drawdown': self.current_drawdown,
            'peak_value': self.peak_value,
            'is_trading_allowed': self.is_trading_allowed,
            'total_risk_events': len(self.risk_events),
            'risk_events': self.risk_events[-10:]  # 最近10条
        }
    
    def reset(self):
        """重置风控状态"""
        self.positions = {}
        self.daily_pnl = []
        self.peak_value = 0
        self.current_drawdown = 0
        self.is_trading_allowed = True
        self.risk_events = []
        logger.info("风险管理器已重置")
