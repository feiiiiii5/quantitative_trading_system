# 量化交易系统核心配置文件
# 此文件包含系统运行所需的所有配置参数

import os
from pathlib import Path

# 项目根目录
PROJECT_ROOT = Path(__file__).parent.parent.absolute()

# 数据目录配置
DATA_DIR = PROJECT_ROOT / "data"
DATA_DIR.mkdir(exist_ok=True)

# 日志目录配置
LOG_DIR = PROJECT_ROOT / "logs"
LOG_DIR.mkdir(exist_ok=True)

# 策略目录配置
STRATEGY_DIR = PROJECT_ROOT / "strategies"

# 回测结果目录
BACKTEST_RESULT_DIR = PROJECT_ROOT / "backtest_results"
BACKTEST_RESULT_DIR.mkdir(exist_ok=True)


# 数据源配置
DATA_SOURCE = {
    "default": "akshare",  # 默认使用akshare（免费数据源）
    "akshare": {
        "enabled": True,
        "daily_data_cache": DATA_DIR / "daily",  # 日线数据缓存
        "minute_data_cache": DATA_DIR / "minute",  # 分钟数据缓存
    },
    "tushare": {
        "enabled": False,
        "token": "your_tushare_token_here",  # 需要从tushare.pro获取
    },
    "baostock": {
        "enabled": True,
    }
}

# 风控配置
RISK_CONTROL = {
    "max_position_per_stock": 0.2,      # 单只股票最大仓位比例
    "max_total_position": 0.8,          # 总仓位上限
    "stop_loss": 0.05,                  # 止损比例（5%）
    "take_profit": 0.15,                # 止盈比例（15%）
    "max_drawdown": 0.2,                 # 最大回撤容忍度
    "max_daily_loss": 0.03,             # 单日最大亏损
    "min_cash_ratio": 0.1,              # 最小现金比例
}

# 交易配置
TRADING = {
    "broker": "backtest",               # backtest: 回测, paper: 模拟, real: 实盘
    "commission_rate": 0.0003,          # 交易佣金（含印花税等）
    "slippage": 0.001,                  # 滑点（0.1%）
    "initial_cash": 1000000,            # 初始资金（100万）
}

# 回测配置
BACKTEST = {
    "start_date": "2020-01-01",         # 回测开始日期
    "end_date": "2024-12-31",           # 回测结束日期
    "benchmark": "000300.XSHG",         # 基准指数（沪深300）
}

# 市场配置
MARKET_CONFIG = {
    "CN": {
        "currency": "CNY",
        "lot_size": 100,                    # A股每手100股
        "commission_rate": 0.0003,          # 佣金
        "stamp_duty": 0.001,                # 印花税（卖出时）
        "transfer_fee": 0.00002,            # 过户费
        "settlement": "T+1",                # T+1结算
        "price_limit": 0.1,                 # 涨跌停±10%
        "st_price_limit": 0.05,             # ST股±5%
        "trading_hours": ("09:30", "15:00"),
    },
    "HK": {
        "currency": "HKD",
        "lot_size": 100,                    # 港股每手（不同股票不同，默认100）
        "commission_rate": 0.0003,          # 佣金
        "stamp_duty": 0.001,                # 印花税
        "settlement": "T+2",                # T+2结算
        "price_limit": None,                # 无涨跌停限制
        "trading_hours": ("09:30", "16:00"),
    },
    "US": {
        "currency": "USD",
        "lot_size": 1,                      # 美股无手数限制
        "commission_rate": 0.0,             # 多数券商零佣金
        "sec_fee": 0.000008,                # SEC费（卖出）
        "settlement": "T+1",                # T+1结算（2024年5月起）
        "price_limit": None,                # 无涨跌停，但有熔断
        "circuit_breaker": {                # 熔断机制
            "level1": -0.07,                # 跌7%暂停15分钟
            "level2": -0.13,                # 跌13%暂停15分钟
            "level3": -0.20,                # 跌20%当日停止
        },
        "trading_hours": ("09:30", "16:00"),
    },
}

# 实盘交易配置
REAL_TRADING = {
    "enabled": False,
    "broker": "simulated",              # simulated: 模拟, futu: 富途, tushare: Tushare
    "websocket": {
        "enabled": False,
        "host": "127.0.0.1",
        "port": 8888,
    }
}

# 日志配置
LOGGING = {
    "level": "INFO",                    # DEBUG, INFO, WARNING, ERROR
    "format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    "file": LOG_DIR / "quantitative_trading.log",
}

# 策略配置模板
STRATEGY_TEMPLATE = {
    "name": "ExampleStrategy",
    "class": "ExampleStrategy",
    "parameters": {
        "fast_period": 5,
        "slow_period": 20,
        "volume_period": 10,
    }
}
