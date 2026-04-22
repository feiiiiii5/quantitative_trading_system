#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
QuantSystem Pro - Apple Design Style CSS
"""

APPLE_CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&display=swap');

:root {
    --bg-primary: #f5f5f7;
    --bg-secondary: #fbfbfd;
    --bg-card: rgba(255, 255, 255, 0.72);
    --bg-card-solid: #ffffff;
    --text-primary: #1d1d1f;
    --text-secondary: #86868b;
    --text-tertiary: #aeaeb2;
    --accent-blue: #0071e3;
    --accent-blue-hover: #0077ed;
    --accent-green: #34c759;
    --accent-red: #ff3b30;
    --accent-orange: #ff9500;
    --accent-purple: #af52de;
    --accent-teal: #5ac8fa;
    --border-color: rgba(0, 0, 0, 0.06);
    --border-color-strong: rgba(0, 0, 0, 0.12);
    --shadow-card: 0 2px 12px rgba(0, 0, 0, 0.06);
    --shadow-hover: 0 8px 30px rgba(0, 0, 0, 0.12);
    --shadow-modal: 0 20px 60px rgba(0, 0, 0, 0.15);
    --radius-card: 20px;
    --radius-button: 12px;
    --radius-pill: 20px;
    --radius-input: 12px;
    --font-family: -apple-system, BlinkMacSystemFont, 'Inter', 'SF Pro Display', 'Segoe UI', Roboto, sans-serif;
    --transition-fast: 0.15s ease;
    --transition-normal: 0.3s cubic-bezier(0.25, 0.1, 0.25, 1);
    --transition-spring: 0.5s cubic-bezier(0.34, 1.56, 0.64, 1);
}

* { box-sizing: border-box; }

.stApp {
    background: var(--bg-primary) !important;
    font-family: var(--font-family) !important;
    color: var(--text-primary) !important;
    -webkit-font-smoothing: antialiased;
    -moz-osx-font-smoothing: grayscale;
}

#MainMenu {visibility: hidden;}
footer {visibility: hidden;}
header {visibility: hidden;}

.hero-section {
    text-align: center;
    padding: 80px 20px 48px;
    background: linear-gradient(180deg, var(--bg-secondary) 0%, var(--bg-primary) 100%);
    position: relative;
    overflow: hidden;
}

.hero-section::before {
    content: '';
    position: absolute;
    top: -50%;
    left: -50%;
    width: 200%;
    height: 200%;
    background: radial-gradient(circle at 30% 50%, rgba(0, 113, 227, 0.04) 0%, transparent 50%),
                radial-gradient(circle at 70% 50%, rgba(175, 82, 222, 0.04) 0%, transparent 50%);
    pointer-events: none;
}

.hero-title {
    font-size: 56px;
    font-weight: 800;
    letter-spacing: -0.03em;
    color: var(--text-primary);
    margin-bottom: 16px;
    line-height: 1.05;
    background: linear-gradient(135deg, #1d1d1f 0%, #424245 100%);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    background-clip: text;
}

.hero-subtitle {
    font-size: 21px;
    font-weight: 400;
    color: var(--text-secondary);
    margin-bottom: 32px;
    line-height: 1.5;
}

.apple-card {
    background: var(--bg-card);
    backdrop-filter: blur(20px) saturate(180%);
    -webkit-backdrop-filter: blur(20px) saturate(180%);
    border-radius: var(--radius-card);
    border: 1px solid var(--border-color);
    box-shadow: var(--shadow-card);
    padding: 24px;
    transition: all var(--transition-normal);
}

.apple-card:hover {
    box-shadow: var(--shadow-hover);
    transform: translateY(-2px);
    border-color: var(--border-color-strong);
}

.metric-card {
    background: var(--bg-card);
    backdrop-filter: blur(20px) saturate(180%);
    -webkit-backdrop-filter: blur(20px) saturate(180%);
    border-radius: var(--radius-card);
    border: 1px solid var(--border-color);
    box-shadow: var(--shadow-card);
    padding: 20px;
    text-align: center;
    transition: all var(--transition-normal);
}

.metric-card:hover {
    box-shadow: var(--shadow-hover);
    transform: translateY(-2px);
}

.metric-value {
    font-size: 28px;
    font-weight: 700;
    color: var(--text-primary);
    margin: 8px 0 4px;
    letter-spacing: -0.02em;
    font-variant-numeric: tabular-nums;
}

.metric-label {
    font-size: 12px;
    font-weight: 600;
    color: var(--text-secondary);
    text-transform: uppercase;
    letter-spacing: 0.06em;
}

.badge-up {
    display: inline-flex;
    align-items: center;
    gap: 4px;
    background: rgba(52, 199, 89, 0.12);
    color: var(--accent-green);
    padding: 4px 14px;
    border-radius: var(--radius-pill);
    font-size: 14px;
    font-weight: 600;
    letter-spacing: -0.01em;
}

.badge-down {
    display: inline-flex;
    align-items: center;
    gap: 4px;
    background: rgba(255, 59, 48, 0.12);
    color: var(--accent-red);
    padding: 4px 14px;
    border-radius: var(--radius-pill);
    font-size: 14px;
    font-weight: 600;
    letter-spacing: -0.01em;
}

.badge-neutral {
    display: inline-flex;
    align-items: center;
    gap: 4px;
    background: rgba(134, 134, 139, 0.12);
    color: var(--text-secondary);
    padding: 4px 14px;
    border-radius: var(--radius-pill);
    font-size: 14px;
    font-weight: 600;
    letter-spacing: -0.01em;
}

.badge-opensource {
    display: inline-flex;
    align-items: center;
    background: rgba(52, 199, 89, 0.12);
    color: var(--accent-green);
    padding: 6px 18px;
    border-radius: var(--radius-pill);
    font-size: 14px;
    font-weight: 600;
    margin-left: 12px;
    letter-spacing: -0.01em;
}

.market-tags {
    display: flex;
    justify-content: center;
    gap: 20px;
    margin-top: 20px;
    font-size: 15px;
    color: var(--text-secondary);
    font-weight: 500;
}

.section-title {
    font-size: 36px;
    font-weight: 700;
    color: var(--text-primary);
    margin: 48px 0 24px;
    letter-spacing: -0.02em;
    line-height: 1.1;
}

.section-subtitle {
    font-size: 17px;
    color: var(--text-secondary);
    margin-bottom: 24px;
    line-height: 1.5;
}

.stButton > button {
    border-radius: var(--radius-button) !important;
    font-weight: 600 !important;
    font-size: 15px !important;
    transition: all var(--transition-fast) !important;
    border: none !important;
    letter-spacing: -0.01em !important;
}

.stButton > button:hover {
    transform: scale(1.02);
    box-shadow: 0 4px 16px rgba(0, 113, 227, 0.25) !important;
}

.stButton > button:active {
    transform: scale(0.98);
}

.stButton > button[kind="primary"] {
    background: var(--accent-blue) !important;
    color: white !important;
}

.stTextInput > div > div > input {
    border-radius: var(--radius-input) !important;
    border: 2px solid var(--border-color) !important;
    font-size: 17px !important;
    padding: 14px 18px !important;
    transition: all var(--transition-fast) !important;
    background: var(--bg-card-solid) !important;
    color: var(--text-primary) !important;
    font-weight: 400 !important;
}

.stTextInput > div > div > input:focus {
    border-color: var(--accent-blue) !important;
    box-shadow: 0 0 0 4px rgba(0, 113, 227, 0.12) !important;
}

.stTextInput > div > div > input::placeholder {
    color: var(--text-tertiary) !important;
}

.stTabs [data-baseweb="tab-list"] {
    gap: 6px;
    background: var(--bg-card);
    border-radius: 14px;
    padding: 5px;
    border: 1px solid var(--border-color);
}

.stTabs [data-baseweb="tab"] {
    border-radius: 10px;
    padding: 10px 22px;
    font-weight: 600;
    font-size: 14px;
    color: var(--text-secondary);
    transition: all var(--transition-fast);
    letter-spacing: -0.01em;
}

.stTabs [aria-selected="true"] {
    background: var(--accent-blue) !important;
    color: white !important;
    box-shadow: 0 2px 8px rgba(0, 113, 227, 0.3);
}

.stProgress > div > div > div {
    border-radius: 8px;
}

.signal-bar {
    height: 6px;
    border-radius: 3px;
    background: rgba(0, 0, 0, 0.06);
    overflow: hidden;
}

.signal-bar-fill {
    height: 100%;
    border-radius: 3px;
    transition: width 0.6s cubic-bezier(0.25, 0.1, 0.25, 1);
}

.disclaimer {
    background: rgba(255, 149, 0, 0.06);
    border: 1px solid rgba(255, 149, 0, 0.12);
    border-radius: 14px;
    padding: 16px 20px;
    font-size: 13px;
    color: var(--accent-orange);
    margin-top: 20px;
    line-height: 1.5;
}

section[data-testid="stSidebar"] {
    background: rgba(255, 255, 255, 0.92) !important;
    backdrop-filter: blur(30px) saturate(180%) !important;
    -webkit-backdrop-filter: blur(30px) saturate(180%) !important;
    border-right: 1px solid var(--border-color) !important;
}

section[data-testid="stSidebar"] .stMarkdown {
    font-size: 14px;
}

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

.stExpander {
    border: 1px solid var(--border-color) !important;
    border-radius: var(--radius-card) !important;
    overflow: hidden;
}

.stExpander > details > summary {
    font-weight: 600 !important;
    font-size: 15px !important;
    padding: 16px 20px !important;
}

.stSelectbox > div > div {
    border-radius: var(--radius-input) !important;
}

.stSlider > div > div > div > div {
    background: var(--accent-blue) !important;
}

.stMetric {
    background: var(--bg-card) !important;
    border-radius: var(--radius-card) !important;
    border: 1px solid var(--border-color) !important;
    padding: 16px !important;
    box-shadow: var(--shadow-card) !important;
}

.stMetric > label {
    font-size: 12px !important;
    font-weight: 600 !important;
    color: var(--text-secondary) !important;
    text-transform: uppercase !important;
    letter-spacing: 0.04em !important;
}

.stMetric > div {
    font-size: 28px !important;
    font-weight: 700 !important;
    color: var(--text-primary) !important;
    letter-spacing: -0.02em !important;
}

@keyframes fadeInUp {
    from { opacity: 0; transform: translateY(20px); }
    to { opacity: 1; transform: translateY(0); }
}

.apple-card, .metric-card, .section-title {
    animation: fadeInUp 0.5s ease-out;
}

@media (max-width: 768px) {
    .hero-title { font-size: 36px; }
    .hero-subtitle { font-size: 17px; }
    .section-title { font-size: 28px; }
    .metric-value { font-size: 22px; }
    .hero-section { padding: 48px 16px 32px; }
}

@media (max-width: 480px) {
    .hero-title { font-size: 28px; }
    .section-title { font-size: 24px; }
    .market-tags { gap: 12px; font-size: 13px; }
}
</style>
"""

DARK_CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&display=swap');

:root {
    --bg-primary: #000000;
    --bg-secondary: #1c1c1e;
    --bg-card: rgba(28, 28, 30, 0.85);
    --bg-card-solid: #1c1c1e;
    --text-primary: #f5f5f7;
    --text-secondary: #98989d;
    --text-tertiary: #636366;
    --accent-blue: #0a84ff;
    --accent-blue-hover: #409cff;
    --accent-green: #30d158;
    --accent-red: #ff453a;
    --accent-orange: #ff9f0a;
    --accent-purple: #bf5af2;
    --accent-teal: #64d2ff;
    --border-color: rgba(255, 255, 255, 0.08);
    --border-color-strong: rgba(255, 255, 255, 0.15);
    --shadow-card: 0 2px 12px rgba(0, 0, 0, 0.4);
    --shadow-hover: 0 8px 30px rgba(0, 0, 0, 0.5);
    --shadow-modal: 0 20px 60px rgba(0, 0, 0, 0.6);
    --radius-card: 20px;
    --radius-button: 12px;
    --radius-pill: 20px;
    --radius-input: 12px;
    --font-family: -apple-system, BlinkMacSystemFont, 'Inter', 'SF Pro Display', 'Segoe UI', Roboto, sans-serif;
    --transition-fast: 0.15s ease;
    --transition-normal: 0.3s cubic-bezier(0.25, 0.1, 0.25, 1);
    --transition-spring: 0.5s cubic-bezier(0.34, 1.56, 0.64, 1);
}

* { box-sizing: border-box; }

.stApp {
    background: #000000 !important;
    font-family: var(--font-family) !important;
    color: #f5f5f7 !important;
    -webkit-font-smoothing: antialiased;
}

#MainMenu {visibility: hidden;}
footer {visibility: hidden;}
header {visibility: hidden;}

.hero-section {
    text-align: center;
    padding: 80px 20px 48px;
    background: linear-gradient(180deg, #1c1c1e 0%, #000000 100%);
    position: relative;
    overflow: hidden;
}

.hero-section::before {
    content: '';
    position: absolute;
    top: -50%;
    left: -50%;
    width: 200%;
    height: 200%;
    background: radial-gradient(circle at 30% 50%, rgba(10, 132, 255, 0.06) 0%, transparent 50%),
                radial-gradient(circle at 70% 50%, rgba(191, 90, 242, 0.06) 0%, transparent 50%);
    pointer-events: none;
}

.hero-title {
    font-size: 56px;
    font-weight: 800;
    letter-spacing: -0.03em;
    margin-bottom: 16px;
    line-height: 1.05;
    background: linear-gradient(135deg, #f5f5f7 0%, #98989d 100%);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    background-clip: text;
}

.hero-subtitle {
    font-size: 21px;
    font-weight: 400;
    color: #98989d;
    margin-bottom: 32px;
    line-height: 1.5;
}

.apple-card {
    background: var(--bg-card);
    backdrop-filter: blur(20px) saturate(180%);
    -webkit-backdrop-filter: blur(20px) saturate(180%);
    border-radius: var(--radius-card);
    border: 1px solid var(--border-color);
    box-shadow: var(--shadow-card);
    padding: 24px;
    transition: all var(--transition-normal);
}

.apple-card:hover {
    box-shadow: var(--shadow-hover);
    transform: translateY(-2px);
    border-color: var(--border-color-strong);
}

.metric-card {
    background: var(--bg-card);
    backdrop-filter: blur(20px) saturate(180%);
    -webkit-backdrop-filter: blur(20px) saturate(180%);
    border-radius: var(--radius-card);
    border: 1px solid var(--border-color);
    box-shadow: var(--shadow-card);
    padding: 20px;
    text-align: center;
    transition: all var(--transition-normal);
}

.metric-card:hover {
    box-shadow: var(--shadow-hover);
    transform: translateY(-2px);
}

.metric-value {
    font-size: 28px;
    font-weight: 700;
    color: #f5f5f7;
    margin: 8px 0 4px;
    letter-spacing: -0.02em;
    font-variant-numeric: tabular-nums;
}

.metric-label {
    font-size: 12px;
    font-weight: 600;
    color: #98989d;
    text-transform: uppercase;
    letter-spacing: 0.06em;
}

.badge-up {
    display: inline-flex;
    align-items: center;
    gap: 4px;
    background: rgba(48, 209, 88, 0.15);
    color: #30d158;
    padding: 4px 14px;
    border-radius: var(--radius-pill);
    font-size: 14px;
    font-weight: 600;
}

.badge-down {
    display: inline-flex;
    align-items: center;
    gap: 4px;
    background: rgba(255, 69, 58, 0.15);
    color: #ff453a;
    padding: 4px 14px;
    border-radius: var(--radius-pill);
    font-size: 14px;
    font-weight: 600;
}

.badge-neutral {
    display: inline-flex;
    align-items: center;
    gap: 4px;
    background: rgba(152, 152, 157, 0.15);
    color: #98989d;
    padding: 4px 14px;
    border-radius: var(--radius-pill);
    font-size: 14px;
    font-weight: 600;
}

.badge-opensource {
    display: inline-flex;
    align-items: center;
    background: rgba(48, 209, 88, 0.15);
    color: #30d158;
    padding: 6px 18px;
    border-radius: var(--radius-pill);
    font-size: 14px;
    font-weight: 600;
    margin-left: 12px;
}

.market-tags {
    display: flex;
    justify-content: center;
    gap: 20px;
    margin-top: 20px;
    font-size: 15px;
    color: #98989d;
    font-weight: 500;
}

.section-title {
    font-size: 36px;
    font-weight: 700;
    color: #f5f5f7;
    margin: 48px 0 24px;
    letter-spacing: -0.02em;
}

.section-subtitle {
    font-size: 17px;
    color: #98989d;
    margin-bottom: 24px;
}

.stButton > button {
    border-radius: var(--radius-button) !important;
    font-weight: 600 !important;
    font-size: 15px !important;
    transition: all var(--transition-fast) !important;
    border: none !important;
}

.stButton > button:hover {
    transform: scale(1.02);
    box-shadow: 0 4px 16px rgba(10, 132, 255, 0.3) !important;
}

.stButton > button:active {
    transform: scale(0.98);
}

.stButton > button[kind="primary"] {
    background: #0a84ff !important;
    color: white !important;
}

.stTextInput > div > div > input {
    border-radius: var(--radius-input) !important;
    border: 2px solid rgba(255, 255, 255, 0.1) !important;
    font-size: 17px !important;
    padding: 14px 18px !important;
    background: #1c1c1e !important;
    color: #f5f5f7 !important;
}

.stTextInput > div > div > input:focus {
    border-color: #0a84ff !important;
    box-shadow: 0 0 0 4px rgba(10, 132, 255, 0.2) !important;
}

.stTextInput > div > div > input::placeholder {
    color: #636366 !important;
}

.stTabs [data-baseweb="tab-list"] {
    gap: 6px;
    background: rgba(28, 28, 30, 0.85);
    border-radius: 14px;
    padding: 5px;
    border: 1px solid rgba(255, 255, 255, 0.08);
}

.stTabs [data-baseweb="tab"] {
    border-radius: 10px;
    padding: 10px 22px;
    font-weight: 600;
    font-size: 14px;
    color: #98989d;
    transition: all var(--transition-fast);
}

.stTabs [aria-selected="true"] {
    background: #0a84ff !important;
    color: white !important;
    box-shadow: 0 2px 8px rgba(10, 132, 255, 0.4);
}

.signal-bar {
    height: 6px;
    border-radius: 3px;
    background: rgba(255, 255, 255, 0.06);
    overflow: hidden;
}

.signal-bar-fill {
    height: 100%;
    border-radius: 3px;
    transition: width 0.6s cubic-bezier(0.25, 0.1, 0.25, 1);
}

.disclaimer {
    background: rgba(255, 159, 10, 0.08);
    border: 1px solid rgba(255, 159, 10, 0.15);
    border-radius: 14px;
    padding: 16px 20px;
    font-size: 13px;
    color: #ff9f0a;
    margin-top: 20px;
    line-height: 1.5;
}

section[data-testid="stSidebar"] {
    background: rgba(28, 28, 30, 0.95) !important;
    backdrop-filter: blur(30px) saturate(180%) !important;
    -webkit-backdrop-filter: blur(30px) saturate(180%) !important;
    border-right: 1px solid rgba(255, 255, 255, 0.08) !important;
}

section[data-testid="stSidebar"] .stMarkdown {
    color: #f5f5f7 !important;
}

.stExpander {
    border: 1px solid rgba(255, 255, 255, 0.08) !important;
    border-radius: var(--radius-card) !important;
    background: rgba(28, 28, 30, 0.6) !important;
}

.stExpander > details > summary {
    color: #f5f5f7 !important;
    font-weight: 600 !important;
}

.stSelectbox > div > div {
    background: #1c1c1e !important;
    color: #f5f5f7 !important;
}

.stSelectbox svg {
    fill: #98989d !important;
}

.stSlider > div > div > div > div {
    background: #0a84ff !important;
}

.stMetric {
    background: var(--bg-card) !important;
    border-radius: var(--radius-card) !important;
    border: 1px solid var(--border-color) !important;
    padding: 16px !important;
    box-shadow: var(--shadow-card) !important;
}

.stMetric > label {
    font-size: 12px !important;
    font-weight: 600 !important;
    color: #98989d !important;
    text-transform: uppercase !important;
}

.stMetric > div {
    font-size: 28px !important;
    font-weight: 700 !important;
    color: #f5f5f7 !important;
}

.stDataFrame {
    background: #1c1c1e !important;
    border-radius: var(--radius-card) !important;
}

.js-plotly-plot .plotly .main-svg {
    background: transparent !important;
}

@keyframes fadeInUp {
    from { opacity: 0; transform: translateY(20px); }
    to { opacity: 1; transform: translateY(0); }
}

.apple-card, .metric-card, .section-title {
    animation: fadeInUp 0.5s ease-out;
}

@media (max-width: 768px) {
    .hero-title { font-size: 36px; }
    .hero-subtitle { font-size: 17px; }
    .section-title { font-size: 28px; }
    .metric-value { font-size: 22px; }
    .hero-section { padding: 48px 16px 32px; }
}

@media (max-width: 480px) {
    .hero-title { font-size: 28px; }
    .section-title { font-size: 24px; }
    .market-tags { gap: 12px; font-size: 13px; }
}
</style>
"""
