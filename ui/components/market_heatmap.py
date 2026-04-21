#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
市场热力图组件
使用Plotly treemap展示行业板块涨跌
"""

import streamlit as st
import pandas as pd
import plotly.graph_objects as go


def render_market_heatmap(market: str = "CN"):
    """
    渲染行业板块涨跌热力图

    Args:
        market: 市场代码
    """
    st.markdown("### 🗺️ 行业板块热力图")

    with st.spinner("正在获取板块数据..."):
        df = _get_sector_data(market)

    if df is None or df.empty:
        st.warning("暂无板块数据")
        return

    # A股习惯：红涨绿跌
    fig = go.Figure(go.Treemap(
        labels=df['name'],
        parents=[''] * len(df),
        values=df['value'],
        marker=dict(
            colors=df['change_pct'],
            colorscale=[
                [0, '#34c759'],
                [0.5, '#f5f5f7'],
                [1, '#ff3b30']
            ],
            cmid=0,
        ),
        textinfo="label+text",
        text=df.apply(lambda r: f"{r['change_pct']:+.2f}%", axis=1),
        hovertemplate="<b>%{label}</b><br>涨跌幅: %{customdata:+.2f}%<extra></extra>",
        customdata=df['change_pct'],
    ))

    fig.update_layout(
        height=500,
        margin=dict(l=10, r=10, t=10, b=10),
        font=dict(family="-apple-system, BlinkMacSystemFont, sans-serif"),
    )

    st.plotly_chart(fig, use_container_width=True)


def _get_sector_data(market: str) -> pd.DataFrame:
    """获取行业板块数据"""
    try:
        import akshare as ak
        df = ak.stock_board_industry_name_em()

        result = pd.DataFrame()
        result['name'] = df['板块名称']
        result['change_pct'] = pd.to_numeric(df['涨跌幅'], errors='coerce').fillna(0)
        result['value'] = pd.to_numeric(df.get('总市值', df.get('成交额', 1)), errors='coerce').fillna(1)

        return result
    except Exception as e:
        st.error(f"获取板块数据失败: {e}")
        return None
