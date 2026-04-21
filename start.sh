#!/bin/bash
# QuantSystem Pro 启动脚本

# 项目根目录
PROJECT_DIR="$(dirname "$0")"

# 检查虚拟环境
if [ -d "$PROJECT_DIR/venv" ]; then
    echo "激活虚拟环境..."
    source "$PROJECT_DIR/venv/bin/activate"
else
    echo "未找到虚拟环境，使用系统Python..."
fi

# 检查依赖
if ! python -c "import streamlit" 2>/dev/null; then
    echo "安装依赖..."
    pip install -r "$PROJECT_DIR/requirements.txt"
fi

# 启动Streamlit
echo "🚀 启动 QuantSystem Pro..."
echo "📍 浏览器访问: http://localhost:8501"
echo "⏹  按 Ctrl+C 停止服务"
echo "-" * 50

streamlit run "$PROJECT_DIR/app.py" --server.runOnSave true --browser.gatherUsageStats false
