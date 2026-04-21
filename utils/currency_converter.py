#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
货币转换模块

多货币组合统一折算为基准货币
"""

from typing import Dict


# 汇率配置（简化版，实际应接入实时汇率API）
FX_CONFIG = {
    "base_currency": "CNY",
    "rates": {
        "CNY": 1.0,
        "HKD": 0.92,   # 1 HKD = 0.92 CNY
        "USD": 7.25,   # 1 USD = 7.25 CNY
    },
    "update_frequency": "daily",
}


class CurrencyConverter:
    """货币转换器"""

    def __init__(self, base_currency: str = "CNY"):
        self.base_currency = base_currency
        self.rates = FX_CONFIG["rates"].copy()

    def convert(self, amount: float, from_currency: str, to_currency: str = None) -> float:
        """
        货币转换

        Args:
            amount: 金额
            from_currency: 源货币
            to_currency: 目标货币（默认基准货币）

        Returns:
            转换后金额
        """
        to_currency = to_currency or self.base_currency

        if from_currency not in self.rates or to_currency not in self.rates:
            raise ValueError(f"不支持的货币: {from_currency} -> {to_currency}")

        # 先转为CNY，再转为目标货币
        amount_in_cny = amount * self.rates[from_currency]
        return amount_in_cny / self.rates[to_currency]

    def set_rate(self, currency: str, rate: float):
        """设置汇率（相对于CNY）"""
        self.rates[currency] = rate

    def get_rate(self, currency: str) -> float:
        """获取汇率"""
        return self.rates.get(currency, 1.0)

    @classmethod
    def normalize_to_base(cls, values: Dict[str, float], base: str = "CNY") -> Dict[str, float]:
        """
        将多货币金额统一折算为基准货币

        Args:
            values: Dict[currency, amount]
            base: 基准货币

        Returns:
            Dict[currency, amount_in_base]
        """
        converter = cls(base)
        return {
            currency: converter.convert(amount, currency, base)
            for currency, amount in values.items()
        }
