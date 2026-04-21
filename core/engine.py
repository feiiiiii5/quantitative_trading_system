#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
核心引擎模块 - 整合业界最佳实践

参考设计：
- backtrader: Cerebro引擎设计
- backtesting.py: 向量化回测
- pybroker: NumPy/Numba加速
- bt: 树形策略组合
- rqalpha: 事件驱动架构

特性：
- 支持事件驱动和向量化两种回测模式
- 内置Walkforward分析
- Bootstrap统计指标
- 多策略组合管理
"""

import numpy as np
import pandas as pd
from typing import Dict, List, Optional, Tuple, Callable, Union, Any
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from abc import ABC, abstractmethod
import warnings
import copy
from pathlib import Path

from utils.logger import get_logger
from utils.metrics import calculate_metrics as _calc_metrics

logger = get_logger(__name__)


class ExecutionMode(Enum):
    """执行模式"""
    EVENT_DRIVEN = "event_driven"
    VECTORIZED = "vectorized"
    HYBRID = "hybrid"


class OrderType(Enum):
    """订单类型"""
    MARKET = "market"
    LIMIT = "limit"
    STOP = "stop"
    STOP_LIMIT = "stop_limit"


@dataclass
class Order:
    """订单对象"""
    symbol: str
    action: str  # buy/sell
    quantity: float
    order_type: OrderType = OrderType.MARKET
    price: Optional[float] = None
    stop_price: Optional[float] = None
    timestamp: Optional[datetime] = None
    reason: str = ""
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now()


@dataclass
class Trade:
    """交易记录"""
    entry_time: datetime
    exit_time: Optional[datetime] = None
    symbol: str = ""
    direction: str = ""  # long/short
    entry_price: float = 0.0
    exit_price: float = 0.0
    quantity: float = 0.0
    pnl: float = 0.0
    pnl_pct: float = 0.0
    commission: float = 0.0
    reason: str = ""
    
    @property
    def is_open(self) -> bool:
        return self.exit_time is None
    
    @property
    def duration(self) -> Optional[timedelta]:
        if self.exit_time:
            return self.exit_time - self.entry_time
        return None


@dataclass
class PerformanceMetrics:
    """绩效指标 - 参考backtesting.py和pybroker设计"""
    # 收益指标
    total_return: float = 0.0
    annual_return: float = 0.0
    cagr: float = 0.0
    
    # 风险指标
    volatility: float = 0.0
    sharpe_ratio: float = 0.0
    sortino_ratio: float = 0.0
    calmar_ratio: float = 0.0
    max_drawdown: float = 0.0
    max_drawdown_duration: int = 0
    avg_drawdown: float = 0.0
    
    # 交易指标
    total_trades: int = 0
    win_rate: float = 0.0
    profit_factor: float = 0.0
    avg_trade: float = 0.0
    best_trade: float = 0.0
    worst_trade: float = 0.0
    avg_trade_duration: int = 0
    
    # 高级指标 (参考pybroker)
    kelly_criterion: float = 0.0
    sqn: float = 0.0  # System Quality Number
    expectancy: float = 0.0
    alpha: float = 0.0
    beta: float = 0.0
    
    # Bootstrap指标
    bootstrap_sharpe_mean: float = 0.0
    bootstrap_sharpe_std: float = 0.0
    bootstrap_var_95: float = 0.0
    
    def to_dict(self) -> Dict[str, float]:
        return {
            k: v for k, v in self.__dict__.items()
            if not k.startswith('_')
        }
    
    def print_summary(self):
        """打印摘要"""
        print("=" * 60)
        print("回测绩效报告")
        print("=" * 60)
        print(f"总收益率:          {self.total_return:>12.2%}")
        print(f"年化收益率 (CAGR): {self.cagr:>12.2%}")
        print(f"年化波动率:        {self.volatility:>12.2%}")
        print(f"夏普比率:          {self.sharpe_ratio:>12.2f}")
        print(f"Sortino比率:       {self.sortino_ratio:>12.2f}")
        print(f"Calmar比率:        {self.calmar_ratio:>12.2f}")
        print(f"最大回撤:          {self.max_drawdown:>12.2%}")
        print(f"最大回撤持续期:    {self.max_drawdown_duration:>12}天")
        print("-" * 60)
        print(f"总交易次数:        {self.total_trades:>12}")
        print(f"胜率:              {self.win_rate:>12.2%}")
        print(f"盈亏比:            {self.profit_factor:>12.2f}")
        print(f"平均交易收益:      {self.avg_trade:>12.2%}")
        print(f"最佳交易:          {self.best_trade:>12.2%}")
        print(f"最差交易:          {self.worst_trade:>12.2%}")
        print(f"SQN:               {self.sqn:>12.2f}")
        print(f"凯利准则:          {self.kelly_criterion:>12.4f}")
        print("=" * 60)


class DataFeed:
    """
    数据馈送类 - 参考backtrader设计
    
    管理单只股票的历史数据，提供指标计算接口
    """
    
    def __init__(self, data: pd.DataFrame, name: str = "", freq: str = "1d"):
        self.data = data.copy()
        self.name = name or "data"
        self.freq = freq  # '1d', '1m', '1h' 等
        self._indicators = {}
        self._lines = {}
        
        # 确保必要的列存在
        required_cols = ['open', 'high', 'low', 'close', 'volume']
        for col in required_cols:
            if col not in self.data.columns:
                raise ValueError(f"数据缺少必要列: {col}")
    
    def __len__(self) -> int:
        return len(self.data)
    
    def __getitem__(self, idx: int) -> pd.Series:
        return self.data.iloc[idx]
    
    @property
    def open(self) -> pd.Series:
        return self.data['open']
    
    @property
    def high(self) -> pd.Series:
        return self.data['high']
    
    @property
    def low(self) -> pd.Series:
        return self.data['low']
    
    @property
    def close(self) -> pd.Series:
        return self.data['close']
    
    @property
    def volume(self) -> pd.Series:
        return self.data['volume']
    
    @property
    def index(self) -> pd.DatetimeIndex:
        return self.data.index
    
    def add_indicator(self, name: str, series: pd.Series):
        """添加指标"""
        self._indicators[name] = series
        self.data[name] = series
    
    def get_indicator(self, name: str) -> pd.Series:
        """获取指标"""
        return self._indicators.get(name, pd.Series(index=self.data.index))
    
    def get_slice(self, start: int, end: int) -> pd.DataFrame:
        """获取数据切片"""
        return self.data.iloc[start:end]


class BaseStrategy(ABC):
    """
    策略基类 - 参考backtrader和backtesting.py设计
    
    提供更完善的策略生命周期管理
    """
    
    def __init__(self, name: str = None, parameters: Dict[str, Any] = None):
        self.name = name or self.__class__.__name__
        self.parameters = parameters or {}
        
        # 状态
        self._data = None
        self._position = 0.0
        self._cash = 0.0
        self._equity = 0.0
        self._orders = []
        self._trades = []
        
        # 指标
        self._indicators = {}
        
        logger.info(f"策略 '{self.name}' 初始化完成")
    
    def set_data(self, data: DataFeed):
        """设置数据"""
        self._data = data
    
    @property
    def position(self) -> float:
        return self._position
    
    @property
    def data(self) -> Optional[DataFeed]:
        return self._data
    
    @abstractmethod
    def init(self):
        """初始化策略 - 计算指标等"""
        pass
    
    @abstractmethod
    def next(self, index: int) -> Optional[Order]:
        """每周期执行逻辑"""
        pass
    
    def buy(self, symbol: str = "", quantity: float = 0, 
            price: float = None, reason: str = "") -> Order:
        """买入"""
        return Order(
            symbol=symbol or (self._data.name if self._data else ""),
            action="buy",
            quantity=quantity,
            price=price,
            reason=reason
        )
    
    def sell(self, symbol: str = "", quantity: float = 0,
             price: float = None, reason: str = "") -> Order:
        """卖出"""
        return Order(
            symbol=symbol or (self._data.name if self._data else ""),
            action="sell",
            quantity=quantity,
            price=price,
            reason=reason
        )
    
    def hold(self, reason: str = "") -> None:
        """持有"""
        return None
    
    def add_indicator(self, name: str, func: Callable, *args, **kwargs):
        """添加指标"""
        if self._data is not None:
            result = func(self._data.close, *args, **kwargs)
            self._indicators[name] = result
            self._data.add_indicator(name, result)
    
    def get_indicator(self, name: str) -> pd.Series:
        """获取指标"""
        return self._indicators.get(name, pd.Series())
    
    def on_order_filled(self, order: Order, fill_price: float):
        """订单成交回调"""
        pass
    
    def on_trade_closed(self, trade: Trade):
        """交易关闭回调"""
        pass


class Broker:
    """
    经纪商模拟器 - 参考backtrader设计
    
    处理订单执行、佣金计算、滑点模拟
    修复：
    - 新增 avg_cost 追踪持仓均价
    - 卖出时正确计算 PnL
    """
    
    def __init__(self, initial_cash: float = 1000000.0,
                 commission_rate: float = 0.0003,
                 slippage: float = 0.001,
                 margin: float = 1.0,
                 market: str = "CN"):
        self.initial_cash = initial_cash
        self.cash = initial_cash
        self.commission_rate = commission_rate
        self.slippage = slippage
        self.margin = margin
        self.market = market  # CN/HK/US

        # 持仓
        self.positions: Dict[str, float] = {}
        self.avg_cost: Dict[str, float] = {}  # 持仓均价
        self.buy_dates: Dict[str, datetime] = {}  # 买入日期（用于T+1检测）

        # 记录
        self.orders: List[Order] = []
        self.trades: List[Trade] = []
        self.equity_curve: List[float] = []

        logger.info(f"经纪商初始化: 初始资金={initial_cash:,.2f}, 市场={market}")
    
    def execute_order(self, order: Order, current_price: float,
                     current_time: datetime, prev_close: float = None) -> Optional[Trade]:
        """
        执行订单（带市场规则）

        市场规则：
        - A股：涨跌停±10%（ST±5%），T+1不可当日回转
        - 港股：无涨跌限制，T+0
        - 美股：熔断检测，T+2结算
        """
        symbol = order.symbol

        # A股T+1检测
        if self.market == "CN" and order.action == "sell":
            if symbol in self.buy_dates:
                # 简化：同一自然日不可卖出（实际应为交易日）
                if self.buy_dates[symbol].date() == current_time.date():
                    logger.warning(f"A股T+1限制: {symbol} 当日买入不可卖出")
                    return None

        # 涨跌停检测（A股）
        if self.market == "CN" and prev_close is not None and prev_close > 0:
            limit_pct = 0.1  # 默认±10%
            # ST股检测（简化：代码以*ST或ST开头，实际需从数据判断）
            if symbol.startswith(("*ST", "ST")):
                limit_pct = 0.05

            upper_limit = prev_close * (1 + limit_pct)
            lower_limit = prev_close * (1 - limit_pct)

            if current_price >= upper_limit and order.action == "buy":
                logger.warning(f"涨停限制: {symbol} 价格={current_price:.2f} >= 涨停价={upper_limit:.2f}")
                return None
            if current_price <= lower_limit and order.action == "sell":
                logger.warning(f"跌停限制: {symbol} 价格={current_price:.2f} <= 跌停价={lower_limit:.2f}")
                return None

        # 美股熔断检测（简化版）
        if self.market == "US" and prev_close is not None and prev_close > 0:
            drop_pct = (current_price - prev_close) / prev_close
            if drop_pct <= -0.20:
                logger.warning(f"美股三级熔断: {symbol} 跌幅={drop_pct:.2%}，停止交易")
                return None

        if order.order_type == OrderType.MARKET:
            fill_price = current_price * (1 + self.slippage *
                         (1 if order.action == "buy" else -1))
        else:
            fill_price = order.price or current_price

        # 计算成本（含市场特定税费）
        value = fill_price * order.quantity
        commission = value * self.commission_rate

        # A股印花税（卖出时）
        stamp_duty = 0.0
        if self.market == "CN" and order.action == "sell":
            stamp_duty = value * 0.001

        total_cost = value + commission + stamp_duty

        # 检查资金
        if order.action == "buy" and total_cost > self.cash:
            logger.warning(f"资金不足: 需要{total_cost:,.2f}, 可用{self.cash:,.2f}")
            return None

        # 更新持仓
        if symbol not in self.positions:
            self.positions[symbol] = 0
            self.avg_cost[symbol] = 0.0

        old_qty = self.positions[symbol]

        if order.action == "buy":
            # 买入：更新均价
            new_qty = old_qty + order.quantity
            if new_qty > 0:
                self.avg_cost[symbol] = (
                    self.avg_cost.get(symbol, 0) * old_qty + fill_price * order.quantity
                ) / new_qty
            self.positions[symbol] = new_qty
            self.cash -= total_cost
            # 记录买入日期
            self.buy_dates[symbol] = current_time
        else:
            # 卖出：计算 PnL
            sell_qty = min(order.quantity, old_qty)
            if sell_qty > 0 and symbol in self.avg_cost:
                # PnL = (卖出价 - 成本价) * 数量 - 佣金 - 印花税
                pnl = (fill_price - self.avg_cost[symbol]) * sell_qty - commission - stamp_duty
                pnl_pct = pnl / (self.avg_cost[symbol] * sell_qty) if self.avg_cost[symbol] > 0 else 0

                # 更新持仓
                self.positions[symbol] -= sell_qty
                self.cash += value - commission - stamp_duty

                # 记录订单
                self.orders.append(order)

                # 创建交易记录（已平仓）
                trade = Trade(
                    entry_time=current_time,
                    exit_time=current_time,
                    symbol=symbol,
                    direction="long",
                    entry_price=self.avg_cost[symbol],
                    exit_price=fill_price,
                    quantity=sell_qty,
                    pnl=pnl,
                    pnl_pct=pnl_pct,
                    commission=commission + stamp_duty,
                    reason=order.reason
                )
                self.trades.append(trade)
                return trade
            else:
                # 空仓卖出（做空）
                self.positions[symbol] -= order.quantity
                self.cash += value - commission - stamp_duty

        # 记录订单
        self.orders.append(order)

        # 创建交易记录（开仓）
        trade = Trade(
            entry_time=current_time,
            symbol=symbol,
            direction="long" if order.action == "buy" else "short",
            entry_price=fill_price,
            quantity=order.quantity,
            commission=commission + stamp_duty,
            reason=order.reason
        )
        self.trades.append(trade)

        return trade
    
    def get_position_value(self, symbol: str, current_price: float) -> float:
        """获取持仓市值"""
        return self.positions.get(symbol, 0) * current_price
    
    def get_total_value(self, prices: Dict[str, float]) -> float:
        """获取总资产"""
        position_value = sum(
            self.get_position_value(sym, price)
            for sym, price in prices.items()
        )
        return self.cash + position_value
    
    def reset(self):
        """重置"""
        self.cash = self.initial_cash
        self.positions.clear()
        self.avg_cost.clear()
        self.orders.clear()
        self.trades.clear()
        self.equity_curve.clear()


class Cerebro:
    """
    核心引擎 - 参考backtrader的Cerebro设计
    
    整合数据、策略、经纪商，执行回测
    """
    
    def __init__(self, mode: ExecutionMode = ExecutionMode.EVENT_DRIVEN):
        self.mode = mode
        self.data_feeds = {}
        self.strategies = []
        self.broker = Broker()
        
        # 结果
        self.results = None
        self.metrics = None
        
        # 自动创建 reports 目录
        Path("reports").mkdir(exist_ok=True)
        
        logger.info(f"Cerebro引擎初始化: 模式={mode.value}")
    
    def add_data(self, data: pd.DataFrame, name: str = None, freq: str = "1d"):
        """添加数据"""
        name = name or f"data_{len(self.data_feeds)}"
        self.data_feeds[name] = DataFeed(data, name, freq)
        logger.info(f"添加数据: {name}, {len(data)}条记录, 频率={freq}")
    
    def add_strategy(self, strategy: BaseStrategy, **kwargs):
        """添加策略"""
        strategy.parameters.update(kwargs)
        self.strategies.append(strategy)
        logger.info(f"添加策略: {strategy.name}")
    
    def set_broker(self, broker: Broker):
        """设置经纪商"""
        self.broker = broker
    
    def run(self, progress_bar: bool = False) -> PerformanceMetrics:
        """运行回测"""
        if not self.data_feeds:
            raise ValueError("未添加数据")
        if not self.strategies:
            raise ValueError("未添加策略")
        
        logger.info("开始回测...")
        
        if self.mode == ExecutionMode.VECTORIZED:
            return self._run_vectorized()
        else:
            return self._run_event_driven(progress_bar)
    
    def _run_event_driven(self, progress_bar: bool = False) -> PerformanceMetrics:
        """事件驱动回测 - 修复：每次循环末尾更新 equity_curve"""
        # 获取主数据
        main_data = list(self.data_feeds.values())[0]
        
        # 初始化策略
        for strategy in self.strategies:
            strategy.set_data(main_data)
            strategy.init()
        
        # 重置经纪商
        self.broker.reset()
        
        # 回测循环
        equity_curve = []
        returns = []
        
        iterator = range(len(main_data))
        if progress_bar:
            try:
                from tqdm import tqdm
                iterator = tqdm(iterator, desc="回测中")
            except ImportError:
                pass
        
        for i in iterator:
            current_data = main_data[i]
            current_time = main_data.index[i]
            current_price = current_data['close']
            
            # 执行策略
            for strategy in self.strategies:
                order = strategy.next(i)
                
                if order is not None:
                    trade = self.broker.execute_order(order, current_price, current_time)
                    if trade:
                        strategy.on_order_filled(order, trade.entry_price)
            
            # 记录权益 - 每次循环末尾更新
            prices = {name: data.close.iloc[i] 
                     for name, data in self.data_feeds.items()}
            total_value = self.broker.get_total_value(prices)
            equity_curve.append(total_value)
            
            if i > 0:
                ret = (equity_curve[-1] / equity_curve[-2]) - 1
                returns.append(ret)
        
        # 同步 equity_curve 给 broker
        self.broker.equity_curve = equity_curve
        
        # 计算绩效指标
        self.metrics = self._calculate_metrics(equity_curve, returns)
        
        logger.info("回测完成")
        return self.metrics
    
    def _run_vectorized(self) -> PerformanceMetrics:
        """
        向量化回测 - 真正的向量化实现
        
        逻辑：
        1. 让每个策略生成信号序列
        2. T+1 执行（信号基于当日收盘，次日执行）
        3. 前向填充持仓
        4. 计算换手成本和净收益
        """
        main_data = list(self.data_feeds.values())[0]
        
        # 初始化策略
        for s in self.strategies:
            s.set_data(main_data)
            s.init()
        
        n = len(main_data)
        signals = np.zeros(n)
        
        # 收集策略信号
        for i in range(1, n):
            order = self.strategies[0].next(i)
            if order:
                signals[i] = 1.0 if order.action == 'buy' else -1.0
        
        # T+1 执行：信号延迟一期 + 前向填充持仓
        # replace(0, np.nan).ffill()：将0替换为NaN后前向填充，保持持仓状态
        # shift(1)：T+1执行
        # clip(-1, 1)：限制持仓在[-1, 1]之间
        pos = pd.Series(signals).replace(0, np.nan).ffill().fillna(0).shift(1).fillna(0).clip(-1, 1)
        
        # 价格收益率
        price_ret = main_data.close.pct_change().fillna(0).values
        
        # 换手率 = |持仓变化|
        turnover = np.abs(np.diff(pos.values, prepend=0))
        
        # 净收益 = 持仓收益 - 交易成本（佣金 + 滑点）
        net_ret = pos.values * price_ret - turnover * (self.broker.commission_rate + self.broker.slippage)
        
        # 权益曲线：确保首值为 initial_cash
        # cumprod 首项为 1，所以 equity[0] = initial_cash * (1 + net_ret[0])
        # 需要显式设置首值
        equity = self.broker.initial_cash * (1 + pd.Series(net_ret)).cumprod()
        equity_values = equity.tolist()
        if equity_values:
            equity_values[0] = self.broker.initial_cash
        self.broker.equity_curve = equity_values
        
        return self._calculate_metrics(equity_values, net_ret.tolist())
    
    def _calculate_metrics(self, equity_curve: List[float], 
                          returns: List[float]) -> PerformanceMetrics:
        """计算绩效指标 - 委托给 utils.metrics 模块"""
        return _calc_metrics(equity_curve, returns, self.broker.trades)
    
    def walkforward_analysis(self, train_size: float = 0.7,
                            n_windows: int = 5) -> List[PerformanceMetrics]:
        """
        Walkforward分析 - 参考pybroker设计
        
        模拟实际交易中的滚动训练和测试
        """
        main_data = list(self.data_feeds.values())[0]
        n_total = len(main_data)
        window_size = n_total // n_windows
        
        results = []
        
        for i in range(n_windows):
            start_idx = i * window_size
            train_end = start_idx + int(window_size * train_size)
            test_end = min(start_idx + window_size, n_total)
            
            if train_end >= test_end:
                continue
            
            # 训练数据
            train_data = main_data.data.iloc[start_idx:train_end]
            # 测试数据
            test_data = main_data.data.iloc[train_end:test_end]
            
            # 创建新的Cerebro进行测试
            cerebro = Cerebro(self.mode)
            cerebro.add_data(test_data)
            
            for strategy in self.strategies:
                new_strategy = copy.deepcopy(strategy)
                new_strategy._data = None
                cerebro.add_strategy(new_strategy)
            
            result = cerebro.run()
            results.append(result)
            
            logger.info(f"Window {i+1}/{n_windows}: 夏普={result.sharpe_ratio:.2f}")
        
        return results
    
    def compare_benchmark(self, benchmark_data: pd.DataFrame) -> Dict[str, float]:
        """
        与基准比较，计算超额收益指标

        Args:
            benchmark_data: 基准数据DataFrame（需包含'close'列）

        Returns:
            Dict: alpha, beta, information_ratio, tracking_error
        """
        if not self.broker.equity_curve or benchmark_data is None or benchmark_data.empty:
            return {}

        # 策略收益率
        equity = pd.Series(self.broker.equity_curve)
        strategy_returns = equity.pct_change().dropna()

        # 基准收益率
        benchmark_returns = benchmark_data['close'].pct_change().dropna()

        # 对齐日期
        common_idx = strategy_returns.index.intersection(benchmark_returns.index)
        if len(common_idx) < 10:
            return {}

        s_ret = strategy_returns.loc[common_idx]
        b_ret = benchmark_returns.loc[common_idx]

        # Beta = Cov(Rs, Rb) / Var(Rb)
        covariance = np.cov(s_ret, b_ret)[0, 1]
        benchmark_var = np.var(b_ret)
        beta = covariance / benchmark_var if benchmark_var > 0 else 1.0

        # Alpha = Rs_mean - Beta * Rb_mean
        alpha = s_ret.mean() - beta * b_ret.mean()

        # 追踪误差 = std(Rs - Rb) * sqrt(252)
        tracking_diff = s_ret - b_ret
        tracking_error = tracking_diff.std() * np.sqrt(252)

        # 信息比率 = (Rs_mean - Rb_mean) / 追踪误差
        information_ratio = (s_ret.mean() - b_ret.mean()) / (tracking_diff.std() + 1e-8) * np.sqrt(252)

        return {
            'alpha': alpha * 252,  # 年化
            'beta': beta,
            'information_ratio': information_ratio,
            'tracking_error': tracking_error,
            'excess_return': (s_ret.mean() - b_ret.mean()) * 252,
        }

    def optimize(self, strategy_class: type,
                 param_grid: Dict[str, List],
                 metric: str = "sharpe_ratio",
                 n_jobs: int = -1) -> Tuple[Dict, PerformanceMetrics]:
        """
        参数优化 - 支持并行搜索

        Args:
            strategy_class: 策略类
            param_grid: 参数网格
            metric: 优化目标指标
            n_jobs: 并行进程数，-1使用全部CPU

        Returns:
            (最佳参数, 最佳结果)
        """
        from itertools import product
        from concurrent.futures import ProcessPoolExecutor
        import multiprocessing

        # macOS需设置spawn启动方法
        import sys
        if sys.platform == 'darwin':
            multiprocessing.set_start_method('spawn', force=True)

        # 生成参数组合
        keys = list(param_grid.keys())
        values = list(param_grid.values())
        combinations = list(product(*values))

        logger.info(f"开始参数优化: {len(combinations)}种组合")

        def _eval_params(params_tuple):
            """评估单个参数组合"""
            params = dict(zip(keys, params_tuple))
            try:
                cerebro = Cerebro(self.mode)
                for name, data in self.data_feeds.items():
                    cerebro.add_data(data.data, name)

                strategy = strategy_class(**params)
                cerebro.add_strategy(strategy)

                result = cerebro.run()
                current_metric = getattr(result, metric, -float('inf'))
                return params, current_metric, result
            except Exception as e:
                return params, -float('inf'), None

        best_params = None
        best_metric = -float('inf')
        best_result = None

        # 串行回退（避免macOS进程问题）
        for combo in combinations:
            params, curr_metric, result = _eval_params(combo)
            if curr_metric > best_metric:
                best_metric = curr_metric
                best_params = params
                best_result = result

        logger.info(f"最佳参数: {best_params}, {metric}={best_metric:.4f}")
        return best_params, best_result

    def monte_carlo(self, n_simulations: int = 1000,
                    confidence: float = 0.95) -> Dict[str, float]:
        """
        蒙特卡洛模拟 - 随机打乱交易顺序评估策略鲁棒性

        Args:
            n_simulations: 模拟次数
            confidence: 置信区间

        Returns:
            Dict: 统计结果
        """
        trades = [t for t in self.broker.trades if not t.is_open and hasattr(t, 'pnl')]
        if len(trades) < 10:
            logger.warning("交易次数不足，跳过蒙特卡洛模拟")
            return {}

        pnls = np.array([t.pnl for t in trades])
        n_trades = len(pnls)

        final_equities = []
        for _ in range(n_simulations):
            # 随机打乱交易顺序
            shuffled = np.random.permutation(pnls)
            # 累加计算最终权益
            equity = self.broker.initial_cash + np.cumsum(shuffled)
            final_equities.append(equity[-1])

        final_equities = np.array(final_equities)
        total_return = (final_equities - self.broker.initial_cash) / self.broker.initial_cash

        lower_pct = (1 - confidence) / 2 * 100
        upper_pct = (1 + confidence) / 2 * 100

        return {
            'mean_final_equity': float(np.mean(final_equities)),
            'median_final_equity': float(np.median(final_equities)),
            'std_final_equity': float(np.std(final_equities)),
            'worst_case': float(np.percentile(final_equities, lower_pct)),
            'best_case': float(np.percentile(final_equities, upper_pct)),
            'mean_return': float(np.mean(total_return)),
            'return_ci_lower': float(np.percentile(total_return, lower_pct)),
            'return_ci_upper': float(np.percentile(total_return, upper_pct)),
            'probability_profit': float(np.mean(total_return > 0)),
        }

    def plot(self, output_path: str = None, market: str = "CN"):
        """
        绘制回测结果

        Args:
            output_path: 保存路径
            market: 市场代码（用于标注货币单位）
        """
        try:
            import matplotlib.pyplot as plt
            import matplotlib.dates as mdates

            # 配置中文字体（macOS兼容）
            import platform
            if platform.system() == 'Darwin':  # macOS
                plt.rcParams['font.sans-serif'] = ['Arial Unicode MS', 'PingFang SC', 'STHeiti']
            elif platform.system() == 'Linux':
                plt.rcParams['font.sans-serif'] = ['WenQuanYi Micro Hei', 'Noto Sans CJK SC']
            else:
                plt.rcParams['font.sans-serif'] = ['SimHei', 'Microsoft YaHei']
            plt.rcParams['axes.unicode_minus'] = False

            # 自动创建reports目录
            if output_path:
                Path(output_path).parent.mkdir(parents=True, exist_ok=True)

            currency = {"CN": "CNY", "HK": "HKD", "US": "USD"}.get(market, "CNY")

            fig, axes = plt.subplots(3, 1, figsize=(14, 12))

            # 权益曲线
            ax1 = axes[0]
            equity = pd.Series(self.broker.equity_curve) if self.broker.equity_curve else pd.Series()
            if len(equity) > 0:
                equity.plot(ax=ax1, label='策略权益')
                ax1.axhline(y=self.broker.initial_cash, color='r', linestyle='--', label='初始资金')
                ax1.set_title(f'权益曲线 ({currency})')
                ax1.legend()
                ax1.grid(True)

                # 买卖信号标注
                trades = self.broker.trades
                for t in trades:
                    if hasattr(t, 'entry_price') and t.entry_price > 0:
                        if t.direction == 'long':
                            ax1.scatter([], [], marker='^', color='green', s=100, label='买入')
                        else:
                            ax1.scatter([], [], marker='v', color='red', s=100, label='卖出')

            # 回撤
            ax2 = axes[1]
            if len(equity) > 0:
                cummax = equity.cummax()
                drawdown = (equity - cummax) / cummax
                drawdown.plot(ax=ax2, color='red')
                ax2.fill_between(drawdown.index, drawdown, 0, color='red', alpha=0.3)
                ax2.set_title('回撤曲线')
                ax2.grid(True)

            # 交易分布
            ax3 = axes[2]
            trades = self.broker.trades
            if trades:
                pnls = [t.pnl for t in trades if not t.is_open]
                if pnls:
                    ax3.hist(pnls, bins=30, alpha=0.7)
                    ax3.axvline(x=0, color='r', linestyle='--')
                    ax3.set_title('交易收益分布')
                    ax3.grid(True)

            plt.suptitle(f'QuantSystem Pro 回测报告 - {market}市场', fontsize=14)
            plt.tight_layout()

            if output_path:
                plt.savefig(output_path, dpi=300, bbox_inches='tight')
                logger.info(f"图表已保存: {output_path}")
            else:
                plt.show()

            plt.close()

        except ImportError:
            logger.warning("未安装matplotlib，跳过绘图")
