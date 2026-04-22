#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
量化系统指标组件 - Apple Design Style
"""

import streamlit as st
import pandas as pd
import numpy as np


def render_quant_metrics(symbol: str, data: pd.DataFrame, market: str = None):
    if data is None or data.empty:
        st.warning("暂无数据")
        return

    close = data['close']
    high = data['high']
    low = data['low']
    volume = data['volume']

    returns = close.pct_change().dropna()

    annual_return = returns.mean() * 252 * 100
    annual_vol = returns.std() * np.sqrt(252) * 100
    sharpe = (returns.mean() / (returns.std() + 1e-8)) * np.sqrt(252)

    cummax = close.cummax()
    drawdown = (close - cummax) / cummax
    max_drawdown = drawdown.min() * 100

    calmar = annual_return / (abs(max_drawdown) + 1e-8)

    win_rate = (returns > 0).sum() / (len(returns) + 1e-8) * 100

    avg_win = returns[returns > 0].mean() if (returns > 0).any() else 0
    avg_loss = abs(returns[returns < 0].mean()) if (returns < 0).any() else 1e-8
    profit_loss_ratio = avg_win / (avg_loss + 1e-8)

    skew = returns.skew()
    kurtosis = returns.kurtosis()

    var_95 = np.percentile(returns, 5) * 100
    cvar_95 = returns[returns <= np.percentile(returns, 5)].mean() * 100

    col1, col2, col3, col4 = st.columns(4)

    metrics = [
        ("年化收益", f"{annual_return:+.2f}%", annual_return > 0),
        ("年化波动率", f"{annual_vol:.2f}%", annual_vol < 30),
        ("夏普比率", f"{sharpe:.2f}", sharpe > 1),
        ("最大回撤", f"{max_drawdown:.2f}%", max_drawdown > -20),
    ]

    for col, (label, value, is_good) in zip([col1, col2, col3, col4], metrics):
        with col:
            st.markdown(f"""
            <div class="metric-card">
                <div class="metric-label">{label}</div>
                <div class="metric-value" style="color:var(--{'accent-green' if is_good else 'accent-red'});">{value}</div>
            </div>
            """, unsafe_allow_html=True)

    col5, col6, col7, col8 = st.columns(4)

    metrics2 = [
        ("Calmar比率", f"{calmar:.2f}", calmar > 1),
        ("胜率", f"{win_rate:.1f}%", win_rate > 50),
        ("盈亏比", f"{profit_loss_ratio:.2f}", profit_loss_ratio > 1),
        ("偏度", f"{skew:.2f}", skew > 0),
    ]

    for col, (label, value, is_good) in zip([col5, col6, col7, col8], metrics2):
        with col:
            st.markdown(f"""
            <div class="metric-card">
                <div class="metric-label">{label}</div>
                <div class="metric-value" style="color:var(--{'accent-green' if is_good else 'accent-red'});">{value}</div>
            </div>
            """, unsafe_allow_html=True)

    col9, col10, col11, col12 = st.columns(4)

    metrics3 = [
        ("峰度", f"{kurtosis:.2f}", True),
        ("VaR(95%)", f"{var_95:.2f}%", var_95 > -5),
        ("CVaR(95%)", f"{cvar_95:.2f}%", cvar_95 > -8),
        ("日均收益", f"{returns.mean()*100:.4f}%", returns.mean() > 0),
    ]

    for col, (label, value, is_good) in zip([col9, col10, col11, col12], metrics3):
        with col:
            st.markdown(f"""
            <div class="metric-card">
                <div class="metric-label">{label}</div>
                <div class="metric-value" style="color:var(--{'accent-green' if is_good else 'accent-red'});">{value}</div>
            </div>
            """, unsafe_allow_html=True)

    try:
        from utils.metrics import performance_attribution
        attribution = performance_attribution(data)
        if attribution:
            st.markdown("""
            <div style="font-size:14px; font-weight:600; color:var(--text-secondary); margin-top:20px; margin-bottom:10px;">
                收益归因分析
            </div>
            """, unsafe_allow_html=True)

            attr_rows = ""
            for factor, value in attribution.items():
                if isinstance(value, (int, float)):
                    color = 'var(--accent-green)' if value >= 0 else 'var(--accent-red)'
                    attr_rows += f"""
                    <div style="display:flex; justify-content:space-between; align-items:center; padding:8px 0; border-bottom:1px solid var(--border-color);">
                        <span style="font-size:13px; color:var(--text-secondary);">{factor}</span>
                        <span style="font-size:14px; font-weight:600; color:{color};">{value:+.4f}</span>
                    </div>
                    """

            st.markdown(f"""
            <div class="apple-card" style="padding:16px 20px;">
                {attr_rows}
            </div>
            """, unsafe_allow_html=True)
    except Exception:
        pass
