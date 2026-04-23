# 贡献指南

感谢您对 QuantSystem Pro 项目的关注！我们欢迎任何形式的贡献，包括但不限于报告问题、提交代码、改进文档等。

---

## 📋 目录

- [行为准则](#行为准则)
- [快速开始](#快速开始)
- [如何贡献](#如何贡献)
- [开发流程](#开发流程)
- [代码规范](#代码规范)
- [提交信息规范](#提交信息规范)
- [Pull Request 流程](#pull-request-流程)
- [报告问题](#报告问题)

---

## 行为准则

参与本项目的所有成员必须遵守以下行为准则：

- **友善互动** — 对所有参与者保持礼貌和尊重
- **包容开放** — 欢迎不同背景和经验水平的贡献者
- **专业沟通** — 避免任何形式的歧视、骚扰或攻击性言论
- **协作精神** — 积极帮助他人，共同提升项目质量

---

## 快速开始

```bash
# Fork 本仓库
# 克隆你的 Fork
git clone https://github.com/YOUR_USERNAME/quantitative-trading-system.git
cd quantitative-trading-system

# 添加上游仓库
git remote add upstream https://github.com/feiiiiii5/quantitative-trading-system.git

# 创建特性分支
git checkout -b feature/your-feature-name
```

---

## 如何贡献

### 🐛 报告问题

如果您发现任何问题，请通过 GitHub Issues 创建并提供以下信息：

- 问题描述（清晰简洁）
- 复现步骤
- 预期行为 vs 实际行为
- 环境信息（操作系统、Python 版本等）
- 相关的日志或截图

### 💡 提出新功能

欢迎提出新功能建议！请通过 GitHub Issues 创建并包含：

- 功能描述
- 使用场景
- 可能的实现方案（可选）

### 🔧 提交代码

1. 认领或创建 Issue
2. 按照下方的代码规范编写代码
3. 添加或更新相关测试
4. 确保所有测试通过
5. 更新相关文档

---

## 开发流程

### 环境设置

```bash
# 使用 Python 3.9+
python --version

# 创建虚拟环境
python -m venv venv
source venv/bin/activate  # Linux/macOS
# 或
.\venv\Scripts\activate   # Windows

# 安装开发依赖
pip install -r requirements.txt
pip install pytest pytest-cov black flake8 mypy
```

### 运行测试

```bash
# 运行所有测试
pytest tests/ -v

# 运行单个测试文件
pytest tests/test_backtest_v2.py -v

# 带覆盖率报告
pytest tests/ --cov=. --cov-report=html
```

### 代码检查

```bash
# 代码格式化 (black)
black .

# 代码检查 (flake8)
flake8 .

# 类型检查 (mypy)
mypy .
```

---

## 代码规范

### Python 代码规范

- 遵循 [PEP 8](https://pep8.org/) 风格指南
- 使用 4 空格缩进
- 最大行长度：120 字符
- 使用有意义的变量和函数命名

### 命名约定

| 类型 | 约定 | 示例 |
|------|------|------|
| 模块 | lowercase | `data_fetcher.py` |
| 类 | CamelCase | `BacktestEngine` |
| 函数 | lowercase_with_underscores | `get_stock_data` |
| 常量 | UPPERCASE_WITH_UNDERSCORES | `MAX_POSITION_SIZE` |
| 变量 | lowercase_with_underscores | `stock_price` |

### 文档字符串

```python
def calculate_returns(prices: list[float]) -> float:
    """
    计算收益率。

    Args:
        prices: 价格序列

    Returns:
        收益率（百分比）

    Raises:
        ValueError: 当价格序列为空时
    """
    if not prices:
        raise ValueError("价格序列不能为空")
    return ((prices[-1] - prices[0]) / prices[0]) * 100
```

---

## 提交信息规范

### 格式

```
<type>(<scope>): <subject>

<body>

<footer>
```

### 类型 (Type)

| 类型 | 描述 |
|------|------|
| feat | 新功能 |
| fix | 修复 bug |
| docs | 文档更新 |
| style | 代码格式（不影响功能） |
| refactor | 重构 |
| test | 测试相关 |
| chore | 构建/工具相关 |

### 作用域 (Scope)

- `core` - 核心引擎
- `api` - API 路由
- `strategy` - 策略模块
- `risk` - 风险管理
- `data` - 数据处理
- `ui` - 用户界面

### 示例

```
feat(strategy): 添加均线交叉策略

- 实现 MA5/MA20/MA60 交叉信号
- 添加成交量确认机制
- 支持 A股/港股/美股

Closes #123
```

---

## Pull Request 流程

### 步骤

1. **Fork & Clone** — Fork 仓库并克隆到本地
2. **创建分支** — `git checkout -b feature/your-feature`
3. **编写代码** — 遵循代码规范
4. **提交更改** — 使用规范的提交信息
5. **推送到 Fork** — `git push origin feature/your-feature`
6. **创建 PR** — 在 GitHub 上创建 Pull Request
7. **等待审核** — 项目维护者会尽快审核

### PR 模板

```markdown
## 描述
<!-- 简要描述此 PR 的内容和目的 -->

## 更改类型
- [ ] 新功能 (feat)
- [ ] 修复 bug (fix)
- [ ] 文档更新 (docs)
- [ ] 代码重构 (refactor)
- [ ] 测试相关 (test)
- [ ] 其他 (chore)

## 关联 Issue
<!-- 关联的 Issue 编号，如：Closes #123 -->

## 测试
<!-- 描述您是如何测试这些更改的 -->

## 检查清单
- [ ] 我的代码遵循本项目的代码规范
- [ ] 我已经添加了必要的测试
- [ ] 所有测试都通过了
- [ ] 我已经更新了相关文档
```

---

## 报告问题

### 创建 Issue 时请使用模板

```markdown
## 问题描述
<!-- 清晰描述问题 -->

## 复现步骤
1.
2.
3.

## 预期行为
<!-- 您期望发生什么 -->

## 实际行为
<!-- 实际发生了什么 -->

## 环境信息
- 操作系统：
- Python 版本：
- 相关依赖版本：

## 额外信息
<!-- 任何其他有帮助的信息 -->
```

---

## 许可证

通过贡献代码，您同意您的贡献将按照 MIT 许可证开源。

---

感谢您的贡献！ 🎉
