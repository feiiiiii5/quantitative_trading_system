#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""模块导入测试脚本"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path.cwd()))

print('=== 测试核心模块导入 ===')

try:
    from core.engine import Cerebro, Broker, ExecutionMode, BaseStrategy, Order
    print('core.engine OK')
except Exception as e:
    print(f'core.engine FAIL: {e}')

try:
    from strategies.ma_cross import MACrossStrategy
    print('strategies.ma_cross OK')
except Exception as e:
    print(f'strategies.ma_cross FAIL: {e}')

try:
    from data.async_data_manager import AsyncDataManager
    print('data.async_data_manager OK')
except Exception as e:
    print(f'data.async_data_manager FAIL: {e}')

try:
    from data.market_detector import MarketDetector
    print('data.market_detector OK')
except Exception as e:
    print(f'data.market_detector FAIL: {e}')

try:
    from utils.metrics import calculate_metrics
    print('utils.metrics OK')
except Exception as e:
    print(f'utils.metrics FAIL: {e}')

try:
    from utils.logger import get_logger
    print('utils.logger OK')
except Exception as e:
    print(f'utils.logger FAIL: {e}')

try:
    from risk.advanced_risk_manager import AdvancedRiskManager
    print('risk.advanced_risk_manager OK')
except Exception as e:
    print(f'risk.advanced_risk_manager FAIL: {e}')

try:
    from strategies.advanced_strategies import MultiFactorStrategy, AdaptiveMarketRegimeStrategy, MachineLearningStrategy
    print('strategies.advanced_strategies OK')
except Exception as e:
    print(f'strategies.advanced_strategies FAIL: {e}')

print('\n=== 测试UI组件导入 ===')

try:
    from ui.styles import APPLE_CSS
    print('ui.styles OK')
except Exception as e:
    print(f'ui.styles FAIL: {e}')

try:
    from ui.components.stock_overview import render_overview_cards
    print('ui.components.stock_overview OK')
except Exception as e:
    print(f'ui.components.stock_overview FAIL: {e}')

try:
    from ui.components.kline_chart import render_kline_chart
    print('ui.components.kline_chart OK')
except Exception as e:
    print(f'ui.components.kline_chart FAIL: {e}')

try:
    from ui.components.technical_panel import render_technical_indicators
    print('ui.components.technical_panel OK')
except Exception as e:
    print(f'ui.components.technical_panel FAIL: {e}')

try:
    from ui.components.quant_metrics import render_quant_metrics
    print('ui.components.quant_metrics OK')
except Exception as e:
    print(f'ui.components.quant_metrics FAIL: {e}')

try:
    from ui.components.prediction import render_prediction_panel
    print('ui.components.prediction OK')
except Exception as e:
    print(f'ui.components.prediction FAIL: {e}')

try:
    from ui.components.backtest_ui import render_backtest_panel
    print('ui.components.backtest_ui OK')
except Exception as e:
    print(f'ui.components.backtest_ui FAIL: {e}')

try:
    from ui.components.comparison import render_stock_comparison
    print('ui.components.comparison OK')
except Exception as e:
    print(f'ui.components.comparison FAIL: {e}')

try:
    from ui.components.market_heatmap import render_market_heatmap
    print('ui.components.market_heatmap OK')
except Exception as e:
    print(f'ui.components.market_heatmap FAIL: {e}')

try:
    from ui.components.news_sentiment import render_sentiment
    print('ui.components.news_sentiment OK')
except Exception as e:
    print(f'ui.components.news_sentiment FAIL: {e}')

try:
    from ui.components.watchlist import render_watchlist
    print('ui.components.watchlist OK')
except Exception as e:
    print(f'ui.components.watchlist FAIL: {e}')

print('\n=== 所有模块导入测试完成 ===')
