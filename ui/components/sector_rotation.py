#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
板块轮动分析组件
"""

import streamlit as st
import pandas as pd
import plotly.graph_objects as go


def render_sector_rotation(market: str = "CN"):
    """渲染板块轮动分析"""
    st.markdown("### 🔄 板块轮动分析")

    with st.spinner("正在获取板块资金流向..."):
        df = _get_sector_flow()

    if df is None or df.empty:
        st.warning("暂无板块资金流向数据")
        return

    # 气泡图：X=近5日涨跌，Y=近20日涨跌，大小=成交额
    fig = go.Figure()

    fig.add_trace(go.Scatter(
        x=df['change_5d'],
        y=df['change_20d'],
        mode='markers+text',
        marker=dict(
            size=df['size'],
            color=df['change_5d'],
            colorscale=[
                [0, '#34c759'],
                [0.5, '#f5f5f7'],
                [1, '#ff3b30']
            ],
            cmid=0,
            sizemode='diameter',
            sizeref=2 * max(df['size']) / (100 ** 2),
            opacity=0.8,
            line=dict(width=1, color='rgba(0,0,0,0.1)'),
        ),
        text=df['name'],
        textposition="top center",
        textfont=dict(size=10),
        hovertemplate="<b>%{text}</b><br>5日: %{x:.2f}%<br>20日: %{y:.2f}%<extra></extra>",
    ))

    fig.update_layout(
        height=500,
        xaxis_title="近5日涨跌幅(%)",
        yaxis_title="近20日涨跌幅(%)",
        plot_bgcolor='white',
        font=dict(family="-apple-system, BlinkMacSystemFont, sans-serif"),
        margin=dict(l=50, r=20, t=30, b=40),
    )

    fig.add_hline(y=0, line_dash="dash", line_color="rgba(0,0,0,0.2)")
    fig.add_vline(x=0, line_dash="dash", line_color="rgba(0,0,0,0.2)")

    st.plotly_chart(fig, use_container_width=True)

    # 象限解读
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.markdown("**↗ 右上**：强势板块（资金持续流入）")
    with col2:
        st.markdown("**↘ 右下**：短期回调（可能买入机会）")
    with col3:
        st.markdown("**↙ 左下**：弱势板块（资金流出）")
    with col4:
        st.markdown("**↖ 左上**：长强短弱（等待确认）")


def _get_sector_flow() -> pd.DataFrame:
    """获取板块资金流向"""
    try:
        import akshare as ak
        df = ak.stock_fund_flow_industry(symbol="今日")

        if df is None or df.empty:
            return None

        result = pd.DataFrame()
        result['name'] = df['行业']
        result['change_5d'] = pd.to_numeric(df.get('今日涨跌幅', df.get('5日涨跌幅', 0)), errors='coerce').fillna(0)
        result['change_20d'] = pd.to_numeric(df.get('今日涨跌幅', 0), errors='coerce').fillna(0)
        result['size'] = pd.to_numeric(df.get('今日成交额', 1), errors='coerce').fillna(1)
        result['size'] = (result['size'] / result['size'].max() * 80 + 10)

        return result
    except Exception as e:
        st.error(f"获取板块数据失败: {e}")
        return None
