#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
智能选股扫描器
"""

import streamlit as st
import pandas as pd
import numpy as np


def render_scanner(market: str = "CN"):
    """
    渲染智能选股扫描器

    Args:
        market: 市场代码
    """
    st.markdown("### 🔍 智能选股扫描器")

    template = st.selectbox(
        "选择扫描条件",
        ["突破新高", "超卖反弹", "金叉形成", "放量上涨"],
        key="scanner_template"
    )

    if st.button("🚀 开始扫描", key="run_scan"):
        with st.spinner("正在扫描全市场..."):
            results = _scan_market(template, market)

        if results is None or results.empty:
            st.warning("未找到符合条件的股票")
            return

        st.dataframe(
            results,
            use_container_width=True,
            column_config={
                "代码": st.column_config.TextColumn("代码", width="small"),
                "名称": st.column_config.TextColumn("名称", width="medium"),
                "触发信号": st.column_config.TextColumn("触发信号", width="medium"),
                "评分": st.column_config.ProgressColumn("评分", min_value=0, max_value=100),
            }
        )

        # 点击跳转
        selected = st.selectbox("选择股票查看详情", results['代码'].tolist(), key="scanner_select")
        if selected:
            st.session_state.selected_symbol = selected


def _scan_market(template: str, market: str) -> pd.DataFrame:
    """扫描市场"""
    try:
        import akshare as ak

        df = ak.stock_zh_a_spot_em()
        if df is None or df.empty:
            return None

        results = []

        for _, row in df.head(200).iterrows():
            symbol = str(row.get('代码', ''))
            name = str(row.get('名称', ''))
            price = float(row.get('最新价', 0))
            change_pct = float(row.get('涨跌幅', 0))
            volume = float(row.get('成交量', 0))

            if price <= 0:
                continue

            score = 0
            signal = ""

            if template == "突破新高":
                high = float(row.get('最高', 0))
                if abs(price - high) / high < 0.01 and change_pct > 0:
                    score = 80
                    signal = "突破新高"
            elif template == "超卖反弹":
                if change_pct < -3 and change_pct > -7:
                    score = 70
                    signal = "超卖反弹"
            elif template == "金叉形成":
                if change_pct > 1 and volume > 0:
                    score = 65
                    signal = "疑似金叉"
            elif template == "放量上涨":
                if change_pct > 2 and volume > 0:
                    score = 75
                    signal = "放量上涨"

            if score > 0:
                results.append({
                    '代码': symbol,
                    '名称': name,
                    '触发信号': signal,
                    '评分': score,
                    '涨跌幅': f"{change_pct:.2f}%",
                })

        return pd.DataFrame(results) if results else None

    except Exception as e:
        st.error(f"扫描失败: {e}")
        return None
