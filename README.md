# QuantSystem Pro - 专业量化交易系统

<div align="center">

![Python](https://img.shields.io/badge/Python-3.8+-blue.svg)
![License](https://img.shields.io/badge/License-MIT-green.svg)
![Stars](https://img.shields.io/github/stars/feiiiiii5/quantitative_trading_system?style=social)

**一套功能强大、高效、易用的专业级量化交易系统**

[English](./README_EN.md) | 简体中文

</div>

---

## 📌 项目简介

QuantSystem Pro 是一套面向专业投资者的量化交易系统，集成了业界领先的量化策略、高性能回测引擎和完善的风险管理体系。系统采用模块化设计，易于扩展，适合从入门到专业的各级用户。

### 核心特性

- 🚀 **高性能**: 向量化回测引擎，支持多策略并行计算
- 🧠 **AI驱动**: 集成机器学习预测模型（XGBoost、LightGBM）
- 📊 **丰富策略**: 多因子模型、自适应市场、统计套利等
- 🛡️ **完善风控**: VaR、CVaR、压力测试、动态止损
- 💰 **专业资金管理**: 凯利公式、波动率目标、风险平价
- 📈 **交互界面**: Streamlit Web界面，可视化分析

---

## 🏗️ 系统架构

```
quantitative_trading_system/
├── core/                    # 核心引擎模块
│   ├── engine.py            # Cerebro引擎（事件驱动+向量化）
│   ├── factor_engine.py     # 因子引擎（动量/质量/价值/IC分析）
│   └── portfolio_optimizer.py  # 组合优化器（风险平价/最大夏普/最小方差）
├── strategies/              # 策略模块
│   ├── __init__.py          # 策略包导出
│   ├── base_strategy.py     # 策略基类（从core.engine导入）
│   ├── example_ma_cross.py  # 示例策略
│   └── advanced_strategies.py  # 高级策略（多因子/自适应/ML/套利/做市）
├── data/                    # 数据模块
│   ├── async_data_manager.py  # 异步数据管理（macOS兼容）
│   └── data_manager.py      # 数据获取
├── backtest/                # 回测模块（向后兼容）
│   ├── engine.py            # 回测引擎
│   └── vectorized_engine.py  # 向量化回测
├── risk/                    # 风控模块
│   ├── risk_manager.py      # 风险管理
│   └── advanced_risk_manager.py  # 高级风控（VaR/成分VaR/动态杠杆）
├── trading/                 # 交易模块
│   └── trader.py           # 交易执行
├── ui/                      # 界面模块
│   └── web_interface.py    # Web界面
├── utils/                   # 工具模块
│   ├── logger.py           # 日志工具
│   └── metrics.py          # 绩效指标（Omega/尾部比率/滚动夏普）
├── config/                  # 配置模块
│   └── settings.py         # 系统配置
├── test_engine.py          # 引擎测试脚本
├── pro_main.py             # 专业版入口
└── main.py                 # 标准版入口
```

---

## 🚀 快速开始

### 环境要求

- Python 3.8+
- macOS / Linux / Windows

### 安装

```bash
# 克隆项目
git clone https://github.com/feiiiiii5/quantitative_trading_system.git
cd quantitative_trading_system

# 创建虚拟环境（推荐）
python -m venv venv
source venv/bin/activate  # Linux/macOS
# or
.\venv\Scripts\activate   # Windows

# 安装依赖
pip install -r requirements.txt
```

### 快速运行

```bash
# 回测示例
python pro_main.py backtest --strategy ma_cross --symbol 000001

# 策略分析
python pro_main.py analyze --strategy ml --symbol 000001

# 参数优化
python pro_main.py optimize --strategy ma_cross --symbol 000001

# 启动Web界面
python pro_main.py web
```

---

## 📊 内置策略

| 策略名称 | 类型 | 描述 |
|---------|------|------|
| `ma_cross` | 趋势跟踪 | 均线交叉策略 |
| `rsi` | 均值回归 | RSI超买超卖策略 |
| `bollinger` | 趋势跟踪 | 布林带策略 |
| `multi_factor` | 多因子 | Fama-French五因子模型 |
| `adaptive` | 自适应 | 市场状态自动识别 |
| `ml` | 机器学习 | XGBoost/LightGBM预测 |
| `stat_arb` | 统计套利 | 配对交易策略 |

---

## 🛡️ 风险管理功能

### 核心指标
- **VaR / CVaR**: 风险价值与条件风险价值
- **夏普比率**: 风险调整收益
- **最大回撤**: 历史最大回撤及持续期
- **Calmar比率**: 年化收益/最大回撤

### 风控机制
- 动态仓位管理（凯利公式）
- 波动率目标仓位
- 追踪止损
- 压力测试
- 多市场状态适配

---

## 📈 性能优化

### 向量化回测
- 使用 NumPy/Pandas 向量化运算
- 比传统事件驱动回测快 100x+
- 支持多策略并行回测

### 数据管理
- 异步并发数据获取
- 多级缓存（内存+磁盘）
- 增量数据更新

---

## 🎯 使用示例

### 1. Python API 使用

```python
from data.async_data_manager import AsyncDataManager
from strategies.example_ma_cross import MACrossStrategy
from backtest.vectorized_engine import VectorizedBacktestEngine

# 获取数据
dm = AsyncDataManager()
data = dm.get_data_sync('000001', '2023-01-01', '2024-01-01')

# 创建策略
strategy = MACrossStrategy({'fast_period': 5, 'slow_period': 20})

# 回测
engine = VectorizedBacktestEngine()
result = engine.run(data, your_signal_function)
result.print_summary()
```

### 2. 自定义策略

```python
from strategies.base_strategy import BaseStrategy

class MyStrategy(BaseStrategy):
    def __init__(self, parameters=None):
        super().__init__(name="MyStrategy", parameters=parameters)
    
    def init(self, data):
        # 初始化计算
        self.sma = data['close'].rolling(20).mean()
    
    def next(self, index, current_data):
        # 交易逻辑
        if current_data['close'] > self.sma.iloc[index]:
            return self.buy(reason="价格突破均线")
        return self.hold()
```

---

## ⚙️ 配置说明

### 交易配置 (`config/settings.py`)

```python
TRADING = {
    "broker": "backtest",           # 经纪商: backtest/paper/real
    "commission_rate": 0.0003,       # 手续费率
    "slippage": 0.001,               # 滑点
    "initial_cash": 1000000,         # 初始资金
}

RISK_CONTROL = {
    "max_position_per_stock": 0.2,  # 单只最大仓位
    "max_total_position": 0.8,      # 总仓位上限
    "stop_loss": 0.05,               # 止损比例
    "take_profit": 0.15,             # 止盈比例
    "max_drawdown": 0.2,             # 最大回撤限制
}
```

---

## 🐛 常见问题

### Q: 数据获取失败怎么办？
A: 检查网络连接，或尝试切换数据源（akshare/baostock）。

### Q: 如何处理停牌/涨跌停？
A: 系统内置了涨跌停检测，可在 `risk_manager.py` 中配置。

### Q: 支持哪些市场？
A: 当前主要支持A股市场，可扩展至港股、美股等。

---

## 📝 文档

- [用户指南](./docs/guide.md)
- [API参考](./docs/api.md)
- [策略开发教程](./docs/strategy_tutorial.md)
- [部署指南](./docs/deployment.md)

---

## 🤝 贡献指南

欢迎提交Issue和Pull Request！

1. Fork 本仓库
2. 创建特性分支 (`git checkout -b feature/AmazingFeature`)
3. 提交更改 (`git commit -m 'Add AmazingFeature'`)
4. 推送到分支 (`git push origin feature/AmazingFeature`)
5. 创建Pull Request

---

## 📄 许可证

本项目采用 MIT 许可证 - 详见 [LICENSE](LICENSE) 文件

---

## 🙏 致谢

- [akshare](https://github.com/akfamily/akshare) - 免费财经数据
- [pandas](https://pandas.pydata.org/) - 数据分析
- [scikit-learn](https://scikit-learn.org/) - 机器学习
- [XGBoost](https://xgboost.readthedocs.io/) - 梯度提升
- [Streamlit](https://streamlit.io/) - Web界面框架

---

<div align="center">

**如果这个项目对您有帮助，请给我们一个 ⭐！**

Made with ❤️ by Quantitative Trading Team

</div>
