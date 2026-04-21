#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
交易时间判断工具
"""

from datetime import datetime, time


def is_trading_hours(market: str = "CN") -> bool:
    """
    判断当前是否为交易时间

    Args:
        market: CN/HK/US

    Returns:
        bool
    """
    now = datetime.now()
    current_time = now.time()
    weekday = now.weekday()

    if weekday >= 5:
        return False

    if market == "CN":
        morning = time(9, 30) <= current_time <= time(11, 30)
        afternoon = time(13, 0) <= current_time <= time(15, 0)
        return morning or afternoon
    elif market == "HK":
        morning = time(9, 30) <= current_time <= time(12, 0)
        afternoon = time(13, 0) <= current_time <= time(16, 0)
        return morning or afternoon
    elif market == "US":
        # 美股时间（已转换为北京时间）
        return time(21, 30) <= current_time or current_time <= time(4, 0)

    return False
