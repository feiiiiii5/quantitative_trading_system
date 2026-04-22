#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
板块热力图组件 - Apple Design Style
"""

import streamlit as st
import pandas as pd
import numpy as np


def render_market_heatmap(market: str = "CN"):
    is_dark = st.session_state.get('dark_mode', False)

    try:
        import akshare as ak

        if market == "CN":
            df = ak.stock_board_industry_name_em()
            if df is not None and not df.empty:
                df = df.head(30)
                _render_heatmap_grid(df, '板块名称', '涨跌幅', is_dark)
            else:
                st.warning("暂无板块数据")
        elif market == "HK":
            st.info("港股板块热力图开发中...")
        elif market == "US":
            st.info("美股板块热力图开发中...")
        else:
            st.info("暂不支持该市场")

    except Exception as e:
        st.warning(f"获取板块数据失败: {e}")
        _render_demo_heatmap(is_dark)


def _render_heatmap_grid(df, name_col, change_col, is_dark):
    items = []
    for _, row in df.iterrows():
        name = str(row[name_col])
        change = float(row[change_col]) if pd.notna(row[change_col]) else 0
        items.append((name, change))

    if not items:
        return

    max_abs = max(abs(c) for _, c in items) if items else 1
    if max_abs == 0:
        max_abs = 1

    cells = ""
    for name, change in items:
        intensity = abs(change) / max_abs

        if change > 0:
            if is_dark:
                r, g, b = 48, int(209 * (0.3 + 0.7 * intensity)), 88
            else:
                r, g, b = 52, int(199 * (0.3 + 0.7 * intensity)), 89
        elif change < 0:
            if is_dark:
                r, g, b = int(255 * (0.3 + 0.7 * intensity)), 69, 58
            else:
                r, g, b = int(255 * (0.3 + 0.7 * intensity)), 59, 48
        else:
            r, g, b = (99, 99, 102) if is_dark else (142, 142, 147)

        bg_color = f"rgba({r}, {g}, {b}, 0.85)"
        text_color = "white" if intensity > 0.4 else ("#f5f5f7" if is_dark else "#1d1d1f")

        cells += f"""
        <div style="
            background: {bg_color};
            border-radius: 12px;
            padding: 12px 8px;
            text-align: center;
            transition: all 0.2s ease;
            cursor: pointer;
        ">
            <div style="font-size:12px; font-weight:600; color:{text_color}; margin-bottom:4px; overflow:hidden; text-overflow:ellipsis; white-space:nowrap;">
                {name}
            </div>
            <div style="font-size:16px; font-weight:800; color:{text_color}; letter-spacing:-0.02em;">
                {change:+.2f}%
            </div>
        </div>
        """

    st.markdown(f"""
    <div style="
        display: grid;
        grid-template-columns: repeat(auto-fill, minmax(100px, 1fr));
        gap: 8px;
        padding: 8px;
    ">
        {cells}
    </div>
    """, unsafe_allow_html=True)


def _render_demo_heatmap(is_dark):
    demo_items = [
        ("银行", 1.2), ("证券", -0.8), ("保险", 0.5),
        ("房地产", -2.1), ("医药", 1.8), ("科技", 2.5),
        ("消费", -0.3), ("能源", 0.9), ("材料", -1.5),
        ("工业", 0.7), ("通信", 1.1), ("公用", -0.2),
    ]
    _render_heatmap_grid(
        pd.DataFrame(demo_items, columns=['板块名称', '涨跌幅']),
        '板块名称', '涨跌幅', is_dark
    )
