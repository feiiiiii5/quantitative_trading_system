#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
市场检测器 - 自动识别股票所属市场

支持：
- A股（CN）：6位数字代码
- 港股（HK）：4-5位数字或.HK后缀
- 美股（US）：1-5位字母或.US后缀
"""

import re
from typing import Optional


class MarketDetector:
    """市场检测器"""

    # A股正则：6位数字
    _CN_PATTERN = re.compile(r'^(\d{6})$')
    # 港股正则：4-5位数字 或 .HK后缀
    _HK_PATTERN = re.compile(r'^(\d{4,5})$')
    _HK_SUFFIX_PATTERN = re.compile(r'\.HK$', re.IGNORECASE)
    # 美股正则：1-5位字母 或 .US后缀
    _US_PATTERN = re.compile(r'^[A-Z]{1,5}$')
    _US_SUFFIX_PATTERN = re.compile(r'\.US$', re.IGNORECASE)

    @classmethod
    def detect(cls, symbol: str) -> str:
        """
        检测股票所属市场

        Args:
            symbol: 股票代码

        Returns:
            "CN"/"HK"/"US"
        """
        symbol = symbol.strip().upper()

        # 检查后缀
        if cls._HK_SUFFIX_PATTERN.search(symbol):
            return "HK"
        if cls._US_SUFFIX_PATTERN.search(symbol):
            return "US"

        # 去除后缀后再检测
        clean = symbol.split('.')[0]

        # A股：6位数字
        if cls._CN_PATTERN.match(clean):
            return "CN"

        # 港股：4-5位数字
        if cls._HK_PATTERN.match(clean):
            return "HK"

        # 美股：1-5位字母
        if cls._US_PATTERN.match(clean):
            return "US"

        # 默认A股
        return "CN"

    @classmethod
    def normalize_symbol(cls, symbol: str, market: Optional[str] = None) -> str:
        """
        标准化代码格式

        Args:
            symbol: 原始代码
            market: 指定市场（如未提供则自动检测）

        Returns:
            标准化后的代码
        """
        symbol = symbol.strip().upper()
        if market is None:
            market = cls.detect(symbol)

        clean = symbol.split('.')[0]

        if market == "HK":
            return f"{clean}.HK"
        elif market == "US":
            return f"{clean}.US"
        else:
            return clean  # A股保持纯数字

    @classmethod
    def is_cn(cls, symbol: str) -> bool:
        """是否为A股"""
        return cls.detect(symbol) == "CN"

    @classmethod
    def is_hk(cls, symbol: str) -> bool:
        """是否为港股"""
        return cls.detect(symbol) == "HK"

    @classmethod
    def is_us(cls, symbol: str) -> bool:
        """是否为美股"""
        return cls.detect(symbol) == "US"
