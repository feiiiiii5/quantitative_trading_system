#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
数据获取公共辅助函数
供所有UI页面复用，统一缓存策略
"""

import streamlit as st
import pandas as pd
from datetime import datetime, timedelta

from data.async_data_manager import AsyncDataManager
from data.market_detector import MarketDetector


@st.cache_data(ttl=3600, hash_funcs={pd.DataFrame: lambda df: str(df.shape) + str(df.index[-1]) + str(df['close'].iloc[-1])})
def get_stock_data_cached(symbol: str, days: int = 730, market: str = None) -> tuple:
    """
    带缓存的股票数据获取

    Args:
        symbol: 股票代码
        days: 历史天数
        market: 市场代码（自动检测）

    Returns:
        (data, market) 元组
    """
    if market is None:
        market = MarketDetector.detect(symbol)

    dm = AsyncDataManager()
    end_date = datetime.now().strftime('%Y-%m-%d')
    start_date = (datetime.now() - timedelta(days=days)).strftime('%Y-%m-%d')

    for source in ['akshare', 'baostock']:
        try:
            data = dm.get_data_sync(symbol, start_date, end_date, source=source, market=market)
            if data is not None and not data.empty:
                return data, market
        except Exception:
            pass

    return None, market
