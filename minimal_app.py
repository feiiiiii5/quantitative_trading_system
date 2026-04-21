#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
最小化测试应用
"""

# 只导入streamlit
import streamlit as st

# 页面配置
st.set_page_config(
    page_title="Minimal Test",
    page_icon="📈",
    layout="centered"
)

# 最基本的界面
st.title("QuantSystem Pro")
st.write("完全免费开源的量化交易工具")
st.write("测试部署...")

# 简单的输入输出
symbol = st.text_input("输入股票代码", "000001")
if st.button("分析"):
    st.success(f"股票代码: {symbol}")
    st.write("部署成功！")

st.write("应用运行正常")
