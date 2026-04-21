#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
期权链组件（美股专用）
"""

import streamlit as st
import pandas as pd
import plotly.graph_objects as go


def render_options_chain(symbol: str):
    """
    渲染期权链（美股专用）

    Args:
        symbol: 美股代码
    """
    st.markdown("### 📊 期权链分析（美股）")

    with st.spinner("正在获取期权数据..."):
        options_data = _get_options_data(symbol)

    if options_data is None:
        st.warning("暂无期权数据（仅支持美股）")
        return

    calls, puts, exp_dates = options_data

    if not exp_dates:
        st.warning("无可用到期日")
        return

    # 选择到期日
    selected_date = st.selectbox("选择到期日", exp_dates, key="options_date")

    # 隐含波动率微笑曲线
    fig = go.Figure()

    if selected_date in calls.columns.get_level_values(1) if isinstance(calls.columns, pd.MultiIndex) else True:
        fig.add_trace(go.Scatter(
            x=calls['strike'] if 'strike' in calls.columns else [],
            y=calls.get('impliedVolatility', pd.Series()),
            mode='lines+markers',
            name='看涨IV',
            line=dict(color='#0071e3', width=2),
        ))
        fig.add_trace(go.Scatter(
            x=puts['strike'] if 'strike' in puts.columns else [],
            y=puts.get('impliedVolatility', pd.Series()),
            mode='lines+markers',
            name='看跌IV',
            line=dict(color='#ff3b30', width=2),
        ))

    fig.update_layout(
        height=400,
        title="隐含波动率微笑曲线",
        xaxis_title="行权价",
        yaxis_title="隐含波动率",
        plot_bgcolor='white',
        font=dict(family="-apple-system, BlinkMacSystemFont, sans-serif"),
        margin=dict(l=50, r=20, t=40, b=30),
    )

    st.plotly_chart(fig, use_container_width=True)

    # Max Pain
    if 'strike' in calls.columns and not calls.empty:
        st.info("Max Pain 计算需要更详细的期权数据")


def _get_options_data(symbol: str):
    """获取期权链数据"""
    try:
        import yfinance as yf
        ticker = yf.Ticker(symbol)
        exp_dates = ticker.options

        if not exp_dates:
            return None

        chain = ticker.option_chain(exp_dates[0])
        return chain.calls, chain.puts, list(exp_dates)
    except Exception:
        return None
