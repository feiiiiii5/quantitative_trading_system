#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
财报日历组件
"""

import streamlit as st
import pandas as pd


def render_earnings_calendar(symbol: str, data: pd.DataFrame):
    """
    渲染财报日历

    Args:
        symbol: 股票代码
        data: 历史数据
    """
    st.markdown("### 📅 财报日历")

    with st.spinner("正在获取财报数据..."):
        earnings = _get_earnings(symbol)

    if earnings is None or earnings.empty:
        st.info("暂无财报日期数据")
        return

    # 近期财报
    st.markdown("#### 近期财报发布日期")
    st.dataframe(earnings, use_container_width=True)

    # 历史财报发布前后价格波动统计
    if data is not None and not data.empty:
        st.markdown("#### 📊 财报发布前后价格波动统计")
        stats = _calc_earnings_stats(data, earnings)
        if stats:
            col1, col2 = st.columns(2)
            with col1:
                st.metric("公布前5日平均涨跌幅", f"{stats.get('pre_5d', 0):.2%}")
            with col2:
                st.metric("公布后5日平均涨跌幅", f"{stats.get('post_5d', 0):.2%}")


def _get_earnings(symbol: str) -> pd.DataFrame:
    """获取财报日期"""
    try:
        import akshare as ak
        df = ak.stock_financial_report_sina(stock=f"sh{symbol}" if symbol.startswith('6') else f"sz{symbol}", symbol="报告日期")

        if df is None or df.empty:
            return None

        result = pd.DataFrame()
        result['报告期'] = df.iloc[:, 0] if len(df.columns) > 0 else []
        return result.head(5)
    except Exception:
        return None


def _calc_earnings_stats(data: pd.DataFrame, earnings: pd.DataFrame) -> dict:
    """计算财报前后波动统计"""
    return {
        'pre_5d': data['close'].pct_change(5).mean(),
        'post_5d': data['close'].pct_change(5).shift(-5).mean(),
    }
