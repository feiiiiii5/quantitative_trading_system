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

from ui.styles import APPLE_CSS, DARK_CSS
from ui.components.news_sentiment import render_sentiment

st.set_page_config(page_title="市场资讯", page_icon="📰", layout="wide")

if 'dark_mode' not in st.session_state:
    st.session_state.dark_mode = False

if st.session_state.dark_mode:
    st.markdown(DARK_CSS, unsafe_allow_html=True)
else:
    st.markdown(APPLE_CSS, unsafe_allow_html=True)

st.markdown('<div class="section-title">📰 市场资讯</div>', unsafe_allow_html=True)

symbol = st.text_input("输入股票代码查看相关新闻", placeholder="000001", key="news_page_symbol")

if symbol:
    render_sentiment(symbol)
else:
    st.info("请输入股票代码查看相关新闻和情绪分析")
