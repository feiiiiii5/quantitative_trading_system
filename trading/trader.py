#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
交易引擎模块
支持多种交易模式：
- backtest: 回测模式
- paper: 模拟交易模式
- real: 实盘交易模式（需接入券商API）
"""

import time
import pandas as pd
from datetime import datetime
from typing import Dict, Optional
from enum import Enum

from strategies.base_strategy import BaseStrategy
from risk.risk_manager import RiskManager
from data.data_manager import DataManager
from utils.logger import get_logger
from config.settings import TRADING

logger = get_logger(__name__)


class TradingMode(Enum):
    """交易模式枚举"""
    BACKTEST = "backtest"    # 回测模式
    PAPER = "paper"          # 模拟交易模式
    REAL = "real"            # 实盘交易模式


class TradingEngine:
    """
    交易引擎
    
    功能：
    - 管理交易执行
    - 连接风控模块
    - 支持多种交易模式
    - 记录交易日志
    """
    
    def __init__(
        self,
        mode: str = "paper",
        risk_manager: RiskManager = None,
        initial_cash: float = None
    ):
        """
        初始化交易引擎
        
        Args:
            mode: 交易模式 ('backtest', 'paper', 'real')
            risk_manager: 风险管理器实例
            initial_cash: 初始资金
        """
        self.mode = TradingMode(mode)
        self.risk_manager = risk_manager or RiskManager()
        self.initial_cash = initial_cash or TRADING["initial_cash"]
        
        # 账户状态
        self.cash = self.initial_cash
        self.positions = {}        # 持仓 {stock_code: {'quantity': 数量, 'avg_price': 均价}}
        self.total_value = self.initial_cash
        
        # 数据管理
        self.data_manager = DataManager()
        
        # 交易记录
        self.trades = []
        self.is_running = False
        
        logger.info(f"交易引擎初始化完成，模式: {self.mode.value}")
    
    def start(self, strategy: BaseStrategy, stock_code: str = "000300.XSHG"):
        """
        启动交易引擎
        
        Args:
            strategy: 策略实例
            stock_code: 交易标的
        """
        self.is_running = True
        logger.info(f"交易引擎启动，标的: {stock_code}")
        
        if self.mode == TradingMode.BACKTEST:
            logger.info("回测模式无需启动实时引擎")
            return
        
        # 模拟交易模式
        if self.mode == TradingMode.PAPER:
            self._run_paper_trading(strategy, stock_code)
        
        # 实盘交易模式
        elif self.mode == TradingMode.REAL:
            self._run_real_trading(strategy, stock_code)
    
    def stop(self):
        """停止交易引擎"""
        self.is_running = False
        logger.info("交易引擎已停止")
    
    def _run_paper_trading(self, strategy: BaseStrategy, stock_code: str):
        """
        运行模拟交易
        
        使用实时数据模拟交易，不实际下单
        """
        logger.info("启动模拟交易...")
        
        while self.is_running:
            try:
                # 获取实时数据
                current_data = self._get_current_data(stock_code)
                
                if current_data is None:
                    time.sleep(5)
                    continue
                
                # 获取策略信号
                signal = strategy.next(0, current_data)
                
                # 执行交易（通过风控检查）
                self._execute_trade(signal, stock_code, current_data['close'])
                
                # 更新组合价值
                self._update_portfolio_value()
                
                # 打印当前状态
                self._print_status()
                
                # 等待下一个周期
                time.sleep(60)  # 每分钟检查一次
                
            except Exception as e:
                logger.error(f"模拟交易出错: {e}")
                time.sleep(5)
    
    def _run_real_trading(self, strategy: BaseStrategy, stock_code: str):
        """
        运行实盘交易
        
        需要接入券商API（如富途、雪球等）
        此处为框架，实际使用时需要实现具体的API接口
        """
        logger.info("启动实盘交易...")
        logger.warning("实盘交易需要接入券商API，请确保已配置")
        
        # TODO: 接入券商API
        # 示例：
        # from trading.brokers.futu import FutuBroker
        # broker = FutuBroker()
        # broker.connect()
        
        while self.is_running:
            try:
                # 获取实时数据
                current_data = self._get_current_data(stock_code)
                
                if current_data is None:
                    time.sleep(5)
                    continue
                
                # 获取策略信号
                signal = strategy.next(0, current_data)
                
                # 执行交易（通过风控检查）
                if self._execute_trade(signal, stock_code, current_data['close']):
                    # 实盘下单
                    # broker.place_order(stock_code, signal['action'], quantity)
                    pass
                
                time.sleep(60)
                
            except Exception as e:
                logger.error(f"实盘交易出错: {e}")
                time.sleep(5)
    
    def _get_current_data(self, stock_code: str) -> Optional[pd.Series]:
        """
        获取当前数据
        
        Args:
            stock_code: 股票代码
            
        Returns:
            当前数据
        """
        try:
            # 获取最近的数据
            df = self.data_manager.get_stock_data(
                stock_code,
                start_date=datetime.now().strftime("%Y-%m-%d"),
                end_date=datetime.now().strftime("%Y-%m-%d")
            )
            
            if df is not None and len(df) > 0:
                return df.iloc[-1]
            
            return None
            
        except Exception as e:
            logger.error(f"获取数据失败: {e}")
            return None
    
    def _execute_trade(self, signal: Dict, stock_code: str, price: float) -> bool:
        """
        执行交易
        
        Args:
            signal: 交易信号
            stock_code: 股票代码
            price: 当前价格
            
        Returns:
            是否执行成功
        """
        action = signal['action']
        
        if action == 'hold':
            return False
        
        # 计算交易数量
        if action == 'buy':
            # 计算可买入数量
            trade_value = self.cash * signal['weight']
            quantity = int(trade_value / price / 100) * 100  # A股100股为一手
            
            if quantity <= 0:
                return False
            
            # 风控检查
            allowed, reason = self.risk_manager.check_trade(
                action='buy',
                stock_code=stock_code,
                price=price,
                quantity=quantity,
                portfolio_value=self.total_value,
                cash=self.cash
            )
            
            if not allowed:
                logger.warning(f"买入被风控拦截: {reason}")
                return False
            
            # 执行买入
            self._buy(stock_code, quantity, price)
            
        elif action == 'sell':
            # 获取持仓
            position = self.positions.get(stock_code, {})
            current_quantity = position.get('quantity', 0)
            
            quantity = int(current_quantity * signal['weight'])
            
            if quantity <= 0:
                return False
            
            # 风控检查
            allowed, reason = self.risk_manager.check_trade(
                action='sell',
                stock_code=stock_code,
                price=price,
                quantity=quantity,
                portfolio_value=self.total_value,
                cash=self.cash
            )
            
            if not allowed:
                logger.warning(f"卖出被风控拦截: {reason}")
                return False
            
            # 执行卖出
            self._sell(stock_code, quantity, price)
        
        return True
    
    def _buy(self, stock_code: str, quantity: int, price: float):
        """
        执行买入操作
        
        Args:
            stock_code: 股票代码
            quantity: 买入数量
            price: 买入价格
        """
        trade_value = quantity * price
        commission = trade_value * TRADING["commission_rate"]
        total_cost = trade_value + commission
        
        # 更新现金
        self.cash -= total_cost
        
        # 更新持仓
        if stock_code not in self.positions:
            self.positions[stock_code] = {
                'quantity': 0,
                'avg_price': 0
            }
        
        position = self.positions[stock_code]
        total_quantity = position['quantity'] + quantity
        avg_price = (position['quantity'] * position['avg_price'] + trade_value) / total_quantity
        
        position['quantity'] = total_quantity
        position['avg_price'] = avg_price
        
        # 记录交易
        trade = {
            'timestamp': datetime.now(),
            'action': 'buy',
            'stock_code': stock_code,
            'quantity': quantity,
            'price': price,
            'value': trade_value,
            'commission': commission,
            'cash_after': self.cash
        }
        self.trades.append(trade)
        
        # 更新风控持仓
        self.risk_manager.update_position(stock_code, quantity, price, 'buy')
        
        logger.info(f"买入 {stock_code}: {quantity}股 @ {price:.2f}, 手续费: {commission:.2f}")
    
    def _sell(self, stock_code: str, quantity: int, price: float):
        """
        执行卖出操作
        
        Args:
            stock_code: 股票代码
            quantity: 卖出数量
            price: 卖出价格
        """
        trade_value = quantity * price
        commission = trade_value * TRADING["commission_rate"]
        net_value = trade_value - commission
        
        # 更新现金
        self.cash += net_value
        
        # 更新持仓
        if stock_code in self.positions:
            self.positions[stock_code]['quantity'] -= quantity
            
            if self.positions[stock_code]['quantity'] <= 0:
                del self.positions[stock_code]
        
        # 记录交易
        trade = {
            'timestamp': datetime.now(),
            'action': 'sell',
            'stock_code': stock_code,
            'quantity': quantity,
            'price': price,
            'value': trade_value,
            'commission': commission,
            'cash_after': self.cash
        }
        self.trades.append(trade)
        
        # 更新风控持仓
        self.risk_manager.update_position(stock_code, quantity, price, 'sell')
        
        logger.info(f"卖出 {stock_code}: {quantity}股 @ {price:.2f}, 手续费: {commission:.2f}")
    
    def _update_portfolio_value(self):
        """更新组合总价值"""
        stock_value = 0
        
        for stock_code, position in self.positions.items():
            # 获取当前价格
            current_data = self._get_current_data(stock_code)
            if current_data is not None:
                current_price = current_data['close']
                stock_value += position['quantity'] * current_price
        
        self.total_value = self.cash + stock_value
        
        # 更新风控
        self.risk_manager.update_portfolio_value(self.total_value)
    
    def _print_status(self):
        """打印当前状态"""
        logger.info(
            f"账户状态 - 总资产: {self.total_value:,.2f}, "
            f"现金: {self.cash:,.2f}, "
            f"持仓: {len(self.positions)} 只"
        )
    
    def get_account_info(self) -> Dict:
        """
        获取账户信息
        
        Returns:
            账户信息字典
        """
        return {
            'mode': self.mode.value,
            'initial_cash': self.initial_cash,
            'cash': self.cash,
            'total_value': self.total_value,
            'total_return': (self.total_value - self.initial_cash) / self.initial_cash,
            'positions': self.positions,
            'total_trades': len(self.trades)
        }
    
    def get_trade_history(self) -> pd.DataFrame:
        """
        获取交易历史
        
        Returns:
            交易记录DataFrame
        """
        return pd.DataFrame(self.trades)
