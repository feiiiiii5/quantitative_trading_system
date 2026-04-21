# 更新日志

所有重要变更都会记录在此文件中。

格式基于 [Keep a Changelog](https://keepachangelog.com/zh-CN/1.0.0/)，
版本号遵循 [Semantic Versioning](https://semver.org/lang/zh-CN/)。

## [3.0.0] - 2026-04-21 - QuantSystem Pro 重构

### 修复
- **架构缺陷修复**: 统一 `BaseStrategy` 接口，所有策略通过 `core.engine` 导入
- **Broker PnL 计算**: 新增 `avg_cost` 持仓均价追踪，卖出时正确计算盈亏
- **equity_curve 同步**: 事件驱动回测在每次循环末尾更新权益曲线
- **macOS 兼容**: 修复 `get_data_sync` 在已有事件循环线程中的嵌套问题
- **索引对齐**: 修复机器学习策略中 `feature_data` 与 `labels` 的索引对齐

### 新增
- **因子引擎** (`core/factor_engine.py`): 多周期动量/质量/价值因子、IC分析、中性化、因子合成
- **组合优化器** (`core/portfolio_optimizer.py`): 风险平价/最大夏普/最小方差权重优化
- **独立指标模块** (`utils/metrics.py`): Omega比率、尾部比率、滚动夏普、月度收益热力图
- **成分VaR** (`risk/advanced_risk_manager.py`): 各资产对组合总VaR的贡献量
- **动态杠杆** (`risk/advanced_risk_manager.py`): 波动率目标法实时调整杠杆

### 重构
- **向量化回测**: 真正的向量化实现（T+1执行、前向填充持仓、换手成本计算）
- **策略接口统一**: `__init__(**kwargs)`、`init(self)`、`next(self, index)` 标准签名
- **类型注解**: 完整类型注解覆盖所有公共API

## [2.0.0] - 2026-04-21

### 新增
- 专业版量化交易系统 `pro_main.py`
- 多因子量化策略（Fama-French五因子模型）
- 自适应市场状态策略（自动识别趋势/震荡/高波动/低波动）
- 机器学习预测策略（XGBoost/LightGBM集成）
- 统计套利策略（配对交易）
- 做市商策略（流动性提供）
- 向量化回测引擎（性能提升100x+）
- 异步数据管理器（并发获取、多级缓存）
- 高级风险管理器（VaR、CVaR、压力测试）
- 专业资金管理（凯利公式、波动率目标、风险平价）
- 动态仓位管理（根据市场状态自动调整）
- 追踪止损功能
- 策略参数优化工具
- 完善的GitHub项目文档

### 优化
- 系统架构全面升级，模块化设计
- 数据处理流程异步化
- 回测引擎向量化计算
- 缓存策略优化（内存+磁盘）

## [1.0.0] - 2026-04-21

### 新增
- 基础量化交易系统
- 数据获取与处理模块（akshare、tushare、baostock）
- 策略开发模块（MA交叉、RSI、布林带）
- 回测引擎模块
- 实盘交易接口模块
- 风险控制模块
- 用户界面模块（Streamlit）
- 详细操作文档和教程
