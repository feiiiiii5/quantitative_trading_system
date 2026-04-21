#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
引擎测试脚本 - 使用模拟数据验证回测引擎
"""

import numpy as np
import pandas as pd
from datetime import datetime, timedelta

from core.engine import Cerebro, Broker, ExecutionMode, BaseStrategy, Order
from strategies.advanced_strategies import (
    MultiFactorStrategy,
    AdaptiveMarketRegimeStrategy,
    MachineLearningStrategy
)
from data.market_detector import MarketDetector
from data.data_cleaner import DataCleaner
from core.factor_engine import FactorEngine
from core.portfolio_optimizer import PortfolioOptimizer
from risk.drawdown_analyzer import DrawdownAnalyzer


def generate_mock_data(n_days=500, seed=42):
    """生成模拟股票数据"""
    np.random.seed(seed)
    dates = pd.date_range(end=datetime.now(), periods=n_days, freq='B')

    # 随机游走生成价格
    returns = np.random.normal(0.0005, 0.02, n_days)
    price = 100 * np.exp(np.cumsum(returns))

    # 生成OHLCV
    data = pd.DataFrame({
        'open': price * (1 + np.random.normal(0, 0.005, n_days)),
        'high': price * (1 + abs(np.random.normal(0, 0.01, n_days))),
        'low': price * (1 - abs(np.random.normal(0, 0.01, n_days))),
        'close': price,
        'volume': np.random.randint(1000000, 10000000, n_days)
    }, index=dates)

    return data


class TestMACrossStrategy(BaseStrategy):
    """测试用均线交叉策略"""

    def __init__(self, fast_period=5, slow_period=20):
        super().__init__(name="MA_Cross", parameters={
            'fast_period': fast_period,
            'slow_period': slow_period
        })
        self.fast_ma = None
        self.slow_ma = None

    def init(self):
        fast = self.parameters['fast_period']
        slow = self.parameters['slow_period']
        self.fast_ma = self._data.close.rolling(fast).mean()
        self.slow_ma = self._data.close.rolling(slow).mean()

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


def test_event_driven():
    """测试事件驱动回测"""
    print("\n" + "=" * 60)
    print("测试事件驱动回测")
    print("=" * 60)

    data = generate_mock_data(300)

    cerebro = Cerebro(mode=ExecutionMode.EVENT_DRIVEN)
    cerebro.add_data(data, "TEST")

    broker = Broker(initial_cash=100000)
    cerebro.set_broker(broker)

    strategy = TestMACrossStrategy()
    cerebro.add_strategy(strategy)

    metrics = cerebro.run()
    metrics.print_summary()

    # 验证关键指标
    assert len(broker.equity_curve) == len(data), "权益曲线长度不匹配"
    assert broker.equity_curve[0] == 100000, "初始资金错误"
    assert metrics.total_return != 0, "收益率为0，策略未执行"
    assert metrics.sharpe_ratio != 0, "夏普比率为0"

    print("✓ 事件驱动回测测试通过")
    return True


def test_vectorized():
    """测试向量化回测"""
    print("\n" + "=" * 60)
    print("测试向量化回测")
    print("=" * 60)

    data = generate_mock_data(300)

    cerebro = Cerebro(mode=ExecutionMode.VECTORIZED)
    cerebro.add_data(data, "TEST")

    broker = Broker(initial_cash=100000)
    cerebro.set_broker(broker)

    strategy = TestMACrossStrategy()
    cerebro.add_strategy(strategy)

    metrics = cerebro.run()
    metrics.print_summary()

    # 验证关键指标
    assert len(broker.equity_curve) == len(data), "权益曲线长度不匹配"
    assert broker.equity_curve[0] == 100000, "初始资金错误"

    print("✓ 向量化回测测试通过")
    return True


def test_advanced_strategies():
    """测试高级策略"""
    print("\n" + "=" * 60)
    print("测试高级策略")
    print("=" * 60)

    data = generate_mock_data(500)

    strategies = [
        ("多因子", MultiFactorStrategy()),
        ("自适应", AdaptiveMarketRegimeStrategy()),
        ("机器学习", MachineLearningStrategy()),
    ]

    for name, strategy in strategies:
        print(f"\n测试 {name} 策略...")
        cerebro = Cerebro(mode=ExecutionMode.VECTORIZED)
        cerebro.add_data(data, "TEST")
        cerebro.set_broker(Broker(initial_cash=100000))
        cerebro.add_strategy(strategy)

        try:
            metrics = cerebro.run()
            print(f"  ✓ {name} 策略运行成功，收益率: {metrics.total_return:.2%}")
        except Exception as e:
            print(f"  ✗ {name} 策略失败: {e}")
            return False

    print("\n✓ 高级策略测试通过")
    return True


def test_broker_pnl():
    """测试Broker的PnL计算"""
    print("\n" + "=" * 60)
    print("测试Broker PnL计算")
    print("=" * 60)

    from datetime import datetime, timedelta

    # 测试A股T+1规则
    broker_cn = Broker(initial_cash=100000, slippage=0.0, market="CN")
    order1 = Order(symbol="TEST", action="buy", quantity=100, price=100)
    trade1 = broker_cn.execute_order(order1, 100, datetime(2024, 1, 1, 10, 0))
    assert broker_cn.positions["TEST"] == 100, "持仓数量错误"

    # 同日卖出应被阻止
    order2 = Order(symbol="TEST", action="sell", quantity=100, price=110)
    trade2 = broker_cn.execute_order(order2, 110, datetime(2024, 1, 1, 14, 0))
    assert trade2 is None, "A股T+1应阻止当日卖出"

    # 次日卖出应成功
    order3 = Order(symbol="TEST", action="sell", quantity=100, price=110)
    trade3 = broker_cn.execute_order(order3, 110, datetime(2024, 1, 2, 10, 0))
    assert trade3 is not None, "次日卖出应成功"
    assert trade3.pnl > 0, "盈利交易PnL应为正"
    assert broker_cn.positions["TEST"] == 0, "清仓后持仓应为0"

    print(f"  A股T+1验证通过，次日卖出 PnL: {trade3.pnl:.2f}")

    # 测试港股T+0
    broker_hk = Broker(initial_cash=100000, slippage=0.0, market="HK")
    order4 = Order(symbol="0700", action="buy", quantity=100, price=300)
    broker_hk.execute_order(order4, 300, datetime(2024, 1, 1, 10, 0))

    order5 = Order(symbol="0700", action="sell", quantity=100, price=310)
    trade5 = broker_hk.execute_order(order5, 310, datetime(2024, 1, 1, 14, 0))
    assert trade5 is not None, "港股T+0应允许当日卖出"
    assert trade5.pnl > 0, "盈利交易PnL应为正"

    print(f"  港股T+0验证通过，当日卖出 PnL: {trade5.pnl:.2f}")
    print("✓ Broker PnL计算测试通过")
    return True


def test_market_detection():
    """测试市场检测"""
    print("\n" + "=" * 60)
    print("测试市场检测")
    print("=" * 60)

    detector = MarketDetector()
    assert detector.detect('000001') == 'CN', "A股识别失败"
    assert detector.detect('600519') == 'CN', "沪市识别失败"
    assert detector.detect('00700') == 'HK', "港股识别失败"
    assert detector.detect('0700.HK') == 'HK', "港股后缀识别失败"
    assert detector.detect('AAPL') == 'US', "美股识别失败"
    assert detector.detect('TSLA.US') == 'US', "美股后缀识别失败"

    print("  A股: 000001 ✓")
    print("  港股: 00700 ✓")
    print("  美股: AAPL ✓")
    print("✓ 市场检测测试通过")
    return True


def test_multi_market_broker():
    """测试多市场交易规则"""
    print("\n" + "=" * 60)
    print("测试多市场交易规则")
    print("=" * 60)

    # A股T+1
    broker_cn = Broker(market="CN")
    assert broker_cn.market == "CN"
    print("  A股Broker创建 ✓")

    # 港股T+0
    broker_hk = Broker(market="HK")
    assert broker_hk.market == "HK"
    print("  港股Broker创建 ✓")

    # 美股
    broker_us = Broker(market="US")
    assert broker_us.market == "US"
    print("  美股Broker创建 ✓")

    print("✓ 多市场交易规则测试通过")
    return True


def test_factor_engine():
    """测试因子引擎"""
    print("\n" + "=" * 60)
    print("测试因子引擎")
    print("=" * 60)

    np.random.seed(42)
    close = pd.Series(100 + np.cumsum(np.random.randn(100) * 0.5),
                      index=pd.date_range('2024-01-01', periods=100))
    volume = pd.Series(np.random.randint(1000, 10000, 100),
                       index=close.index)

    # 动量因子
    mom = FactorEngine.compute_momentum(close)
    assert not mom.empty, "动量因子计算失败"
    assert abs(mom.mean().mean()) < 0.1, "动量因子均值应接近0（标准化后）"
    print(f"  动量因子: {mom.shape} ✓")

    # 质量因子
    quality = FactorEngine.compute_quality(close, volume)
    assert not quality.empty, "质量因子计算失败"
    print(f"  质量因子: {quality.shape} ✓")

    # IC分析
    forward = close.pct_change(5).shift(-5)
    ic = FactorEngine.ic_analysis(mom['mom_5'], forward)
    assert 'ic_mean' in ic, "IC分析失败"
    print(f"  IC均值: {ic['ic_mean']:.4f} ✓")

    print("✓ 因子引擎测试通过")
    return True


def test_portfolio_optimizer():
    """测试组合优化器"""
    print("\n" + "=" * 60)
    print("测试组合优化器")
    print("=" * 60)

    np.random.seed(42)
    n = 5
    returns = np.random.randn(252, n) * 0.02
    cov = np.cov(returns.T)
    mean = returns.mean(axis=0) * 252

    # 风险平价
    w_rp = PortfolioOptimizer.risk_parity(cov)
    assert abs(w_rp.sum() - 1.0) < 0.01, f"风险平价权重和={w_rp.sum():.4f}"
    assert np.all(w_rp >= 0) and np.all(w_rp <= 1), "风险平价权重越界"
    print(f"  风险平价: sum={w_rp.sum():.4f}, range=[{w_rp.min():.4f}, {w_rp.max():.4f}] ✓")

    # 最大夏普
    w_ms = PortfolioOptimizer.max_sharpe(mean, cov)
    assert abs(w_ms.sum() - 1.0) < 0.01, "最大夏普权重和错误"
    assert np.all(w_ms >= 0) and np.all(w_ms <= 1), "最大夏普权重越界"
    print(f"  最大夏普: sum={w_ms.sum():.4f} ✓")

    # 最小方差
    w_mv = PortfolioOptimizer.min_volatility(cov)
    assert abs(w_mv.sum() - 1.0) < 0.01, "最小方差权重和错误"
    assert np.all(w_mv >= 0) and np.all(w_mv <= 1), "最小方差权重越界"
    print(f"  最小方差: sum={w_mv.sum():.4f} ✓")

    print("✓ 组合优化器测试通过")
    return True


def test_data_cleaner():
    """测试数据清洗"""
    print("\n" + "=" * 60)
    print("测试数据清洗")
    print("=" * 60)

    # 创建含异常值的数据
    data = pd.DataFrame({
        'open': [100, 101, 102, 500, 103, 104],
        'high': [101, 102, 103, 501, 104, 105],
        'low': [99, 100, 101, 499, 102, 103],
        'close': [100, 101, 102, 500, 103, 104],
        'volume': [1000, 1100, 1200, 1300, 1400, 1500],
    })

    # 异常值检测
    valid, errors = DataCleaner.validate_ohlcv(data)
    assert valid, f"数据验证失败: {errors}"
    print("  数据验证 ✓")

    # 异常值处理
    cleaned = DataCleaner.remove_outliers(data, method='zscore', threshold=2)
    assert cleaned.isna().sum().sum() > 0, "应检测到异常值"
    print("  异常值处理 ✓")

    # 缺失值填充
    filled = DataCleaner.fill_missing(cleaned, method='ffill')
    assert filled.isna().sum().sum() == 0, "填充后不应有NaN"
    print("  缺失值填充 ✓")

    print("✓ 数据清洗测试通过")
    return True


if __name__ == "__main__":
    print("QuantSystem Pro 引擎测试")

    all_passed = True

    all_passed &= test_broker_pnl()
    all_passed &= test_event_driven()
    all_passed &= test_vectorized()
    all_passed &= test_advanced_strategies()
    all_passed &= test_market_detection()
    all_passed &= test_multi_market_broker()
    all_passed &= test_factor_engine()
    all_passed &= test_portfolio_optimizer()
    all_passed &= test_data_cleaner()

    print("\n" + "=" * 60)
    if all_passed:
        print("✓ 所有测试通过！")
    else:
        print("✗ 部分测试失败")
    print("=" * 60)
