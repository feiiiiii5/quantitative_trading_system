#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
市场资讯页面
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

import streamlit as st

from ui.styles import APPLE_CSS
from ui.components.news_sentiment import render_sentiment
from ui.components.market_heatmap import render_market_heatmap

st.set_page_config(page_title="市场资讯", page_icon="📰", layout="wide")
st.markdown(APPLE_CSS, unsafe_allow_html=True)

tab1, tab2 = st.tabs(["📰 个股新闻", "🗺️ 板块热力图"])

with tab1:
    symbol = st.text_input("输入股票代码", placeholder="000001", key="news_page_symbol")
    if symbol:
        render_sentiment(symbol)

with tab2:
    render_market_heatmap()
