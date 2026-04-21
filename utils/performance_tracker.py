#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
滚动绩效监控模块

每N根K线输出一次实时指标快照，支持预警阈值配置
"""

import numpy as np
import pandas as pd
from typing import Dict, Optional
from dataclasses import dataclass


@dataclass
class AlertConfig:
    """预警配置"""
    max_drawdown_threshold: float = -0.10  # 最大回撤预警
    min_sharpe_threshold: float = 0.5      # 最小夏普预警
    max_volatility_threshold: float = 0.30  # 最大波动率预警


class PerformanceTracker:
    """滚动绩效监控器"""

    def __init__(self, snapshot_interval: int = 20, alert_config: AlertConfig = None):
        """
        Args:
            snapshot_interval: 每N根K线输出一次快照
            alert_config: 预警配置
        """
        self.snapshot_interval = snapshot_interval
        self.alert_config = alert_config or AlertConfig()
        self.snapshots: list = []
        self.alert_history: list = []

    def update(self, equity: float, timestamp, bar_count: int):
        """
        更新权益并检查是否需要输出快照

        Args:
            equity: 当前权益
            timestamp: 时间戳
            bar_count: 当前K线计数
        """
        self.snapshots.append({
            'timestamp': timestamp,
            'equity': equity,
            'bar_count': bar_count,
        })

        if bar_count % self.snapshot_interval == 0 and bar_count > 0:
            self._print_snapshot()

    def _print_snapshot(self):
        """输出绩效快照"""
        if len(self.snapshots) < 2:
            return

        recent = self.snapshots[-self.snapshot_interval:]
        equities = [s['equity'] for s in recent]

        # 计算指标
        returns = pd.Series(equities).pct_change().dropna()
        total_ret = (equities[-1] / equities[0]) - 1
        volatility = returns.std() * np.sqrt(252) if len(returns) > 1 else 0
        sharpe = (returns.mean() / (returns.std() + 1e-8)) * np.sqrt(252) if len(returns) > 1 else 0

        # 最大回撤
        eq_series = pd.Series(equities)
        cummax = eq_series.cummax()
        max_dd = ((eq_series - cummax) / cummax).min()

        snapshot = {
            'timestamp': recent[-1]['timestamp'],
            'total_return': total_ret,
            'volatility': volatility,
            'sharpe_ratio': sharpe,
            'max_drawdown': max_dd,
            'bars': len(recent),
        }

        print(f"\n[绩效快照] {snapshot['timestamp']}")
        print(f"  区间收益: {total_ret:+.2%} | 波动率: {volatility:.2%}")
        print(f"  夏普比率: {sharpe:.2f} | 最大回撤: {max_dd:.2%}")

        # 检查预警
        alerts = []
        if max_dd < self.alert_config.max_drawdown_threshold:
            alerts.append(f"回撤超限: {max_dd:.2%}")
        if sharpe < self.alert_config.min_sharpe_threshold:
            alerts.append(f"夏普过低: {sharpe:.2f}")
        if volatility > self.alert_config.max_volatility_threshold:
            alerts.append(f"波动过高: {volatility:.2%}")

        if alerts:
            print(f"  ⚠️ 预警: {' | '.join(alerts)}")
            self.alert_history.append({
                'timestamp': snapshot['timestamp'],
                'alerts': alerts,
                'metrics': snapshot,
            })

    def get_alert_summary(self) -> Dict:
        """获取预警汇总"""
        return {
            'total_alerts': len(self.alert_history),
            'alert_history': self.alert_history,
        }
