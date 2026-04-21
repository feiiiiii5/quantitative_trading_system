#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Web用户界面模块
使用Streamlit构建交互式Web界面
提供：
- 数据查看
- 策略回测
- 结果可视化
- 实时监控
"""

import sys
from pathlib import Path

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent))

import pandas as pd
import numpy as np
from datetime import datetime, timedelta

from utils.logger import get_logger
from data.data_manager import DataManager
from strategies.strategy_manager import StrategyManager
from backtest.engine import BacktestEngine
from config.settings import BACKTEST, TRADING

logger = get_logger(__name__)


def launch_web_interface():
    """启动Web界面"""
    try:
        import streamlit as st
    except ImportError:
        logger.error("请先安装streamlit: pip install streamlit")
        print("请先安装streamlit: pip install streamlit")
        return
    
    # 页面配置
    st.set_page_config(
        page_title="量化交易系统",
        page_icon="📈",
        layout="wide",
        initial_sidebar_state="expanded"
    )
    
    # 标题
    st.title("📈 量化交易系统")
    st.markdown("---")
    
    # 侧边栏导航
    st.sidebar.title("导航菜单")
    page = st.sidebar.radio(
        "选择功能",
        ["首页", "数据查看", "策略回测", "结果分析", "使用帮助"]
    )
    
    if page == "首页":
        show_home_page()
    elif page == "数据查看":
        show_data_page()
    elif page == "策略回测":
        show_backtest_page()
    elif page == "结果分析":
        show_analysis_page()
    elif page == "使用帮助":
        show_help_page()


def show_home_page():
    """首页"""
    st.header("欢迎使用量化交易系统")
    
    st.markdown("""
    ### 系统简介
    
    这是一个为**零基础用户**设计的完整量化交易系统，包含：
    
    - **📊 数据获取与处理**：自动获取股票数据，支持多种数据源
    - **🎯 策略开发**：内置多种经典策略，支持自定义策略
    - **🔄 回测引擎**：完整的回测功能，计算各项绩效指标
    - **⚠️ 风险控制**：仓位控制、止损止盈、回撤监控
    - **💻 交易接口**：支持回测、模拟和实盘交易
    - **🖥️ 用户界面**：友好的Web界面，可视化操作
    
    ### 快速开始
    
    1. 在左侧菜单选择"数据查看"浏览股票数据
    2. 选择"策略回测"测试策略效果
    3. 查看"结果分析"了解策略表现
    
    ### 系统状态
    """)
    
    # 显示系统状态
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.metric("内置策略数", "3")
    with col2:
        st.metric("数据源", "akshare (免费)")
    with col3:
        st.metric("交易模式", "回测/模拟")


def show_data_page():
    """数据查看页面"""
    st.header("📊 数据查看")
    
    # 输入参数
    col1, col2, col3 = st.columns(3)
    
    with col1:
        stock_code = st.text_input("股票代码", "000001.XSHE")
    with col2:
        start_date = st.date_input("开始日期", datetime(2023, 1, 1))
    with col3:
        end_date = st.date_input("结束日期", datetime.now())
    
    if st.button("获取数据"):
        with st.spinner("正在获取数据..."):
            try:
                data_manager = DataManager()
                df = data_manager.get_stock_data(
                    stock_code,
                    start_date.strftime("%Y-%m-%d"),
                    end_date.strftime("%Y-%m-%d")
                )
                
                if df is not None and len(df) > 0:
                    st.success(f"成功获取 {len(df)} 条数据")
                    
                    # 显示数据
                    st.subheader("数据预览")
                    st.dataframe(df.tail(10))
                    
                    # 显示统计信息
                    st.subheader("统计信息")
                    st.write(df.describe())
                    
                    # 绘制K线图
                    st.subheader("价格走势")
                    chart_data = df.set_index('date')[['open', 'high', 'low', 'close']]
                    st.line_chart(chart_data)
                    
                    # 成交量
                    st.subheader("成交量")
                    volume_data = df.set_index('date')['volume']
                    st.bar_chart(volume_data)
                    
                else:
                    st.error("未获取到数据，请检查股票代码")
                    
            except Exception as e:
                st.error(f"获取数据失败: {e}")


def show_backtest_page():
    """策略回测页面"""
    st.header("🔄 策略回测")
    
    # 策略选择
    strategy_manager = StrategyManager()
    strategies = strategy_manager.list_strategies()
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        strategy_name = st.selectbox("选择策略", strategies)
    with col2:
        stock_code = st.text_input("回测标的", "000001.XSHE")
    with col3:
        initial_cash = st.number_input("初始资金", value=100000, step=10000)
    
    # 日期范围
    col1, col2 = st.columns(2)
    with col1:
        start_date = st.date_input("回测开始", datetime(2020, 1, 1))
    with col2:
        end_date = st.date_input("回测结束", datetime.now())
    
    # 策略参数
    st.subheader("策略参数")
    
    strategy_info = strategy_manager.get_strategy_info(strategy_name)
    default_params = strategy_info.get('default_parameters', {})
    
    params = {}
    cols = st.columns(len(default_params))
    
    for i, (param_name, default_value) in enumerate(default_params.items()):
        with cols[i]:
            params[param_name] = st.number_input(
                param_name,
                value=float(default_value),
                step=1.0
            )
    
    # 运行回测
    if st.button("运行回测", type="primary"):
        with st.spinner("正在运行回测..."):
            try:
                # 加载策略
                strategy = strategy_manager.load_strategy(strategy_name, params)
                
                # 创建回测引擎
                engine = BacktestEngine(
                    initial_cash=initial_cash,
                    commission=TRADING["commission_rate"],
                    slippage=TRADING["slippage"]
                )
                
                # 运行回测
                results = engine.run(
                    strategy=strategy,
                    stock_code=stock_code,
                    start_date=start_date.strftime("%Y-%m-%d"),
                    end_date=end_date.strftime("%Y-%m-%d")
                )
                
                # 显示结果
                st.success("回测完成！")
                
                # 关键指标
                st.subheader("绩效指标")
                
                metric_col1, metric_col2, metric_col3, metric_col4 = st.columns(4)
                
                with metric_col1:
                    st.metric("总收益率", f"{results['total_return']*100:.2f}%")
                with metric_col2:
                    st.metric("年化收益率", f"{results['annual_return']*100:.2f}%")
                with metric_col3:
                    st.metric("夏普比率", f"{results['sharpe_ratio']:.2f}")
                with metric_col4:
                    st.metric("最大回撤", f"{results['max_drawdown']*100:.2f}%")
                
                # 资产曲线
                st.subheader("资产曲线")
                portfolio_df = results['portfolio_values']
                st.line_chart(portfolio_df['total_value'])
                
                # 交易记录
                st.subheader("交易记录")
                trades_df = pd.DataFrame(results['trades'])
                if len(trades_df) > 0:
                    st.dataframe(trades_df)
                else:
                    st.info("无交易记录")
                
                # 保存结果
                result_file = engine.save_results(results, strategy_name)
                st.info(f"结果已保存: {result_file}")
                
            except Exception as e:
                st.error(f"回测失败: {e}")
                logger.exception("回测失败")


def show_analysis_page():
    """结果分析页面"""
    st.header("📈 结果分析")
    
    st.info("此页面用于分析历史回测结果")
    
    # 这里可以添加更多分析功能
    # 如：策略对比、参数优化、风险分析等
    
    st.markdown("""
    ### 分析功能（开发中）
    
    - 策略对比分析
    - 参数敏感性分析
    - 风险归因分析
    - 交易明细分析
    """)


def show_help_page():
    """使用帮助页面"""
    st.header("❓ 使用帮助")
    
    st.markdown("""
    ### 快速入门指南
    
    #### 1. 环境搭建
    ```bash
    # 安装依赖
    pip install -r requirements.txt
    
    # 启动系统
    python main.py init
    ```
    
    #### 2. 获取数据
    ```bash
    # 更新数据
    python main.py update-data --codes 000001.XSHE
    ```
    
    #### 3. 运行回测
    ```bash
    # 回测默认策略
    python main.py backtest
    
    # 回测指定策略
    python main.py backtest --strategy ma_cross
    ```
    
    #### 4. 启动Web界面
    ```bash
    streamlit run ui/web_interface.py
    ```
    
    ### 策略开发指南
    
    1. 继承 `BaseStrategy` 基类
    2. 实现 `init()` 方法计算指标
    3. 实现 `next()` 方法生成交易信号
    4. 使用 `buy()` / `sell()` / `hold()` 方法返回信号
    
    ### 常见问题
    
    **Q: 如何添加新的数据源？**
    A: 在 `data/data_manager.py` 中添加新的数据获取方法。
    
    **Q: 如何接入实盘交易？**
    A: 需要实现具体的券商API接口，参考 `trading/trader.py` 中的框架。
    
    **Q: 数据存储在哪里？**
    A: 默认存储在 `data/` 目录下，以CSV格式缓存。
    """)


if __name__ == "__main__":
    launch_web_interface()
