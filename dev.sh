#!/bin/bash
# QuantCore 开发模式启动脚本
# 前端: http://localhost:8080 (Vite HMR)
# 后端: http://localhost:8081 (FastAPI)

set -e

PROJECT_DIR="$(cd "$(dirname "$0")" && pwd)"

echo "🚀 启动 QuantCore 开发环境..."
echo "   前端: http://localhost:8080"
echo "   后端: http://localhost:8081"
echo ""

# 启动后端 (8081)
echo "⏳ 启动后端服务..."
(cd "$PROJECT_DIR" && python main.py --dev) &
BACKEND_PID=$!

# 等待后端启动
sleep 3

# 启动前端 (8080)
echo "⏳ 启动前端开发服务器..."
(cd "$PROJECT_DIR/frontend" && npm run dev) &
FRONTEND_PID=$!

echo ""
echo "✅ 开发环境已启动"
echo "   访问 http://localhost:8080"
echo ""
echo "按 Ctrl+C 停止所有服务"

cleanup() {
    echo ""
    echo "🛑 停止服务..."
    kill $BACKEND_PID 2>/dev/null
    kill $FRONTEND_PID 2>/dev/null
    wait 2>/dev/null
    echo "✅ 已停止"
}

trap cleanup EXIT INT TERM

wait
