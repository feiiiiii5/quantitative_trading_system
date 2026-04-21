#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
技术指标面板组件
分4组展示：趋势/动量/成交量/波动性
"""

import streamlit as st
import pandas as pd
import numpy as np


def render_technical_indicators(data: pd.DataFrame):
    """
    渲染技术指标面板

    Args:
        data: 历史数据DataFrame
    """
    if data is None or data.empty:
        st.warning("暂无数据")
        return

    indicators = _calc_all_indicators(data)

    tab1, tab2, tab3, tab4 = st.tabs(["📈 趋势", "⚡ 动量", "📊 成交量", "🌊 波动性"])

    with tab1:
        _render_trend_tab(data, indicators)
    with tab2:
        _render_momentum_tab(data, indicators)
    with tab3:
        _render_volume_tab(data, indicators)
    with tab4:
        _render_volatility_tab(data, indicators)


def _calc_all_indicators(data: pd.DataFrame) -> dict:
    """计算所有技术指标"""
    close = data['close']
    high = data['high']
    low = data['low']
    volume = data['volume']
    ind = {}

    # 趋势指标
    for p in [5, 10, 20, 60]:
        ind[f'ma{p}'] = close.rolling(p).mean()
        ind[f'ema{p}'] = close.ewm(span=p, adjust=False).mean()

    ind['ema12'] = close.ewm(span=12, adjust=False).mean()
    ind['ema26'] = close.ewm(span=26, adjust=False).mean()

    bb_ma = close.rolling(20).mean()
    bb_std = close.rolling(20).std()
    ind['boll_upper'] = bb_ma + 2 * bb_std
    ind['boll_mid'] = bb_ma
    ind['boll_lower'] = bb_ma - 2 * bb_std

    # 金叉死叉信号
    ma5 = ind['ma5']
    ma20 = ind['ma20']
    ind['golden_cross'] = (ma5 > ma20) & (ma5.shift(1) <= ma20.shift(1))
    ind['death_cross'] = (ma5 < ma20) & (ma5.shift(1) >= ma20.shift(1))

    # 动量指标
    delta = close.diff()
    gain = delta.where(delta > 0, 0).rolling(14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
    rs = gain / (loss + 1e-8)
    ind['rsi'] = 100 - (100 / (1 + rs))

    ema12 = close.ewm(span=12, adjust=False).mean()
    ema26 = close.ewm(span=26, adjust=False).mean()
    ind['macd'] = ema12 - ema26
    ind['macd_signal'] = ind['macd'].ewm(span=9, adjust=False).mean()
    ind['macd_hist'] = ind['macd'] - ind['macd_signal']

    low_min = low.rolling(9).min()
    high_max = high.rolling(9).max()
    rsv = (close - low_min) / (high_max - low_min + 1e-8) * 100
    ind['k'] = rsv.ewm(com=2, adjust=False).mean()
    ind['d'] = ind['k'].ewm(com=2, adjust=False).mean()
    ind['j'] = 3 * ind['k'] - 2 * ind['d']

    tp = (high + low + close) / 3
    ind['cci'] = (tp - tp.rolling(14).mean()) / (0.015 * tp.rolling(14).std() + 1e-8)
    ind['roc'] = close.pct_change(12) * 100

    # 成交量指标
    ind['obv'] = (np.sign(close.diff()) * volume).cumsum()
    vol_ma5 = volume.rolling(5).mean()
    vol_ma20 = volume.rolling(20).mean()
    ind['vol_ratio'] = vol_ma5 / (vol_ma20 + 1e-8)

    # 波动性指标
    tr1 = high - low
    tr2 = abs(high - close.shift(1))
    tr3 = abs(low - close.shift(1))
    tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
    ind['atr'] = tr.rolling(14).mean()
    ind['hist_vol'] = close.pct_change().rolling(20).std() * np.sqrt(252) * 100

    return ind


def _render_trend_tab(data, ind):
    """趋势指标标签页"""
    close = data['close'].iloc[-1]

    cols = st.columns(3)

    # MA/EMA
    with cols[0]:
        _indicator_card("MA5", f"{ind['ma5'].iloc[-1]:.2f}",
                        _trend_signal(close, ind['ma5'].iloc[-1]),
                        _signal_strength(close, ind['ma5'].iloc[-1]))
    with cols[1]:
        _indicator_card("MA20", f"{ind['ma20'].iloc[-1]:.2f}",
                        _trend_signal(close, ind['ma20'].iloc[-1]),
                        _signal_strength(close, ind['ma20'].iloc[-1]))
    with cols[2]:
        _indicator_card("MA60", f"{ind['ma60'].iloc[-1]:.2f}",
                        _trend_signal(close, ind['ma60'].iloc[-1]),
                        _signal_strength(close, ind['ma60'].iloc[-1]))

    cols2 = st.columns(3)
    with cols2[0]:
        ema12_val = ind.get('ema12', close)
        _indicator_card("EMA12", f"{ema12_val.iloc[-1]:.2f}",
                        _trend_signal(close, ema12_val.iloc[-1]),
                        _signal_strength(close, ema12_val.iloc[-1]))
    with cols2[1]:
        ema26_val = ind.get('ema26', close)
        _indicator_card("EMA26", f"{ema26_val.iloc[-1]:.2f}",
                        _trend_signal(close, ema26_val.iloc[-1]),
                        _signal_strength(close, ema26_val.iloc[-1]))

    # 布林带
    with cols2[2]:
        bb_pos = (close - ind['boll_lower'].iloc[-1]) / (ind['boll_upper'].iloc[-1] - ind['boll_lower'].iloc[-1] + 1e-8)
        if bb_pos > 0.8:
            sig = "超买 ⚠️"
        elif bb_pos < 0.2:
            sig = "超卖 ⚠️"
        else:
            sig = "中性"
        _indicator_card("BOLL", f"{ind['boll_mid'].iloc[-1]:.2f}", sig, int(bb_pos * 100))

    # 金叉死叉信号
    gc = ind['golden_cross'].iloc[-1] if len(ind['golden_cross']) > 0 else False
    dc = ind['death_cross'].iloc[-1] if len(ind['death_cross']) > 0 else False
    if gc:
        st.markdown('<span class="badge-up">🔥 金叉信号</span>', unsafe_allow_html=True)
    elif dc:
        st.markdown('<span class="badge-down">💀 死叉信号</span>', unsafe_allow_html=True)


def _render_momentum_tab(data, ind):
    """动量指标标签页"""
    cols = st.columns(3)

    rsi_val = ind['rsi'].iloc[-1]
    rsi_sig = "超买" if rsi_val > 70 else ("超卖" if rsi_val < 30 else "中性")
    rsi_strength = min(int(rsi_val), 100)
    _indicator_card("RSI(14)", f"{rsi_val:.1f}", rsi_sig, rsi_strength, parent=cols[0])

    macd_val = ind['macd'].iloc[-1]
    macd_sig = "多头" if macd_val > 0 else "空头"
    _indicator_card("MACD", f"{macd_val:.4f}", macd_sig,
                    70 if macd_val > 0 else 30, parent=cols[1])

    k_val = ind['k'].iloc[-1]
    d_val = ind['d'].iloc[-1]
    j_val = ind['j'].iloc[-1]
    kdj_sig = "超买" if k_val > 80 else ("超卖" if k_val < 20 else "中性")
    _indicator_card("KDJ", f"K:{k_val:.1f} D:{d_val:.1f} J:{j_val:.1f}",
                    kdj_sig, min(int(k_val), 100), parent=cols[2])

    cols2 = st.columns(2)
    cci_val = ind['cci'].iloc[-1]
    cci_sig = "超买" if cci_val > 100 else ("超卖" if cci_val < -100 else "中性")
    _indicator_card("CCI", f"{cci_val:.1f}", cci_sig,
                    min(max(int((cci_val + 200) / 4), 0), 100), parent=cols2[0])

    roc_val = ind['roc'].iloc[-1]
    roc_sig = "上涨" if roc_val > 0 else "下跌"
    _indicator_card("ROC", f"{roc_val:.2f}%", roc_sig,
                    70 if roc_val > 0 else 30, parent=cols2[1])


def _render_volume_tab(data, ind):
    """成交量指标标签页"""
    cols = st.columns(2)

    obv_val = ind['obv'].iloc[-1]
    obv_prev = ind['obv'].iloc[-2] if len(ind['obv']) > 1 else obv_val
    obv_sig = "放量" if obv_val > obv_prev else "缩量"
    _indicator_card("OBV", f"{obv_val:,.0f}", obv_sig,
                    70 if obv_val > obv_prev else 30, parent=cols[0])

    vr_val = ind['vol_ratio'].iloc[-1]
    vr_sig = "放量" if vr_val > 1.5 else ("缩量" if vr_val < 0.5 else "正常")
    _indicator_card("量比", f"{vr_val:.2f}", vr_sig,
                    min(int(vr_val * 50), 100), parent=cols[1])

    # 量价背离检测
    close_chg = data['close'].pct_change(5).iloc[-1]
    vol_chg = data['volume'].rolling(5).mean().pct_change(5).iloc[-1]
    if close_chg > 0.02 and vol_chg < -0.1:
        st.markdown('<span class="badge-down">⚠️ 量价背离：价涨量缩</span>', unsafe_allow_html=True)
    elif close_chg < -0.02 and vol_chg > 0.1:
        st.markdown('<span class="badge-up">⚠️ 量价背离：价跌量增（可能见底）</span>', unsafe_allow_html=True)


def _render_volatility_tab(data, ind):
    """波动性指标标签页"""
    cols = st.columns(2)

    atr_val = ind['atr'].iloc[-1]
    atr_pct = atr_val / data['close'].iloc[-1] * 100
    atr_sig = "高波动" if atr_pct > 3 else ("低波动" if atr_pct < 1 else "正常")
    _indicator_card("ATR(14)", f"{atr_val:.2f} ({atr_pct:.1f}%)", atr_sig,
                    min(int(atr_pct * 25), 100), parent=cols[0])

    hv_val = ind['hist_vol'].iloc[-1]
    hv_sig = "高波动" if hv_val > 30 else ("低波动" if hv_val < 15 else "正常")
    _indicator_card("历史波动率", f"{hv_val:.1f}%", hv_sig,
                    min(int(hv_val * 2), 100), parent=cols[1])


def _indicator_card(name, value, signal, strength, parent=None):
    """渲染单个指标卡片"""
    if signal in ("超买", "多头", "上涨", "放量", "高波动"):
        sig_color = "var(--accent-green)"
    elif signal in ("超卖", "空头", "下跌", "缩量", "低波动"):
        sig_color = "var(--accent-red)"
    else:
        sig_color = "var(--accent-blue)"

    strength = max(0, min(100, int(strength)))

    html = f"""
    <div class="metric-card" style="text-align:left; padding:16px">
        <div class="metric-label">{name}</div>
        <div class="metric-value" style="font-size:20px; margin:6px 0">{value}</div>
        <div style="color:{sig_color}; font-size:13px; font-weight:600; margin-bottom:8px">{signal}</div>
        <div class="signal-bar">
            <div class="signal-bar-fill" style="width:{strength}%; background:{sig_color}"></div>
        </div>
    </div>
    """

    if parent:
        parent.markdown(html, unsafe_allow_html=True)
    else:
        st.markdown(html, unsafe_allow_html=True)


def _trend_signal(price, ma):
    """判断趋势信号"""
    if price > ma:
        return "多头 ▲"
    else:
        return "空头 ▼"


def _signal_strength(price, ma):
    """计算信号强度"""
    diff = abs(price - ma) / ma * 100
    return min(int(diff * 20), 100)
