#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
关注列表组件 - Apple Design Style
"""

import streamlit as st
from datetime import datetime


DEFAULT_WATCHLIST = {
    "CN": ["000001", "600519", "000858", "601318", "600036"],
    "HK": ["00700", "09988", "09618"],
    "US": ["AAPL", "GOOGL", "MSFT", "AMZN"],
}


def render_watchlist():
    if 'watchlist' not in st.session_state:
        st.session_state.watchlist = DEFAULT_WATCHLIST.copy()

    st.markdown("""
    <div style="font-size:20px; font-weight:700; color:var(--text-primary); margin-bottom:16px; letter-spacing:-0.02em;">
        ⭐ 关注列表
    </div>
    """, unsafe_allow_html=True)

    add_col1, add_col2 = st.columns([3, 1])
    with add_col1:
        new_symbol = st.text_input("添加股票", placeholder="输入代码", key="wl_add_input", label_visibility="collapsed")
    with add_col2:
        st.markdown("<div style='height:34px'></div>", unsafe_allow_html=True)
        if st.button("➕", key="wl_add_btn", use_container_width=True):
            if new_symbol:
                from data.market_detector import MarketDetector
                market = MarketDetector.detect(new_symbol)
                if market not in st.session_state.watchlist:
                    st.session_state.watchlist[market] = []
                if new_symbol not in st.session_state.watchlist[market]:
                    st.session_state.watchlist[market].append(new_symbol)

    for market, symbols in st.session_state.watchlist.items():
        if not symbols:
            continue

        market_name = {"CN": "🇨🇳 A股", "HK": "🇭🇰 港股", "US": "🇺🇸 美股"}.get(market, "📊")

        st.markdown(f"""
        <div style="font-size:12px; font-weight:600; color:var(--text-secondary); text-transform:uppercase; letter-spacing:0.04em; margin:16px 0 8px;">
            {market_name}
        </div>
        """, unsafe_allow_html=True)

        for symbol in symbols:
            col1, col2 = st.columns([4, 1])
            with col1:
                if st.button(f"📊 {symbol}", key=f"wl_{market}_{symbol}", use_container_width=True):
                    st.session_state.selected_symbol = symbol
            with col2:
                if st.button("✕", key=f"wl_del_{market}_{symbol}"):
                    if symbol in st.session_state.watchlist.get(market, []):
                        st.session_state.watchlist[market].remove(symbol)
                        st.rerun()
