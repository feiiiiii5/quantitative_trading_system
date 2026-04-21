#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
北向资金追踪组件（A股专用）
"""

import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime, timedelta


def render_northbound_flow():
    """渲染北向资金追踪"""
    st.markdown("### 🌊 北向资金追踪（A股）")

    with st.spinner("正在获取北向资金数据..."):
        df = _get_northbound_data()

    if df is None or df.empty:
        st.warning("暂无北向资金数据")
        return

    # 近30日净买入/卖出柱状图
    fig = go.Figure()

    colors = ['#ff3b30' if v < 0 else '#34c759' for v in df['net_buy']]

    fig.add_trace(go.Bar(
        x=df['date'],
        y=df['net_buy'],
        marker_color=colors,
        name='净买入(亿)',
    ))

    # 标注大幅流入/流出
    for _, row in df.iterrows():
        if row['net_buy'] > df['net_buy'].quantile(0.9):
            fig.add_annotation(
                x=row['date'], y=row['net_buy'],
                text=f"+{row['net_buy']:.1f}亿",
                showarrow=True, arrowhead=2,
                font=dict(color='#34c759', size=10),
            )
        elif row['net_buy'] < df['net_buy'].quantile(0.1):
            fig.add_annotation(
                x=row['date'], y=row['net_buy'],
                text=f"{row['net_buy']:.1f}亿",
                showarrow=True, arrowhead=2,
                font=dict(color='#ff3b30', size=10),
            )

    fig.update_layout(
        height=400,
        title="近30日沪深港通净买入",
        yaxis_title="净买入(亿元)",
        plot_bgcolor='white',
        font=dict(family="-apple-system, BlinkMacSystemFont, sans-serif"),
        margin=dict(l=50, r=20, t=40, b=30),
    )

    st.plotly_chart(fig, use_container_width=True)

    # 统计摘要
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("近5日净买入", f"{df['net_buy'].tail(5).sum():.1f}亿")
    with col2:
        st.metric("近20日净买入", f"{df['net_buy'].tail(20).sum():.1f}亿")
    with col3:
        st.metric("最大单日流入", f"{df['net_buy'].max():.1f}亿")
    with col4:
        st.metric("最大单日流出", f"{df['net_buy'].min():.1f}亿")


def _get_northbound_data() -> pd.DataFrame:
    """获取北向资金数据"""
    try:
        import akshare as ak
        df = ak.stock_connect_hist_sina(symbol="北向")

        if df is None or df.empty:
            return None

        result = pd.DataFrame()
        result['date'] = pd.to_datetime(df['date'])
        result['net_buy'] = pd.to_numeric(df.get('north_net', df.get('净买入', 0)), errors='coerce').fillna(0)

        return result.tail(30)
    except Exception as e:
        st.error(f"获取北向资金数据失败: {e}")
        return None
