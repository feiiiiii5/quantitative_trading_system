#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
绩效指标计算模块

从 core/engine.py 提取为独立纯函数，便于复用和测试
新增指标：Omega比率、尾部比率、滚动夏普、月度收益热力图
"""

import numpy as np
import pandas as pd
from typing import List, Dict
from dataclasses import dataclass


@dataclass
class PerformanceMetrics:
    """绩效指标数据类"""
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

    # 高级指标
    kelly_criterion: float = 0.0
    sqn: float = 0.0
    expectancy: float = 0.0
    alpha: float = 0.0
    beta: float = 0.0
    omega_ratio: float = 0.0
    tail_ratio: float = 0.0

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
        print(f"Omega比率:         {self.omega_ratio:>12.2f}")
        print(f"尾部比率:          {self.tail_ratio:>12.2f}")
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


def omega_ratio(returns: pd.Series, threshold: float = 0.0) -> float:
    """
    Omega比率

    数学原理：
    - Omega = E[max(R - threshold, 0)] / E[max(threshold - R, 0)]
    - 衡量收益相对于阈值的上下波动比
    - Omega > 1 表示正期望

    Args:
        returns: 收益率序列
        threshold: 阈值，默认0

    Returns:
        Omega比率
    """
    excess = returns - threshold
    upside = excess[excess > 0].sum()
    downside = -excess[excess < 0].sum()
    return upside / (downside + 1e-8)


def tail_ratio(returns: pd.Series) -> float:
    """
    尾部比率

    数学原理：
    - Tail Ratio = |95%分位数| / |5%分位数|
    - 衡量收益分布的尾部对称性
    - >1 表示右尾更厚（大涨概率高）

    Args:
        returns: 收益率序列

    Returns:
        尾部比率
    """
    upper = np.percentile(returns, 95)
    lower = np.percentile(returns, 5)
    return abs(upper) / (abs(lower) + 1e-8)


def rolling_sharpe(returns: pd.Series, window: int = 252) -> pd.Series:
    """
    滚动夏普比率

    数学原理：
    - Sharpe_t = mean(returns_{t-window:t}) / std(returns_{t-window:t}) * sqrt(252)

    Args:
        returns: 收益率序列
        window: 滚动窗口，默认252天

    Returns:
        滚动夏普序列
    """
    rolling_mean = returns.rolling(window=window).mean()
    rolling_std = returns.rolling(window=window).std()
    return rolling_mean / (rolling_std + 1e-8) * np.sqrt(252)


def monthly_returns_heatmap_data(equity: pd.Series) -> pd.DataFrame:
    """
    月度收益热力图数据

    Args:
        equity: 权益曲线序列

    Returns:
        DataFrame (月 x 年)，单元格为月度收益率
    """
    # 计算日收益率
    returns = equity.pct_change().dropna()

    # 创建年月索引
    df = pd.DataFrame({'returns': returns})
    df['year'] = df.index.year
    df['month'] = df.index.month

    # 按月聚合
    monthly = df.groupby(['year', 'month'])['returns'].apply(lambda x: (1 + x).prod() - 1)

    # 透视表
    heatmap = monthly.unstack(level='month')
    heatmap.columns = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun',
                       'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']
    return heatmap


def performance_attribution(equity: pd.Series, factor_returns: pd.DataFrame) -> Dict:
    """
    绩效归因分析

    将策略收益分解为各因子贡献和残差Alpha

    数学原理：
    - R_p = α + Σ(β_i * F_i) + ε
    - 通过多元线性回归分解收益来源

    Args:
        equity: 策略权益曲线
        factor_returns: 因子收益率DataFrame（列=因子）

    Returns:
        Dict: 各因子贡献、Alpha、R²
    """
    strategy_returns = equity.pct_change().dropna()

    # 对齐日期
    common_idx = strategy_returns.index.intersection(factor_returns.index)
    if len(common_idx) < 30:
        return {'alpha': 0, 'r_squared': 0, 'factor_contrib': {}}

    y = strategy_returns.loc[common_idx].values
    X = factor_returns.loc[common_idx].values

    # 添加常数项（Alpha）
    X_with_const = np.column_stack([np.ones(len(X)), X])

    # 最小二乘回归: y = Xβ + ε
    # β = (X'X)^(-1) X'y
    try:
        beta = np.linalg.lstsq(X_with_const, y, rcond=None)[0]
    except np.linalg.LinAlgError:
        return {'alpha': 0, 'r_squared': 0, 'factor_contrib': {}}

    alpha = beta[0]
    factor_betas = beta[1:]

    # 预测值
    y_pred = X_with_const @ beta

    # R²
    ss_res = np.sum((y - y_pred) ** 2)
    ss_tot = np.sum((y - np.mean(y)) ** 2)
    r_squared = 1 - ss_res / (ss_tot + 1e-8)

    # 各因子贡献（年化）
    factor_contrib = {}
    for i, col in enumerate(factor_returns.columns):
        contrib = factor_betas[i] * factor_returns[col].mean() * 252
        factor_contrib[col] = contrib

    return {
        'alpha': alpha * 252,  # 年化Alpha
        'r_squared': r_squared,
        'factor_betas': dict(zip(factor_returns.columns, factor_betas)),
        'factor_contrib': factor_contrib,
        'residual_std': np.std(y - y_pred) * np.sqrt(252),
    }


def calculate_metrics(equity_curve: List[float], returns: List[float],
                     trades: List = None) -> PerformanceMetrics:
    """
    计算完整绩效指标

    Args:
        equity_curve: 权益曲线列表
        returns: 收益率列表
        trades: 交易记录列表（可选）

    Returns:
        PerformanceMetrics 对象
    """
    metrics = PerformanceMetrics()

    equity_series = pd.Series(equity_curve)
    returns_series = pd.Series(returns)

    if len(equity_series) < 2:
        return metrics

    # 基础收益指标
    metrics.total_return = (equity_series.iloc[-1] / equity_series.iloc[0]) - 1

    n_years = len(equity_series) / 252
    if n_years > 0:
        metrics.cagr = (1 + metrics.total_return) ** (1 / n_years) - 1
        metrics.annual_return = metrics.cagr

    # 风险指标
    metrics.volatility = returns_series.std() * np.sqrt(252)

    if metrics.volatility > 0:
        metrics.sharpe_ratio = metrics.annual_return / metrics.volatility

    # 最大回撤
    cummax = equity_series.cummax()
    drawdown = (equity_series - cummax) / cummax
    metrics.max_drawdown = drawdown.min()
    metrics.avg_drawdown = drawdown[drawdown < 0].mean()

    # 回撤持续期
    is_dd = drawdown < 0
    dd_periods = []
    current = 0
    for val in is_dd:
        if val:
            current += 1
        else:
            if current > 0:
                dd_periods.append(current)
            current = 0
    if current > 0:
        dd_periods.append(current)

    if dd_periods:
        metrics.max_drawdown_duration = max(dd_periods)

    # Sortino比率
    downside = returns_series[returns_series < 0]
    if len(downside) > 0 and downside.std() > 0:
        metrics.sortino_ratio = metrics.annual_return / (downside.std() * np.sqrt(252))

    # Calmar比率
    if metrics.max_drawdown != 0:
        metrics.calmar_ratio = metrics.annual_return / abs(metrics.max_drawdown)

    # Omega比率
    metrics.omega_ratio = omega_ratio(returns_series)

    # 尾部比率
    metrics.tail_ratio = tail_ratio(returns_series)

    # 交易统计
    if trades:
        metrics.total_trades = len(trades)
        pnls = [t.pnl for t in trades if hasattr(t, 'pnl') and not getattr(t, 'is_open', False)]
        if pnls:
            wins = [p for p in pnls if p > 0]
            losses = [p for p in pnls if p < 0]

            metrics.win_rate = len(wins) / len(pnls) if pnls else 0
            metrics.profit_factor = abs(sum(wins) / sum(losses)) if losses else float('inf')
            metrics.avg_trade = np.mean(pnls)
            metrics.best_trade = max(pnls) if pnls else 0
            metrics.worst_trade = min(pnls) if pnls else 0

            # SQN
            if len(pnls) > 1:
                std_pnl = np.std(pnls)
                if std_pnl > 0:
                    metrics.sqn = (np.mean(pnls) / std_pnl) * np.sqrt(len(pnls))

            # 凯利准则
            if metrics.win_rate > 0 and metrics.profit_factor > 0:
                metrics.kelly_criterion = metrics.win_rate - (1 - metrics.win_rate) / metrics.profit_factor

    # Bootstrap指标
    if len(returns_series) > 30:
        bootstrap_sharpes = []
        for _ in range(100):
            sample = returns_series.sample(n=len(returns_series), replace=True)
            if sample.std() > 0:
                bs_sharpe = sample.mean() / sample.std() * np.sqrt(252)
                bootstrap_sharpes.append(bs_sharpe)

        if bootstrap_sharpes:
            metrics.bootstrap_sharpe_mean = np.mean(bootstrap_sharpes)
            metrics.bootstrap_sharpe_std = np.std(bootstrap_sharpes)
            metrics.bootstrap_var_95 = np.percentile(bootstrap_sharpes, 5)

    return metrics
