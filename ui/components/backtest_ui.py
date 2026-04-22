#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
策略回测面板 - Apple Design Style
支持参数调整、多策略对比、Walkforward分析
"""

import streamlit as st
import pandas as pd
import numpy as np
from datetime import datetime, timedelta


def render_backtest_panel(symbol: str, data: pd.DataFrame):
    if data is None or data.empty:
        st.warning("暂无数据")
        return

    is_dark = st.session_state.get('dark_mode', False)

    st.markdown("""
    <div class="section-subtitle">选择策略并调整参数</div>
    """, unsafe_allow_html=True)

    col1, col2 = st.columns([1, 2])

    with col1:
        strategy_name = st.selectbox(
            "策略",
            ["MA交叉", "多因子", "自适应市场", "机器学习", "龙头战法", "北向资金"],
            key="bt_strategy_select",
            label_visibility="collapsed",
        )

        strategy_map = {
            "MA交叉": "ma_cross",
            "多因子": "multi_factor",
            "自适应市场": "adaptive",
            "机器学习": "ml",
            "龙头战法": "dragon_head",
            "北向资金": "north_bound",
        }

        params = _render_params_panel(strategy_name)

        initial_cash = st.number_input(
            "初始资金", min_value=10000, max_value=100000000,
            value=1000000, step=100000, key="bt_cash",
        )

        bt_mode = st.selectbox(
            "执行模式", ["事件驱动", "向量化"],
            key="bt_mode_select",
        )

    with col2:
        if st.button("🚀 开始回测", type="primary", use_container_width=True, key="bt_run"):
            with st.spinner("正在运行回测..."):
                _run_backtest(symbol, data, strategy_map[strategy_name], params, initial_cash, bt_mode)


def _render_params_panel(strategy_name: str) -> dict:
    params = {}

    if strategy_name == "MA交叉":
        params['fast_period'] = st.slider("快线周期", 3, 30, 5, key="bt_fast")
        params['slow_period'] = st.slider("慢线周期", 10, 120, 20, key="bt_slow")

    elif strategy_name == "多因子":
        params['momentum_weight'] = st.slider("动量权重", 0.0, 1.0, 0.3, 0.05, key="bt_mom_w")
        params['value_weight'] = st.slider("价值权重", 0.0, 1.0, 0.3, 0.05, key="bt_val_w")
        params['quality_weight'] = st.slider("质量权重", 0.0, 1.0, 0.4, 0.05, key="bt_qual_w")

    elif strategy_name == "自适应市场":
        params['lookback'] = st.slider("回看周期", 10, 100, 30, key="bt_lookback")
        params['regime_threshold'] = st.slider("市场状态阈值", 0.1, 2.0, 0.5, 0.1, key="bt_regime")

    elif strategy_name == "机器学习":
        params['train_ratio'] = st.slider("训练集比例", 0.5, 0.9, 0.7, 0.05, key="bt_train_ratio")
        params['n_estimators'] = st.slider("树数量", 50, 500, 100, 50, key="bt_n_est")

    elif strategy_name == "龙头战法":
        params['volume_ratio'] = st.slider("放量倍数", 1.5, 5.0, 2.0, 0.5, key="bt_vol_ratio")
        params['hold_days'] = st.slider("持仓天数", 3, 30, 10, key="bt_hold_days")

    elif strategy_name == "北向资金":
        params['flow_threshold'] = st.slider("资金流入阈值(亿)", 1.0, 50.0, 10.0, 1.0, key="bt_flow_th")
        params['hold_days'] = st.slider("持仓天数", 3, 30, 5, key="bt_flow_hold")

    return params


def _run_backtest(symbol, data, strategy_key, params, initial_cash, bt_mode):
    try:
        from core.engine import Cerebro, Broker, ExecutionMode
        from strategies.ma_cross import MACrossStrategy
        from strategies.advanced_strategies import (
            MultiFactorStrategy, AdaptiveMarketRegimeStrategy, MachineLearningStrategy
        )
        from strategies.market_strategies.cn_strategies import DragonHeadStrategy, NorthBoundFlowStrategy

        strategy_classes = {
            'ma_cross': MACrossStrategy,
            'multi_factor': MultiFactorStrategy,
            'adaptive': AdaptiveMarketRegimeStrategy,
            'ml': MachineLearningStrategy,
            'dragon_head': DragonHeadStrategy,
            'north_bound': NorthBoundFlowStrategy,
        }

        if strategy_key not in strategy_classes:
            st.error(f"未知策略: {strategy_key}")
            return

        exec_mode = ExecutionMode.EVENT_DRIVEN if bt_mode == "事件驱动" else ExecutionMode.VECTORIZED

        cerebro = Cerebro(mode=exec_mode)
        cerebro.add_data(data, symbol)

        from data.market_detector import MarketDetector
        market = MarketDetector.detect(symbol)
        broker = Broker(initial_cash=initial_cash, market=market)
        cerebro.set_broker(broker)

        strategy = strategy_classes[strategy_key](**params)
        cerebro.add_strategy(strategy)

        metrics = cerebro.run(progress_bar=True)

        _render_backtest_results(metrics, initial_cash)

    except Exception as e:
        st.error(f"回测执行失败: {e}")


def _render_backtest_results(metrics, initial_cash):
    is_dark = st.session_state.get('dark_mode', False)

    total_return = getattr(metrics, 'total_return', 0) * 100
    annual_return = getattr(metrics, 'annual_return', 0) * 100
    max_drawdown = getattr(metrics, 'max_drawdown', 0) * 100
    sharpe = getattr(metrics, 'sharpe_ratio', 0)
    win_rate = getattr(metrics, 'win_rate', 0) * 100
    total_trades = getattr(metrics, 'total_trades', 0)
    profit_factor = getattr(metrics, 'profit_factor', 0)
    calmar = getattr(metrics, 'calmar_ratio', 0)

    is_profit = total_return >= 0
    return_class = "badge-up" if is_profit else "badge-down"

    st.markdown(f"""
    <div class="apple-card" style="text-align:center; padding:28px 24px; margin-bottom:20px;">
        <div style="font-size:14px; color:var(--text-secondary); font-weight:600; text-transform:uppercase; letter-spacing:0.04em; margin-bottom:12px;">
            回测结果
        </div>
        <div style="font-size:48px; font-weight:800; color:var(--{'accent-green' if is_profit else 'accent-red'}); letter-spacing:-0.03em;">
            {total_return:+.2f}%
        </div>
        <div style="margin-top:8px;">
            <span class="{return_class}">总收益</span>
        </div>
    </div>
    """, unsafe_allow_html=True)

    col1, col2, col3, col4 = st.columns(4)

    items = [
        ("年化收益", f"{annual_return:+.2f}%", annual_return >= 0),
        ("最大回撤", f"{max_drawdown:.2f}%", False),
        ("夏普比率", f"{sharpe:.2f}", sharpe >= 1),
        ("胜率", f"{win_rate:.1f}%", win_rate >= 50),
    ]

    for col, (label, value, is_good) in zip([col1, col2, col3, col4], items):
        with col:
            st.markdown(f"""
            <div class="metric-card">
                <div class="metric-label">{label}</div>
                <div class="metric-value" style="color:var(--{'accent-green' if is_good else 'accent-red'});">{value}</div>
            </div>
            """, unsafe_allow_html=True)

    col5, col6, col7, col8 = st.columns(4)

    items2 = [
        ("总交易次数", f"{total_trades}", True),
        ("盈亏比", f"{profit_factor:.2f}", profit_factor >= 1),
        ("Calmar比率", f"{calmar:.2f}", calmar >= 1),
        ("初始资金", f"¥{initial_cash:,.0f}", True),
    ]

    for col, (label, value, is_good) in zip([col5, col6, col7, col8], items2):
        with col:
            st.markdown(f"""
            <div class="metric-card">
                <div class="metric-label">{label}</div>
                <div class="metric-value" style="color:var(--{'accent-green' if is_good else 'accent-red'});">{value}</div>
            </div>
            """, unsafe_allow_html=True)

    try:
        equity_curve = getattr(metrics, 'equity_curve', None)
        if equity_curve is not None and len(equity_curve) > 0:
            import plotly.graph_objects as go

            bg_color = '#000000' if is_dark else 'white'
            text_color = '#f5f5f7' if is_dark else '#1d1d1f'
            grid_color = 'rgba(255,255,255,0.06)' if is_dark else 'rgba(0,0,0,0.05)'
            line_color = '#0a84ff' if is_dark else '#0071e3'

            fig = go.Figure()
            fig.add_trace(go.Scatter(
                y=equity_curve,
                mode='lines',
                name='权益曲线',
                line=dict(color=line_color, width=2),
                fill='tozeroy',
                fillcolor=f'rgba(10, 132, 255, 0.1)' if is_dark else 'rgba(0, 113, 227, 0.1)',
            ))

            fig.update_layout(
                height=300,
                plot_bgcolor=bg_color,
                paper_bgcolor=bg_color,
                font=dict(family="-apple-system, BlinkMacSystemFont, sans-serif", size=12, color=text_color),
                margin=dict(l=50, r=20, t=20, b=20),
                xaxis_title="交易日",
                yaxis_title="权益",
                showlegend=False,
            )
            fig.update_xaxes(showgrid=True, gridcolor=grid_color)
            fig.update_yaxes(showgrid=True, gridcolor=grid_color)

            st.plotly_chart(fig, use_container_width=True)
    except Exception:
        pass
