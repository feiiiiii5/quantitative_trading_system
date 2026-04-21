#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
QuantSystem Pro - Apple风格CSS样式定义
"""

APPLE_CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');

:root {
    --bg-primary: #f5f5f7;
    --bg-card: rgba(255, 255, 255, 0.72);
    --bg-card-solid: #ffffff;
    --text-primary: #1d1d1f;
    --text-secondary: #86868b;
    --accent-blue: #0071e3;
    --accent-green: #34c759;
    --accent-red: #ff3b30;
    --accent-orange: #ff9500;
    --border-color: rgba(0, 0, 0, 0.06);
    --shadow-card: 0 2px 12px rgba(0, 0, 0, 0.08);
    --shadow-hover: 0 4px 20px rgba(0, 0, 0, 0.12);
    --radius-card: 18px;
    --radius-button: 12px;
    --radius-pill: 20px;
    --font-family: -apple-system, BlinkMacSystemFont, 'Inter', 'SF Pro Display', 'Segoe UI', Roboto, sans-serif;
}

/* 全局样式 */
.stApp {
    background: var(--bg-primary) !important;
    font-family: var(--font-family) !important;
    color: var(--text-primary) !important;
}

/* 隐藏Streamlit默认元素 */
#MainMenu {visibility: hidden;}
footer {visibility: hidden;}
header {visibility: hidden;}

/* Hero区域 */
.hero-section {
    text-align: center;
    padding: 60px 20px 40px;
    background: linear-gradient(180deg, #fbfbfd 0%, var(--bg-primary) 100%);
}

.hero-title {
    font-size: 56px;
    font-weight: 700;
    letter-spacing: -0.02em;
    color: var(--text-primary);
    margin-bottom: 12px;
    line-height: 1.1;
}

.hero-subtitle {
    font-size: 21px;
    font-weight: 400;
    color: var(--text-secondary);
    margin-bottom: 32px;
    line-height: 1.4;
}

/* 卡片样式 */
.apple-card {
    background: var(--bg-card);
    backdrop-filter: blur(20px);
    -webkit-backdrop-filter: blur(20px);
    border-radius: var(--radius-card);
    border: 1px solid var(--border-color);
    box-shadow: var(--shadow-card);
    padding: 24px;
    transition: all 0.3s ease;
}

.apple-card:hover {
    box-shadow: var(--shadow-hover);
    transform: translateY(-2px);
}

/* 指标卡片 */
.metric-card {
    background: var(--bg-card);
    backdrop-filter: blur(20px);
    -webkit-backdrop-filter: blur(20px);
    border-radius: var(--radius-card);
    border: 1px solid var(--border-color);
    box-shadow: var(--shadow-card);
    padding: 20px;
    text-align: center;
}

.metric-value {
    font-size: 28px;
    font-weight: 600;
    color: var(--text-primary);
    margin: 8px 0 4px;
}

.metric-label {
    font-size: 13px;
    font-weight: 500;
    color: var(--text-secondary);
    text-transform: uppercase;
    letter-spacing: 0.02em;
}

/* 涨跌徽章 */
.badge-up {
    display: inline-block;
    background: rgba(52, 199, 89, 0.12);
    color: var(--accent-green);
    padding: 4px 12px;
    border-radius: var(--radius-pill);
    font-size: 14px;
    font-weight: 600;
}

.badge-down {
    display: inline-block;
    background: rgba(255, 59, 48, 0.12);
    color: var(--accent-red);
    padding: 4px 12px;
    border-radius: var(--radius-pill);
    font-size: 14px;
    font-weight: 600;
}

.badge-neutral {
    display: inline-block;
    background: rgba(134, 134, 139, 0.12);
    color: var(--text-secondary);
    padding: 4px 12px;
    border-radius: var(--radius-pill);
    font-size: 14px;
    font-weight: 600;
}

/* 开源徽章 */
.badge-opensource {
    display: inline-block;
    background: rgba(52, 199, 89, 0.15);
    color: var(--accent-green);
    padding: 6px 16px;
    border-radius: var(--radius-pill);
    font-size: 14px;
    font-weight: 600;
    margin-left: 12px;
}

/* 市场标签 */
.market-tags {
    display: flex;
    justify-content: center;
    gap: 16px;
    margin-top: 16px;
    font-size: 15px;
    color: var(--text-secondary);
}

/* Section标题 */
.section-title {
    font-size: 32px;
    font-weight: 700;
    color: var(--text-primary);
    margin: 40px 0 20px;
    letter-spacing: -0.01em;
}

.section-subtitle {
    font-size: 17px;
    color: var(--text-secondary);
    margin-bottom: 24px;
}

/* 按钮样式 */
.stButton > button {
    border-radius: var(--radius-button) !important;
    font-weight: 500 !important;
    transition: all 0.2s ease !important;
}

.stButton > button:hover {
    transform: scale(1.02);
}

/* 输入框 */
.stTextInput > div > div > input {
    border-radius: var(--radius-button) !important;
    border: 2px solid var(--border-color) !important;
    font-size: 18px !important;
    padding: 12px 16px !important;
}

.stTextInput > div > div > input:focus {
    border-color: var(--accent-blue) !important;
    box-shadow: 0 0 0 3px rgba(0, 113, 227, 0.15) !important;
}

/* Tab样式 */
.stTabs [data-baseweb="tab-list"] {
    gap: 8px;
    background: var(--bg-card);
    border-radius: var(--radius-button);
    padding: 4px;
}

.stTabs [data-baseweb="tab"] {
    border-radius: 8px;
    padding: 8px 20px;
    font-weight: 500;
    color: var(--text-secondary);
}

.stTabs [aria-selected="true"] {
    background: var(--accent-blue) !important;
    color: white !important;
}

/* 进度条 */
.stProgress > div > div > div {
    border-radius: 8px;
}

/* 信号强度条 */
.signal-bar {
    height: 6px;
    border-radius: 3px;
    background: #e5e5ea;
    overflow: hidden;
}

.signal-bar-fill {
    height: 100%;
    border-radius: 3px;
    transition: width 0.5s ease;
}

/* 免责声明 */
.disclaimer {
    background: rgba(255, 149, 0, 0.08);
    border-radius: var(--radius-button);
    padding: 12px 16px;
    font-size: 13px;
    color: var(--accent-orange);
    margin-top: 16px;
}

/* 侧边栏 */
section[data-testid="stSidebar"] {
    background: rgba(255, 255, 255, 0.9) !important;
    backdrop-filter: blur(20px) !important;
    -webkit-backdrop-filter: blur(20px) !important;
}

/* Sparkline容器 */
.sparkline-container {
    height: 30px;
    display: flex;
    align-items: flex-end;
    gap: 1px;
}

.sparkline-bar {
    width: 3px;
    border-radius: 1px;
    transition: height 0.2s ease;
}

/* 暗色模式 */
.dark-mode {
    --bg-primary: #000000;
    --bg-card: rgba(28, 28, 30, 0.9);
    --bg-card-solid: #1c1c1e;
    --text-primary: #f5f5f7;
    --text-secondary: #98989d;
    --border-color: rgba(255, 255, 255, 0.08);
    --shadow-card: 0 2px 12px rgba(0, 0, 0, 0.3);
    --shadow-hover: 0 4px 20px rgba(0, 0, 0, 0.4);
}

/* 响应式 */
@media (max-width: 768px) {
    .hero-title { font-size: 36px; }
    .hero-subtitle { font-size: 17px; }
    .section-title { font-size: 24px; }
    .metric-value { font-size: 22px; }
}
</style>
"""

DARK_CSS = """
<style>
:root {
    --bg-primary: #000000;
    --bg-card: rgba(28, 28, 30, 0.9);
    --bg-card-solid: #1c1c1e;
    --text-primary: #f5f5f7;
    --text-secondary: #98989d;
    --accent-blue: #0a84ff;
    --accent-green: #30d158;
    --accent-red: #ff453a;
    --accent-orange: #ff9f0a;
    --border-color: rgba(255, 255, 255, 0.08);
    --shadow-card: 0 2px 12px rgba(0, 0, 0, 0.3);
    --shadow-hover: 0 4px 20px rgba(0, 0, 0, 0.4);
}

.stApp {
    background: #000000 !important;
    color: #f5f5f7 !important;
}

section[data-testid="stSidebar"] {
    background: rgba(28, 28, 30, 0.95) !important;
}

.stTabs [data-baseweb="tab"] {
    color: #98989d !important;
}

.stTabs [aria-selected="true"] {
    background: #0a84ff !important;
    color: white !important;
}

.stTextInput > div > div > input {
    background: #1c1c1e !important;
    color: #f5f5f7 !important;
    border-color: rgba(255, 255, 255, 0.1) !important;
}
</style>
"""
