#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
多股对比分析组件 - Apple Design Style
"""

import streamlit as st
import pandas as pd
import numpy as np
from datetime import datetime, timedelta


def render_stock_comparison():
    st.markdown("""
    <div class="section-subtitle">输入多只股票代码进行对比分析（用逗号分隔）</div>
    """, unsafe_allow_html=True)

    symbols_input = st.text_input(
        "股票代码",
        value="000001,600519,000858",
        placeholder="例如：000001,600519,000858",
        key="cmp_symbols",
        label_visibility="collapsed",
    )

    if not symbols_input:
        return

    symbols = [s.strip() for s in symbols_input.split(",") if s.strip()]
    if len(symbols) < 2:
        st.warning("请至少输入2只股票代码")
        return

    if st.button("📊 开始对比", type="primary", key="cmp_run"):
        with st.spinner("正在获取数据..."):
            _run_comparison(symbols)


def _run_comparison(symbols: list):
    from data.async_data_manager import AsyncDataManager
    from data.market_detector import MarketDetector

    dm = AsyncDataManager()
    end_date = datetime.now().strftime('%Y-%m-%d')
    start_date = (datetime.now() - timedelta(days=365)).strftime('%Y-%m-%d')

    all_data = {}
    for symbol in symbols:
        market = MarketDetector.detect(symbol)
        for source in ['akshare', 'baostock']:
            try:
                data = dm.get_data_sync(symbol, start_date, end_date, source=source, market=market)
                if data is not None and not data.empty:
                    all_data[symbol] = data
                    break
            except Exception:
                continue

    if not all_data:
        st.error("无法获取任何股票数据")
        return

    _render_comparison_table(all_data)
    _render_comparison_chart(all_data)


def _render_comparison_table(all_data: dict):
    rows = ""
    for symbol, data in all_data.items():
        close = data['close']
        ret_1m = (close.iloc[-1] / close.iloc[-22] - 1) * 100 if len(close) > 22 else 0
        ret_3m = (close.iloc[-1] / close.iloc[-66] - 1) * 100 if len(close) > 66 else 0
        ret_1y = (close.iloc[-1] / close.iloc[0] - 1) * 100

        vol = close.pct_change().std() * np.sqrt(252) * 100

        max_dd = 0
        peak = close.iloc[0]
        for c in close:
            if c > peak:
                peak = c
            dd = (peak - c) / peak * 100
            if dd > max_dd:
                max_dd = dd

        ret_color_1m = 'var(--accent-green)' if ret_1m >= 0 else 'var(--accent-red)'
        ret_color_3m = 'var(--accent-green)' if ret_3m >= 0 else 'var(--accent-red)'
        ret_color_1y = 'var(--accent-green)' if ret_1y >= 0 else 'var(--accent-red)'

        rows += f"""
        <tr>
            <td style="font-weight:600; color:var(--text-primary);">{symbol}</td>
            <td style="color:var(--text-primary);">{close.iloc[-1]:,.2f}</td>
            <td style="color:{ret_color_1m}; font-weight:600;">{ret_1m:+.2f}%</td>
            <td style="color:{ret_color_3m}; font-weight:600;">{ret_3m:+.2f}%</td>
            <td style="color:{ret_color_1y}; font-weight:600;">{ret_1y:+.2f}%</td>
            <td style="color:var(--text-primary);">{vol:.1f}%</td>
            <td style="color:var(--accent-red);">{max_dd:.1f}%</td>
        </tr>
        """

    st.markdown(f"""
    <div class="apple-card" style="padding:0; overflow:hidden;">
        <table style="width:100%; border-collapse:collapse; font-size:13px;">
            <thead>
                <tr style="background:var(--border-color);">
                    <th style="padding:12px 16px; text-align:left; font-weight:600; color:var(--text-secondary); text-transform:uppercase; font-size:11px; letter-spacing:0.04em;">代码</th>
                    <th style="padding:12px 16px; text-align:right; font-weight:600; color:var(--text-secondary); text-transform:uppercase; font-size:11px; letter-spacing:0.04em;">最新价</th>
                    <th style="padding:12px 16px; text-align:right; font-weight:600; color:var(--text-secondary); text-transform:uppercase; font-size:11px; letter-spacing:0.04em;">1月</th>
                    <th style="padding:12px 16px; text-align:right; font-weight:600; color:var(--text-secondary); text-transform:uppercase; font-size:11px; letter-spacing:0.04em;">3月</th>
                    <th style="padding:12px 16px; text-align:right; font-weight:600; color:var(--text-secondary); text-transform:uppercase; font-size:11px; letter-spacing:0.04em;">1年</th>
                    <th style="padding:12px 16px; text-align:right; font-weight:600; color:var(--text-secondary); text-transform:uppercase; font-size:11px; letter-spacing:0.04em;">波动率</th>
                    <th style="padding:12px 16px; text-align:right; font-weight:600; color:var(--text-secondary); text-transform:uppercase; font-size:11px; letter-spacing:0.04em;">最大回撤</th>
                </tr>
            </thead>
            <tbody>
                {rows}
            </tbody>
        </table>
    </div>
    """, unsafe_allow_html=True)


def _render_comparison_chart(all_data: dict):
    import plotly.graph_objects as go

    is_dark = st.session_state.get('dark_mode', False)
    bg_color = '#000000' if is_dark else 'white'
    text_color = '#f5f5f7' if is_dark else '#1d1d1f'
    grid_color = 'rgba(255,255,255,0.06)' if is_dark else 'rgba(0,0,0,0.05)'

    colors = ['#0a84ff', '#30d158', '#ff9f0a', '#bf5af2', '#ff453a', '#64d2ff']

    fig = go.Figure()

    for i, (symbol, data) in enumerate(all_data.items()):
        normalized = (data['close'] / data['close'].iloc[0]) * 100
        fig.add_trace(go.Scatter(
            x=data.index, y=normalized,
            mode='lines', name=symbol,
            line=dict(color=colors[i % len(colors)], width=2),
        ))

    fig.update_layout(
        height=400,
        plot_bgcolor=bg_color,
        paper_bgcolor=bg_color,
        font=dict(family="-apple-system, BlinkMacSystemFont, sans-serif", size=12, color=text_color),
        margin=dict(l=50, r=20, t=20, b=20),
        yaxis_title="归一化收益 (%)",
        showlegend=True,
        legend=dict(
            orientation="h", yanchor="bottom", y=1.02,
            xanchor="right", x=1, font=dict(size=11, color=text_color),
        ),
    )
    fig.update_xaxes(showgrid=True, gridcolor=grid_color)
    fig.update_yaxes(showgrid=True, gridcolor=grid_color)

    st.plotly_chart(fig, use_container_width=True)
