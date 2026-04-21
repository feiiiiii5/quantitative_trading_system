#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
股票分析页面
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

import streamlit as st
from datetime import datetime, timedelta

from ui.styles import APPLE_CSS
from data.async_data_manager import AsyncDataManager
from data.market_detector import MarketDetector
from ui.components.stock_overview import render_overview_cards
from ui.components.kline_chart import render_kline_chart
from ui.components.technical_panel import render_technical_indicators
from ui.components.quant_metrics import render_quant_metrics
from ui.components.prediction import render_prediction_panel

st.set_page_config(page_title="股票分析", page_icon="📊", layout="wide")
st.markdown(APPLE_CSS, unsafe_allow_html=True)

symbol = st.text_input("输入股票代码", placeholder="000001", key="page_symbol")

if symbol:
    market = MarketDetector.detect(symbol)
    dm = AsyncDataManager()
    end_date = datetime.now().strftime('%Y-%m-%d')
    start_date = (datetime.now() - timedelta(days=730)).strftime('%Y-%m-%d')

    with st.spinner("正在获取数据..."):
        data, market = dm.get_data_sync(symbol, start_date, end_date, source='akshare', market=market), market

    if data is not None and not data.empty:
        render_overview_cards(symbol, market, data)
        render_kline_chart(data)
        render_technical_indicators(data)
        render_quant_metrics(symbol, data, market)
        render_prediction_panel(symbol, data)
