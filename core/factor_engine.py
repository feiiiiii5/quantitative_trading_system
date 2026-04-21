#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
因子引擎模块

提供多因子模型的计算、分析和合成：
- 动量因子：多周期收益率（截面标准化）
- 质量因子：夏普比率代理
- 价值因子：52周价格偏离度反转
- IC分析：因子预测能力评估
- 中性化：去除行业和市值影响
- 因子合成：加权组合多个因子
"""

import numpy as np
import pandas as pd
from typing import Dict, List, Optional
from scipy import stats


class FactorEngine:
    """因子引擎：计算、分析和合成Alpha因子"""

    @staticmethod
    def compute_momentum(close: pd.Series, periods: List[int] = None) -> pd.DataFrame:
        """
        多周期动量因子（截面标准化）

        数学原理：
        - 动量 = (P_t - P_{t-n}) / P_{t-n}
        - 截面标准化：z-score = (x - μ) / σ，使不同股票可比

        Args:
            close: 收盘价序列
            periods: 计算周期列表，默认 [5, 10, 20, 60]

        Returns:
            DataFrame，每列为一个周期的标准化动量因子
        """
        if periods is None:
            periods = [5, 10, 20, 60]

        momentum = pd.DataFrame(index=close.index)
        for p in periods:
            # 计算p期收益率
            ret = close.pct_change(p)
            # 截面标准化（去均值除标准差）
            momentum[f'mom_{p}'] = (ret - ret.mean()) / (ret.std() + 1e-8)
        return momentum

    @staticmethod
    def compute_quality(close: pd.Series, volume: pd.Series) -> pd.Series:
        """
        质量因子：夏普比率代理（20日均收益/波动率）

        数学原理：
        - 质量 = mean(returns) / std(returns)
        - 高均值低波动 = 高质量

        Args:
            close: 收盘价序列
            volume: 成交量序列

        Returns:
            质量因子序列
        """
        returns = close.pct_change()
        mean_ret = returns.rolling(window=20).mean()
        std_ret = returns.rolling(window=20).std()
        quality = mean_ret / (std_ret + 1e-8)
        return quality

    @staticmethod
    def compute_value(close: pd.Series, window: int = 252) -> pd.Series:
        """
        价值因子：52周价格偏离度的反转

        数学原理：
        - 偏离度 = (当前价 - 最高价) / (最高价 - 最低价)
        - 偏离度越低 = 越"便宜" = 价值越高

        Args:
            close: 收盘价序列
            window: 回看窗口，默认252（约52周）

        Returns:
            价值因子序列（低偏离度=高价值）
        """
        high = close.rolling(window=window).max()
        low = close.rolling(window=window).min()
        # 归一化偏离度：0=最低，1=最高
        deviation = (close - low) / (high - low + 1e-8)
        # 反转：低偏离度=高价值
        value = 1 - deviation
        return value

    @staticmethod
    def ic_analysis(factor: pd.Series, forward_returns: pd.Series, window: int = 20) -> Dict:
        """
        滚动IC/ICIR分析

        数学原理：
        - IC = corr(factor_t, return_{t+1})：因子与下期收益的相关系数
        - ICIR = mean(IC) / std(IC)：信息比率，衡量因子稳定性
        - |IC| > 0.03 通常认为有预测能力

        Args:
            factor: 因子值序列
            forward_returns: 未来一期收益序列
            window: 滚动窗口

        Returns:
            {'ic_series': IC序列, 'ic_mean': IC均值, 'ic_std': IC标准差, 'icir': ICIR}
        """
        # 对齐数据
        aligned_factor, aligned_returns = factor.align(forward_returns, join='inner')

        # 滚动IC（Spearman秩相关系数，更稳健）
        # pandas新版不支持method参数，手动计算
        def _rolling_spearman(x, y, window):
            """滚动Spearman相关系数"""
            result = pd.Series(index=x.index, dtype=float)
            for i in range(window - 1, len(x)):
                xi = x.iloc[i - window + 1:i + 1]
                yi = y.iloc[i - window + 1:i + 1]
                if len(xi.dropna()) < window * 0.5:
                    result.iloc[i] = np.nan
                    continue
                # 计算秩次
                rank_x = xi.rank()
                rank_y = yi.rank()
                # Pearson相关系数（秩次）
                result.iloc[i] = rank_x.corr(rank_y)
            return result

        ic_series = _rolling_spearman(aligned_factor, aligned_returns, window)

        ic_mean = ic_series.mean()
        ic_std = ic_series.std()
        icir = ic_mean / (ic_std + 1e-8)

        return {
            'ic_series': ic_series,
            'ic_mean': ic_mean,
            'ic_std': ic_std,
            'icir': icir
        }

    @staticmethod
    def neutralize(factor: pd.Series, groups: Optional[pd.Series] = None) -> pd.Series:
        """
        行业/市值中性化（截面去均值标准化）

        数学原理：
        - 去均值：factor - mean(factor)
        - 标准化：/ std(factor)
        - 分组中性化：在每个组内分别去均值

        Args:
            factor: 原始因子序列
            groups: 分组标签（如行业分类），None则整体中性化

        Returns:
            中性化后的因子
        """
        if groups is None:
            # 整体中性化
            return (factor - factor.mean()) / (factor.std() + 1e-8)
        else:
            # 分组中性化
            neutralized = pd.Series(index=factor.index, dtype=float)
            for group in groups.unique():
                mask = groups == group
                group_factor = factor[mask]
                neutralized[mask] = (group_factor - group_factor.mean()) / (group_factor.std() + 1e-8)
            return neutralized

    @staticmethod
    def combine_factors(factors: Dict[str, pd.Series], weights: Dict[str, float]) -> pd.Series:
        """
        加权合成复合因子

        数学原理：
        - 复合因子 = Σ(weight_i * factor_i)
        - 要求各因子已标准化，使权重可比

        Args:
            factors: 因子字典 {名称: 序列}
            weights: 权重字典 {名称: 权重}

        Returns:
            合成后的复合因子
        """
        combined = pd.Series(0.0, index=list(factors.values())[0].index)
        total_weight = 0.0

        for name, factor in factors.items():
            w = weights.get(name, 0.0)
            combined += w * factor
            total_weight += abs(w)

        # 归一化
        if total_weight > 0:
            combined /= total_weight

        return combined
