#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
涨跌概率预测模块 - Apple Design Style
集成多种预测方法：技术指标综合、动量分析、波动率分析
"""

import streamlit as st
import pandas as pd
import numpy as np
from datetime import datetime


def render_prediction_panel(symbol: str, data: pd.DataFrame):
    if data is None or data.empty or len(data) < 60:
        st.warning("数据不足，至少需要60个交易日")
        return

    is_dark = st.session_state.get('dark_mode', False)

    pred_result = _comprehensive_predict(data)

    up_prob = pred_result['up_prob']
    down_prob = 100 - up_prob
    signal = pred_result['signal']
    confidence = pred_result['confidence']

    if signal == "看多":
        signal_class = "badge-up"
        signal_icon = "📈"
    elif signal == "看空":
        signal_class = "badge-down"
        signal_icon = "📉"
    else:
        signal_class = "badge-neutral"
        signal_icon = "➡️"

    up_bar_color = 'var(--accent-green)'
    down_bar_color = 'var(--accent-red)'

    st.markdown(f"""
    <div class="apple-card" style="text-align:center; padding:32px 24px;">
        <div style="font-size:14px; color:var(--text-secondary); font-weight:600; text-transform:uppercase; letter-spacing:0.04em; margin-bottom:20px;">
            涨跌概率预测
        </div>
        <div style="display:flex; justify-content:center; align-items:center; gap:24px; margin-bottom:24px;">
            <div>
                <div style="font-size:48px; font-weight:800; color:var(--accent-green); letter-spacing:-0.03em;">
                    {up_prob:.0f}%
                </div>
                <div style="font-size:13px; color:var(--text-secondary); font-weight:500;">上涨概率</div>
            </div>
            <div style="font-size:32px; color:var(--text-tertiary);">vs</div>
            <div>
                <div style="font-size:48px; font-weight:800; color:var(--accent-red); letter-spacing:-0.03em;">
                    {down_prob:.0f}%
                </div>
                <div style="font-size:13px; color:var(--text-secondary); font-weight:500;">下跌概率</div>
            </div>
        </div>
        <div style="max-width:400px; margin:0 auto 20px;">
            <div style="display:flex; height:8px; border-radius:4px; overflow:hidden; background:rgba(0,0,0,0.06);">
                <div style="width:{up_prob}%; background:var(--accent-green); border-radius:4px 0 0 4px;"></div>
                <div style="width:{down_prob}%; background:var(--accent-red); border-radius:0 4px 4px 0;"></div>
            </div>
        </div>
        <div style="margin-bottom:12px;">
            <span class="{signal_class}" style="font-size:16px; padding:8px 24px;">
                {signal_icon} {signal}
            </span>
        </div>
        <div style="font-size:13px; color:var(--text-tertiary);">
            置信度: {confidence:.0f}% · 基于多因子综合分析
        </div>
    </div>
    """, unsafe_allow_html=True)

    col1, col2 = st.columns(2)

    with col1:
        st.markdown('<div class="section-subtitle">因子贡献分析</div>', unsafe_allow_html=True)
        _render_factor_analysis(pred_result)

    with col2:
        st.markdown('<div class="section-subtitle">近期趋势</div>', unsafe_allow_html=True)
        _render_trend_analysis(data)

    st.markdown("""
    <div class="disclaimer">
        ⚠️ 以上预测仅基于技术分析，不构成投资建议。股市有风险，投资需谨慎。
        预测结果仅供参考，实际走势可能受政策、消息、资金面等多种因素影响。
    </div>
    """, unsafe_allow_html=True)


def _comprehensive_predict(data: pd.DataFrame) -> dict:
    close = data['close']
    high = data['high']
    low = data['low']
    volume = data['volume']

    factors = {}

    delta = close.diff()
    gain = delta.where(delta > 0, 0).rolling(14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
    rs = gain / (loss + 1e-8)
    rsi = (100 - (100 / (1 + rs))).iloc[-1]

    if rsi < 30:
        factors['RSI'] = {'score': 75, 'direction': 'up', 'weight': 0.15}
    elif rsi > 70:
        factors['RSI'] = {'score': 25, 'direction': 'down', 'weight': 0.15}
    else:
        rsi_score = 50 + (50 - rsi) * 0.5
        factors['RSI'] = {'score': rsi_score, 'direction': 'neutral', 'weight': 0.15}

    ema12 = close.ewm(span=12, adjust=False).mean()
    ema26 = close.ewm(span=26, adjust=False).mean()
    macd = ema12 - ema26
    macd_signal = macd.ewm(span=9, adjust=False).mean()
    macd_hist = macd - macd_signal

    if macd.iloc[-1] > macd_signal.iloc[-1] and macd_hist.iloc[-1] > 0:
        factors['MACD'] = {'score': 70, 'direction': 'up', 'weight': 0.15}
    elif macd.iloc[-1] < macd_signal.iloc[-1] and macd_hist.iloc[-1] < 0:
        factors['MACD'] = {'score': 30, 'direction': 'down', 'weight': 0.15}
    else:
        factors['MACD'] = {'score': 50, 'direction': 'neutral', 'weight': 0.15}

    ma5 = close.rolling(5).mean()
    ma20 = close.rolling(20).mean()
    ma60 = close.rolling(60).mean()

    if ma5.iloc[-1] > ma20.iloc[-1] > ma60.iloc[-1]:
        factors['均线'] = {'score': 80, 'direction': 'up', 'weight': 0.15}
    elif ma5.iloc[-1] < ma20.iloc[-1] < ma60.iloc[-1]:
        factors['均线'] = {'score': 20, 'direction': 'down', 'weight': 0.15}
    else:
        factors['均线'] = {'score': 50, 'direction': 'neutral', 'weight': 0.15}

    ret_5 = (close.iloc[-1] / close.iloc[-6] - 1) * 100 if len(close) > 5 else 0
    ret_20 = (close.iloc[-1] / close.iloc[-21] - 1) * 100 if len(close) > 20 else 0

    if ret_5 > 3 and ret_20 > 5:
        factors['动量'] = {'score': 70, 'direction': 'up', 'weight': 0.12}
    elif ret_5 < -3 and ret_20 < -5:
        factors['动量'] = {'score': 30, 'direction': 'down', 'weight': 0.12}
    else:
        factors['动量'] = {'score': 50, 'direction': 'neutral', 'weight': 0.12}

    vol_5 = close.iloc[-5:].pct_change().std() * np.sqrt(252)
    vol_20 = close.iloc[-20:].pct_change().std() * np.sqrt(252)

    if vol_5 < vol_20 * 0.8:
        factors['波动率'] = {'score': 60, 'direction': 'up', 'weight': 0.10}
    elif vol_5 > vol_20 * 1.3:
        factors['波动率'] = {'score': 35, 'direction': 'down', 'weight': 0.10}
    else:
        factors['波动率'] = {'score': 50, 'direction': 'neutral', 'weight': 0.10}

    vol_ma5 = volume.iloc[-5:].mean()
    vol_ma20 = volume.iloc[-20:].mean()
    if vol_ma5 > vol_ma20 * 1.3 and close.iloc[-1] > close.iloc[-2]:
        factors['量价'] = {'score': 72, 'direction': 'up', 'weight': 0.12}
    elif vol_ma5 > vol_ma20 * 1.3 and close.iloc[-1] < close.iloc[-2]:
        factors['量价'] = {'score': 28, 'direction': 'down', 'weight': 0.12}
    else:
        factors['量价'] = {'score': 50, 'direction': 'neutral', 'weight': 0.12}

    boll_mid = close.rolling(20).mean()
    std20 = close.rolling(20).std()
    boll_upper = boll_mid + 2 * std20
    boll_lower = boll_mid - 2 * std20

    if close.iloc[-1] < boll_lower.iloc[-1]:
        factors['布林带'] = {'score': 72, 'direction': 'up', 'weight': 0.10}
    elif close.iloc[-1] > boll_upper.iloc[-1]:
        factors['布林带'] = {'score': 28, 'direction': 'down', 'weight': 0.10}
    else:
        factors['布林带'] = {'score': 50, 'direction': 'neutral', 'weight': 0.10}

    recent_high = high.iloc[-20:].max()
    recent_low = low.iloc[-20:].min()
    price_pos = (close.iloc[-1] - recent_low) / (recent_high - recent_low + 1e-8)

    if price_pos < 0.2:
        factors['支撑阻力'] = {'score': 68, 'direction': 'up', 'weight': 0.11}
    elif price_pos > 0.8:
        factors['支撑阻力'] = {'score': 32, 'direction': 'down', 'weight': 0.11}
    else:
        factors['支撑阻力'] = {'score': 50, 'direction': 'neutral', 'weight': 0.11}

    weighted_score = sum(
        f['score'] * f['weight'] for f in factors.values()
    )

    up_prob = np.clip(weighted_score, 5, 95)

    up_factors = sum(1 for f in factors.values() if f['direction'] == 'up')
    down_factors = sum(1 for f in factors.values() if f['direction'] == 'down')
    total = len(factors)

    if up_factors > down_factors + 2:
        signal = "看多"
    elif down_factors > up_factors + 2:
        signal = "看空"
    elif up_prob > 60:
        signal = "偏多"
    elif up_prob < 40:
        signal = "偏空"
    else:
        signal = "中性"

    max_weight = max(f['weight'] for f in factors.values())
    confidence = min(95, abs(up_prob - 50) * 1.5 + 30)

    return {
        'up_prob': up_prob,
        'signal': signal,
        'confidence': confidence,
        'factors': factors,
    }


def _render_factor_analysis(pred_result: dict):
    factors = pred_result['factors']

    rows = ""
    for name, info in factors.items():
        score = info['score']
        direction = info['direction']
        weight = info['weight']

        if direction == 'up':
            bar_color = 'var(--accent-green)'
            dir_text = '↑'
        elif direction == 'down':
            bar_color = 'var(--accent-red)'
            dir_text = '↓'
        else:
            bar_color = 'var(--text-tertiary)'
            dir_text = '→'

        rows += f"""
        <div style="display:flex; align-items:center; gap:12px; margin-bottom:10px;">
            <div style="width:60px; font-size:13px; font-weight:600; color:var(--text-primary);">{name}</div>
            <div style="flex:1;">
                <div class="signal-bar">
                    <div class="signal-bar-fill" style="width:{score}%; background:{bar_color};"></div>
                </div>
            </div>
            <div style="width:30px; text-align:right; font-size:13px; font-weight:600; color:{bar_color};">
                {dir_text}
            </div>
            <div style="width:35px; text-align:right; font-size:11px; color:var(--text-tertiary);">
                {weight*100:.0f}%
            </div>
        </div>
        """

    st.markdown(f"""
    <div class="apple-card" style="padding:20px;">
        {rows}
    </div>
    """, unsafe_allow_html=True)


def _render_trend_analysis(data: pd.DataFrame):
    close = data['close']

    periods = [
        ("5日", 5),
        ("10日", 10),
        ("20日", 20),
        ("60日", 60),
    ]

    rows = ""
    for name, period in periods:
        if len(close) > period:
            ret = (close.iloc[-1] / close.iloc[-period-1] - 1) * 100
            if ret > 0:
                color = 'var(--accent-green)'
                sign = '+'
            else:
                color = 'var(--accent-red)'
                sign = ''

            rows += f"""
            <div style="display:flex; justify-content:space-between; align-items:center; padding:10px 0; border-bottom:1px solid var(--border-color);">
                <span style="font-size:14px; font-weight:500; color:var(--text-secondary);">{name}涨跌幅</span>
                <span style="font-size:16px; font-weight:700; color:{color};">{sign}{ret:.2f}%</span>
            </div>
            """

    st.markdown(f"""
    <div class="apple-card" style="padding:20px;">
        {rows}
    </div>
    """, unsafe_allow_html=True)
