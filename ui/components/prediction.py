#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
涨跌概率预测组件
调用MachineLearningStrategy生成预测
"""

import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go


def render_prediction_panel(symbol: str, data: pd.DataFrame):
    """
    渲染涨跌概率预测面板

    Args:
        symbol: 股票代码
        data: 历史数据
    """
    if data is None or data.empty:
        st.warning("暂无数据")
        return

    st.markdown("### 🔮 涨跌概率预测")

    # 预测维度切换
    period = st.radio(
        "预测周期",
        ["明日", "3日", "5日", "10日"],
        horizontal=True,
        key="pred_period"
    )
    period_map = {"明日": 1, "3日": 3, "5日": 5, "10日": 10}
    forward = period_map[period]

    with st.spinner("正在计算预测..."):
        prediction = _calc_prediction(data, forward)

    if prediction is None:
        st.error("预测计算失败")
        return

    up_prob = prediction['up_prob']
    down_prob = prediction['down_prob']
    neutral_prob = 1 - up_prob - down_prob

    # Gauge仪表盘
    col1, col2 = st.columns([2, 1])

    with col1:
        fig = go.Figure(go.Indicator(
            mode="gauge+number+delta",
            value=up_prob * 100,
            domain={'x': [0, 1], 'y': [0, 1]},
            title={'text': f"上涨概率 ({period})", 'font': {'size': 18}},
            delta={'reference': 50, 'increasing': {'color': "#34c759"},
                   'decreasing': {'color': "#ff3b30"}},
            gauge={
                'axis': {'range': [0, 100], 'tickwidth': 1, 'tickcolor': "rgba(0,0,0,0.1)"},
                'bar': {'color': "#34c759" if up_prob > 0.5 else "#ff3b30"},
                'bgcolor': "white",
                'borderwidth': 0,
                'steps': [
                    {'range': [0, 30], 'color': 'rgba(255, 59, 48, 0.15)'},
                    {'range': [30, 50], 'color': 'rgba(255, 149, 0, 0.1)'},
                    {'range': [50, 70], 'color': 'rgba(0, 113, 227, 0.1)'},
                    {'range': [70, 100], 'color': 'rgba(52, 199, 89, 0.15)'},
                ],
                'threshold': {
                    'line': {'color': "rgba(0,0,0,0.3)", 'width': 2},
                    'thickness': 0.8,
                    'value': 50
                }
            }
        ))
        fig.update_layout(height=280, margin=dict(l=20, r=20, t=40, b=20))
        st.plotly_chart(fig, use_container_width=True)

    with col2:
        # 概率分布
        st.markdown(f"""
        <div class="apple-card" style="text-align:center">
            <div style="margin:12px 0">
                <span class="badge-up">上涨 {up_prob:.1%}</span>
            </div>
            <div style="margin:12px 0">
                <span class="badge-neutral">震荡 {neutral_prob:.1%}</span>
            </div>
            <div style="margin:12px 0">
                <span class="badge-down">下跌 {down_prob:.1%}</span>
            </div>
        </div>
        """, unsafe_allow_html=True)

    # Top3触发信号
    st.markdown("#### 📋 触发信号")
    signals = prediction.get('signals', [])
    if signals:
        for i, sig in enumerate(signals[:3]):
            sig_color = "var(--accent-green)" if sig['direction'] == '看多' else (
                "var(--accent-red)" if sig['direction'] == '看空' else "var(--accent-blue)")
            st.markdown(f"""
            <div class="apple-card" style="margin-bottom:8px; padding:12px 16px">
                <div style="display:flex; justify-content:space-between; align-items:center">
                    <span style="font-weight:600">{sig['name']}</span>
                    <span style="color:{sig_color}; font-weight:600; font-size:14px">{sig['direction']}</span>
                </div>
                <div style="font-size:13px; color:var(--text-secondary); margin-top:4px">{sig['desc']}</div>
            </div>
            """, unsafe_allow_html=True)
    else:
        st.info("暂无明确信号")

    # 免责声明
    st.markdown("""
    <div class="disclaimer">
        ⚠️ 以上预测基于历史数据和技术指标，仅供参考，不构成任何投资建议。
        市场有风险，投资需谨慎。
    </div>
    """, unsafe_allow_html=True)


@st.cache_data(ttl=1800)
def _calc_prediction(data: pd.DataFrame, forward: int) -> dict:
    """
    计算涨跌概率预测

    基于技术指标综合评分，不依赖外部ML库
    """
    try:
        close = data['close']
        high = data['high']
        low = data['low']
        volume = data['volume']

        signals = []
        scores = []

        # 1. MA趋势评分
        ma5 = close.rolling(5).mean().iloc[-1]
        ma20 = close.rolling(20).mean().iloc[-1]
        ma60 = close.rolling(60).mean().iloc[-1] if len(data) > 60 else ma20
        curr = close.iloc[-1]

        if ma5 > ma20 > ma60:
            scores.append(0.3)
            signals.append({"name": "均线多头排列", "direction": "看多",
                          "desc": f"MA5({ma5:.2f}) > MA20({ma20:.2f}) > MA60({ma60:.2f})"})
        elif ma5 < ma20 < ma60:
            scores.append(-0.3)
            signals.append({"name": "均线空头排列", "direction": "看空",
                          "desc": f"MA5({ma5:.2f}) < MA20({ma20:.2f}) < MA60({ma60:.2f})"})
        else:
            scores.append(0.0)

        # 2. RSI评分
        delta = close.diff()
        gain = delta.where(delta > 0, 0).rolling(14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
        rs = gain / (loss + 1e-8)
        rsi = (100 - (100 / (1 + rs))).iloc[-1]

        if rsi < 30:
            scores.append(0.25)
            signals.append({"name": "RSI超卖", "direction": "看多",
                          "desc": f"RSI={rsi:.1f}，处于超卖区间"})
        elif rsi > 70:
            scores.append(-0.25)
            signals.append({"name": "RSI超买", "direction": "看空",
                          "desc": f"RSI={rsi:.1f}，处于超买区间"})
        else:
            scores.append((50 - rsi) / 100)

        # 3. MACD评分
        ema12 = close.ewm(span=12, adjust=False).mean()
        ema26 = close.ewm(span=26, adjust=False).mean()
        macd = ema12 - ema26
        signal = macd.ewm(span=9, adjust=False).mean()
        hist = macd - signal

        if hist.iloc[-1] > 0 and hist.iloc[-2] <= 0:
            scores.append(0.2)
            signals.append({"name": "MACD金叉", "direction": "看多",
                          "desc": "MACD柱由负转正"})
        elif hist.iloc[-1] < 0 and hist.iloc[-2] >= 0:
            scores.append(-0.2)
            signals.append({"name": "MACD死叉", "direction": "看空",
                          "desc": "MACD柱由正转负"})
        else:
            scores.append(0.05 if hist.iloc[-1] > 0 else -0.05)

        # 4. 成交量评分
        vol_ma = volume.rolling(20).mean().iloc[-1]
        curr_vol = volume.iloc[-1]
        vol_ratio = curr_vol / (vol_ma + 1e-8)

        if vol_ratio > 1.5 and curr > close.iloc[-2]:
            scores.append(0.15)
            signals.append({"name": "放量上涨", "direction": "看多",
                          "desc": f"量比={vol_ratio:.2f}，价涨量增"})
        elif vol_ratio > 1.5 and curr < close.iloc[-2]:
            scores.append(-0.15)
            signals.append({"name": "放量下跌", "direction": "看空",
                          "desc": f"量比={vol_ratio:.2f}，价跌量增"})

        # 5. 动量评分
        momentum = close.pct_change(forward).iloc[-1]
        if momentum > 0.03:
            scores.append(0.1)
        elif momentum < -0.03:
            scores.append(-0.1)
        else:
            scores.append(0.0)

        # 综合概率
        total_score = sum(scores)
        up_prob = _sigmoid(total_score + 0.5)
        down_prob = _sigmoid(-total_score + 0.5)
        up_prob = min(max(up_prob, 0.05), 0.95)
        down_prob = min(max(down_prob, 0.05), 0.95)

        if up_prob + down_prob > 1:
            scale = 1.0 / (up_prob + down_prob)
            up_prob *= scale
            down_prob *= scale

        # 按信号强度排序
        signals.sort(key=lambda x: abs(x.get('strength', 0)), reverse=True)

        return {
            'up_prob': up_prob,
            'down_prob': down_prob,
            'signals': signals,
        }

    except Exception as e:
        return None


def _sigmoid(x):
    """Sigmoid函数"""
    return 1 / (1 + np.exp(-x * 3))
