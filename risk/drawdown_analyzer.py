#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
回撤分析模块

- 水下曲线
- 回撤区间分析
- 平均恢复时间
- 痛苦指数
"""

import numpy as np
import pandas as pd
from typing import List, Dict, Tuple


class DrawdownAnalyzer:
    """回撤分析器"""

    @staticmethod
    def underwater_curve(equity: pd.Series) -> pd.Series:
        """
        水下曲线（回撤曲线）

        Args:
            equity: 权益曲线

        Returns:
            回撤序列（负值）
        """
        cummax = equity.cummax()
        return (equity - cummax) / cummax

    @staticmethod
    def drawdown_periods(equity: pd.Series) -> List[Dict]:
        """
        所有回撤区间

        Returns:
            List[Dict]: 每个回撤区间的开始/底部/恢复时间
        """
        dd = DrawdownAnalyzer.underwater_curve(equity)
        is_dd = dd < 0

        periods = []
        in_dd = False
        start_idx = None
        bottom_idx = None
        bottom_value = 0

        for i, (idx, val) in enumerate(dd.items()):
            if val < 0 and not in_dd:
                # 回撤开始
                in_dd = True
                start_idx = idx
                bottom_idx = idx
                bottom_value = val
            elif val < 0 and in_dd:
                # 更新底部
                if val < bottom_value:
                    bottom_idx = idx
                    bottom_value = val
            elif val == 0 and in_dd:
                # 回撤恢复
                in_dd = False
                periods.append({
                    'start': start_idx,
                    'bottom': bottom_idx,
                    'recovery': idx,
                    'max_drawdown': bottom_value,
                    'duration': (idx - start_idx).days if hasattr(idx, 'day') else i,
                })

        # 未结束的回撤
        if in_dd:
            periods.append({
                'start': start_idx,
                'bottom': bottom_idx,
                'recovery': None,
                'max_drawdown': bottom_value,
                'duration': (dd.index[-1] - start_idx).days if hasattr(start_idx, 'day') else len(dd) - 1,
            })

        return periods

    @staticmethod
    def avg_recovery_time(equity: pd.Series) -> float:
        """
        平均恢复时间（天）

        Args:
            equity: 权益曲线

        Returns:
            平均恢复天数
        """
        periods = DrawdownAnalyzer.drawdown_periods(equity)
        completed = [p for p in periods if p['recovery'] is not None]

        if not completed:
            return 0.0

        durations = [p['duration'] for p in completed]
        return np.mean(durations)

    @staticmethod
    def pain_index(equity: pd.Series) -> float:
        """
        痛苦指数（水下曲线面积）

        数学原理：
        - Pain Index = mean(|underwater_curve|)
        - 衡量持续回撤的平均深度

        Args:
            equity: 权益曲线

        Returns:
            痛苦指数
        """
        dd = DrawdownAnalyzer.underwater_curve(equity)
        underwater = dd[dd < 0]

        if len(underwater) == 0:
            return 0.0

        return abs(underwater.mean())

    @staticmethod
    def calmar_ratio(equity: pd.Series, window: int = 36) -> float:
        """
        Calmar比率（基于最大回撤）

        Args:
            equity: 权益曲线
            window: 计算窗口（月）

        Returns:
            Calmar比率
        """
        if len(equity) < window * 21:
            window = len(equity) // 21

        if window <= 0:
            return 0.0

        # 年化收益率
        total_ret = (equity.iloc[-1] / equity.iloc[-window * 21]) - 1
        annual_ret = total_ret * (12 / window)

        # 窗口内最大回撤
        recent = equity.iloc[-window * 21:]
        cummax = recent.cummax()
        max_dd = ((recent - cummax) / cummax).min()

        if max_dd == 0:
            return 0.0

        return annual_ret / abs(max_dd)

    @staticmethod
    def full_report(equity: pd.Series) -> Dict:
        """
        完整回撤分析报告

        Args:
            equity: 权益曲线

        Returns:
            Dict: 所有回撤指标
        """
        dd = DrawdownAnalyzer.underwater_curve(equity)
        periods = DrawdownAnalyzer.drawdown_periods(equity)

        return {
            'max_drawdown': dd.min(),
            'max_drawdown_duration': max((p['duration'] for p in periods), default=0),
            'avg_drawdown': dd[dd < 0].mean(),
            'drawdown_count': len(periods),
            'avg_recovery_time': DrawdownAnalyzer.avg_recovery_time(equity),
            'pain_index': DrawdownAnalyzer.pain_index(equity),
            'calmar_ratio': DrawdownAnalyzer.calmar_ratio(equity),
            'periods': periods,
        }
