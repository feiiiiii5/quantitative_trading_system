#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
高级风险管理与资金管理模块

包含：
- 动态仓位管理（凯利公式、波动率目标）
- 多维度风控体系（市场、信用、流动性）
- 组合风险监控（VaR、CVaR、压力测试）
- 止损止盈动态调整
"""

import numpy as np
import pandas as pd
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
import warnings

from utils.logger import get_logger

logger = get_logger(__name__)


class RiskLevel(Enum):
    """风险等级"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class RiskType(Enum):
    """风险类型"""
    MARKET = "market"           # 市场风险
    CREDIT = "credit"           # 信用风险
    LIQUIDITY = "liquidity"     # 流动性风险
    OPERATIONAL = "operational" # 操作风险
    SYSTEMIC = "systemic"       # 系统性风险


@dataclass
class RiskMetrics:
    """风险指标"""
    var_95: float = 0.0           # 95% VaR
    var_99: float = 0.0           # 99% VaR
    cvar_95: float = 0.0          # 95% CVaR
    cvar_99: float = 0.0          # 99% CVaR
    volatility: float = 0.0       # 波动率
    beta: float = 1.0             # Beta系数
    correlation: float = 0.0      # 相关性
    tail_risk: float = 0.0        # 尾部风险


@dataclass
class PositionConfig:
    """仓位配置"""
    max_position: float = 1.0     # 最大仓位
    min_position: float = 0.0     # 最小仓位
    position_step: float = 0.1    # 仓位调整步长
    rebalance_threshold: float = 0.05  # 再平衡阈值


@dataclass
class RiskConfig:
    """风险配置"""
    # 基础风控
    max_position_per_stock: float = 0.2
    max_total_position: float = 0.8
    stop_loss: float = 0.05
    take_profit: float = 0.15
    max_drawdown: float = 0.2
    
    # 高级风控
    max_leverage: float = 2.0
    max_turnover: float = 0.5
    max_concentration: float = 0.3
    max_correlation: float = 0.8
    
    # 资金管理
    kelly_fraction: float = 0.5   # 凯利公式分数
    volatility_target: float = 0.15  # 波动率目标
    risk_budget: float = 0.02     # 风险预算
    
    # 动态调整
    enable_dynamic_stop: bool = True
    enable_trailing_stop: bool = True
    trailing_stop_distance: float = 0.1


class PositionSizer:
    """
    仓位管理器
    
    支持多种仓位管理方法：
    - 固定分数法
    - 凯利公式
    - 波动率目标法
    - 风险平价法
    """
    
    def __init__(self, config: RiskConfig = None):
        self.config = config or RiskConfig()
        self.position_history = []
    
    def fixed_fraction(
        self,
        capital: float,
        price: float,
        stop_loss_pct: float,
        risk_fraction: float = 0.02
    ) -> float:
        """
        固定分数仓位管理
        
        Args:
            capital: 总资金
            price: 当前价格
            stop_loss_pct: 止损比例
            risk_fraction: 每笔交易风险占总资金比例
        
        Returns:
            应买入的股数
        """
        risk_amount = capital * risk_fraction
        stop_loss_amount = price * stop_loss_pct
        
        if stop_loss_amount <= 0:
            return 0
        
        shares = risk_amount / stop_loss_amount
        max_shares = (capital * self.config.max_position_per_stock) / price
        
        return min(shares, max_shares)
    
    def kelly_criterion(
        self,
        win_rate: float,
        avg_win: float,
        avg_loss: float,
        fraction: float = None
    ) -> float:
        """
        凯利公式仓位管理
        
        f* = (p*b - q) / b
        其中：p=胜率, q=败率, b=盈亏比
        
        Args:
            win_rate: 胜率
            avg_win: 平均盈利
            avg_loss: 平均亏损
            fraction: 凯利分数（默认使用配置值）
        
        Returns:
            建议仓位比例
        """
        if avg_loss == 0:
            return 0
        
        win_loss_ratio = avg_win / avg_loss
        loss_rate = 1 - win_rate
        
        # 凯利公式
        kelly_pct = (win_rate * win_loss_ratio - loss_rate) / win_loss_ratio
        
        # 应用凯利分数（通常使用半凯利或四分之一凯利）
        fraction = fraction or self.config.kelly_fraction
        position_pct = kelly_pct * fraction
        
        # 限制在合理范围内
        return max(0, min(position_pct, self.config.max_position_per_stock))
    
    def volatility_targeting(
        self,
        returns: pd.Series,
        target_volatility: float = None
    ) -> float:
        """
        波动率目标仓位管理
        
        根据历史波动率动态调整仓位，使组合波动率接近目标值
        
        Args:
            returns: 历史收益率序列
            target_volatility: 目标年化波动率
        
        Returns:
            建议仓位比例
        """
        target_vol = target_volatility or self.config.volatility_target
        
        if len(returns) < 20:
            return self.config.max_position_per_stock
        
        # 计算历史波动率（年化）
        hist_vol = returns.std() * np.sqrt(252)
        
        if hist_vol <= 0:
            return self.config.max_position_per_stock
        
        # 计算目标仓位
        position_pct = target_vol / hist_vol
        
        return max(0, min(position_pct, self.config.max_position_per_stock))
    
    def risk_parity(
        self,
        returns: pd.DataFrame,
        risk_budget: float = None
    ) -> pd.Series:
        """
        风险平价仓位分配
        
        使每个资产对组合风险的贡献相等
        
        Args:
            returns: 各资产收益率DataFrame
            risk_budget: 风险预算
        
        Returns:
            各资产权重
        """
        risk_budget = risk_budget or self.config.risk_budget
        
        # 计算协方差矩阵
        cov_matrix = returns.cov()
        
        # 计算各资产波动率
        vols = returns.std()
        
        # 风险平价权重（简化版：与波动率成反比）
        inv_vols = 1 / vols
        weights = inv_vols / inv_vols.sum()
        
        # 归一化
        weights = weights / weights.sum()
        
        return weights
    
    def dynamic_position_adjustment(
        self,
        current_position: float,
        signal_strength: float,
        market_regime: str,
        volatility: float
    ) -> float:
        """
        动态仓位调整
        
        根据市场状态和信号强度动态调整仓位
        
        Args:
            current_position: 当前仓位
            signal_strength: 信号强度 (0-1)
            market_regime: 市场状态
            volatility: 当前波动率
        
        Returns:
            调整后的仓位
        """
        # 基础仓位
        base_position = signal_strength * self.config.max_position_per_stock
        
        # 根据市场状态调整
        regime_multiplier = {
            'bull': 1.2,
            'bear': 0.5,
            'high_vol': 0.6,
            'low_vol': 1.0,
            'trending': 1.1,
            'mean_revert': 0.8,
        }.get(market_regime, 1.0)
        
        # 根据波动率调整
        vol_threshold = 0.2  # 20%年化波动率
        vol_multiplier = min(1.0, vol_threshold / (volatility + 0.001))
        
        # 计算目标仓位
        target_position = base_position * regime_multiplier * vol_multiplier
        
        # 平滑过渡
        adjustment_speed = 0.3  # 调整速度
        new_position = current_position + (target_position - current_position) * adjustment_speed
        
        # 限制范围
        return max(self.config.min_position, min(new_position, self.config.max_position_per_stock))

    def optimal_f(self, returns: pd.Series) -> float:
        """
        最优f值计算（Ralph Vince）

        遍历f∈[0.01,1.0]步长0.01，计算每个f下的TWR，
        返回最大TWR对应的f值

        Args:
            returns: 历史收益率序列

        Returns:
            最优f值
        """
        if len(returns) < 10:
            return 0.0

        # 转换为盈亏比（相对于最大亏损）
        trades = returns.dropna().values
        max_loss = abs(trades.min()) if trades.min() < 0 else 1e-8
        hpr = 1 + trades / max_loss  # Holding Period Returns

        best_f = 0.0
        best_twr = 0.0

        for f in np.arange(0.01, 1.01, 0.01):
            # TWR = ∏(1 + f * (-trade/max_loss))
            twr = np.prod(1 + f * (-trades / max_loss))
            if twr > best_twr:
                best_twr = twr
                best_f = f

        return round(best_f, 2)


class AdvancedRiskManager:
    """
    高级风险管理器
    
    提供全面的风险控制功能：
    - 多维度风险评估
    - 动态止损止盈
    - 组合风险监控
    - 压力测试
    """
    
    def __init__(self, config: RiskConfig = None):
        self.config = config or RiskConfig()
        self.position_sizer = PositionSizer(config)
        
        # 风险状态
        self.current_risk_level = RiskLevel.LOW
        self.risk_metrics = RiskMetrics()
        
        # 持仓监控
        self.positions = {}
        self.entry_prices = {}
        self.highest_prices = {}  # 用于追踪止损
        self.stop_loss_prices = {}
        self.take_profit_prices = {}
        
        # 风险事件记录
        self.risk_events = []
        
        logger.info("高级风险管理器初始化完成")
    
    def calculate_risk_metrics(
        self,
        returns: pd.Series,
        benchmark_returns: pd.Series = None
    ) -> RiskMetrics:
        """
        计算风险指标
        
        Args:
            returns: 策略收益率序列
            benchmark_returns: 基准收益率序列
        
        Returns:
            RiskMetrics
        """
        metrics = RiskMetrics()
        
        if len(returns) < 30:
            return metrics
        
        # VaR计算（历史模拟法）
        metrics.var_95 = np.percentile(returns, 5)
        metrics.var_99 = np.percentile(returns, 1)
        
        # CVaR计算
        metrics.cvar_95 = returns[returns <= metrics.var_95].mean()
        metrics.cvar_99 = returns[returns <= metrics.var_99].mean()
        
        # 波动率
        metrics.volatility = returns.std() * np.sqrt(252)
        
        # Beta系数
        if benchmark_returns is not None and len(benchmark_returns) == len(returns):
            covariance = np.cov(returns, benchmark_returns)[0, 1]
            benchmark_var = benchmark_returns.var()
            if benchmark_var > 0:
                metrics.beta = covariance / benchmark_var
        
        # 尾部风险（偏度）
        metrics.tail_risk = returns.skew()
        
        self.risk_metrics = metrics
        return metrics
    
    def check_position_risk(
        self,
        symbol: str,
        current_price: float,
        position_size: float,
        portfolio_value: float
    ) -> Tuple[bool, str]:
        """
        检查持仓风险
        
        Returns:
            (是否通过检查, 风险信息)
        """
        # 检查单只持仓上限
        position_value = position_size * current_price
        position_ratio = position_value / portfolio_value if portfolio_value > 0 else 0
        
        if position_ratio > self.config.max_position_per_stock:
            return False, f"单只持仓超限: {position_ratio:.2%} > {self.config.max_position_per_stock:.2%}"
        
        # 检查止损
        if symbol in self.entry_prices:
            entry_price = self.entry_prices[symbol]
            loss_pct = (current_price - entry_price) / entry_price
            
            if loss_pct < -self.config.stop_loss:
                return False, f"触发止损: 亏损{loss_pct:.2%}"
        
        # 检查止盈
        if symbol in self.take_profit_prices:
            if current_price >= self.take_profit_prices[symbol]:
                return False, "触发止盈"
        
        return True, "风险检查通过"
    
    def update_trailing_stop(
        self,
        symbol: str,
        current_price: float
    ) -> Optional[float]:
        """
        更新追踪止损价格
        
        Args:
            symbol: 股票代码
            current_price: 当前价格
        
        Returns:
            新的止损价格（如有更新）
        """
        if not self.config.enable_trailing_stop:
            return None
        
        # 更新最高价
        if symbol not in self.highest_prices:
            self.highest_prices[symbol] = current_price
        else:
            self.highest_prices[symbol] = max(self.highest_prices[symbol], current_price)
        
        # 计算追踪止损价格
        highest = self.highest_prices[symbol]
        trailing_stop_price = highest * (1 - self.config.trailing_stop_distance)
        
        # 更新止损价格（只上调不下调）
        if symbol not in self.stop_loss_prices:
            self.stop_loss_prices[symbol] = trailing_stop_price
        else:
            self.stop_loss_prices[symbol] = max(
                self.stop_loss_prices[symbol],
                trailing_stop_price
            )
        
        return self.stop_loss_prices[symbol]
    
    def check_portfolio_risk(
        self,
        portfolio_value: float,
        peak_value: float,
        total_position_ratio: float
    ) -> Tuple[bool, RiskLevel, str]:
        """
        检查组合风险
        
        Returns:
            (是否继续交易, 风险等级, 风险信息)
        """
        # 计算回撤
        if peak_value > 0:
            drawdown = (peak_value - portfolio_value) / peak_value
        else:
            drawdown = 0
        
        # 确定风险等级
        if drawdown > self.config.max_drawdown * 1.5:
            risk_level = RiskLevel.CRITICAL
            can_trade = False
            message = f"严重回撤: {drawdown:.2%}，暂停交易"
        elif drawdown > self.config.max_drawdown:
            risk_level = RiskLevel.HIGH
            can_trade = False
            message = f"触及最大回撤: {drawdown:.2%}"
        elif total_position_ratio > self.config.max_total_position:
            risk_level = RiskLevel.HIGH
            can_trade = False
            message = f"总仓位超限: {total_position_ratio:.2%}"
        elif drawdown > self.config.max_drawdown * 0.7:
            risk_level = RiskLevel.MEDIUM
            can_trade = True
            message = f"回撤警告: {drawdown:.2%}"
        else:
            risk_level = RiskLevel.LOW
            can_trade = True
            message = "风险正常"
        
        self.current_risk_level = risk_level
        
        # 记录风险事件
        if risk_level in [RiskLevel.HIGH, RiskLevel.CRITICAL]:
            self.risk_events.append({
                'timestamp': datetime.now(),
                'level': risk_level.value,
                'message': message,
                'drawdown': drawdown
            })
        
        return can_trade, risk_level, message
    
    def stress_test(
        self,
        returns: pd.Series,
        scenarios: Dict[str, float] = None
    ) -> Dict[str, float]:
        """
        压力测试
        
        Args:
            returns: 历史收益率
            scenarios: 压力情景（如：{'market_crash': -0.3}）
        
        Returns:
            各情景下的预期损失
        """
        if scenarios is None:
            scenarios = {
                'minor_correction': -0.1,    # 小幅回调
                'market_crash': -0.3,         # 市场崩盘
                'black_swan': -0.5,           # 黑天鹅事件
                'high_volatility': 0.4,       # 高波动
            }
        
        results = {}
        
        for scenario_name, shock in scenarios.items():
            # 计算在压力情景下的VaR
            stressed_returns = returns + shock
            var = np.percentile(stressed_returns, 5)
            results[scenario_name] = var
        
        return results
    
    def get_risk_report(self) -> Dict:
        """获取风险报告"""
        return {
            'current_risk_level': self.current_risk_level.value,
            'risk_metrics': {
                'var_95': self.risk_metrics.var_95,
                'var_99': self.risk_metrics.var_99,
                'cvar_95': self.risk_metrics.cvar_95,
                'volatility': self.risk_metrics.volatility,
                'beta': self.risk_metrics.beta,
            },
            'positions': len(self.positions),
            'risk_events_24h': len([
                e for e in self.risk_events
                if e['timestamp'] > datetime.now() - timedelta(hours=24)
            ]),
        }
    
    def component_var(self, weights: np.ndarray, cov_matrix: np.ndarray,
                      confidence: float = 0.95) -> np.ndarray:
        """
        成分VaR：各资产对组合总VaR的贡献量

        数学原理：
        - 组合VaR = z * σ_p
        - 边际VaR = z * (Σw) / σ_p
        - 成分VaR = w * 边际VaR

        Args:
            weights: 资产权重数组
            cov_matrix: 协方差矩阵
            confidence: 置信度，默认95%

        Returns:
            各资产的成分VaR数组
        """
        from scipy import stats
        z = stats.norm.ppf(1 - confidence)
        port_vol = np.sqrt(weights @ cov_matrix @ weights)
        marginal = z * (cov_matrix @ weights) / port_vol
        return weights * marginal

    def dynamic_leverage(self, returns: pd.Series, target_vol: float = 0.15,
                         lookback: int = 20) -> float:
        """
        波动率目标法：实时调整杠杆使组合波动率贴近目标

        数学原理：
        - 实现波动率 RV = std(returns) * sqrt(252)
        - 目标杠杆 = target_vol / RV
        - 限制最大杠杆不超过配置值

        Args:
            returns: 历史收益率序列
            target_vol: 目标年化波动率，默认15%
            lookback: 回看窗口，默认20天

        Returns:
            建议杠杆倍数
        """
        rv = returns.tail(lookback).std() * np.sqrt(252)
        return min(target_vol / rv if rv > 1e-6 else 1.0, self.config.max_leverage)

    def correlation_monitor(self, returns_df: pd.DataFrame,
                            threshold: float = None) -> dict:
        """
        持仓相关性监控

        计算两两相关性，超阈值时触发降相关信号

        Args:
            returns_df: 各资产收益率DataFrame（列=资产）
            threshold: 相关性阈值（默认使用配置值）

        Returns:
            dict: 相关性矩阵、超标组合、是否触发
        """
        threshold = threshold or self.config.max_correlation

        if returns_df.empty or len(returns_df.columns) < 2:
            return {'triggered': False, 'correlation_matrix': None}

        corr_matrix = returns_df.corr()

        # 找出超阈值组合（排除对角线）
        high_corr_pairs = []
        for i in range(len(corr_matrix.columns)):
            for j in range(i + 1, len(corr_matrix.columns)):
                corr_val = corr_matrix.iloc[i, j]
                if abs(corr_val) > threshold:
                    high_corr_pairs.append({
                        'asset1': corr_matrix.columns[i],
                        'asset2': corr_matrix.columns[j],
                        'correlation': corr_val
                    })

        triggered = len(high_corr_pairs) > 0

        if triggered:
            logger.warning(f"相关性监控触发: {len(high_corr_pairs)} 对资产相关性超阈值")
            self.risk_events.append({
                'timestamp': datetime.now(),
                'level': RiskLevel.MEDIUM.value,
                'message': f"高相关性警报: {len(high_corr_pairs)} 对",
                'details': high_corr_pairs
            })

        return {
            'triggered': triggered,
            'correlation_matrix': corr_matrix,
            'high_corr_pairs': high_corr_pairs,
            'threshold': threshold,
        }

    def reset(self):
        """重置风险状态"""
        self.positions.clear()
        self.entry_prices.clear()
        self.highest_prices.clear()
        self.stop_loss_prices.clear()
        self.take_profit_prices.clear()
        self.risk_events.clear()
        self.current_risk_level = RiskLevel.LOW
        logger.info("风险管理器已重置")


class CapitalManager:
    """
    资金管理器
    
    管理整体资金的分配和使用：
    - 资金分配策略
    - 现金流管理
    - 保证金管理
    """
    
    def __init__(self, initial_capital: float = 1000000):
        self.initial_capital = initial_capital
        self.current_capital = initial_capital
        self.available_cash = initial_capital
        
        # 资金分配
        self.strategy_allocations = {}
        self.asset_allocations = {}
        
        # 记录
        self.cash_flows = []
        
        logger.info(f"资金管理器初始化，初始资金: {initial_capital:,.2f}")
    
    def allocate_to_strategy(
        self,
        strategy_name: str,
        allocation_pct: float
    ) -> float:
        """
        分配资金给策略
        
        Args:
            strategy_name: 策略名称
            allocation_pct: 分配比例
        
        Returns:
            分配金额
        """
        allocation_amount = self.current_capital * allocation_pct
        self.strategy_allocations[strategy_name] = allocation_amount
        
        logger.info(f"策略 '{strategy_name}' 分配资金: {allocation_amount:,.2f}")
        return allocation_amount
    
    def calculate_available_capital(
        self,
        reserved_pct: float = 0.1
    ) -> float:
        """
        计算可用资金
        
        Args:
            reserved_pct: 预留资金比例
        
        Returns:
            可用资金
        """
        reserved = self.current_capital * reserved_pct
        return max(0, self.available_cash - reserved)
    
    def record_cash_flow(
        self,
        amount: float,
        flow_type: str,
        description: str = ""
    ):
        """记录现金流"""
        self.cash_flows.append({
            'timestamp': datetime.now(),
            'amount': amount,
            'type': flow_type,
            'description': description,
            'balance': self.available_cash
        })
        
        self.available_cash += amount
        self.current_capital += amount
    
    def get_capital_report(self) -> Dict:
        """获取资金报告"""
        return {
            'initial_capital': self.initial_capital,
            'current_capital': self.current_capital,
            'available_cash': self.available_cash,
            'total_return': (self.current_capital / self.initial_capital) - 1,
            'strategy_allocations': self.strategy_allocations,
            'recent_cash_flows': self.cash_flows[-10:] if self.cash_flows else []
        }
