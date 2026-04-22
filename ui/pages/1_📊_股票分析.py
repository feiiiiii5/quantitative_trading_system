#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import sys
from pathlib import Path

root = Path(__file__).resolve()
while not (root / 'app.py').exists() and root != root.parent:
    root = root.parent
if str(root) not in sys.path:
    sys.path.insert(0, str(root))

import streamlit as st
from datetime import datetime, timedelta

from ui.styles import APPLE_CSS, DARK_CSS
from data.async_data_manager import AsyncDataManager
from data.market_detector import MarketDetector
from ui.components.stock_overview import render_overview_cards
from ui.components.kline_chart import render_kline_chart
from ui.components.technical_panel import render_technical_indicators
from ui.components.quant_metrics import render_quant_metrics
from ui.components.prediction import render_prediction_panel

st.set_page_config(page_title="股票分析", page_icon="📊", layout="wide")

if 'dark_mode' not in st.session_state:
    st.session_state.dark_mode = False

if st.session_state.dark_mode:
    st.markdown(DARK_CSS, unsafe_allow_html=True)
else:
    st.markdown(APPLE_CSS, unsafe_allow_html=True)

symbol = st.text_input("输入股票代码", placeholder="000001", key="page_symbol")

if symbol:
    market = MarketDetector.detect(symbol)
    dm = AsyncDataManager()
    end_date = datetime.now().strftime('%Y-%m-%d')
    start_date = (datetime.now() - timedelta(days=730)).strftime('%Y-%m-%d')

    data = None
    with st.spinner("正在获取数据..."):
        for source in ['akshare', 'baostock']:
            try:
                data = dm.get_data_sync(symbol, start_date, end_date, source=source, market=market)
                if data is not None and not data.empty:
                    break
            except Exception:
                pass

    if data is not None and not data.empty:
        render_overview_cards(symbol, market, data)
        render_kline_chart(data, market=market)
        render_technical_indicators(data)
        render_quant_metrics(symbol, data, market)
        render_prediction_panel(symbol, data)
    else:
        st.error(f"无法获取 {symbol} 的数据，请检查代码是否正确")
