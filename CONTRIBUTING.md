# 贡献指南

感谢您对 QuantSystem Pro 项目的兴趣！我们非常欢迎各种形式的贡献。

---

## 📋 目录

- [行为准则](#行为准则)
- [如何贡献](#如何贡献)
- [开发环境设置](#开发环境设置)
- [开发流程](#开发流程)
- [代码规范](#代码规范)
- [提交信息规范](#提交信息规范)
- [测试要求](#测试要求)
- [文档要求](#文档要求)
- [Pull Request 流程](#pull-request-流程)

---

## 行为准则

参与本项目即表示您同意遵守我们的行为准则。请阅读我们的 [CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md) 了解详情。

---

## 如何贡献

### 🐛 报告 Bug

1. 在提交 Issue 之前，请先搜索是否已经存在相同的问题
2. 使用 Bug Report 模板创建 Issue
3. 包含以下信息：
   - 清晰的标题和描述
   - 复现步骤
   - 预期行为和实际行为
   - Python 版本、操作系统环境
   - 相关日志或错误信息
   - 建议的修复方案（如果有）

### 💡 提出新功能

1. 先在 [Discussions](https://github.com/feiiiiii5/quantitative_trading_system/discussions) 中讨论您的想法
2. 使用 Feature Request 模板创建 Issue
3. 详细描述功能需求和使用场景

### 📖 完善文档

- 修复文档中的错别字或语法错误
- 添加缺失的文档内容
- 翻译文档到其他语言
- 添加使用示例或教程

### 🔧 提交代码

请遵循下方的开发流程和代码规范。

---

## 开发环境设置

### 1. 前提条件

- Python 3.9 或更高版本
- Git
- pip 或 conda

### 2. 克隆仓库

```bash
# 1. Fork 仓库到您的账户

# 2. 克隆您的 Fork
git clone https://github.com/YOUR_USERNAME/quantitative_trading_system.git
cd quantitative_trading_system

# 3. 添加上游仓库
git remote add upstream https://github.com/feiiiiii5/quantitative_trading_system.git

# 4. 验证远程仓库
git remote -v
# 应该显示:
# origin    https://github.com/YOUR_USERNAME/quantitative_trading_system.git (fetch)
# origin    https://github.com/YOUR_USERNAME/quantitative_trading_system.git (push)
# upstream  https://github.com/feiiiiii5/quantitative_trading_system.git (fetch)
# upstream  https://github.com/feiiiiii5/quantitative_trading_system.git (push)
```

### 3. 创建虚拟环境

```bash
# 使用 venv
python -m venv venv
source venv/bin/activate  # Linux/macOS
# 或
.\venv\Scripts\activate   # Windows

# 使用 conda
conda create -n quantsystem python=3.11
conda activate quantsystem
```

### 4. 安装依赖

```bash
# 安装项目依赖
pip install -r requirements.txt

# 安装开发依赖
pip install pytest pytest-cov black flake8 mypy sphinx
```

### 5. 验证安装

```bash
python app.py --cli --help
```

---

## 开发流程

### 1. 创建特性分支

```bash
# 确保在 main 分支上
git checkout main

# 拉取最新代码
git pull upstream main

# 创建特性分支
git checkout -b feature/your-feature-name
# 或
git checkout -b bugfix/your-bugfix-name
# 或
git checkout -b docs/your-documentation-name
```

### 2. 进行开发

```bash
# 进行您的更改...
# 编写代码、修复 bug、完善文档等

# 定期同步上游更改（推荐）
git fetch upstream
git merge upstream/main
```

### 3. 运行测试

```bash
# 运行所有测试
python -m pytest

# 运行特定测试文件
python -m pytest tests/test_engine.py

# 运行特定测试
python -m pytest tests/test_engine.py::test_specific_function

# 查看测试覆盖率
python -m pytest --cov=. --cov-report=html
```

### 4. 格式化代码

```bash
# 使用 black 格式化
black .

# 使用 flake8 检查
flake8 .

# 使用 mypy 类型检查
mypy .
```

### 5. 提交更改

```bash
# 添加更改的文件
git add .

# 提交（使用语义化提交信息）
git commit -m "Add: 添加新的均线交叉策略"

# 推送到您的 Fork
git push origin feature/your-feature-name
```

---

## 代码规范

### Python 风格指南

本项目遵循 **PEP 8** 规范，并使用 **Black** 进行代码格式化。

### 主要规范

| 规范 | 说明 |
|------|------|
| 缩进 | 4 个空格（不要使用 Tab） |
| 行长度 | 最大 88 字符（Black 默认） |
| 字符串引号 | 使用双引号 `""` |
| 导入顺序 | 标准库 → 第三方库 → 本地导入 |
| 命名规范 | `snake_case` 函数/变量，`PascalCase` 类名 |

### 导入顺序示例

```python
# 1. 标准库
import os
import sys
from datetime import datetime, timedelta
from typing import List, Dict, Optional

# 2. 第三方库
import pandas as pd
import numpy as np
from plotly import graph_objects as go

# 3. 本地导入
from core.engine import Cerebro, Broker
from strategies.base_strategy import BaseStrategy
from utils.logger import get_logger
```

### 文档字符串规范

```python
class MyStrategy(BaseStrategy):
    """策略的简短描述。

    更详细的说明（如果需要）。

    Args:
        param1: 参数1的描述
        param2: 参数2的描述

    Attributes:
        attribute1: 属性1的描述

    Example:
        >>> strategy = MyStrategy(param1=5, param2=10)
        >>> strategy.init()

    Note:
        注意事项（如果有）。
    """

    def my_method(self, value: int) -> bool:
        """方法的简短描述。

        更详细的说明（如果需要）。

        Args:
            value: 输入值的描述

        Returns:
            返回值的描述

        Raises:
            ValueError: 何时抛出此异常
        """
        pass
```

---

## 提交信息规范

本项目使用 **语义化提交信息（Semantic Commits）**。

### 格式

```
<type>(<scope>): <subject>

<body>

<footer>
```

### 类型 (Type)

| 类型 | 描述 |
|------|------|
| `Add` | 新功能 |
| `Fix` | Bug 修复 |
| `Update` | 更新功能/改进 |
| `Remove` | 删除功能/代码 |
| `Refactor` | 重构（不改变功能） |
| `Test` | 添加/修改测试 |
| `Docs` | 文档修改 |
| `Style` | 代码格式（不影响功能） |
| `Perf` | 性能优化 |
| `CI` | CI/CD 修改 |
| `Chore` | 其他更改 |

### 范围 (Scope)

可选，用于标注影响的模块：

- `core` - 核心引擎
- `strategy` - 策略相关
- `data` - 数据模块
- `risk` - 风险管理
- `ui` - 用户界面
- `docs` - 文档
- `test` - 测试
- `deps` - 依赖

### 示例

```bash
# 新功能
Add(strategy): 添加 Fama-French 五因子模型
Fix(core): 修复 broker PnL 计算错误
Update(ui): 优化 K 线图加载速度
Docs(readme): 更新安装指南
Refactor(data): 重构数据缓存机制
Test(engine): 添加回测引擎单元测试
```

---

## 测试要求

### 测试覆盖率

- 新功能必须包含测试
- Bug 修复必须包含回归测试
- 目标覆盖率：**80%+**

### 测试文件命名

```
tests/
├── test_core/
│   ├── __init__.py
│   ├── test_engine.py
│   └── test_broker.py
├── test_strategies/
│   ├── __init__.py
│   ├── test_ma_cross.py
│   └── test_multi_factor.py
└── test_data/
    ├── __init__.py
    └── test_data_manager.py
```

### 测试示例

```python
import pytest
from core.engine import Cerebro, Broker, ExecutionMode
from strategies.ma_cross import MACrossStrategy

class TestMACrossStrategy:
    """均线交叉策略测试"""

    def test_initialization(self):
        """测试策略初始化"""
        strategy = MACrossStrategy(fast_period=5, slow_period=20)
        assert strategy.name == "MA_Cross"
        assert strategy.parameters['fast_period'] == 5
        assert strategy.parameters['slow_period'] == 20

    def test_generate_signal(self):
        """测试信号生成"""
        # 创建测试数据
        import pandas as pd
        import numpy as np

        dates = pd.date_range('2023-01-01', periods=30)
        close = pd.Series([100 + i + np.random.randn() for i in range(30)], index=dates)

        # 测试策略
        strategy = MACrossStrategy(fast_period=5, slow_period=20)
        # ... 执行测试
```

---

## 文档要求

### 新功能文档

每个新功能必须包含：

1. **代码注释** - 解释复杂逻辑
2. **docstring** - 所有公共类和方法的文档
3. **更新 README.md** - 如果影响用户使用流程
4. **更新 CHANGELOG.md** - 记录更改

### 文档目录结构

```
docs/
├── index.md          # 文档首页
├── getting-started.md # 快速开始
├── strategies.md     # 策略开发
├── backtesting.md    # 回测指南
├── risk-management.md # 风险管理
└── api/              # API 参考
    ├── engine.md
    ├── strategy.md
    └── data.md
```

---

## Pull Request 流程

### 1. 创建 PR

1. 在 GitHub 上创建 Pull Request
2. 使用 PR 模板
3. 详细描述更改内容和动机
4. 关联相关 Issue

### 2. PR 模板

```markdown
## 描述
<!-- 简要描述此 PR 的更改 -->

## 更改类型
- [ ] 🐛 Bug 修复
- [ ] ✨ 新功能
- [ ] 📖 文档
- [ ] 🔧 改进
- [ ] 🧹 代码清理

## 相关 Issue
<!-- 使用 Closes #123 关联 Issue -->

## 检查清单
- [ ] 我的代码遵循此项目的代码规范
- [ ] 我已经进行了自我代码审查
- [ ] 我已经添加了必要的测试
- [ ] 所有测试都通过了
- [ ] 我已经更新了相关文档

## 其他备注
<!-- 其他需要审查者注意的事项 -->
```

### 3. 代码审查

- 至少需要 1 人审查
- 所有 CI 检查必须通过
- 审查者会检查：
  - 代码质量和风格
  - 测试覆盖率
  - 文档完整性
  - 功能正确性

### 4. 合并

合并条件：
- ✅ 所有 CI 检查通过
- ✅ 至少 1 人批准
- ✅ 无冲突
- ✅ 更新了 CHANGELOG

---

## 问题？

如果您有任何问题，请：

1. 查看 [常见问题](../README.md#🐛-常见问题)
2. 在 [Discussions](https://github.com/feiiiiii5/quantitative_trading_system/discussions) 中提问
3. 提交 [Issue](https://github.com/feiiiiii5/quantitative_trading_system/issues)

---

再次感谢您的贡献！ 🎉
