#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
回测引擎模块
提供完整的回测功能，包括：
- 交易模拟
- 绩效计算
- 结果可视化
- 报告生成
"""

import pandas as pd
import numpy as np
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple
import json

from strategies.base_strategy import BaseStrategy
from data.data_manager import DataManager
from utils.logger import get_logger
from config.settings import BACKTEST_RESULT_DIR, BACKTEST

logger = get_logger(__name__)


class BacktestEngine:
    """
    回测引擎
    
    功能：
    - 模拟历史交易
    - 计算策略绩效
    - 生成回测报告
    - 与基准比较
    """
    
    def __init__(
        self,
        initial_cash: float = 1000000,
        commission: float = 0.0003,
        slippage: float = 0.001,
        risk_free_rate: float = 0.03
    ):
        """
        初始化回测引擎
        
        Args:
            initial_cash: 初始资金
            commission: 交易佣金率
            slippage: 滑点率
            risk_free_rate: 无风险利率（年化）
        """
        self.initial_cash = initial_cash
        self.commission = commission
        self.slippage = slippage
        self.risk_free_rate = risk_free_rate
        
        # 回测状态
        self.cash = initial_cash
        self.position = 0.0
        self.total_value = initial_cash
        
        # 记录
        self.portfolio_values = []
        self.trades = []
        self.daily_returns = []
        
        logger.info("回测引擎初始化完成")
    
    def run(
        self,
        strategy: BaseStrategy,
        stock_code: str = "000300.XSHG",
        start_date: str = None,
        end_date: str = None,
        data: pd.DataFrame = None,
        benchmark: str = "000300.XSHG"
    ) -> Dict:
        """
        运行回测
        
        Args:
            strategy: 策略实例
            stock_code: 股票代码
            start_date: 开始日期
            end_date: 结束日期
            data: 直接传入数据（可选）
            benchmark: 基准指数
            
        Returns:
            回测结果字典
        """
        # 获取数据
        if data is None:
            data_manager = DataManager()
            start = start_date or BACKTEST["start_date"]
            end = end_date or BACKTEST["end_date"]
            
            logger.info(f"获取 {stock_code} 数据: {start} ~ {end}")
            data = data_manager.get_stock_data(stock_code, start, end)
        
        if data is None or len(data) == 0:
            raise ValueError("没有可用的数据")
        
        # 重置状态
        self._reset()
        
        # 初始化策略
        strategy.init(data)
        
        logger.info(f"开始回测: {len(data)} 个交易日")
        
        # 逐日回测
        for i in range(len(data)):
            current_data = data.iloc[i]
            date = current_data['date']
            
            # 更新总资产
            current_price = current_data['close']
            stock_value = self.position * current_price
            self.total_value = self.cash + stock_value
            
            # 记录每日资产
            self.portfolio_values.append({
                'date': date,
                'cash': self.cash,
                'position': self.position,
                'stock_value': stock_value,
                'total_value': self.total_value,
                'price': current_price
            })
            
            # 获取策略信号
            signal = strategy.next(i, current_data)
            
            # 执行交易
            if signal['action'] == 'buy':
                self._execute_buy(current_price, signal['weight'], date)
            elif signal['action'] == 'sell':
                self._execute_sell(current_price, signal['weight'], date)
        
        # 计算绩效指标
        results = self._calculate_metrics(data, strategy)
        
        logger.info("回测完成")
        return results
    
    def _reset(self):
        """重置回测状态"""
        self.cash = self.initial_cash
        self.position = 0.0
        self.total_value = self.initial_cash
        self.portfolio_values = []
        self.trades = []
        self.daily_returns = []
    
    def _execute_buy(self, price: float, weight: float, date):
        """
        执行买入
        
        Args:
            price: 当前价格
            weight: 买入权重
            date: 交易日期
        """
        # 考虑滑点
        executed_price = price * (1 + self.slippage)
        
        # 计算买入金额
        buy_amount = self.cash * weight
        
        # 计算手续费
        commission = buy_amount * self.commission
        
        # 计算可买入的股数
        buy_value = buy_amount - commission
        shares = buy_value / executed_price
        
        if buy_value <= 0:
            return
        
        # 更新状态
        self.position += shares
        self.cash -= buy_amount
        
        # 记录交易
        trade = {
            'date': date,
            'action': 'buy',
            'price': executed_price,
            'shares': shares,
            'amount': buy_amount,
            'commission': commission,
            'cash_after': self.cash,
            'position_after': self.position
        }
        self.trades.append(trade)
        
        logger.debug(f"买入: {date} 价格{executed_price:.2f} 数量{shares:.0f}")
    
    def _execute_sell(self, price: float, weight: float, date):
        """
        执行卖出
        
        Args:
            price: 当前价格
            weight: 卖出权重
            date: 交易日期
        """
        if self.position <= 0:
            return
        
        # 考虑滑点
        executed_price = price * (1 - self.slippage)
        
        # 计算卖出股数
        sell_shares = self.position * weight
        
        # 计算卖出金额
        sell_amount = sell_shares * executed_price
        
        # 计算手续费
        commission = sell_amount * self.commission
        
        # 实际到账金额
        net_amount = sell_amount - commission
        
        # 更新状态
        self.position -= sell_shares
        self.cash += net_amount
        
        # 记录交易
        trade = {
            'date': date,
            'action': 'sell',
            'price': executed_price,
            'shares': sell_shares,
            'amount': sell_amount,
            'commission': commission,
            'cash_after': self.cash,
            'position_after': self.position
        }
        self.trades.append(trade)
        
        logger.debug(f"卖出: {date} 价格{executed_price:.2f} 数量{sell_shares:.0f}")
    
    def _calculate_metrics(self, data: pd.DataFrame, strategy: BaseStrategy) -> Dict:
        """
        计算回测绩效指标
        
        Args:
            data: 原始数据
            strategy: 策略实例
            
        Returns:
            绩效指标字典
        """
        # 转换为DataFrame
        portfolio_df = pd.DataFrame(self.portfolio_values)
        portfolio_df['date'] = pd.to_datetime(portfolio_df['date'])
        portfolio_df = portfolio_df.set_index('date')
        
        # 计算每日收益率
        portfolio_df['daily_return'] = portfolio_df['total_value'].pct_change()
        
        # 计算累计收益率
        total_return = (portfolio_df['total_value'].iloc[-1] - self.initial_cash) / self.initial_cash
        
        # 计算年化收益率
        trading_days = len(portfolio_df)
        annual_return = (1 + total_return) ** (252 / trading_days) - 1
        
        # 计算波动率
        volatility = portfolio_df['daily_return'].std() * np.sqrt(252)
        
        # 计算夏普比率
        if volatility > 0:
            sharpe_ratio = (annual_return - self.risk_free_rate) / volatility
        else:
            sharpe_ratio = 0
        
        # 计算最大回撤
        cumulative = (1 + portfolio_df['daily_return']).cumprod()
        running_max = cumulative.expanding().max()
        drawdown = (cumulative - running_max) / running_max
        max_drawdown = drawdown.min()
        
        # 计算胜率
        if len(self.trades) > 0:
            buy_trades = [t for t in self.trades if t['action'] == 'buy']
            sell_trades = [t for t in self.trades if t['action'] == 'sell']
            
            # 简单计算：盈利交易次数 / 总交易次数
            win_count = 0
            for i in range(0, len(sell_trades)):
                if i < len(buy_trades):
                    if sell_trades[i]['price'] > buy_trades[i]['price']:
                        win_count += 1
            
            win_rate = win_count / len(sell_trades) if sell_trades else 0
        else:
            win_rate = 0
        
        # 计算基准收益
        benchmark_return = (data['close'].iloc[-1] - data['close'].iloc[0]) / data['close'].iloc[0]
        
        # 超额收益
        excess_return = total_return - benchmark_return
        
        results = {
            # 基本指标
            'initial_cash': self.initial_cash,
            'final_value': portfolio_df['total_value'].iloc[-1],
            'total_return': total_return,
            'annual_return': annual_return,
            
            # 风险指标
            'volatility': volatility,
            'sharpe_ratio': sharpe_ratio,
            'max_drawdown': max_drawdown,
            
            # 交易统计
            'total_trades': len(self.trades),
            'win_rate': win_rate,
            
            # 基准比较
            'benchmark_return': benchmark_return,
            'excess_return': excess_return,
            
            # 详细数据
            'portfolio_values': portfolio_df,
            'trades': self.trades,
            'strategy_signals': strategy.signals
        }
        
        return results
    
    def print_results(self, results: Dict):
        """
        打印回测结果
        
        Args:
            results: 回测结果字典
        """
        print("\n" + "="*60)
        print("                   回测结果报告")
        print("="*60)
        
        print(f"\n【基本收益】")
        print(f"  初始资金:     {results['initial_cash']:>12,.2f} 元")
        print(f"  最终资产:     {results['final_value']:>12,.2f} 元")
        print(f"  总收益率:     {results['total_return']*100:>11.2f}%")
        print(f"  年化收益率:   {results['annual_return']*100:>11.2f}%")
        
        print(f"\n【风险指标】")
        print(f"  波动率:       {results['volatility']*100:>11.2f}%")
        print(f"  夏普比率:     {results['sharpe_ratio']:>12.2f}")
        print(f"  最大回撤:     {results['max_drawdown']*100:>11.2f}%")
        
        print(f"\n【交易统计】")
        print(f"  总交易次数:   {results['total_trades']:>12} 次")
        print(f"  胜率:         {results['win_rate']*100:>11.2f}%")
        
        print(f"\n【基准比较】")
        print(f"  基准收益率:   {results['benchmark_return']*100:>11.2f}%")
        print(f"  超额收益:     {results['excess_return']*100:>11.2f}%")
        
        print("\n" + "="*60)
    
    def save_results(self, results: Dict, strategy_name: str = "default") -> str:
        """
        保存回测结果
        
        Args:
            results: 回测结果
            strategy_name: 策略名称
            
        Returns:
            保存的文件路径
        """
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"backtest_{strategy_name}_{timestamp}.json"
        filepath = BACKTEST_RESULT_DIR / filename
        
        # 提取可序列化的数据
        save_data = {
            'strategy': strategy_name,
            'timestamp': timestamp,
            'metrics': {
                'initial_cash': results['initial_cash'],
                'final_value': float(results['final_value']),
                'total_return': float(results['total_return']),
                'annual_return': float(results['annual_return']),
                'volatility': float(results['volatility']),
                'sharpe_ratio': float(results['sharpe_ratio']),
                'max_drawdown': float(results['max_drawdown']),
                'total_trades': results['total_trades'],
                'win_rate': float(results['win_rate']),
                'benchmark_return': float(results['benchmark_return']),
                'excess_return': float(results['excess_return'])
            },
            'trades': results['trades']
        }
        
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(save_data, f, ensure_ascii=False, indent=2)
        
        logger.info(f"回测结果已保存: {filepath}")
        return str(filepath)
    
    def plot_results(self, results: Dict, save_path: str = None):
        """
        绘制回测结果图表
        
        Args:
            results: 回测结果
            save_path: 保存路径（可选）
        """
        try:
            import matplotlib.pyplot as plt
            import matplotlib.dates as mdates
            
            portfolio_df = results['portfolio_values']
            
            fig, axes = plt.subplots(3, 1, figsize=(14, 10))
            
            # 1. 资产曲线
            ax1 = axes[0]
            ax1.plot(portfolio_df.index, portfolio_df['total_value'], label='策略资产', linewidth=2)
            ax1.axhline(y=self.initial_cash, color='r', linestyle='--', label='初始资金')
            ax1.set_title('资产曲线')
            ax1.set_ylabel('资产价值')
            ax1.legend()
            ax1.grid(True, alpha=0.3)
            
            # 2. 每日收益
            ax2 = axes[1]
            ax2.bar(portfolio_df.index, portfolio_df['daily_return']*100, alpha=0.7)
            ax2.set_title('每日收益率')
            ax2.set_ylabel('收益率 (%)')
            ax2.axhline(y=0, color='k', linestyle='-', linewidth=0.5)
            ax2.grid(True, alpha=0.3)
            
            # 3. 回撤
            ax3 = axes[2]
            cumulative = (1 + portfolio_df['daily_return']).cumprod()
            running_max = cumulative.expanding().max()
            drawdown = (cumulative - running_max) / running_max * 100
            ax3.fill_between(portfolio_df.index, drawdown, 0, alpha=0.5, color='red')
            ax3.set_title('回撤曲线')
            ax3.set_ylabel('回撤 (%)')
            ax3.set_xlabel('日期')
            ax3.grid(True, alpha=0.3)
            
            plt.tight_layout()
            
            if save_path:
                plt.savefig(save_path, dpi=150, bbox_inches='tight')
                logger.info(f"图表已保存: {save_path}")
            else:
                plt.show()
                
        except ImportError:
            logger.warning("请先安装matplotlib: pip install matplotlib")
