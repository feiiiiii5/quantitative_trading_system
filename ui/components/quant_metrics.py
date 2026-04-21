#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
量化系统指标组件
调用Cerebro运行回测，展示年化收益/夏普/最大回撤等
"""

import streamlit as st
import pandas as pd
from datetime import datetime, timedelta

from core.engine import Cerebro, Broker, ExecutionMode
from data.async_data_manager import AsyncDataManager
from data.market_detector import MarketDetector


def render_quant_metrics(symbol: str, data: pd.DataFrame, market: str):
    """
    渲染量化系统指标

    Args:
        symbol: 股票代码
        data: 历史数据
        market: 市场代码
    """
    if data is None or data.empty:
        st.warning("暂无数据")
        return

    st.markdown("### 🎯 量化系统指标")

    with st.spinner("正在运行回测分析..."):
        metrics = _run_backtest(symbol, data, market)

    if metrics is None:
        st.error("回测运行失败")
        return

    # 核心指标展示
    col1, col2, col3 = st.columns(3)

    with col1:
        _score_card("年化收益率", f"{metrics.annual_return:.2%}",
                     _rating(metrics.annual_return, [0, 0.1, 0.2, 0.3]))
        _score_card("夏普比率", f"{metrics.sharpe_ratio:.2f}",
                     _rating(metrics.sharpe_ratio, [0, 0.5, 1.0, 2.0]))
        _score_card("胜率", f"{metrics.win_rate:.2%}",
                     _rating(metrics.win_rate, [0.3, 0.45, 0.55, 0.65]))

    with col2:
        _score_card("最大回撤", f"{metrics.max_drawdown:.2%}",
                     _rating(-metrics.max_drawdown, [0, 0.1, 0.2, 0.3]))
        _score_card("盈亏比", f"{metrics.profit_factor:.2f}",
                     _rating(metrics.profit_factor, [0.5, 1.0, 1.5, 2.0]))
        _score_card("SQN", f"{metrics.sqn:.2f}",
                     _rating(metrics.sqn, [0, 1.0, 2.0, 3.0]))

    with col3:
        _score_card("Sortino比率", f"{metrics.sortino_ratio:.2f}",
                     _rating(metrics.sortino_ratio, [0, 0.5, 1.0, 2.0]))
        _score_card("Calmar比率", f"{metrics.calmar_ratio:.2f}",
                     _rating(metrics.calmar_ratio, [0, 0.5, 1.0, 2.0]))
        _score_card("Omega比率", f"{metrics.omega_ratio:.2f}",
                     _rating(metrics.omega_ratio, [0.5, 1.0, 1.5, 2.0]))

    # 买入持有对比
    st.markdown("---")
    st.markdown("#### 📊 与买入持有对比")
    bh_return = (data['close'].iloc[-1] / data['close'].iloc[0]) - 1
    excess = metrics.annual_return - bh_return

    col_bh1, col_bh2, col_bh3 = st.columns(3)
    with col_bh1:
        st.metric("策略年化收益", f"{metrics.annual_return:.2%}")
    with col_bh2:
        st.metric("买入持有收益", f"{bh_return:.2%}")
    with col_bh3:
        st.metric("超额收益", f"{excess:.2%}",
                  delta=f"{excess:.2%}", delta_color="normal")


@st.cache_data(ttl=3600)
def _run_backtest(symbol: str, data: pd.DataFrame, market: str):
    """运行MA交叉回测"""
    try:
        from app import MACrossStrategy

        cerebro = Cerebro(mode=ExecutionMode.VECTORIZED)
        cerebro.add_data(data, symbol)
        broker = Broker(initial_cash=100000, market=market)
        cerebro.set_broker(broker)

        strategy = MACrossStrategy()
        cerebro.add_strategy(strategy)
        metrics = cerebro.run()
        return metrics
    except Exception as e:
        st.error(f"回测错误: {e}")
        return None


def _score_card(label, value, rating):
    """评分卡片"""
    colors = ["var(--accent-red)", "var(--accent-orange)",
              "var(--accent-blue)", "var(--accent-green)"]
    color = colors[min(rating, 3)]
    pct = (rating + 1) * 25

    st.markdown(f"""
    <div style="padding:8px 0">
        <div style="display:flex; justify-content:space-between; align-items:center">
            <span style="font-size:13px; color:var(--text-secondary)">{label}</span>
            <span style="font-size:18px; font-weight:600; color:{color}">{value}</span>
        </div>
        <div class="signal-bar" style="margin-top:6px">
            <div class="signal-bar-fill" style="width:{pct}%; background:{color}"></div>
        </div>
    </div>
    """, unsafe_allow_html=True)


def _rating(value, thresholds):
    """计算评级 0-3"""
    for i, t in enumerate(thresholds):
        if value < t:
            return i
    return 3
