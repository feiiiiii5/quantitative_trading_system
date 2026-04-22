#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
技术指标面板 - Apple Design Style
支持 MACD, RSI, KDJ, BOLL, ATR, OBV, CCI, WR, DMI, SAR
"""

import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots


def render_technical_indicators(data: pd.DataFrame):
    if data is None or data.empty:
        st.warning("暂无数据")
        return

    is_dark = st.session_state.get('dark_mode', False)

    indicators = st.multiselect(
        "选择技术指标",
        ["MACD", "RSI", "KDJ", "BOLL", "ATR", "OBV", "CCI", "WR", "DMI", "SAR"],
        default=["MACD", "RSI", "KDJ"],
        key="tech_indicators_select",
    )

    if not indicators:
        return

    df = _calc_all_indicators(data.copy())

    n_subplots = len(indicators) + 1
    row_heights = [0.4] + [0.6 / len(indicators)] * len(indicators)

    fig = make_subplots(
        rows=n_subplots, cols=1,
        shared_xaxes=True,
        vertical_spacing=0.04,
        row_heights=row_heights,
    )

    up_color = '#30d158' if is_dark else '#34c759'
    down_color = '#ff453a' if is_dark else '#ff3b30'
    bg_color = '#000000' if is_dark else 'white'
    text_color = '#f5f5f7' if is_dark else '#1d1d1f'
    grid_color = 'rgba(255,255,255,0.06)' if is_dark else 'rgba(0,0,0,0.05)'

    fig.add_trace(go.Candlestick(
        x=df.index, open=df['open'], high=df['high'],
        low=df['low'], close=df['close'],
        name='K线',
        increasing_line_color=up_color, decreasing_line_color=down_color,
        increasing_fillcolor=up_color, decreasing_fillcolor=down_color,
    ), row=1, col=1)

    row_idx = 2
    for indicator in indicators:
        if indicator == "MACD":
            _add_macd(fig, df, row_idx, is_dark)
        elif indicator == "RSI":
            _add_rsi(fig, df, row_idx, is_dark)
        elif indicator == "KDJ":
            _add_kdj(fig, df, row_idx, is_dark)
        elif indicator == "BOLL":
            _add_boll(fig, df, 1, is_dark)
            row_idx -= 1
        elif indicator == "ATR":
            _add_atr(fig, df, row_idx, is_dark)
        elif indicator == "OBV":
            _add_obv(fig, df, row_idx, is_dark)
        elif indicator == "CCI":
            _add_cci(fig, df, row_idx, is_dark)
        elif indicator == "WR":
            _add_wr(fig, df, row_idx, is_dark)
        elif indicator == "DMI":
            _add_dmi(fig, df, row_idx, is_dark)
        elif indicator == "SAR":
            _add_sar(fig, df, 1, is_dark)
            row_idx -= 1

        row_idx += 1

    fig.update_layout(
        height=200 + len(indicators) * 150,
        xaxis_rangeslider_visible=False,
        plot_bgcolor=bg_color,
        paper_bgcolor=bg_color,
        font=dict(family="-apple-system, BlinkMacSystemFont, sans-serif", size=12, color=text_color),
        margin=dict(l=50, r=20, t=30, b=20),
        showlegend=True,
        legend=dict(
            orientation="h", yanchor="bottom", y=1.02,
            xanchor="right", x=1, font=dict(size=10, color=text_color),
        ),
    )
    fig.update_xaxes(showgrid=True, gridcolor=grid_color)
    fig.update_yaxes(showgrid=True, gridcolor=grid_color)

    st.plotly_chart(fig, use_container_width=True)

    _render_signal_summary(df, indicators)


def _calc_all_indicators(df: pd.DataFrame) -> pd.DataFrame:
    close = df['close']
    high = df['high']
    low = df['low']

    ema12 = close.ewm(span=12, adjust=False).mean()
    ema26 = close.ewm(span=26, adjust=False).mean()
    df['macd'] = ema12 - ema26
    df['macd_signal'] = df['macd'].ewm(span=9, adjust=False).mean()
    df['macd_hist'] = df['macd'] - df['macd_signal']

    delta = close.diff()
    gain = delta.where(delta > 0, 0).rolling(14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
    rs = gain / (loss + 1e-8)
    df['rsi'] = 100 - (100 / (1 + rs))

    low_9 = low.rolling(9).min()
    high_9 = high.rolling(9).max()
    rsv = (close - low_9) / (high_9 - low_9 + 1e-8) * 100
    df['k'] = rsv.ewm(com=2, adjust=False).mean()
    df['d'] = df['k'].ewm(com=2, adjust=False).mean()
    df['j'] = 3 * df['k'] - 2 * df['d']

    df['boll_mid'] = close.rolling(20).mean()
    std20 = close.rolling(20).std()
    df['boll_upper'] = df['boll_mid'] + 2 * std20
    df['boll_lower'] = df['boll_mid'] - 2 * std20

    tr = pd.concat([
        high - low,
        (high - close.shift(1)).abs(),
        (low - close.shift(1)).abs()
    ], axis=1).max(axis=1)
    df['atr'] = tr.rolling(14).mean()

    df['obv'] = (np.sign(close.diff()) * df['volume']).cumsum()

    tp = (high + low + close) / 3
    ma_tp = tp.rolling(20).mean()
    md = tp.rolling(20).apply(lambda x: np.abs(x - x.mean()).mean(), raw=True)
    df['cci'] = (tp - ma_tp) / (0.015 * md + 1e-8)

    high_14 = high.rolling(14).max()
    low_14 = low.rolling(14).min()
    df['wr'] = (high_14 - close) / (high_14 - low_14 + 1e-8) * -100

    plus_dm = high.diff()
    minus_dm = -low.diff()
    plus_dm = plus_dm.where((plus_dm > minus_dm) & (plus_dm > 0), 0)
    minus_dm = minus_dm.where((minus_dm > plus_dm) & (minus_dm > 0), 0)
    atr14 = tr.rolling(14).mean()
    plus_di = 100 * plus_dm.rolling(14).mean() / (atr14 + 1e-8)
    minus_di = 100 * minus_dm.rolling(14).mean() / (atr14 + 1e-8)
    dx = 100 * (plus_di - minus_di).abs() / (plus_di + minus_di + 1e-8)
    df['adx'] = dx.rolling(14).mean()
    df['plus_di'] = plus_di
    df['minus_di'] = minus_di

    return df


def _add_macd(fig, df, row, is_dark):
    blue = '#0a84ff' if is_dark else '#0071e3'
    orange = '#ff9f0a' if is_dark else '#ff9500'
    up = '#30d158' if is_dark else '#34c759'
    down = '#ff453a' if is_dark else '#ff3b30'

    fig.add_trace(go.Scatter(
        x=df.index, y=df['macd'], mode='lines', name='MACD',
        line=dict(color=blue, width=1.5),
    ), row=row, col=1)
    fig.add_trace(go.Scatter(
        x=df.index, y=df['macd_signal'], mode='lines', name='Signal',
        line=dict(color=orange, width=1.5),
    ), row=row, col=1)
    colors = [up if v >= 0 else down for v in df['macd_hist'].fillna(0)]
    fig.add_trace(go.Bar(
        x=df.index, y=df['macd_hist'], name='Hist',
        marker_color=colors, showlegend=False,
    ), row=row, col=1)


def _add_rsi(fig, df, row, is_dark):
    purple = '#bf5af2' if is_dark else '#af52de'
    red = '#ff453a' if is_dark else '#ff3b30'
    green = '#30d158' if is_dark else '#34c759'

    fig.add_trace(go.Scatter(
        x=df.index, y=df['rsi'], mode='lines', name='RSI',
        line=dict(color=purple, width=1.5),
    ), row=row, col=1)
    fig.add_hline(y=70, line_dash="dash", line_color=red, row=row, col=1)
    fig.add_hline(y=30, line_dash="dash", line_color=green, row=row, col=1)


def _add_kdj(fig, df, row, is_dark):
    blue = '#0a84ff' if is_dark else '#0071e3'
    orange = '#ff9f0a' if is_dark else '#ff9500'
    purple = '#bf5af2' if is_dark else '#af52de'

    fig.add_trace(go.Scatter(
        x=df.index, y=df['k'], mode='lines', name='K',
        line=dict(color=blue, width=1.5),
    ), row=row, col=1)
    fig.add_trace(go.Scatter(
        x=df.index, y=df['d'], mode='lines', name='D',
        line=dict(color=orange, width=1.5),
    ), row=row, col=1)
    fig.add_trace(go.Scatter(
        x=df.index, y=df['j'], mode='lines', name='J',
        line=dict(color=purple, width=1.5),
    ), row=row, col=1)


def _add_boll(fig, df, row, is_dark):
    blue = '#0a84ff' if is_dark else '#0071e3'
    fig.add_trace(go.Scatter(
        x=df.index, y=df['boll_upper'], mode='lines', name='BOLL上轨',
        line=dict(color=blue, width=1, dash='dash'), opacity=0.6,
    ), row=row, col=1)
    fig.add_trace(go.Scatter(
        x=df.index, y=df['boll_mid'], mode='lines', name='BOLL中轨',
        line=dict(color=blue, width=1.5),
    ), row=row, col=1)
    fig.add_trace(go.Scatter(
        x=df.index, y=df['boll_lower'], mode='lines', name='BOLL下轨',
        line=dict(color=blue, width=1, dash='dash'), opacity=0.6,
    ), row=row, col=1)


def _add_atr(fig, df, row, is_dark):
    teal = '#64d2ff' if is_dark else '#5ac8fa'
    fig.add_trace(go.Scatter(
        x=df.index, y=df['atr'], mode='lines', name='ATR',
        line=dict(color=teal, width=1.5),
    ), row=row, col=1)


def _add_obv(fig, df, row, is_dark):
    teal = '#64d2ff' if is_dark else '#5ac8fa'
    fig.add_trace(go.Scatter(
        x=df.index, y=df['obv'], mode='lines', name='OBV',
        line=dict(color=teal, width=1.5),
    ), row=row, col=1)


def _add_cci(fig, df, row, is_dark):
    purple = '#bf5af2' if is_dark else '#af52de'
    fig.add_trace(go.Scatter(
        x=df.index, y=df['cci'], mode='lines', name='CCI',
        line=dict(color=purple, width=1.5),
    ), row=row, col=1)
    fig.add_hline(y=100, line_dash="dash", line_color='rgba(255,69,58,0.5)', row=row, col=1)
    fig.add_hline(y=-100, line_dash="dash", line_color='rgba(48,209,88,0.5)', row=row, col=1)


def _add_wr(fig, df, row, is_dark):
    orange = '#ff9f0a' if is_dark else '#ff9500'
    fig.add_trace(go.Scatter(
        x=df.index, y=df['wr'], mode='lines', name='WR',
        line=dict(color=orange, width=1.5),
    ), row=row, col=1)
    fig.add_hline(y=-20, line_dash="dash", line_color='rgba(255,69,58,0.5)', row=row, col=1)
    fig.add_hline(y=-80, line_dash="dash", line_color='rgba(48,209,88,0.5)', row=row, col=1)


def _add_dmi(fig, df, row, is_dark):
    blue = '#0a84ff' if is_dark else '#0071e3'
    orange = '#ff9f0a' if is_dark else '#ff9500'
    purple = '#bf5af2' if is_dark else '#af52de'

    fig.add_trace(go.Scatter(
        x=df.index, y=df['plus_di'], mode='lines', name='+DI',
        line=dict(color=blue, width=1.5),
    ), row=row, col=1)
    fig.add_trace(go.Scatter(
        x=df.index, y=df['minus_di'], mode='lines', name='-DI',
        line=dict(color=orange, width=1.5),
    ), row=row, col=1)
    fig.add_trace(go.Scatter(
        x=df.index, y=df['adx'], mode='lines', name='ADX',
        line=dict(color=purple, width=1.5),
    ), row=row, col=1)


def _add_sar(fig, df, row, is_dark):
    orange = '#ff9f0a' if is_dark else '#ff9500'
    try:
        high = df['high'].values
        low = df['low'].values
        close = df['close'].values

        sar = _calc_sar(high, low)
        df['sar'] = sar

        fig.add_trace(go.Scatter(
            x=df.index, y=df['sar'], mode='markers', name='SAR',
            marker=dict(color=orange, size=3, symbol='diamond'),
        ), row=row, col=1)
    except Exception:
        pass


def _calc_sar(high, low, af_step=0.02, af_max=0.2):
    n = len(high)
    sar = np.zeros(n)
    trend = np.ones(n)
    ep = high[0]
    af = af_step
    sar[0] = low[0]

    for i in range(1, n):
        sar[i] = sar[i-1] + af * (ep - sar[i-1])

        if trend[i-1] == 1:
            if low[i] < sar[i]:
                trend[i] = -1
                sar[i] = ep
                ep = low[i]
                af = af_step
            else:
                trend[i] = 1
                if high[i] > ep:
                    ep = high[i]
                    af = min(af + af_step, af_max)
        else:
            if high[i] > sar[i]:
                trend[i] = 1
                sar[i] = ep
                ep = high[i]
                af = af_step
            else:
                trend[i] = -1
                if low[i] < ep:
                    ep = low[i]
                    af = min(af + af_step, af_max)

    return sar


def _render_signal_summary(df: pd.DataFrame, indicators: list):
    latest = df.iloc[-1]
    signals = []

    if "MACD" in indicators:
        if latest['macd'] > latest['macd_signal'] and latest['macd_hist'] > 0:
            signals.append(("MACD", "看多", "badge-up"))
        elif latest['macd'] < latest['macd_signal'] and latest['macd_hist'] < 0:
            signals.append(("MACD", "看空", "badge-down"))
        else:
            signals.append(("MACD", "中性", "badge-neutral"))

    if "RSI" in indicators:
        rsi_val = latest.get('rsi', 50)
        if rsi_val > 70:
            signals.append(("RSI", "超买", "badge-down"))
        elif rsi_val < 30:
            signals.append(("RSI", "超卖", "badge-up"))
        else:
            signals.append(("RSI", "中性", "badge-neutral"))

    if "KDJ" in indicators:
        j_val = latest.get('j', 50)
        if j_val > 100:
            signals.append(("KDJ", "超买", "badge-down"))
        elif j_val < 0:
            signals.append(("KDJ", "超卖", "badge-up"))
        else:
            signals.append(("KDJ", "中性", "badge-neutral"))

    if "CCI" in indicators:
        cci_val = latest.get('cci', 0)
        if cci_val > 100:
            signals.append(("CCI", "超买", "badge-down"))
        elif cci_val < -100:
            signals.append(("CCI", "超卖", "badge-up"))
        else:
            signals.append(("CCI", "中性", "badge-neutral"))

    if "WR" in indicators:
        wr_val = latest.get('wr', -50)
        if wr_val > -20:
            signals.append(("WR", "超买", "badge-down"))
        elif wr_val < -80:
            signals.append(("WR", "超卖", "badge-up"))
        else:
            signals.append(("WR", "中性", "badge-neutral"))

    if signals:
        signals_html = " ".join([
            f'<span class="{cls}" style="margin:4px 0;">{name}: {sig}</span>'
            for name, sig, cls in signals
        ])
        st.markdown(f"""
        <div class="apple-card" style="padding:16px 20px; margin-top:16px;">
            <div style="font-size:12px; color:var(--text-secondary); font-weight:600; text-transform:uppercase; letter-spacing:0.04em; margin-bottom:10px;">
                信号汇总
            </div>
            <div style="display:flex; gap:10px; flex-wrap:wrap;">
                {signals_html}
            </div>
        </div>
        """, unsafe_allow_html=True)
