#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
导出功能组件
"""

import streamlit as st
import pandas as pd
from datetime import datetime


def render_export(symbol: str, data: pd.DataFrame, metrics=None):
    """
    渲染导出功能

    Args:
        symbol: 股票代码
        data: 历史数据
        metrics: 回测指标
    """
    st.markdown("### 📥 导出")

    col1, col2 = st.columns(2)

    with col1:
        # 导出数据CSV
        if data is not None and not data.empty:
            csv = data.to_csv().encode('utf-8')
            st.download_button(
                label="📊 导出数据 (CSV)",
                data=csv,
                file_name=f"{symbol}_data_{datetime.now().strftime('%Y%m%d')}.csv",
                mime="text/csv",
                use_container_width=True,
            )

    with col2:
        # 导出报告
        if st.button("📄 导出报告 (PDF)", use_container_width=True):
            try:
                from reports.report_generator import ReportGenerator
                generator = ReportGenerator()
                report_path = f"reports/{symbol}_report_{datetime.now().strftime('%Y%m%d')}.html"
                generator.generate_html_report(
                    metrics=metrics,
                    equity_curve=[],
                    trades=[],
                    output_path=report_path,
                )
                st.success(f"报告已生成: {report_path}")
            except Exception as e:
                st.error(f"报告生成失败: {e}")
