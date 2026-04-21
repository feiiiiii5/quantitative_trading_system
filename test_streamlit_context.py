#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""测试Streamlit上下文检测"""

import sys
import os
from pathlib import Path

project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

def _is_streamlit_context():
    """检测是否在Streamlit上下文中运行"""
    try:
        # 方法1：检查streamlit特定的环境变量
        if 'STREAMLIT_SERVER_PORT' in os.environ:
            return True
        # 方法2：检查当前进程是否是streamlit
        import psutil
        current_process = psutil.Process()
        cmdline = current_process.cmdline()
        for arg in cmdline:
            if 'streamlit' in arg.lower():
                return True
        # 方法3：检查是否有ScriptRunContext且不是None
        from streamlit.runtime.scriptrunner import get_script_run_ctx
        ctx = get_script_run_ctx()
        # 只有当ctx存在且有session_id时，才认为是在Streamlit上下文中
        return ctx is not None and hasattr(ctx, 'session_id') and ctx.session_id is not None
    except (ImportError, Exception) as e:
        print(f"检测失败: {e}")
        return False

print(f"是否在Streamlit上下文中: {_is_streamlit_context()}")
print(f"环境变量 STREAMLIT_SERVER_PORT: {os.environ.get('STREAMLIT_SERVER_PORT', '未设置')}")

try:
    import psutil
    current_process = psutil.Process()
    print(f"当前进程: {current_process.name()}")
    print(f"命令行: {' '.join(current_process.cmdline())}")
except ImportError:
    print("psutil 未安装")

# 测试导入streamlit
try:
    import streamlit as st
    from streamlit.runtime.scriptrunner import get_script_run_ctx
    ctx = get_script_run_ctx()
    print(f"Streamlit版本: {st.__version__}")
    print(f"ScriptRunContext: {ctx}")
    if ctx:
        print(f"Session ID: {getattr(ctx, 'session_id', '无')}")
except Exception as e:
    print(f"Streamlit导入失败: {e}")
