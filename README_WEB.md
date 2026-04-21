# QuantSystem Pro Web

**QuantSystem Pro 是完全免费开源的量化交易工具**

## 🚀 快速启动

```bash
# 安装依赖
pip install -r requirements_web.txt

# 启动Web界面
streamlit run app.py

# 或使用Python直接运行
python app.py
```

## 💻 命令行模式

```bash
# 回测
python app.py --cli backtest --symbol 000001 --strategy ma_cross

# 完整分析
python app.py --cli analyze --symbol 000001

# 参数优化
python app.py --cli optimize --symbol 000001 --strategy ma_cross

# Walkforward分析
python app.py --cli walkforward --symbol 000001 --windows 5
```

## 🌐 支持市场

| 市场 | 代码格式 | 示例 |
|------|---------|------|
| 🇨🇳 A股 | 6位数字 | 000001, 600519 |
| 🇭🇰 港股 | 4-5位数字 | 00700, 09988 |
| 🇺🇸 美股 | 字母代码 | AAPL, TSLA |

## ⚠️ 免责声明

本工具仅供学习和研究使用，不构成任何投资建议。市场有风险，投资需谨慎。
