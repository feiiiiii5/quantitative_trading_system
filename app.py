#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
QuantSystem Pro - 完全免费开源的量化交易工具

启动方式：
  双击运行：python app.py（自动启动Web界面）
  命令行：  python app.py --cli backtest --symbol 000001
"""

import sys
import os
import subprocess
import webbrowser
import threading
from pathlib import Path
from datetime import datetime, timedelta

project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))


def _detect_system_dark_mode():
    try:
        if sys.platform == 'darwin':
            result = subprocess.run(
                ['defaults', 'read', '-g', 'AppleInterfaceStyle'],
                capture_output=True, text=True, timeout=3
            )
            return result.returncode == 0 and 'dark' in result.stdout.lower()
        elif sys.platform == 'win32':
            import winreg
            key = winreg.OpenKey(
                winreg.HKEY_CURRENT_USER,
                r'Software\Microsoft\Windows\CurrentVersion\Themes\Personalize'
            )
            value, _ = winreg.QueryValueEx(key, 'AppsUseLightTheme')
            return value == 0
        elif sys.platform == 'linux':
            result = subprocess.run(
                ['gsettings', 'get', 'org.gnome.desktop.interface', 'color-scheme'],
                capture_output=True, text=True, timeout=3
            )
            return 'dark' in result.stdout.lower()
    except Exception:
        pass
    return False


def _check_dependencies():
    missing = []
    try:
        import streamlit
    except ImportError:
        missing.append('streamlit')
    try:
        import pandas
    except ImportError:
        missing.append('pandas')
    try:
        import numpy
    except ImportError:
        missing.append('numpy')
    try:
        import plotly
    except ImportError:
        missing.append('plotly')
    if missing:
        print("=" * 50)
        print("缺少必要依赖，正在自动安装...")
        print(f"需要安装: {', '.join(missing)}")
        print("=" * 50)
        try:
            subprocess.check_call(
                [sys.executable, '-m', 'pip', 'install'] + missing,
                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
            )
            print("依赖安装完成！")
        except Exception as e:
            print(f"自动安装失败: {e}")
            print(f"请手动运行: pip install {' '.join(missing)}")
            sys.exit(1)


def _open_browser(url, delay=3):
    def _open():
        import time
        time.sleep(delay)
        webbrowser.open(url)
    threading.Thread(target=_open, daemon=True).start()


def _is_running_in_streamlit():
    try:
        from streamlit.runtime.scriptrunner import get_script_run_ctx
        return get_script_run_ctx() is not None
    except Exception:
        try:
            import streamlit as st
            if hasattr(st, 'runtime'):
                return True
        except Exception:
            pass
    return False


if _is_running_in_streamlit():
    from core.engine import Cerebro, Broker, ExecutionMode, BaseStrategy, Order
    from data.async_data_manager import AsyncDataManager
    from data.market_detector import MarketDetector
    from strategies.ma_cross import MACrossStrategy
    from strategies.advanced_strategies import (
        MultiFactorStrategy,
        AdaptiveMarketRegimeStrategy,
        MachineLearningStrategy
    )
    from strategies.market_strategies.cn_strategies import DragonHeadStrategy, NorthBoundFlowStrategy
    from strategies.market_strategies.hk_strategies import AHPremiumStrategy, SouthBoundFlowStrategy
    from strategies.market_strategies.us_strategies import EarningsMomentumStrategy, PutCallSentimentStrategy
    from risk.advanced_risk_manager import AdvancedRiskManager, RiskConfig
    from utils.metrics import performance_attribution
    from utils.logger import get_logger

    try:
        from reports.report_generator import ReportGenerator
        HAS_REPORT = True
    except ImportError:
        HAS_REPORT = False

    try:
        from data.index_data import IndexData
        HAS_INDEX = True
    except ImportError:
        HAS_INDEX = False

    logger = get_logger(__name__)

    _import_errors = []

    STRATEGIES = {
        'ma_cross': MACrossStrategy,
        'multi_factor': MultiFactorStrategy,
        'adaptive': AdaptiveMarketRegimeStrategy,
        'ml': MachineLearningStrategy,
        'dragon_head': DragonHeadStrategy,
        'north_bound': NorthBoundFlowStrategy,
        'ah_premium': AHPremiumStrategy,
        'south_bound': SouthBoundFlowStrategy,
        'earnings_mom': EarningsMomentumStrategy,
        'put_call': PutCallSentimentStrategy,
    }


class QuantSystem:
    def __init__(self):
        self.data_manager = AsyncDataManager()
        self.risk_manager = AdvancedRiskManager()
        self.strategies = STRATEGIES.copy() if 'STRATEGIES' in dir() else {}

    def _fetch_data(self, symbol, start_date, end_date, market=None):
        if market is None:
            market = MarketDetector.detect(symbol)
        data_sources = ['akshare', 'baostock']
        for source in data_sources:
            logger.info(f"尝试从 {source} 获取数据")
            data = self.data_manager.get_data_sync(
                symbol, start_date, end_date, source=source, market=market)
            if data is not None and not data.empty:
                logger.info(f"成功从 {source} 获取数据")
                return data, market
        logger.error("所有数据源都获取失败")
        return None, market


def run_web():
    try:
        import streamlit as st
    except ImportError:
        print("请先安装streamlit: pip install streamlit")
        return

    qs = QuantSystem()

    st.set_page_config(
        page_title="QuantSystem Pro",
        page_icon="📈",
        layout="wide",
        initial_sidebar_state="expanded",
    )

    if 'dark_mode' not in st.session_state:
        st.session_state.dark_mode = _detect_system_dark_mode()

    from ui.styles import APPLE_CSS, DARK_CSS
    if st.session_state.dark_mode:
        st.markdown(DARK_CSS, unsafe_allow_html=True)
    else:
        st.markdown(APPLE_CSS, unsafe_allow_html=True)

    with st.sidebar:
        dark_toggle = st.toggle("🌙 暗色模式", value=st.session_state.dark_mode, key="dark_toggle_key")
        if dark_toggle != st.session_state.dark_mode:
            st.session_state.dark_mode = dark_toggle
            st.rerun()

        from ui.components.watchlist import render_watchlist
        render_watchlist()

    st.markdown("""
    <div class="hero-section">
        <div class="hero-title">QuantSystem Pro</div>
        <div class="hero-subtitle">
            完全免费开源的量化交易工具
            <span class="badge-opensource">完全免费 · 开源</span>
        </div>
        <div class="market-tags">
            🇨🇳 A股 · 🇭🇰 港股 · 🇺🇸 美股
        </div>
    </div>
    """, unsafe_allow_html=True)

    col_input1, col_input2 = st.columns([3, 1])
    with col_input1:
        symbol = st.text_input(
            "输入股票代码",
            value=st.session_state.get('selected_symbol', ''),
            placeholder="例如：000001（A股）00700（港股）AAPL（美股）",
            key="main_symbol_input",
            label_visibility="collapsed",
        )
    with col_input2:
        st.markdown("<div style='height:34px'></div>", unsafe_allow_html=True)
        search_btn = st.button("🔍 分析", type="primary", use_container_width=True)

    if not symbol and not search_btn:
        st.markdown("""
        <div style="text-align:center; padding:80px 20px; color:var(--text-secondary)">
            <div style="font-size:48px; margin-bottom:16px">📈</div>
            <div style="font-size:20px; font-weight:500">输入股票代码开始分析</div>
            <div style="font-size:15px; margin-top:8px">支持A股、港股、美股市场</div>
        </div>
        """, unsafe_allow_html=True)
        _show_debug_info(st)
        return

    if not symbol:
        _show_debug_info(st)
        return

    market = MarketDetector.detect(symbol)
    dm = AsyncDataManager()

    end_date = datetime.now().strftime('%Y-%m-%d')
    start_date = (datetime.now() - timedelta(days=730)).strftime('%Y-%m-%d')

    data = None
    with st.spinner(f"正在获取 {symbol} 的数据..."):
        data_sources = ['akshare', 'baostock']
        for source in data_sources:
            try:
                data = dm.get_data_sync(
                    symbol, start_date, end_date, source=source, market=market)
                if data is not None and not data.empty:
                    break
            except Exception as e:
                logger.warning(f"数据源 {source} 获取失败: {e}")

    if data is None or data.empty:
        st.error(f"无法获取 {symbol} 的数据，请检查代码是否正确")
        _show_debug_info(st)
        return

    st.markdown('<div class="section-title">📊 股票概览</div>', unsafe_allow_html=True)
    from ui.components.stock_overview import render_overview_cards
    render_overview_cards(symbol, market, data)

    st.markdown('<div class="section-title">🕯️ K线图</div>', unsafe_allow_html=True)
    from ui.components.kline_chart import render_kline_chart
    render_kline_chart(data, market=market)

    st.markdown('<div class="section-title">📐 技术指标</div>', unsafe_allow_html=True)
    from ui.components.technical_panel import render_technical_indicators
    render_technical_indicators(data)

    st.markdown('<div class="section-title">🎯 量化系统指标</div>', unsafe_allow_html=True)
    from ui.components.quant_metrics import render_quant_metrics
    render_quant_metrics(symbol, data, market)

    st.markdown('<div class="section-title">🔮 涨跌概率预测</div>', unsafe_allow_html=True)
    from ui.components.prediction import render_prediction_panel
    render_prediction_panel(symbol, data)

    with st.expander("📦 更多功能", expanded=False):
        tab_bt, tab_cmp, tab_heat, tab_news = st.tabs([
            "🔄 策略回测", "📊 多股对比", "🗺️ 板块热力图", "📰 新闻情绪"
        ])

        with tab_bt:
            from ui.components.backtest_ui import render_backtest_panel
            render_backtest_panel(symbol, data)

        with tab_cmp:
            from ui.components.comparison import render_stock_comparison
            render_stock_comparison()

        with tab_heat:
            from ui.components.market_heatmap import render_market_heatmap
            render_market_heatmap(market)

        with tab_news:
            from ui.components.news_sentiment import render_sentiment
            render_sentiment(symbol)

    try:
        from utils.trading_hours import is_trading_hours
        if is_trading_hours(market):
            from streamlit_autorefresh import st_autorefresh
            st_autorefresh(interval=60000, key="datarefresh")
    except ImportError:
        pass

    _show_debug_info(st)


def _show_debug_info(st):
    if '_import_errors' in dir() and _import_errors:
        with st.expander("🔧 调试信息", expanded=False):
            for err in _import_errors:
                st.warning(err)


def run_cli():
    import argparse

    from core.engine import Cerebro, Broker, ExecutionMode, BaseStrategy, Order
    from data.async_data_manager import AsyncDataManager
    from data.market_detector import MarketDetector
    from strategies.ma_cross import MACrossStrategy
    from strategies.advanced_strategies import (
        MultiFactorStrategy, AdaptiveMarketRegimeStrategy, MachineLearningStrategy
    )
    from strategies.market_strategies.cn_strategies import DragonHeadStrategy, NorthBoundFlowStrategy
    from strategies.market_strategies.hk_strategies import AHPremiumStrategy, SouthBoundFlowStrategy
    from strategies.market_strategies.us_strategies import EarningsMomentumStrategy, PutCallSentimentStrategy
    from risk.advanced_risk_manager import AdvancedRiskManager, RiskConfig
    from utils.logger import get_logger

    logger = get_logger(__name__)

    STRATEGIES = {
        'ma_cross': MACrossStrategy,
        'multi_factor': MultiFactorStrategy,
        'adaptive': AdaptiveMarketRegimeStrategy,
        'ml': MachineLearningStrategy,
        'dragon_head': DragonHeadStrategy,
        'north_bound': NorthBoundFlowStrategy,
        'ah_premium': AHPremiumStrategy,
        'south_bound': SouthBoundFlowStrategy,
        'earnings_mom': EarningsMomentumStrategy,
        'put_call': PutCallSentimentStrategy,
    }

    def fetch_data(symbol, start_date, end_date, market=None):
        if market is None:
            market = MarketDetector.detect(symbol)
        dm = AsyncDataManager()
        for source in ['akshare', 'baostock']:
            logger.info(f"尝试从 {source} 获取数据")
            data = dm.get_data_sync(symbol, start_date, end_date, source=source, market=market)
            if data is not None and not data.empty:
                logger.info(f"成功从 {source} 获取数据")
                return data, market
        logger.error("所有数据源都获取失败")
        return None, market

    parser = argparse.ArgumentParser(
        description='QuantSystem Pro - 完全免费开源的量化交易工具',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  回测:     python app.py --cli backtest --symbol 000001 --strategy ma_cross
  分析:     python app.py --cli analyze --symbol 000001
  优化:     python app.py --cli optimize --symbol 000001 --strategy ma_cross
  Web界面:  python app.py
        """
    )

    parser.add_argument('--cli', action='store_true', help='命令行模式')
    subparsers = parser.add_subparsers(dest='command', help='命令')

    bt_parser = subparsers.add_parser('backtest', help='运行回测')
    bt_parser.add_argument('--symbol', '-s', default='000001')
    bt_parser.add_argument('--strategy', default='ma_cross',
                           choices=list(STRATEGIES.keys()))
    bt_parser.add_argument('--start', default=None)
    bt_parser.add_argument('--end', default=None)
    bt_parser.add_argument('--cash', type=float, default=1000000)
    bt_parser.add_argument('--mode', default='event_driven',
                           choices=['event_driven', 'vectorized'])
    bt_parser.add_argument('--market', default=None, choices=['CN', 'HK', 'US'])

    an_parser = subparsers.add_parser('analyze', help='运行完整分析')
    an_parser.add_argument('--symbol', '-s', default='000001')
    an_parser.add_argument('--start', default=None)
    an_parser.add_argument('--end', default=None)
    an_parser.add_argument('--market', default=None, choices=['CN', 'HK', 'US'])

    op_parser = subparsers.add_parser('optimize', help='参数优化')
    op_parser.add_argument('--symbol', '-s', default='000001')
    op_parser.add_argument('--strategy', default='ma_cross')
    op_parser.add_argument('--start', default=None)
    op_parser.add_argument('--end', default=None)

    wf_parser = subparsers.add_parser('walkforward', help='Walkforward分析')
    wf_parser.add_argument('--symbol', '-s', default='000001')
    wf_parser.add_argument('--strategy', default='ma_cross')
    wf_parser.add_argument('--windows', type=int, default=5)
    wf_parser.add_argument('--train-size', type=float, default=0.7)

    args = parser.parse_args()

    if args.command is None:
        parser.print_help()
        sys.exit(0)

    if args.command == 'backtest':
        end_date = args.end or datetime.now().strftime('%Y-%m-%d')
        start_date = args.start or (datetime.now() - timedelta(days=365)).strftime('%Y-%m-%d')
        data, market = fetch_data(args.symbol, start_date, end_date, args.market)
        if data is None:
            print("数据获取失败")
            sys.exit(1)

        exec_mode = ExecutionMode.EVENT_DRIVEN if args.mode == 'event_driven' else ExecutionMode.VECTORIZED
        cerebro = Cerebro(mode=exec_mode)
        cerebro.add_data(data, args.symbol)
        broker = Broker(initial_cash=args.cash, market=market)
        cerebro.set_broker(broker)

        if args.strategy not in STRATEGIES:
            print(f"未知策略: {args.strategy}")
            sys.exit(1)

        strategy = STRATEGIES[args.strategy]()
        cerebro.add_strategy(strategy)
        metrics = cerebro.run(progress_bar=True)
        metrics.print_summary()

    elif args.command == 'analyze':
        end_date = args.end or datetime.now().strftime('%Y-%m-%d')
        start_date = args.start or (datetime.now() - timedelta(days=730)).strftime('%Y-%m-%d')
        data, market = fetch_data(args.symbol, start_date, end_date, args.market)
        if data is None:
            print("数据获取失败")
            sys.exit(1)

        cerebro = Cerebro(mode=ExecutionMode.VECTORIZED)
        cerebro.add_data(data, args.symbol)
        broker = Broker(initial_cash=100000, market=market)
        cerebro.set_broker(broker)
        strategy = MACrossStrategy()
        cerebro.add_strategy(strategy)
        metrics = cerebro.run()
        metrics.print_summary()

        if HAS_INDEX:
            benchmark_name = "沪深300" if market == "CN" else ("恒生指数" if market == "HK" else "标普500")
            benchmark_data = IndexData.get_index_data(benchmark_name, start_date, end_date)
            if benchmark_data is not None:
                bench_result = cerebro.compare_benchmark(benchmark_data)
                print("\n" + "=" * 60)
                print("基准比较")
                print("=" * 60)
                for k, v in bench_result.items():
                    print(f"{k}: {v:.4f}")

    elif args.command == 'optimize':
        end_date = args.end or datetime.now().strftime('%Y-%m-%d')
        start_date = args.start or (datetime.now() - timedelta(days=365)).strftime('%Y-%m-%d')
        data, _ = fetch_data(args.symbol, start_date, end_date)
        if data is None:
            print("数据获取失败")
            sys.exit(1)

        cerebro = Cerebro()
        cerebro.add_data(data, args.symbol)
        if args.strategy not in STRATEGIES:
            print(f"未知策略: {args.strategy}")
            sys.exit(1)

        strategy_class = STRATEGIES[args.strategy]
        param_grid = {'fast_period': [5, 10, 15], 'slow_period': [20, 30, 60]} if args.strategy == 'ma_cross' else {}
        best_params, best_result = cerebro.optimize(strategy_class, param_grid)
        print(f"\n最佳参数: {best_params}")
        if best_result:
            print(f"最佳夏普比率: {best_result.sharpe_ratio:.4f}")

    elif args.command == 'walkforward':
        end_date = args.end or datetime.now().strftime('%Y-%m-%d')
        start_date = args.start or (datetime.now() - timedelta(days=730)).strftime('%Y-%m-%d')
        data, _ = fetch_data(args.symbol, start_date, end_date)
        if data is None:
            print("数据获取失败")
            sys.exit(1)

        cerebro = Cerebro()
        cerebro.add_data(data, args.symbol)
        if args.strategy not in STRATEGIES:
            print(f"未知策略: {args.strategy}")
            sys.exit(1)

        strategy = STRATEGIES[args.strategy]()
        cerebro.add_strategy(strategy)
        results = cerebro.walkforward_analysis(train_size=args.train_size, n_windows=args.windows)
        print("\n" + "=" * 60)
        print("Walkforward分析结果")
        print("=" * 60)
        for i, result in enumerate(results):
            print(f"窗口 {i+1}: 夏普={result.sharpe_ratio:.2f}, "
                  f"收益={result.total_return:.2%}, 回撤={result.max_drawdown:.2%}")


if __name__ == '__main__':
    if '--cli' in sys.argv:
        sys.argv.remove('--cli')
        run_cli()
    else:
        _check_dependencies()
        print("🚀 QuantSystem Pro 启动中...")
        print("📍 浏览器访问: http://localhost:8501")
        print("⏹  按 Ctrl+C 停止服务")
        print("-" * 50)
        _open_browser("http://localhost:8501")
        try:
            subprocess.run(
                [sys.executable, '-m', 'streamlit', 'run', str(__file__),
                 '--server.port=8501', '--server.headless=true',
                 '--browser.gatherUsageStats=false'],
                cwd=str(project_root)
            )
        except KeyboardInterrupt:
            print("\n服务已停止")
else:
    if _is_running_in_streamlit():
        run_web()
