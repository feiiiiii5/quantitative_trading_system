#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
K线图 + 成交量组件
使用Plotly绘制专业级K线图
"""

import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from datetime import datetime, timedelta


def render_kline_chart(data: pd.DataFrame, indicators_config: dict = None, market: str = None):
    """
    渲染K线图 + 技术指标

    Args:
        data: 历史数据DataFrame（需含open/high/low/close/volume列）
        indicators_config: 指标配置
    """
    if data is None or data.empty:
        st.warning("暂无数据")
        return

    # 时间范围选择
    col1, col2, col3, col4, col5 = st.columns(5)
    with col1:
        range_1m = st.button("1月", key="range_1m")
    with col2:
        range_3m = st.button("3月", key="range_3m")
    with col3:
        range_6m = st.button("6月", key="range_6m")
    with col4:
        range_1y = st.button("1年", key="range_1y")
    with col5:
        range_all = st.button("全部", key="range_all")

    # 根据选择截取数据
    df = data.copy()
    if range_1m:
        df = df.tail(22)
    elif range_3m:
        df = df.tail(66)
    elif range_6m:
        df = df.tail(132)
    elif range_1y:
        df = df.tail(252)

    if df.empty:
        df = data.copy()

    # 计算技术指标
    df = _calc_indicators(df)

    # 创建子图：K线 + MACD + 成交量 + RSI
    fig = make_subplots(
        rows=4, cols=1,
        shared_xaxes=True,
        vertical_spacing=0.03,
        row_heights=[0.5, 0.15, 0.2, 0.15],
        subplot_titles=('', 'MACD', '成交量', 'RSI')
    )

    # 主图：K线
    fig.add_trace(go.Candlestick(
        x=df.index,
        open=df['open'],
        high=df['high'],
        low=df['low'],
        close=df['close'],
        name='K线',
        increasing_line_color='#34c759',
        decreasing_line_color='#ff3b30',
        increasing_fillcolor='#34c759',
        decreasing_fillcolor='#ff3b30',
    ), row=1, col=1)

    # MA均线
    for period, color in [(5, '#0071e3'), (20, '#ff9500'), (60, '#af52de')]:
        col_name = f'ma{period}'
        if col_name in df.columns:
            fig.add_trace(go.Scatter(
                x=df.index,
                y=df[col_name],
                mode='lines',
                name=f'MA{period}',
                line=dict(color=color, width=1.5),
                opacity=0.8,
            ), row=1, col=1)

    # MACD
    if 'macd' in df.columns:
        fig.add_trace(go.Scatter(
            x=df.index, y=df['macd'],
            mode='lines', name='MACD',
            line=dict(color='#0071e3', width=1.5),
        ), row=2, col=1)
        fig.add_trace(go.Scatter(
            x=df.index, y=df['macd_signal'],
            mode='lines', name='Signal',
            line=dict(color='#ff9500', width=1.5),
        ), row=2, col=1)

        # MACD柱状图
        colors = ['#34c759' if v >= 0 else '#ff3b30' for v in df['macd_hist'].fillna(0)]
        fig.add_trace(go.Bar(
            x=df.index, y=df['macd_hist'],
            name='MACD Hist',
            marker_color=colors,
            showlegend=False,
        ), row=2, col=1)

    # 成交量（涨跌着色）
    vol_colors = ['#34c759' if df['close'].iloc[i] >= df['open'].iloc[i]
                  else '#ff3b30' for i in range(len(df))]
    fig.add_trace(go.Bar(
        x=df.index, y=df['volume'],
        name='成交量',
        marker_color=vol_colors,
        opacity=0.7,
        showlegend=False,
    ), row=3, col=1)

    # RSI
    if 'rsi' in df.columns:
        fig.add_trace(go.Scatter(
            x=df.index, y=df['rsi'],
            mode='lines', name='RSI',
            line=dict(color='#af52de', width=1.5),
        ), row=4, col=1)
        # 超买超卖线
        fig.add_hline(y=70, line_dash="dash", line_color="#ff3b30",
                      line_width=1, row=4, col=1)
        fig.add_hline(y=30, line_dash="dash", line_color="#34c759",
                      line_width=1, row=4, col=1)

    # 布局
    fig.update_layout(
        height=700,
        xaxis_rangeslider_visible=False,
        plot_bgcolor='white',
        paper_bgcolor='white',
        font=dict(family="-apple-system, BlinkMacSystemFont, sans-serif", size=12),
        margin=dict(l=50, r=20, t=30, b=20),
        showlegend=True,
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="right",
            x=1,
            font=dict(size=11),
        ),
    )

    # 隐藏非交易时间空隙
    if market in ("CN", "HK", "US"):
        fig.update_xaxes(
            rangebreaks=[dict(bounds=["sat", "mon"])],
            showgrid=True,
            gridcolor='rgba(0,0,0,0.05)',
        )
    else:
        fig.update_xaxes(
            showgrid=True,
            gridcolor='rgba(0,0,0,0.05)',
        )

    fig.update_yaxes(showgrid=True, gridcolor='rgba(0,0,0,0.05)')

    st.plotly_chart(fig, use_container_width=True)


def _calc_indicators(df: pd.DataFrame) -> pd.DataFrame:
    """计算技术指标"""
    close = df['close']
    high = df['high']
    low = df['low']

    # MA
    for p in [5, 20, 60]:
        df[f'ma{p}'] = close.rolling(p).mean()

    # MACD
    ema12 = close.ewm(span=12, adjust=False).mean()
    ema26 = close.ewm(span=26, adjust=False).mean()
    df['macd'] = ema12 - ema26
    df['macd_signal'] = df['macd'].ewm(span=9, adjust=False).mean()
    df['macd_hist'] = df['macd'] - df['macd_signal']

    # RSI
    delta = close.diff()
    gain = delta.where(delta > 0, 0).rolling(14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
    rs = gain / (loss + 1e-8)
    df['rsi'] = 100 - (100 / (1 + rs))

    return df
