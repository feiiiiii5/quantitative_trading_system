#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
组合回测引擎 - 多标的组合策略回测

支持：
- 同时回测多只股票
- 统一调仓日期管理
- 组合级别的绩效计算
"""

import numpy as np
import pandas as pd
from typing import Dict, List, Optional
from datetime import datetime

from core.engine import Cerebro, Broker, ExecutionMode, BaseStrategy, DataFeed
from utils.metrics import calculate_metrics


class PortfolioBacktestEngine:
    """
    组合回测引擎

    管理多标的的组合策略回测
    """

    def __init__(self, mode: ExecutionMode = ExecutionMode.VECTORIZED):
        self.mode = mode
        self.data_feeds: Dict[str, DataFeed] = {}
        self.broker = Broker()
        self.rebalance_dates: List[datetime] = []
        self.weights_history: List[Dict[str, float]] = []

    def add_data(self, data: pd.DataFrame, name: str):
        """添加标的"""
        self.data_feeds[name] = DataFeed(data, name)

    def set_rebalance_dates(self, dates: List[datetime]):
        """设置调仓日期"""
        self.rebalance_dates = sorted(dates)

    def run_portfolio(self, strategy: BaseStrategy,
                      weights_func) -> dict:
        """
        运行组合回测

        Args:
            strategy: 策略实例
            weights_func: 权重计算函数，接收(data_dict, current_date) -> Dict[symbol, weight]

        Returns:
            dict: 组合绩效结果
        """
        if not self.data_feeds:
            raise ValueError("未添加数据")

        # 获取统一日期索引
        all_dates = None
        for df in self.data_feeds.values():
            if all_dates is None:
                all_dates = set(df.index)
            else:
                all_dates = all_dates.intersection(set(df.index))

        sorted_dates = sorted(all_dates)

        # 初始化
        self.broker.reset()
        equity_curve = [self.broker.initial_cash]
        returns = []

        for i, date in enumerate(sorted_dates[1:], 1):
            # 检查是否调仓日
            is_rebalance = any(d.date() == date.date() for d in self.rebalance_dates) if self.rebalance_dates else False

            if is_rebalance or i == 1:
                # 计算目标权重
                current_data = {
                    name: df.data.loc[date]
                    for name, df in self.data_feeds.items()
                    if date in df.index
                }
                target_weights = weights_func(current_data, date)
                self.weights_history.append(target_weights)

                # 执行调仓（简化：全仓再平衡）
                total_value = self.broker.cash + sum(
                    self.broker.positions.get(sym, 0) * current_data[sym]['close']
                    for sym in current_data if sym in self.broker.positions
                )

                for symbol, weight in target_weights.items():
                    if symbol not in current_data:
                        continue
                    price = current_data[symbol]['close']
                    target_value = total_value * weight
                    target_shares = int(target_value / price)
                    current_shares = self.broker.positions.get(symbol, 0)

                    if target_shares > current_shares:
                        order = BaseStrategy.buy(strategy, symbol=symbol, quantity=target_shares - current_shares)
                        self.broker.execute_order(order, price, date)
                    elif target_shares < current_shares:
                        order = BaseStrategy.sell(strategy, symbol=symbol, quantity=current_shares - target_shares)
                        self.broker.execute_order(order, price, date)

            # 计算当日权益
            prices = {
                name: df.data.loc[date]['close'] if date in df.index else 0
                for name, df in self.data_feeds.items()
            }
            total_value = self.broker.get_total_value(prices)
            equity_curve.append(total_value)

            ret = (equity_curve[-1] / equity_curve[-2]) - 1
            returns.append(ret)

        self.broker.equity_curve = equity_curve
        metrics = calculate_metrics(equity_curve, returns, self.broker.trades)

        return {
            'metrics': metrics,
            'equity_curve': equity_curve,
            'weights_history': self.weights_history,
        }
