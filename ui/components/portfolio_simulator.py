#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
组合模拟器组件
"""

import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from datetime import datetime, timedelta

from data.async_data_manager import AsyncDataManager
from core.portfolio_optimizer import PortfolioOptimizer


def render_portfolio_simulator():
    """渲染组合模拟器"""
    st.markdown("### 💼 组合模拟器")

    # 输入股票和权重
    input_str = st.text_input(
        "输入股票代码（逗号分隔）",
        value="000001,600519,000858",
        key="portfolio_input"
    )
    symbols = [s.strip() for s in input_str.split(",") if s.strip()]

    if len(symbols) < 2:
        st.info("请输入至少2只股票")
        return

    # 获取数据
    with st.spinner("正在获取数据..."):
        dm = AsyncDataManager()
        end_date = datetime.now().strftime('%Y-%m-%d')
        start_date = (datetime.now() - timedelta(days=365)).strftime('%Y-%m-%d')

        data_dict = {}
        for symbol in symbols:
            data = dm.get_data_sync(symbol, start_date, end_date, source='akshare')
            if data is not None and not data.empty:
                data_dict[symbol] = data

    if len(data_dict) < 2:
        st.warning("获取到有效数据的股票不足2只")
        return

    # 计算收益率和协方差
    returns = pd.DataFrame()
    for symbol, data in data_dict.items():
        returns[symbol] = data['close'].pct_change().dropna()

    mean_returns = returns.mean() * 252
    cov_matrix = returns.cov() * 252

    # 优化
    opt = PortfolioOptimizer()

    tab1, tab2, tab3 = st.tabs(["风险平价", "最大夏普", "最小方差"])

    with tab1:
        weights = opt.risk_parity(cov_matrix.values)
        _show_portfolio_result(symbols, weights, mean_returns, cov_matrix)

    with tab2:
        weights = opt.max_sharpe(mean_returns.values, cov_matrix.values)
        _show_portfolio_result(symbols, weights, mean_returns, cov_matrix)

    with tab3:
        weights = opt.min_volatility(cov_matrix.values)
        _show_portfolio_result(symbols, weights, mean_returns, cov_matrix)

    # 有效前沿
    st.markdown("#### 📈 有效前沿")
    _render_efficient_frontier(mean_returns, cov_matrix, opt)


def _show_portfolio_result(symbols, weights, mean_returns, cov_matrix):
    """展示组合结果"""
    port_ret = np.dot(weights, mean_returns)
    port_vol = np.sqrt(np.dot(weights, np.dot(cov_matrix, weights)))
    sharpe = port_ret / port_vol if port_vol > 0 else 0

    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("预期年化收益", f"{port_ret:.2%}")
    with col2:
        st.metric("年化波动率", f"{port_vol:.2%}")
    with col3:
        st.metric("夏普比率", f"{sharpe:.2f}")

    # 权重饼图
    import plotly.graph_objects as go
    fig = go.Figure(go.Pie(
        labels=symbols,
        values=weights,
        hole=0.5,
        marker=dict(colors=['#0071e3', '#34c759', '#ff9500', '#af52de', '#ff3b30']),
    ))
    fig.update_layout(height=300, margin=dict(l=20, r=20, t=20, b=20),
                     font=dict(family="-apple-system, BlinkMacSystemFont, sans-serif"))
    st.plotly_chart(fig, use_container_width=True)


def _render_efficient_frontier(mean_returns, cov_matrix, opt):
    """渲染有效前沿"""
    n_portfolios = 500
    returns_list = []
    vols_list = []

    for _ in range(n_portfolios):
        w = np.random.random(len(mean_returns))
        w /= np.sum(w)
        ret = np.dot(w, mean_returns)
        vol = np.sqrt(np.dot(w, np.dot(cov_matrix, w)))
        returns_list.append(ret)
        vols_list.append(vol)

    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=vols_list, y=returns_list,
        mode='markers',
        marker=dict(size=3, color=returns_list, colorscale='Viridis', opacity=0.5),
        showlegend=False,
    ))

    # 标注最优点
    max_sharpe_w = opt.max_sharpe(mean_returns.values, cov_matrix.values)
    ms_ret = np.dot(max_sharpe_w, mean_returns)
    ms_vol = np.sqrt(np.dot(max_sharpe_w, np.dot(cov_matrix, max_sharpe_w)))
    fig.add_trace(go.Scatter(
        x=[ms_vol], y=[ms_ret],
        mode='markers', name='最大夏普',
        marker=dict(size=12, color='#ff3b30', symbol='star'),
    ))

    fig.update_layout(
        height=400,
        xaxis_title="年化波动率",
        yaxis_title="年化收益率",
        plot_bgcolor='white',
        font=dict(family="-apple-system, BlinkMacSystemFont, sans-serif"),
        margin=dict(l=50, r=20, t=30, b=30),
    )
    st.plotly_chart(fig, use_container_width=True)
