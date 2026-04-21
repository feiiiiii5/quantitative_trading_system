#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试Streamlit部署
"""

import streamlit as st

# 页面配置
st.set_page_config(
    page_title="Test App",
    page_icon="📈",
    layout="wide"
)

# 简单的测试界面
st.title("Streamlit 部署测试")
st.write("如果您看到这个页面，说明Streamlit部署成功！")

# 测试输入框
user_input = st.text_input("请输入股票代码", "000001")
if st.button("分析"):
    st.success(f"您输入的股票代码是: {user_input}")
    st.write("部署成功！")

# 测试图表
import pandas as pd
import numpy as np
import plotly.graph_objects as go

dates = pd.date_range('2023-01-01', periods=100)
data = pd.DataFrame({
    'date': dates,
    'value': np.random.randn(100).cumsum() + 100
})

fig = go.Figure()
fig.add_trace(go.Scatter(x=data['date'], y=data['value'], mode='lines'))
fig.update_layout(title="测试图表")
st.plotly_chart(fig)

st.write("部署测试完成！")
