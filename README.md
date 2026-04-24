# QuantSystem Pro

<p align="center">
  <img src="https://img.shields.io/badge/Python-3.9+-blue.svg" alt="Python">
  <img src="https://img.shields.io/badge/License-MIT-green.svg" alt="License">
  <img src="https://img.shields.io/badge/Platform-macOS%20|%20Linux%20|%20Windows-lightgrey.svg" alt="Platform">
</p>

<p align="center">
  <strong>专业量化交易系统 | Professional Quantitative Trading System</strong>
</p>

QuantSystem Pro 是一套面向专业投资者的量化交易系统，集成了业界领先的量化策略、高性能回测引擎和完善的风险管理体系。系统采用模块化设计，支持 A股、港股、美股 三大市场。

---

## ✨ 核心特性

| 特性 | 描述 |
|------|------|
| 🚀 高性能 | 向量化回测引擎，支持多策略并行计算 |
| 🧠 AI驱动 | 集成机器学习预测模型（XGBoost、LightGBM） |
| 📊 丰富策略 | 多因子模型、自适应市场、统计套利等 10+ 策略 |
| 🛡️ 完善风控 | VaR、CVaR、压力测试、动态止损 |
| 💰 专业资金管理 | 凯利公式、波动率目标、风险平价 |
| 📈 交互界面 | Streamlit Web 界面，可视化分析 |
| 🌐 多市场 | A股、港股、美股 全面支持 |

---

## 📋 支持的市场

| 市场 | 数据源（优先级排序） | 代码示例 |
|------|------------------------|----------|
| 🇨🇳 A股 | 腾讯财经 > Akshare > 新浪财经 > Baostock > 东方财富 | 000001, 600519 |
| 🇭🇰 港股 | 腾讯财经 > Akshare > 东方财富 | 00700, 09988 |
| 🇺🇸 美股 | 腾讯财经 > Akshare > 东方财富 | AAPL, TSLA, GOOGL |

### 数据源稳定性说明
- **腾讯财经**：稳定性高，响应速度快，适合作为首选数据源
- **Akshare**：数据全面，支持多个市场，作为主要备用数据源
- **新浪财经**：A股数据稳定，作为辅助数据源
- **Baostock**：A股历史数据丰富，作为历史数据补充
- **东方财富**：数据全面但稳定性较差，作为最后备用

---

## 🚀 快速开始

### 环境要求

| 要求 | 最低版本 | 推荐版本 |
|------|----------|----------|
| Python | 3.9 | 3.11+ |
| 内存 | 4GB | 8GB+ |
| 系统 | macOS / Linux / Windows | macOS 12+ / Ubuntu 20.04+ / Windows 10+ |

### 安装

```bash
# 克隆项目
git clone https://github.com/feiiiiii5/quantitative-trading-system.git
cd quantitative-trading-system

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
# Web 界面（一键启动，自动打开浏览器）
python main.py

# 命令行模式
python main.py --cli backtest --symbol 000001 --strategy ma_cross
```

---

## 🏗️ 系统架构

```
quantitative-trading-system/
├── main.py                      # 一键启动入口（Web + CLI）
├── core/                        # 核心引擎模块
│   ├── ai/                      # AI 预测模块
│   ├── backtest_v2/            # 回测引擎 V2
│   ├── data_infra/             # 数据基础设施
│   ├── execution/              # 订单执行引擎
│   ├── monitor/                # 监控告警系统
│   ├── platform/                # 平台管理模块
│   ├── portfolio/              # 组合管理模块
│   ├── research/               # 研究分析模块
│   ├── risk/                   # 风险管理模块
│   └── strategy_v2/            # 策略引擎 V2
├── api/                        # API 路由模块
├── strategies/                 # 策略模块
├── data/                       # 数据目录
├── static/                     # 静态文件
└── tests/                      # 测试模块
```

---

## 📊 内置策略

| 策略 | 类型 | 市场 | 描述 |
|------|------|------|------|
| ma_cross | 趋势跟踪 | A股/港股/美股 | 均线交叉策略 |
| rsi | 均值回归 | A股/港股/美股 | RSI 超买超卖策略 |
| bollinger | 趋势跟踪 | A股/港股/美股 | 布林带策略 |
| multi_factor | 多因子 | A股 | Fama-French 五因子模型 |
| adaptive | 自适应 | A股/港股/美股 | 市场状态自动识别 |
| ml | 机器学习 | A股/港股/美股 | XGBoost/LightGBM 预测 |
| stat_arb | 统计套利 | 跨市场 | 配对交易策略 |
| dragon_head | 趋势跟踪 | A股 | 龙头战法 |

---

## 🔧 API 接口

### REST API

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/stock/{symbol}` | 完整数据（历史+指标+预测+实时） |
| GET | `/api/history?symbol=&period=` | 历史 K 线数据 |
| GET | `/api/realtime?symbol=` | 实时行情 |
| GET | `/api/indicators?symbol=` | 技术指标 |
| GET | `/api/prediction?symbol=` | 涨跌预测 |
| GET | `/api/backtest` | 策略回测 |
| GET | `/api/risk/var` | VaR 风险计算 |
| WS | `/ws/{symbol}` | 实时推送（30s间隔） |

### 技术指标

支持 20+ 技术指标：MA / EMA / BOLL / MACD / SuperTrend / Ichimoku / RSI / KDJ / CCI / Williams %R / ROC / VWAP / OBV / CMF / ATR / 历史波动率

---

## 📁 项目结构详解

### 核心模块

- **core/ai** — AI 预测模块（机器学习模型、自适应参数、模式识别）
- **core/backtest_v2** — 事件驱动回测引擎（微观结构、蒙特卡洛模拟、参数优化）
- **core/data_infra** — 数据基础设施（异步数据管理、实时流、历史数据）
- **core/execution** — 订单执行引擎（算法交易、多账户管理、订单路由）
- **core/monitor** — 监控告警系统（性能面板、异常检测、审计日志）
- **core/platform** — 平台管理（认证安全、环境管理、微服务、调度器）
- **core/portfolio** — 组合管理（归因分析、资金分配、衍生品、再平衡）
- **core/research** — 研究分析（基本面、研报分析、板块分析、情绪分析）
- **core/risk** — 风险管理（仓位管理、风险归因、止损、压力测试、VaR）
- **core/strategy_v2** — 策略引擎 V2（因子研究、ML 策略、可视化构建器）

---

## 🛠️ 开发指南

### 添加新策略

```python
from core.strategies import BaseStrategy

class MyStrategy(BaseStrategy):
    def __init__(self, params=None):
        super().__init__(params)

    def next(self, bar):
        # 策略逻辑
        if self.signal:
            self.order_target_percent(target=self.signal)
```

### 运行测试

```bash
pytest tests/ -v
```

---

## 🤝 贡献指南

欢迎提交 Pull Request 或创建 Issue！

1. Fork 本仓库
2. 创建特性分支 (`git checkout -b feature/amazing-feature`)
3. 提交更改 (`git commit -m 'Add amazing feature'`)
4. 推送到分支 (`git push origin feature/amazing-feature`)
5. 创建 Pull Request

---

## 📄 许可证

本项目基于 MIT 许可证开源。详见 [LICENSE](LICENSE) 文件。

---

## ⚠️ 免责声明

本系统所有预测结果和回测绩效仅供参考，不构成任何投资建议。模型基于历史数据统计，无法保证未来收益。投资有风险，入市需谨慎。

---

## 📧 联系方式

- GitHub Issues: [https://github.com/feiiiiii5/quantitative-trading-system/issues](https://github.com/feiiiiii5/quantitative-trading-system/issues)

---

<p align="center">
  <sub>Made with ❤️ by <a href="https://github.com/feiiiiii5">feiiiiii5</a></sub>
</p>
