#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
策略回测页面
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

import streamlit as st
from datetime import datetime, timedelta

from ui.styles import APPLE_CSS
from data.async_data_manager import AsyncDataManager
from data.market_detector import MarketDetector
from ui.components.backtest_ui import render_backtest_panel

st.set_page_config(page_title="策略回测", page_icon="📈", layout="wide")
st.markdown(APPLE_CSS, unsafe_allow_html=True)

st.markdown("# 📈 策略回测")

symbol = st.text_input("输入股票代码", placeholder="000001", key="bt_page_symbol")

if symbol:
    market = MarketDetector.detect(symbol)
    dm = AsyncDataManager()
    end_date = datetime.now().strftime('%Y-%m-%d')
    start_date = (datetime.now() - timedelta(days=365)).strftime('%Y-%m-%d')

    with st.spinner("正在获取数据..."):
        data = dm.get_data_sync(symbol, start_date, end_date, source='akshare', market=market)

    if data is not None and not data.empty:
        render_backtest_panel(symbol, data)
