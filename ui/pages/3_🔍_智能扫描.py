#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
智能扫描页面
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

import streamlit as st

from ui.styles import APPLE_CSS
from ui.components.smart_scanner import render_scanner
from ui.components.sector_rotation import render_sector_rotation
from ui.components.northbound_flow import render_northbound_flow

st.set_page_config(page_title="智能扫描", page_icon="🔍", layout="wide")
st.markdown(APPLE_CSS, unsafe_allow_html=True)

tab1, tab2, tab3 = st.tabs(["🔍 选股扫描", "🔄 板块轮动", "🌊 北向资金"])

with tab1:
    render_scanner()
with tab2:
    render_sector_rotation()
with tab3:
    render_northbound_flow()
