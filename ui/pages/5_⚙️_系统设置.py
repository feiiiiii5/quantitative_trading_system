#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import sys
from pathlib import Path

root = Path(__file__).resolve()
while not (root / 'app.py').exists() and root != root.parent:
    root = root.parent
if str(root) not in sys.path:
    sys.path.insert(0, str(root))

import streamlit as st
import subprocess

from ui.styles import APPLE_CSS, DARK_CSS

st.set_page_config(page_title="系统设置", page_icon="⚙️", layout="wide")

if 'dark_mode' not in st.session_state:
    st.session_state.dark_mode = False

if st.session_state.dark_mode:
    st.markdown(DARK_CSS, unsafe_allow_html=True)
else:
    st.markdown(APPLE_CSS, unsafe_allow_html=True)

st.markdown('<div class="section-title">⚙️ 系统设置</div>', unsafe_allow_html=True)

dark_toggle = st.toggle("🌙 暗色模式", value=st.session_state.dark_mode, key="settings_dark")
if dark_toggle != st.session_state.dark_mode:
    st.session_state.dark_mode = dark_toggle
    st.rerun()

st.markdown('<div class="section-subtitle">缓存管理</div>', unsafe_allow_html=True)

col1, col2 = st.columns(2)
with col1:
    if st.button("🗑️ 清理内存缓存", use_container_width=True):
        try:
            from data.async_data_manager import data_manager
            data_manager.cache.clear_memory_cache()
            st.success("内存缓存已清理")
        except Exception as e:
            st.error(f"清理失败: {e}")

with col2:
    if st.button("💾 清理磁盘缓存", use_container_width=True):
        try:
            from data.async_data_manager import data_manager
            data_manager.cache.clear_disk_cache()
            st.success("磁盘缓存已清理")
        except Exception as e:
            st.error(f"清理失败: {e}")

try:
    from data.async_data_manager import data_manager
    stats = data_manager.cache.cache_stats()

    st.markdown("""
    <div class="section-subtitle">缓存状态</div>
    """, unsafe_allow_html=True)

    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-label">内存条目</div>
            <div class="metric-value">{stats['memory_entries']}</div>
        </div>
        """, unsafe_allow_html=True)
    with col2:
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-label">磁盘条目</div>
            <div class="metric-value">{stats['disk_entries']}</div>
        </div>
        """, unsafe_allow_html=True)
    with col3:
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-label">内存大小</div>
            <div class="metric-value">{stats['memory_size_mb']}MB</div>
        </div>
        """, unsafe_allow_html=True)
    with col4:
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-label">磁盘大小</div>
            <div class="metric-value">{stats['disk_size_mb']}MB</div>
        </div>
        """, unsafe_allow_html=True)
except Exception:
    pass

st.markdown('<div class="section-subtitle">关于</div>', unsafe_allow_html=True)
st.markdown("""
<div class="apple-card" style="padding:24px;">
    <div style="font-size:24px; font-weight:700; color:var(--text-primary); margin-bottom:8px;">
        QuantSystem Pro
    </div>
    <div style="font-size:14px; color:var(--text-secondary); margin-bottom:16px;">
        完全免费开源的量化交易工具
    </div>
    <div style="display:flex; gap:12px; flex-wrap:wrap;">
        <span class="badge-up">🇨🇳 A股</span>
        <span class="badge-up">🇭🇰 港股</span>
        <span class="badge-up">🇺🇸 美股</span>
        <span class="badge-neutral">开源免费</span>
    </div>
</div>
""", unsafe_allow_html=True)
