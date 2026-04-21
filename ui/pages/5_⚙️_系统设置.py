#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
系统设置页面
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

import streamlit as st

from ui.styles import APPLE_CSS

st.set_page_config(page_title="系统设置", page_icon="⚙️", layout="wide")
st.markdown(APPLE_CSS, unsafe_allow_html=True)

st.markdown("# ⚙️ 系统设置")

# 主题切换
st.markdown("### 🎨 主题")
dark_mode = st.toggle("暗色模式", value=st.session_state.get('dark_mode', False))
st.session_state.dark_mode = dark_mode

if dark_mode:
    from ui.styles import DARK_CSS
    st.markdown(DARK_CSS, unsafe_allow_html=True)

# 缓存管理
st.markdown("### 🗄️ 缓存管理")
from data.async_data_manager import AsyncDataManager
dm = AsyncDataManager()

col1, col2 = st.columns(2)
with col1:
    if st.button("清理内存缓存"):
        dm.cache.clear_memory_cache()
        st.success("内存缓存已清理")
with col2:
    if st.button("清理磁盘缓存"):
        dm.cache.clear_disk_cache()
        st.success("磁盘缓存已清理")

# 缓存统计
stats = dm.cache.cache_stats()
st.markdown("#### 缓存统计")
st.json(stats)

# 数据源配置
st.markdown("### 📡 数据源")
st.info("当前支持：akshare（免费）、baostock（免费）、yfinance（美股/港股）")

# 关于
st.markdown("### ℹ️ 关于")
st.markdown("""
**QuantSystem Pro** - 完全免费开源的量化交易工具

版本：1.0.0

功能：
- 📊 股票数据分析（A股/港股/美股）
- 📈 K线图 + 技术指标
- 🔄 策略回测
- 🔮 涨跌概率预测
- 🔍 智能选股扫描
- 🌊 北向资金追踪
- 💼 组合优化

⚠️ 免责声明：本工具仅供学习研究，不构成投资建议。
""")
