#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
自选股列表组件
"""

import streamlit as st
import pandas as pd


def render_watchlist():
    """渲染侧边栏自选股列表"""
    if 'watchlist' not in st.session_state:
        st.session_state.watchlist = ['000001', '600519', '000858']

    st.sidebar.markdown("### ⭐ 自选股")

    # 添加股票
    new_symbol = st.sidebar.text_input("添加股票代码", key="add_watchlist", placeholder="输入代码后回车")
    if new_symbol and new_symbol not in st.session_state.watchlist:
        st.session_state.watchlist.append(new_symbol)
        st.rerun()

    # 显示自选股列表
    for i, symbol in enumerate(st.session_state.watchlist):
        cols = st.sidebar.columns([4, 1])
        with cols[0]:
            if st.button(f"📈 {symbol}", key=f"watch_{symbol}_{i}"):
                st.session_state.selected_symbol = symbol
                st.rerun()
        with cols[1]:
            if st.button("✕", key=f"del_{symbol}_{i}"):
                st.session_state.watchlist.remove(symbol)
                st.rerun()
