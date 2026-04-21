#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
股票概览卡片组件
"""

import streamlit as st
import pandas as pd


def render_overview_cards(symbol: str, market: str, data: pd.DataFrame):
    """
    渲染股票概览卡片行

    Args:
        symbol: 股票代码
        market: 市场代码
        data: 历史数据DataFrame
    """
    if data is None or data.empty:
        st.warning("暂无数据")
        return

    latest = data.iloc[-1]
    prev = data.iloc[-2] if len(data) > 1 else latest

    current_price = float(latest.get('close', 0))
    prev_close = float(prev.get('close', 0))
    change = current_price - prev_close
    change_pct = (change / prev_close * 100) if prev_close > 0 else 0

    high = float(latest.get('high', 0))
    low = float(latest.get('low', 0))
    volume = float(latest.get('volume', 0))

    # 52周区间
    if len(data) > 1:
        year_data = data.tail(min(252, len(data)))
        week52_high = float(year_data['high'].max())
        week52_low = float(year_data['low'].min())
    else:
        week52_high = high
        week52_low = low

    # 涨跌颜色和徽章
    if change_pct > 0:
        badge_class = "badge-up"
        arrow = "▲"
        color = "var(--accent-green)"
    elif change_pct < 0:
        badge_class = "badge-down"
        arrow = "▼"
        color = "var(--accent-red)"
    else:
        badge_class = "badge-neutral"
        arrow = "—"
        color = "var(--text-secondary)"

    col1, col2, col3, col4, col5 = st.columns(5)

    with col1:
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-label">当前价格</div>
            <div class="metric-value">{current_price:,.2f}</div>
            <span class="{badge_class}">{arrow} {abs(change_pct):.2f}%</span>
        </div>
        """, unsafe_allow_html=True)

    with col2:
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-label">涨跌幅</div>
            <div class="metric-value" style="color: {color}">{change_pct:+.2f}%</div>
            <span class="{badge_class}">{arrow} {abs(change):.2f}</span>
        </div>
        """, unsafe_allow_html=True)

    with col3:
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-label">今日高/低</div>
            <div class="metric-value" style="font-size:20px">{high:,.2f}</div>
            <div style="color: var(--text-secondary); font-size:14px">{low:,.2f}</div>
        </div>
        """, unsafe_allow_html=True)

    with col4:
        vol_str = _format_volume(volume)
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-label">成交量</div>
            <div class="metric-value" style="font-size:22px">{vol_str}</div>
        </div>
        """, unsafe_allow_html=True)

    with col5:
        # 52周区间进度条
        if week52_high > week52_low:
            pos = (current_price - week52_low) / (week52_high - week52_low) * 100
        else:
            pos = 50
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-label">52周区间</div>
            <div style="font-size:12px; color: var(--text-secondary); margin-top:8px">
                {week52_low:,.2f} - {week52_high:,.2f}
            </div>
            <div class="signal-bar" style="margin-top:8px">
                <div class="signal-bar-fill" style="width:{pos}%; background: var(--accent-blue)"></div>
            </div>
        </div>
        """, unsafe_allow_html=True)


def _format_volume(vol: float) -> str:
    """格式化成交量"""
    if vol >= 1e8:
        return f"{vol/1e8:.1f}亿"
    elif vol >= 1e4:
        return f"{vol/1e4:.1f}万"
    else:
        return f"{vol:.0f}"
