#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""功能测试脚本 - 验证核心功能"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path.cwd()))

from datetime import datetime, timedelta
import pandas as pd
import numpy as np

print('=== 测试1: 数据获取 ===')
from data.async_data_manager import AsyncDataManager
from data.market_detector import MarketDetector

dm = AsyncDataManager()
end_date = datetime.now().strftime('%Y-%m-%d')
start_date = (datetime.now() - timedelta(days=365)).strftime('%Y-%m-%d')

data = None
for source in ['akshare', 'baostock']:
    try:
        print(f'尝试从 {source} 获取数据...')
        data = dm.get_data_sync('000001', start_date, end_date, source=source, market='CN')
        if data is not None and not data.empty:
            print(f'数据获取成功 ({source}): {len(data)} 条记录')
            print(f'列: {list(data.columns)}')
            print(f'最新价格: {data["close"].iloc[-1]}')
            break
    except Exception as e:
        print(f'{source} 获取失败: {e}')

if data is None or data.empty:
    print('所有数据源获取失败，使用模拟数据进行引擎测试')
    # 创建模拟数据用于测试引擎
    dates = pd.date_range(end=datetime.now(), periods=252, freq='B')
    np.random.seed(42)
    prices = 10 * np.exp(np.cumsum(np.random.randn(252) * 0.02))
    data = pd.DataFrame({
        'open': prices * (1 + np.random.randn(252) * 0.01),
        'high': prices * (1 + abs(np.random.randn(252)) * 0.02),
        'low': prices * (1 - abs(np.random.randn(252)) * 0.02),
        'close': prices,
        'volume': np.random.randint(1000000, 10000000, 252),
    }, index=dates)
    print(f'模拟数据创建成功: {len(data)} 条记录')

print('\n=== 测试2: 回测引擎 (向量化) ===')
from core.engine import Cerebro, Broker, ExecutionMode
from strategies.ma_cross import MACrossStrategy

try:
    cerebro = Cerebro(mode=ExecutionMode.VECTORIZED)
    cerebro.add_data(data, '000001')
    broker = Broker(initial_cash=100000, market='CN')
    cerebro.set_broker(broker)
    strategy = MACrossStrategy()
    cerebro.add_strategy(strategy)
    metrics = cerebro.run()
    print(f'回测成功!')
    print(f'  总收益: {metrics.total_return:.2%}')
    print(f'  夏普比率: {metrics.sharpe_ratio:.2f}')
    print(f'  最大回撤: {metrics.max_drawdown:.2%}')
    print(f'  交易次数: {metrics.total_trades}')
except Exception as e:
    print(f'回测失败: {e}')
    import traceback
    traceback.print_exc()

print('\n=== 测试3: 事件驱动回测 ===')
try:
    cerebro2 = Cerebro(mode=ExecutionMode.EVENT_DRIVEN)
    cerebro2.add_data(data, '000001')
    broker2 = Broker(initial_cash=100000, market='CN')
    cerebro2.set_broker(broker2)
    strategy2 = MACrossStrategy()
    cerebro2.add_strategy(strategy2)
    metrics2 = cerebro2.run()
    print(f'事件驱动回测成功!')
    print(f'  总收益: {metrics2.total_return:.2%}')
    print(f'  夏普比率: {metrics2.sharpe_ratio:.2f}')
except Exception as e:
    print(f'事件驱动回测失败: {e}')
    import traceback
    traceback.print_exc()

print('\n=== 测试4: 高级策略 ===')
from strategies.advanced_strategies import AdaptiveMarketRegimeStrategy

try:
    cerebro3 = Cerebro(mode=ExecutionMode.VECTORIZED)
    cerebro3.add_data(data, '000001')
    broker3 = Broker(initial_cash=100000, market='CN')
    cerebro3.set_broker(broker3)
    strategy3 = AdaptiveMarketRegimeStrategy()
    cerebro3.add_strategy(strategy3)
    metrics3 = cerebro3.run()
    print(f'自适应策略回测成功!')
    print(f'  总收益: {metrics3.total_return:.2%}')
    print(f'  夏普比率: {metrics3.sharpe_ratio:.2f}')
except Exception as e:
    print(f'自适应策略回测失败: {e}')
    import traceback
    traceback.print_exc()

print('\n=== 测试5: 风险管理器 ===')
from risk.advanced_risk_manager import AdvancedRiskManager, RiskConfig

try:
    rm = AdvancedRiskManager(RiskConfig())
    returns = data['close'].pct_change().dropna()
    metrics = rm.calculate_risk_metrics(returns)
    print(f'风险指标计算成功!')
    print(f'  VaR 95%: {metrics.var_95:.4f}')
    print(f'  CVaR 95%: {metrics.cvar_95:.4f}')
    print(f'  波动率: {metrics.volatility:.4f}')
except Exception as e:
    print(f'风险指标计算失败: {e}')
    import traceback
    traceback.print_exc()

print('\n=== 测试6: 参数优化 ===')
try:
    cerebro4 = Cerebro(mode=ExecutionMode.VECTORIZED)
    cerebro4.add_data(data, '000001')
    param_grid = {'fast_period': [5, 10], 'slow_period': [20, 30]}
    best_params, best_result = cerebro4.optimize(MACrossStrategy, param_grid)
    print(f'参数优化成功!')
    print(f'  最佳参数: {best_params}')
    if best_result:
        print(f'  最佳夏普: {best_result.sharpe_ratio:.2f}')
except Exception as e:
    print(f'参数优化失败: {e}')
    import traceback
    traceback.print_exc()

print('\n=== 所有功能测试完成 ===')
