#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
可视化回测UI组件
"""

import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime, timedelta

from core.engine import Cerebro, Broker, ExecutionMode
from data.async_data_manager import AsyncDataManager
from data.market_detector import MarketDetector


def render_backtest_panel(symbol: str, data: pd.DataFrame):
    """
    渲染回测面板

    Args:
        symbol: 股票代码
        data: 历史数据
    """
    st.markdown("### 🔄 策略回测")

    col1, col2 = st.columns([1, 2])

    with col1:
        strategy_name = st.selectbox(
            "选择策略",
            ["MA交叉", "自适应策略", "多因子策略"],
            key="bt_strategy"
        )

        strategy_map = {
            "MA交叉": "ma_cross",
            "自适应策略": "adaptive",
            "多因子策略": "multi_factor",
        }

        # 参数配置
        st.markdown("#### 参数配置")
        if strategy_name == "MA交叉":
            fast_period = st.slider("快线周期", 3, 30, 5, key="bt_fast")
            slow_period = st.slider("慢线周期", 10, 120, 20, key="bt_slow")
            params = {'fast_period': fast_period, 'slow_period': slow_period}
        else:
            params = {}

        initial_cash = st.number_input("初始资金", value=100000, step=10000, key="bt_cash")

        run_bt = st.button("🚀 运行回测", type="primary", key="run_backtest")

    with col2:
        if run_bt:
            with st.spinner("正在运行回测..."):
                result = _run_backtest(symbol, data, strategy_map[strategy_name], params, initial_cash)

            if result is not None:
                metrics, equity_curve = result

                # 权益曲线
                fig = go.Figure()
                fig.add_trace(go.Scatter(
                    y=equity_curve,
                    mode='lines',
                    name='策略权益',
                    line=dict(color='#0071e3', width=2),
                ))
                fig.add_hline(y=initial_cash, line_dash="dash",
                             line_color="rgba(0,0,0,0.2)", annotation_text="初始资金")
                fig.update_layout(
                    height=300,
                    title="权益曲线",
                    plot_bgcolor='white',
                    margin=dict(l=50, r=20, t=40, b=30),
                    font=dict(family="-apple-system, BlinkMacSystemFont, sans-serif"),
                )
                st.plotly_chart(fig, use_container_width=True)

                # 绩效报告
                st.markdown("#### 📋 绩效报告")
                mc1, mc2, mc3, mc4 = st.columns(4)
                with mc1:
                    st.metric("总收益", f"{metrics.total_return:.2%}")
                with mc2:
                    st.metric("夏普比率", f"{metrics.sharpe_ratio:.2f}")
                with mc3:
                    st.metric("最大回撤", f"{metrics.max_drawdown:.2%}")
                with mc4:
                    st.metric("胜率", f"{metrics.win_rate:.2%}")
            else:
                st.error("回测运行失败")
        else:
            st.info("选择策略和参数后点击运行回测")


def _run_backtest(symbol, data, strategy_name, params, initial_cash):
    """运行回测"""
    try:
        from app import MACrossStrategy
        from strategies.advanced_strategies import (
            MultiFactorStrategy, AdaptiveMarketRegimeStrategy
        )

        market = MarketDetector.detect(symbol)

        cerebro = Cerebro(mode=ExecutionMode.VECTORIZED)
        cerebro.add_data(data, symbol)
        broker = Broker(initial_cash=initial_cash, market=market)
        cerebro.set_broker(broker)

        if strategy_name == 'ma_cross':
            strategy = MACrossStrategy(**params)
        elif strategy_name == 'adaptive':
            strategy = AdaptiveMarketRegimeStrategy(**params)
        elif strategy_name == 'multi_factor':
            strategy = MultiFactorStrategy(**params)
        else:
            strategy = MACrossStrategy()

        cerebro.add_strategy(strategy)
        metrics = cerebro.run()

        return metrics, broker.equity_curve
    except Exception as e:
        st.error(f"回测错误: {e}")
        return None
