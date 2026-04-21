#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
市场交易日历 - 管理各市场的交易日和假期

支持：
- A股（CN）：国内法定节假日
- 港股（HK）：港股假期
- 美股（US）：NYSE假期
"""

from typing import List, Optional
from datetime import date, datetime, timedelta
import pandas as pd


class MarketCalendar:
    """市场交易日历"""

    # 2024-2025年A股法定节假日（简化版，实际可接入交易所日历API）
    _CN_HOLIDAYS = {
        date(2024, 1, 1), date(2024, 2, 9), date(2024, 2, 12), date(2024, 2, 13),
        date(2024, 2, 14), date(2024, 2, 15), date(2024, 2, 16), date(2024, 4, 4),
        date(2024, 4, 5), date(2024, 5, 1), date(2024, 5, 2), date(2024, 5, 3),
        date(2024, 6, 10), date(2024, 9, 16), date(2024, 9, 17), date(2024, 10, 1),
        date(2024, 10, 2), date(2024, 10, 3), date(2024, 10, 4), date(2024, 10, 7),
        date(2025, 1, 1), date(2025, 1, 28), date(2025, 1, 29), date(2025, 1, 30),
        date(2025, 1, 31), date(2025, 2, 3), date(2025, 2, 4), date(2025, 4, 4),
        date(2025, 5, 1), date(2025, 5, 2), date(2025, 5, 5), date(2025, 6, 2),
        date(2025, 10, 1), date(2025, 10, 2), date(2025, 10, 3), date(2025, 10, 6),
        date(2025, 10, 7), date(2025, 10, 8),
    }

    # 港股假期（简化版）
    _HK_HOLIDAYS = {
        date(2024, 1, 1), date(2024, 2, 12), date(2024, 2, 13), date(2024, 3, 29),
        date(2024, 4, 1), date(2024, 4, 4), date(2024, 5, 1), date(2024, 5, 15),
        date(2024, 6, 10), date(2024, 7, 1), date(2024, 9, 18), date(2024, 10, 1),
        date(2024, 10, 11), date(2024, 12, 25), date(2024, 12, 26),
        date(2025, 1, 1), date(2025, 1, 29), date(2025, 1, 30), date(2025, 1, 31),
        date(2025, 4, 4), date(2025, 4, 18), date(2025, 4, 21), date(2025, 5, 1),
        date(2025, 5, 5), date(2025, 7, 1), date(2025, 10, 1), date(2025, 10, 7),
        date(2025, 12, 25), date(2025, 12, 26),
    }

    # 美股NYSE假期（简化版）
    _US_HOLIDAYS = {
        date(2024, 1, 1), date(2024, 1, 15), date(2024, 2, 19), date(2024, 3, 29),
        date(2024, 5, 27), date(2024, 6, 19), date(2024, 7, 4), date(2024, 9, 2),
        date(2024, 11, 28), date(2024, 12, 25),
        date(2025, 1, 1), date(2025, 1, 20), date(2025, 2, 17), date(2025, 4, 18),
        date(2025, 5, 26), date(2025, 6, 19), date(2025, 7, 4), date(2025, 9, 1),
        date(2025, 11, 27), date(2025, 12, 25),
    }

    _MARKET_HOLIDAYS = {
        "CN": _CN_HOLIDAYS,
        "HK": _HK_HOLIDAYS,
        "US": _US_HOLIDAYS,
    }

    @classmethod
    def is_trading_day(cls, check_date: date, market: str = "CN") -> bool:
        """
        判断是否为交易日

        Args:
            check_date: 日期
            market: 市场代码 CN/HK/US

        Returns:
            是否为交易日
        """
        if isinstance(check_date, datetime):
            check_date = check_date.date()

        # 周末非交易日
        if check_date.weekday() >= 5:
            return False

        # 检查假期
        holidays = cls._MARKET_HOLIDAYS.get(market, cls._CN_HOLIDAYS)
        return check_date not in holidays

    @classmethod
    def get_trading_days(cls, start: date, end: date, market: str = "CN") -> List[date]:
        """
        获取指定区间的所有交易日

        Args:
            start: 开始日期
            end: 结束日期
            market: 市场代码

        Returns:
            交易日列表
        """
        if isinstance(start, str):
            start = datetime.strptime(start, "%Y-%m-%d").date()
        if isinstance(end, str):
            end = datetime.strptime(end, "%Y-%m-%d").date()

        trading_days = []
        current = start
        while current <= end:
            if cls.is_trading_day(current, market):
                trading_days.append(current)
            current += timedelta(days=1)

        return trading_days

    @classmethod
    def next_trading_day(cls, check_date: date, market: str = "CN") -> date:
        """获取下一个交易日"""
        if isinstance(check_date, datetime):
            check_date = check_date.date()

        next_day = check_date + timedelta(days=1)
        while not cls.is_trading_day(next_day, market):
            next_day += timedelta(days=1)
        return next_day

    @classmethod
    def prev_trading_day(cls, check_date: date, market: str = "CN") -> date:
        """获取上一个交易日"""
        if isinstance(check_date, datetime):
            check_date = check_date.date()

        prev_day = check_date - timedelta(days=1)
        while not cls.is_trading_day(prev_day, market):
            prev_day -= timedelta(days=1)
        return prev_day

    @classmethod
    def trading_day_count(cls, start: date, end: date, market: str = "CN") -> int:
        """计算交易日数量"""
        return len(cls.get_trading_days(start, end, market))
