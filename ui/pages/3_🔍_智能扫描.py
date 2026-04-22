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
from ui.components.comparison import render_stock_comparison
from ui.components.market_heatmap import render_market_heatmap

st.set_page_config(page_title="智能扫描", page_icon="🔍", layout="wide")

if 'dark_mode' not in st.session_state:
    st.session_state.dark_mode = False

if st.session_state.dark_mode:
    st.markdown(DARK_CSS, unsafe_allow_html=True)
else:
    st.markdown(APPLE_CSS, unsafe_allow_html=True)

st.markdown('<div class="section-title">🔍 智能扫描</div>', unsafe_allow_html=True)

tab1, tab2 = st.tabs(["📊 多股对比", "🗺️ 板块热力图"])

with tab1:
    render_stock_comparison()

with tab2:
    market = st.selectbox("市场", ["CN", "HK", "US"], key="heatmap_market")
    render_market_heatmap(market)
