#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
股票概览卡片组件 - Apple Design Style
"""

import streamlit as st
import pandas as pd
from datetime import datetime


def render_overview_cards(symbol: str, market: str, data: pd.DataFrame):
    if data is None or data.empty:
        return

    latest = data.iloc[-1]
    prev = data.iloc[-2] if len(data) > 1 else latest

    close_price = float(latest.get('close', 0))
    prev_close = float(prev.get('close', 0))
    change = close_price - prev_close
    change_pct = (change / prev_close * 100) if prev_close != 0 else 0

    high_price = float(latest.get('high', 0))
    low_price = float(latest.get('low', 0))
    open_price = float(latest.get('open', 0))
    volume = float(latest.get('volume', 0))

    is_up = change >= 0
    badge_class = "badge-up" if is_up else "badge-down"
    arrow = "↑" if is_up else "↓"

    market_name = {"CN": "🇨🇳 A股", "HK": "🇭🇰 港股", "US": "🇺🇸 美股"}.get(market, "📊")

    st.markdown(f"""
    <div class="apple-card" style="margin-bottom:20px;">
        <div style="display:flex; justify-content:space-between; align-items:flex-start; flex-wrap:wrap; gap:16px;">
            <div>
                <div style="font-size:14px; color:var(--text-secondary); font-weight:600; text-transform:uppercase; letter-spacing:0.04em;">
                    {market_name} · {symbol}
                </div>
                <div style="font-size:42px; font-weight:800; color:var(--text-primary); letter-spacing:-0.03em; margin:8px 0;">
                    {close_price:,.2f}
                </div>
                <div style="display:flex; gap:12px; align-items:center; flex-wrap:wrap;">
                    <span class="{badge_class}">{arrow} {abs(change):,.2f} ({abs(change_pct):.2f}%)</span>
                    <span style="font-size:13px; color:var(--text-tertiary);">{latest.name.strftime('%Y-%m-%d') if hasattr(latest.name, 'strftime') else str(latest.name)}</span>
                </div>
            </div>
            <div style="text-align:right;">
                <div style="font-size:12px; color:var(--text-secondary); font-weight:500;">开盘</div>
                <div style="font-size:18px; font-weight:600; color:var(--text-primary);">{open_price:,.2f}</div>
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-label">最高价</div>
            <div class="metric-value" style="color:var(--accent-green);">{high_price:,.2f}</div>
        </div>
        """, unsafe_allow_html=True)

    with col2:
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-label">最低价</div>
            <div class="metric-value" style="color:var(--accent-red);">{low_price:,.2f}</div>
        </div>
        """, unsafe_allow_html=True)

    with col3:
        vol_str = _format_volume(volume)
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-label">成交量</div>
            <div class="metric-value">{vol_str}</div>
        </div>
        """, unsafe_allow_html=True)

    with col4:
        amplitude = ((high_price - low_price) / prev_close * 100) if prev_close != 0 else 0
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-label">振幅</div>
            <div class="metric-value">{amplitude:.2f}%</div>
        </div>
        """, unsafe_allow_html=True)

    if len(data) >= 20:
        _render_mini_sparkline(data)


def _format_volume(volume: float) -> str:
    if volume >= 1e8:
        return f"{volume/1e8:.1f}亿"
    elif volume >= 1e4:
        return f"{volume/1e4:.1f}万"
    else:
        return f"{volume:,.0f}"


def _render_mini_sparkline(data: pd.DataFrame):
    recent = data.tail(20)
    closes = recent['close'].values
    min_c = closes.min()
    max_c = closes.max()
    range_c = max_c - min_c if max_c != min_c else 1

    bars_html = ""
    for c in closes:
        height = max(4, int((c - min_c) / range_c * 26))
        is_up = c >= closes[0]
        color = "var(--accent-green)" if is_up else "var(--accent-red)"
        bars_html += f'<div class="sparkline-bar" style="height:{height}px; background:{color};"></div>'

    st.markdown(f"""
    <div class="apple-card" style="margin-top:16px; padding:16px 20px;">
        <div style="display:flex; justify-content:space-between; align-items:center;">
            <div>
                <div style="font-size:12px; color:var(--text-secondary); font-weight:600; text-transform:uppercase; letter-spacing:0.04em;">20日走势</div>
                <div style="font-size:22px; font-weight:700; color:var(--text-primary); margin-top:4px;">
                    {closes[-1]:,.2f}
                </div>
            </div>
            <div class="sparkline-container">
                {bars_html}
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)
