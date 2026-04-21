#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
新闻情绪分析组件
"""

import streamlit as st
import pandas as pd


def render_sentiment(symbol: str):
    """
    渲染新闻情绪分析

    Args:
        symbol: 股票代码
    """
    st.markdown("### 📰 新闻情绪分析")

    with st.spinner("正在获取新闻..."):
        news_list = _get_stock_news(symbol)

    if not news_list:
        st.warning("暂无新闻数据")
        return

    # 聚合情绪评分
    scores = [n['sentiment_score'] for n in news_list]
    avg_score = sum(scores) / len(scores) if scores else 0

    col1, col2 = st.columns([1, 2])

    with col1:
        if avg_score > 0.2:
            label = "正面 😊"
            color = "var(--accent-green)"
        elif avg_score < -0.2:
            label = "负面 😟"
            color = "var(--accent-red)"
        else:
            label = "中性 😐"
            color = "var(--accent-blue)"

        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-label">情绪评分</div>
            <div class="metric-value" style="color:{color}">{avg_score:+.2f}</div>
            <div style="font-size:16px; color:{color}">{label}</div>
        </div>
        """, unsafe_allow_html=True)

    with col2:
        for news in news_list[:5]:
            sent_color = "var(--accent-green)" if news['sentiment'] == '正面' else (
                "var(--accent-red)" if news['sentiment'] == '负面' else "var(--text-secondary)")
            st.markdown(f"""
            <div class="apple-card" style="margin-bottom:8px; padding:12px 16px">
                <div style="display:flex; justify-content:space-between; align-items:center">
                    <span style="font-weight:500; font-size:14px">{news['title'][:60]}...</span>
                    <span style="color:{sent_color}; font-size:12px; font-weight:600; white-space:nowrap">{news['sentiment']}</span>
                </div>
                <div style="font-size:12px; color:var(--text-secondary); margin-top:4px">{news['date']}</div>
            </div>
            """, unsafe_allow_html=True)


def _get_stock_news(symbol: str) -> list:
    """获取个股新闻"""
    try:
        import akshare as ak
        df = ak.stock_news_em(symbol=symbol)

        if df is None or df.empty:
            return []

        news_list = []
        positive_kw = ['利好', '上涨', '增长', '突破', '新高', '盈利', '增持', '回购']
        negative_kw = ['利空', '下跌', '亏损', '减持', '违规', '处罚', '退市', '暴雷']

        for _, row in df.head(10).iterrows():
            title = str(row.get('新闻标题', row.get('title', '')))
            date = str(row.get('发布时间', row.get('datetime', '')))[:10]

            score = 0
            for kw in positive_kw:
                if kw in title:
                    score += 1
            for kw in negative_kw:
                if kw in title:
                    score -= 1

            if score > 0:
                sentiment = '正面'
            elif score < 0:
                sentiment = '负面'
            else:
                sentiment = '中性'

            news_list.append({
                'title': title,
                'date': date,
                'sentiment': sentiment,
                'sentiment_score': score,
            })

        return news_list
    except Exception as e:
        return []
