# QuantSystem Pro - 专业量化交易系统

<div align="center">

[![Python](https://img.shields.io/badge/Python-3.9+-blue.svg)](https://www.python.org/)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![Stars](https://img.shields.io/github/stars/feiiiiii5/quantitative_trading_system?style=social)](https://github.com/feiiiiii5/quantitative_trading_system/stargazers)
[![Last Commit](https://img.shields.io/github/last-commit/feiiiiii5/quantitative_trading_system)](https://github.com/feiiiiii5/quantitative_trading_system/commits)
[![Issues](https://img.shields.io/github/issues/feiiiiii5/quantitative_trading_system)](https://github.com/feiiiiii5/quantitative_trading_system/issues)
[![PRs Welcome](https://img.shields.io/badge/PRs-Welcome-brightgreen.svg)](CONTRIBUTING.md)

**一套功能强大、高效、易用的专业级量化交易系统**

[English](./README_EN.md) · [简体中文](./README.md) · [快速开始](#🚀-快速开始) · [文档](./docs/) · [演示](https://quant-system.streamlit.app)

</div>

---

## 📌 项目简介

QuantSystem Pro 是一套面向专业投资者的量化交易系统，集成了业界领先的量化策略、高性能回测引擎和完善的风险管理体系。系统采用模块化设计，易于扩展，适合从入门到专业的各级用户。

### ✨ 核心特性

| 特性 | 描述 |
|------|------|
| 🚀 **高性能** | 向量化回测引擎，支持多策略并行计算 |
| 🧠 **AI驱动** | 集成机器学习预测模型（XGBoost、LightGBM） |
| 📊 **丰富策略** | 多因子模型、自适应市场、统计套利等10+策略 |
| 🛡️ **完善风控** | VaR、CVaR、压力测试、动态止损 |
| 💰 **专业资金管理** | 凯利公式、波动率目标、风险平价 |
| 📈 **交互界面** | Streamlit Web界面，可视化分析 |
| 🌐 **多市场** | A股、港股、美股全面支持 |

---

## 🚀 快速开始

### 环境要求

| 要求 | 最低版本 | 推荐版本 |
|------|---------|---------|
| Python | 3.9 | 3.11+ |
| 内存 | 4GB | 8GB+ |
| 系统 | macOS/Linux/Windows | macOS 12+ / Ubuntu 20.04+ / Windows 10+ |

### 安装

```bash
# 克隆项目
git clone https://github.com/feiiiiii5/quantitative_trading_system.git
cd quantitative_trading_system

# 创建虚拟环境（推荐）
python -m venv venv
source venv/bin/activate  # Linux/macOS
# 或
.\venv\Scripts\activate   # Windows

# 安装依赖
pip install -r requirements.txt
```

### 一键启动

```bash
# Web界面（一键启动，自动打开浏览器）
python app.py

# 命令行模式
python app.py --cli backtest --symbol 000001 --strategy ma_cross
```

### Docker 部署（可选）

```bash
# 构建镜像
docker build -t quantsystem-pro .

# 运行容器
docker run -p 8501:8501 quantsystem-pro
```

---

## 📊 功能演示

### Web界面预览

| 首页 | K线图 | 策略回测 |
|:---:|:---:|:---:|
| ![Home](docs/images/home.png) | ![K线](docs/images/kline.png) | ![回测](docs/images/backtest.png) |

> 📌 访问 [在线演示](https://quant-system.streamlit.app) 体验完整功能

### 支持的市场

| 市场 | 数据源 | 代码示例 |
|------|--------|---------|
| 🇨🇳 A股 | akshare/baostock | `000001` (平安银行) |
| 🇭🇰 港股 | akshare/yfinance | `00700` (腾讯控股) |
| 🇺🇸 美股 | yfinance | `AAPL` (苹果) |

---

## 🏗️ 系统架构

```
quantitative_trading_system/
├── app.py                      # 一键启动入口（Web + CLI）
├── core/                       # 核心引擎模块
│   ├── engine.py               # Cerebro引擎（事件驱动+向量化）
│   ├── factor_engine.py       # 因子引擎（动量/质量/价值/IC分析）
│   ├── portfolio_engine.py    # 组合管理引擎
│   └── portfolio_optimizer.py # 组合优化器（风险平价/最大夏普/最小方差）
├── strategies/                 # 策略模块
│   ├── base_strategy.py       # 策略基类
│   ├── ma_cross.py            # 均线交叉策略
│   ├── advanced_strategies.py  # 高级策略（多因子/自适应/ML/套利/做市）
│   └── market_strategies/     # 市场特色策略
│       ├── cn_strategies.py   # A股策略（龙头战法、北向资金）
│       ├── hk_strategies.py   # 港股策略（AH溢价、南向资金）
│       └── us_strategies.py   # 美股策略（财报动量、put/call情绪）
├── data/                       # 数据模块
│   ├── async_data_manager.py  # 异步数据管理（macOS兼容）
│   ├── data_manager.py        # 数据获取
│   ├── market_detector.py     # 市场检测
│   └── index_data.py          # 指数数据
├── backtest/                   # 回测模块
│   ├── engine.py              # 事件驱动回测
│   └── vectorized_engine.py   # 向量化回测（100x+速度）
├── risk/                       # 风控模块
│   ├── risk_manager.py        # 基础风险管理
│   ├── advanced_risk_manager.py # 高级风控（VaR/CVaR/动态杠杆）
│   └── drawdown_analyzer.py   # 回撤分析
├── ui/                         # 界面模块
│   ├── styles.py             # Apple风格CSS
│   ├── web_interface.py      # Web接口
│   ├── components/            # UI组件
│   │   ├── kline_chart.py    # K线图
│   │   ├── technical_panel.py # 技术指标
│   │   ├── backtest_ui.py    # 回测界面
│   │   ├── quant_metrics.py   # 量化指标
│   │   └── ...               # 更多组件
│   └── pages/                # 多页面
├── utils/                     # 工具模块
│   ├── logger.py            # 日志工具
│   ├── metrics.py           # 绩效指标
│   └── trading_hours.py     # 交易时间
├── config/                   # 配置模块
│   └── settings.py         # 系统配置
└── tests/                   # 测试模块
    └── ...
```

---

## 📊 内置策略

| 策略 | 类型 | 市场 | 描述 |
|------|------|------|------|
| `ma_cross` | 趋势跟踪 | A股/港股/美股 | 均线交叉策略 |
| `rsi` | 均值回归 | A股/港股/美股 | RSI超买超卖策略 |
| `bollinger` | 趋势跟踪 | A股/港股/美股 | 布林带策略 |
| `multi_factor` | 多因子 | A股 | Fama-French五因子模型 |
| `adaptive` | 自适应 | A股/港股/美股 | 市场状态自动识别 |
| `ml` | 机器学习 | A股/港股/美股 | XGBoost/LightGBM预测 |
| `stat_arb` | 统计套利 | 跨市场 | 配对交易策略 |
| `dragon_head` | 趋势跟踪 | A股 | 龙头战法 |
| `north_bound` | 资金流 | A股 | 北向资金跟踪 |
| `earnings_mom` | 事件驱动 | 美股 | 财报动量策略 |

---

## 🛡️ 风险管理功能

### 核心指标

| 指标 | 描述 | 计算方法 |
|------|------|---------|
| **VaR** | 风险价值 | 历史模拟法/参数法 |
| **CVaR** | 条件风险价值 | 尾部期望 |
| **夏普比率** | 风险调整收益 | (年化收益-无风险利率)/年化波动率 |
| **索提诺比率** | 下行风险调整 | (年化收益-无风险利率)/下行波动率 |
| **最大回撤** | 历史最大回撤 | 峰值到谷值的最大跌幅 |
| **Calmar比率** | 收益回撤比 | 年化收益/最大回撤 |

### 风控机制

- ✅ 动态仓位管理（凯利公式）
- ✅ 波动率目标仓位
- ✅ 追踪止损
- ✅ 压力测试（历史极端行情）
- ✅ 多市场状态适配
- ✅ 个股仓位限制
- ✅ 总仓位限制

---

## 🎯 使用示例

### 1. Web界面使用

```bash
# 启动Web界面
python app.py

# 浏览器自动打开 http://localhost:8501
# 输入股票代码（如 000001）即可开始分析
```

### 2. Python API 使用

```python
from datetime import datetime, timedelta
from data.async_data_manager import AsyncDataManager
from strategies.ma_cross import MACrossStrategy
from core.engine import Cerebro, Broker, ExecutionMode

# 1. 获取数据
dm = AsyncDataManager()
data = dm.get_data_sync(
    symbol='000001',
    start_date='2023-01-01',
    end_date='2024-01-01',
    source='baostock'
)

# 2. 创建策略
strategy = MACrossStrategy(fast_period=5, slow_period=20)

# 3. 创建回测引擎
cerebro = Cerebro(mode=ExecutionMode.VECTORIZED)
cerebro.add_data(data, name='000001')
cerebro.set_broker(Broker(initial_cash=1000000))
cerebro.add_strategy(strategy)

# 4. 运行回测
result = cerebro.run()

# 5. 查看结果
result.print_summary()
```

### 3. 自定义策略

```python
from core.engine import BaseStrategy, Order

class MyStrategy(BaseStrategy):
    """自定义策略示例"""
    
    def __init__(self, fast_period=5, slow_period=20):
        super().__init__(
            name="MyStrategy",
            parameters={
                'fast_period': fast_period,
                'slow_period': slow_period
            }
        )
    
    def init(self):
        """初始化指标"""
        fast = self.parameters['fast_period']
        slow = self.parameters['slow_period']
        self.fast_ma = self.data.close.rolling(fast).mean()
        self.slow_ma = self.data.close.rolling(slow).mean()
    
    def next(self, index: int) -> Order:
        """交易逻辑"""
        if index < self.parameters['slow_period']:
            return None
        
        # 金叉买入
        if self.fast_ma.iloc[index] > self.slow_ma.iloc[index]:
            if self.fast_ma.iloc[index-1] <= self.slow_ma.iloc[index-1]:
                return self.buy(quantity=100, reason="金叉买入")
        
        # 死叉卖出
        elif self.fast_ma.iloc[index] < self.slow_ma.iloc[index]:
            if self.fast_ma.iloc[index-1] >= self.slow_ma.iloc[index-1]:
                return self.sell(quantity=100, reason="死叉卖出")
        
        return None
```

---

## ⚙️ 配置说明

### 交易配置 (`config/settings.py`)

```python
TRADING = {
    "broker": "backtest",           # 经纪商: backtest/paper/real
    "commission_rate": 0.0003,       # 手续费率 (万3)
    "slippage": 0.001,               # 滑点 (千1)
    "initial_cash": 1000000,          # 初始资金
}

RISK_CONTROL = {
    "max_position_per_stock": 0.2,   # 单只最大仓位 (20%)
    "max_total_position": 0.8,        # 总仓位上限 (80%)
    "stop_loss": 0.05,                # 止损比例 (5%)
    "take_profit": 0.15,              # 止盈比例 (15%)
    "max_drawdown": 0.2,             # 最大回撤限制 (20%)
}
```

---

## 📈 性能基准

| 测试场景 | 数据量 | 时间 | 性能 |
|---------|--------|------|------|
| 向量化回测 (1年日线) | 243交易日 | <1秒 | 基准 |
| 事件驱动回测 (1年日线) | 243交易日 | ~5秒 | 5x slower |
| 向量化回测 (10年日线) | 2430交易日 | <3秒 | - |
| 多策略并行 (5策略) | 243交易日 | <2秒 | 2.5x faster |

---

## 🐛 常见问题

### Q: 数据获取失败怎么办？
**A**: 检查网络连接，或尝试切换数据源：
```python
# 切换数据源
dm.get_data_sync(symbol, start, end, source='akshare')  # 或 'baostock'
```

### Q: 如何处理停牌/涨跌停？
**A**: 系统内置了涨跌停检测，可在 `risk_manager.py` 中配置：
```python
RISK_CONTROL = {
    "check_limit_up": True,   # 检查涨停
    "check_limit_down": True, # 检查跌停
}
```

### Q: 支持哪些市场？
**A**: 当前支持：
- 🇨🇳 A股 (主要)
- 🇭🇰 港股
- 🇺🇸 美股

### Q: 如何获取帮助？
**A**:
- 📖 查看 [文档](./docs/)
- 💬 提交 [Issue](https://github.com/feiiiiii5/quantitative_trading_system/issues)
- 📧 邮箱: support@quantsystem.pro

---

## 🤝 贡献指南

我们欢迎所有形式的贡献！请参阅 [CONTRIBUTING.md](CONTRIBUTING.md) 了解详情。

### 贡献方式

1. 🐛 **报告Bug** - 通过 [Issue](https://github.com/feiiiiii5/quantitative_trading_system/issues) 报告
2. 💡 **提出新功能** - 通过 [Discussion](https://github.com/feiiiiii5/quantitative_trading_system/discussions) 讨论
3. 📖 **完善文档** - 提交 PR 完善文档
4. 🔧 **提交代码** - 提交 PR 修复/添加功能

### 开发流程

```bash
# 1. Fork 本仓库
# 2. 克隆你的 Fork
git clone https://github.com/YOUR_USERNAME/quantitative_trading_system.git
cd quantitative_trading_system

# 3. 创建特性分支
git checkout -b feature/YourFeatureName

# 4. 安装开发依赖
pip install -r requirements.txt
pip install -r requirements-dev.txt  # 如果有

# 5. 进行开发...
# 6. 运行测试
python -m pytest tests/

# 7. 提交更改
git commit -m "Add: YourFeatureName"

# 8. 推送到你的 Fork
git push origin feature/YourFeatureName

# 9. 在 GitHub 上创建 Pull Request
```

---

## 📄 许可证

本项目采用 **MIT 许可证** - 详见 [LICENSE](LICENSE) 文件

```
MIT License

Copyright (c) 2026 QuantSystem Pro

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
```

---

## 🙏 致谢

| 项目 | 用途 | 链接 |
|------|------|------|
| akshare | 免费财经数据 | [GitHub](https://github.com/akfamily/akshare) |
| baostock | A股数据 | [官网](https://www.baostock.com/) |
| yfinance | 美股数据 | [GitHub](https://github.com/ranaroussi/yfinance) |
| pandas | 数据分析 | [官网](https://pandas.pydata.org/) |
| numpy | 科学计算 | [官网](https://numpy.org/) |
| scikit-learn | 机器学习 | [官网](https://scikit-learn.org/) |
| XGBoost | 梯度提升 | [官网](https://xgboost.readthedocs.io/) |
| Streamlit | Web界面 | [官网](https://streamlit.io/) |
| Plotly | 数据可视化 | [官网](https://plotly.com/) |

---

## 📊 项目统计

![Alt](https://repobeats.axiom.co/api/embed/xxxxxxxxxxxxxxx.svg)

| 指标 | 数值 |
|------|------|
| ⭐ Stars | ![Stars](https://img.shields.io/github/stars/feiiiiii5/quantitative_trading_system?style=social) |
| 🍴 Forks | ![Forks](https://img.shields.io/github/forks/feiiiiii5/quantitative_trading_system?style=social) |
| 👀 Watchers | ![Watchers](https://img.shields.io/github/watchers/feiiiiii5/quantitative_trading_system?style=social) |
| 🐛 Issues | ![Issues](https://img.shields.io/github/issues/feiiiiii5/quantitative_trading_system) |

---

<div align="center">

**如果这个项目对您有帮助，请给我们一个 ⭐！**

Made with ❤️ by Quantitative Trading Team

[![Streamlit](https://static.streamlit.io/badges/streamlit_badge.svg)](https://streamlit.io)
[![Powered by quant](https://img.shields.io/badge/Powered%20by-Quantsystem-blue.svg)](https://github.com/feiiiiii5/quantitative_trading_system)

</div>
