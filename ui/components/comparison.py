#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
多股票对比组件
"""

import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from data.async_data_manager import AsyncDataManager
from datetime import datetime, timedelta


def render_stock_comparison(symbols_list: list = None):
    """
    渲染多股票对比

    Args:
        symbols_list: 股票代码列表
    """
    st.markdown("### 📊 多股票对比")

    # 输入区
    if symbols_list is None:
        input_str = st.text_input(
            "输入股票代码（逗号分隔）",
            value="000001,600519,000858",
            key="compare_input"
        )
        symbols_list = [s.strip() for s in input_str.split(",") if s.strip()]

    if not symbols_list:
        st.info("请输入至少2只股票代码")
        return

    with st.spinner("正在获取数据..."):
        dm = AsyncDataManager()
        end_date = datetime.now().strftime('%Y-%m-%d')
        start_date = (datetime.now() - timedelta(days=365)).strftime('%Y-%m-%d')

        data_dict = {}
        for symbol in symbols_list:
            data = dm.get_data_sync(symbol, start_date, end_date, source='akshare')
            if data is not None and not data.empty:
                data_dict[symbol] = data

    if len(data_dict) < 2:
        st.warning("获取到有效数据的股票不足2只")
        return

    # 归一化收益率对比
    tab1, tab2, tab3 = st.tabs(["📈 收益率对比", "🔥 相关性矩阵", "📋 指标对比"])

    with tab1:
        fig = go.Figure()
        for symbol, data in data_dict.items():
            normalized = data['close'] / data['close'].iloc[0] * 100
            fig.add_trace(go.Scatter(
                x=data.index, y=normalized,
                mode='lines', name=symbol,
                line=dict(width=2),
            ))

        fig.update_layout(
            height=400,
            yaxis_title="归一化价格 (基准=100)",
            plot_bgcolor='white',
            font=dict(family="-apple-system, BlinkMacSystemFont, sans-serif"),
            margin=dict(l=50, r=20, t=30, b=30),
        )
        st.plotly_chart(fig, use_container_width=True)

    with tab2:
        # 相关性矩阵
        returns = pd.DataFrame()
        for symbol, data in data_dict.items():
            returns[symbol] = data['close'].pct_change()

        corr = returns.corr()

        fig = go.Figure(go.Heatmap(
            z=corr.values,
            x=corr.columns,
            y=corr.columns,
            colorscale='RdBu',
            zmid=0,
            text=corr.values.round(2),
            texttemplate="%{text}",
        ))
        fig.update_layout(height=400, margin=dict(l=50, r=20, t=30, b=30))
        st.plotly_chart(fig, use_container_width=True)

    with tab3:
        # 指标对比表格
        metrics_data = []
        for symbol, data in data_dict.items():
            ret = (data['close'].iloc[-1] / data['close'].iloc[0]) - 1
            vol = data['close'].pct_change().std() * np.sqrt(252)
            max_dd = ((data['close'] / data['close'].cummax()) - 1).min()
            metrics_data.append({
                '股票': symbol,
                '收益率': f"{ret:.2%}",
                '年化波动率': f"{vol:.2%}",
                '最大回撤': f"{max_dd:.2%}",
                '夏普比率': f"{ret/vol:.2f}" if vol > 0 else "N/A",
                '最新价': f"{data['close'].iloc[-1]:.2f}",
            })

        st.dataframe(pd.DataFrame(metrics_data), use_container_width=True)
