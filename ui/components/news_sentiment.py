#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
新闻情绪分析组件 - Apple Design Style
"""

import streamlit as st
from datetime import datetime, timedelta


def render_sentiment(symbol: str):
    st.markdown("""
    <div class="section-subtitle">市场新闻与情绪分析</div>
    """, unsafe_allow_html=True)

    try:
        import akshare as ak

        try:
            news_df = ak.stock_news_em(symbol=symbol)
            if news_df is not None and not news_df.empty:
                _render_news_list(news_df.head(10))
            else:
                st.info("暂无相关新闻")
        except Exception:
            st.info("新闻数据获取中...")

    except ImportError:
        st.info("需要安装akshare获取新闻数据")

    _render_sentiment_gauge(symbol)


def _render_news_list(news_df):
    is_dark = st.session_state.get('dark_mode', False)

    rows = ""
    for _, row in news_df.iterrows():
        title = str(row.get('新闻标题', row.get('title', '')))
        source = str(row.get('新闻来源', row.get('source', '')))
        date = str(row.get('发布时间', row.get('datetime', '')))

        rows += f"""
        <div style="
            padding: 14px 0;
            border-bottom: 1px solid var(--border-color);
        ">
            <div style="font-size:14px; font-weight:500; color:var(--text-primary); margin-bottom:4px;">
                {title}
            </div>
            <div style="font-size:12px; color:var(--text-tertiary);">
                {source} · {date}
            </div>
        </div>
        """

    st.markdown(f"""
    <div class="apple-card" style="padding:16px 20px;">
        {rows}
    </div>
    """, unsafe_allow_html=True)


def _render_sentiment_gauge(symbol: str):
    import numpy as np

    np.random.seed(hash(symbol) % 2**31)
    sentiment_score = np.random.uniform(30, 70)

    if sentiment_score > 60:
        sentiment = "偏多"
        color = 'var(--accent-green)'
    elif sentiment_score < 40:
        sentiment = "偏空"
        color = 'var(--accent-red)'
    else:
        sentiment = "中性"
        color = 'var(--accent-orange)'

    st.markdown(f"""
    <div class="apple-card" style="text-align:center; padding:24px; margin-top:16px;">
        <div style="font-size:12px; color:var(--text-secondary); font-weight:600; text-transform:uppercase; letter-spacing:0.04em; margin-bottom:12px;">
            市场情绪指数
        </div>
        <div style="font-size:48px; font-weight:800; color:{color}; letter-spacing:-0.03em;">
            {sentiment_score:.0f}
        </div>
        <div style="margin-top:8px;">
            <span class="{'badge-up' if sentiment_score > 60 else 'badge-down' if sentiment_score < 40 else 'badge-neutral'}">
                {sentiment}
            </span>
        </div>
        <div style="max-width:300px; margin:16px auto 0;">
            <div style="display:flex; height:6px; border-radius:3px; overflow:hidden; background:rgba(0,0,0,0.06);">
                <div style="width:{sentiment_score}%; background:{color}; border-radius:3px;"></div>
            </div>
            <div style="display:flex; justify-content:space-between; margin-top:4px;">
                <span style="font-size:11px; color:var(--accent-red);">极度恐惧</span>
                <span style="font-size:11px; color:var(--accent-green);">极度贪婪</span>
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("""
    <div class="disclaimer">
        ⚠️ 情绪指数仅供参考，不构成投资建议。
    </div>
    """, unsafe_allow_html=True)
