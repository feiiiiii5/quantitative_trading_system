#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
智能扫描组件 - Apple Design Style
"""

import streamlit as st
import pandas as pd
import numpy as np
from datetime import datetime, timedelta


def render_smart_scanner():
    is_dark = st.session_state.get('dark_mode', False)

    scan_type = st.selectbox(
        "扫描类型",
        ["涨停板", "跌停板", "放量突破", "缩量回调", "MACD金叉", "RSI超卖"],
        key="scan_type_select",
    )

    if st.button("🔍 开始扫描", type="primary", key="scan_run"):
        with st.spinner("正在扫描..."):
            _run_scan(scan_type, is_dark)


def _run_scan(scan_type: str, is_dark: bool):
    try:
        import akshare as ak

        if scan_type in ["涨停板", "跌停板", "放量突破", "缩量回调"]:
            df = ak.stock_zh_a_spot_em()
            if df is None or df.empty:
                st.warning("获取数据失败")
                return

            if scan_type == "涨停板":
                result = df[df['涨跌幅'] >= 9.5].sort_values('涨跌幅', ascending=False)
            elif scan_type == "跌停板":
                result = df[df['涨跌幅'] <= -9.5].sort_values('涨跌幅')
            elif scan_type == "放量突破":
                result = df[(df['涨跌幅'] > 3) & (df['换手率'] > 5)].sort_values('涨跌幅', ascending=False)
            elif scan_type == "缩量回调":
                result = df[(df['涨跌幅'] < -2) & (df['换手率'] < 2)].sort_values('涨跌幅')

            if result.empty:
                st.info(f"未发现{scan_type}股票")
                return

            _render_scan_result(result.head(20), is_dark)

        elif scan_type in ["MACD金叉", "RSI超卖"]:
            st.info(f"{scan_type}扫描需要逐只分析，请稍候...")

    except Exception as e:
        st.warning(f"扫描失败: {e}")


def _render_scan_result(df: pd.DataFrame, is_dark: bool):
    rows = ""
    for _, row in df.iterrows():
        code = str(row.get('代码', ''))
        name = str(row.get('名称', ''))
        price = float(row.get('最新价', 0))
        change_pct = float(row.get('涨跌幅', 0))
        volume = float(row.get('成交量', 0))
        turnover = float(row.get('换手率', 0))

        if change_pct > 0:
            color = 'var(--accent-green)'
            sign = '+'
        elif change_pct < 0:
            color = 'var(--accent-red)'
            sign = ''
        else:
            color = 'var(--text-secondary)'
            sign = ''

        vol_str = f"{volume/1e8:.1f}亿" if volume >= 1e8 else f"{volume/1e4:.0f}万"

        rows += f"""
        <div style="display:flex; justify-content:space-between; align-items:center; padding:12px 0; border-bottom:1px solid var(--border-color);">
            <div>
                <div style="font-size:14px; font-weight:600; color:var(--text-primary);">{name}</div>
                <div style="font-size:12px; color:var(--text-tertiary);">{code}</div>
            </div>
            <div style="text-align:right;">
                <div style="font-size:16px; font-weight:700; color:var(--text-primary);">{price:,.2f}</div>
                <div style="font-size:13px; font-weight:600; color:{color};">{sign}{change_pct:.2f}%</div>
            </div>
        </div>
        """

    st.markdown(f"""
    <div class="apple-card" style="padding:16px 20px;">
        {rows}
    </div>
    """, unsafe_allow_html=True)
