#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
策略注册中心

支持动态注册和按市场筛选策略
"""

from typing import Dict, List, Type, Optional
from core.engine import BaseStrategy


class StrategyRegistry:
    """策略注册中心"""

    _registry: Dict[str, Dict] = {}

    @classmethod
    def register(cls, name: str, strategy_class: Type[BaseStrategy],
                 markets: List[str] = None):
        """
        注册策略

        Args:
            name: 策略名称
            strategy_class: 策略类
            markets: 支持的市场列表 ['CN', 'HK', 'US']
        """
        cls._registry[name] = {
            'class': strategy_class,
            'markets': markets or ['CN', 'HK', 'US'],
        }

    @classmethod
    def get(cls, name: str) -> Optional[Type[BaseStrategy]]:
        """获取策略类"""
        entry = cls._registry.get(name)
        return entry['class'] if entry else None

    @classmethod
    def get_strategies_for_market(cls, market: str) -> Dict[str, Type[BaseStrategy]]:
        """
        获取指定市场的所有策略

        Args:
            market: CN/HK/US

        Returns:
            Dict[name, strategy_class]
        """
        return {
            name: entry['class']
            for name, entry in cls._registry.items()
            if market in entry['markets']
        }

    @classmethod
    def list_all(cls) -> List[str]:
        """列出所有策略名称"""
        return list(cls._registry.keys())

    @classmethod
    def unregister(cls, name: str):
        """注销策略"""
        if name in cls._registry:
            del cls._registry[name]

    @classmethod
    def clear(cls):
        """清空注册表"""
        cls._registry.clear()


# 便捷函数
def register(name: str, strategy_class: Type[BaseStrategy], markets: List[str] = None):
    """注册策略"""
    StrategyRegistry.register(name, strategy_class, markets)


def get_strategies_for_market(market: str) -> Dict[str, Type[BaseStrategy]]:
    """获取市场策略"""
    return StrategyRegistry.get_strategies_for_market(market)
