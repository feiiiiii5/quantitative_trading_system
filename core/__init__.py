"""
QuantCore - 量化交易系统核心模块

本包包含所有核心功能：
- 数据获取：data_fetcher
- 回测引擎：backtest
- 策略系统：strategies, strategy_pipeline, strategy_fusion
- 风险管理：risk_manager, risk_monitor, advanced_risk_analytics
- 技术指标：indicators
- 机器学习：ml_utils, ml_factor_scorer, prediction
- 因子工程：factor_pipeline, alpha_engine, alpha_screener
- 市场分析：market_data, market_detector, market_breadth, sector_rotation
- 组合优化：portfolio_optimizer, risk_parity_rebalancer, position_sizer
- 性能分析：metrics, performance_attribution, rolling_metrics
- 回测优化：walk_forward, param_optimizer, stress_test
- 模拟交易：simulated_trading
- 事件系统：events, orders, execution_engine
- 数据库：database
- 配置管理：config
- 日志：logger
- 其他：chip_distribution, volatility, trade_journal, news_engine, stock_search, stock_screener, auto_auditor, memory_guard, mps_accelerator, self_evolver
"""

__all__ = [
    "adaptive_strategy",
    "advanced_risk_analytics",
    "feature_flags",
    "alpha_engine",
    "alpha_screener",
    "auto_auditor",
    "backtest",
    "chip_distribution",
    "config",
    "correlation",
    "data_fetcher",
    "database",
    "events",
    "execution_engine",
    "factor_pipeline",
    "indicators",
    "logger",
    "market_breadth",
    "market_data",
    "market_detector",
    "market_hours",
    "memory_guard",
    "metrics",
    "ml_factor_scorer",
    "ml_utils",
    "models",
    "money_flow",
    "mps_accelerator",
    "news_engine",
    "orders",
    "param_optimizer",
    "performance_attribution",
    "portfolio_optimizer",
    "position_sizer",
    "prediction",
    "regime_detector",
    "risk_manager",
    "risk_monitor",
    "risk_parity_rebalancer",
    "rolling_metrics",
    "sector_rotation",
    "self_evolver",
    "simulated_trading",
    "smart_alerts",
    "stock_screener",
    "stock_search",
    "strategies",
    "strategy_fusion",
    "strategy_pipeline",
    "stress_test",
    "trade_journal",
    "volatility",
    "walk_forward",
]
