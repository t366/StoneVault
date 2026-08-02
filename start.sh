#!/bin/bash
set -e

cd "$(dirname "$0")"

# 启动后端服务（Sanic）
cd backend
python3 -m app.server &
BACKEND_PID=$!

# 启动前端开发服务器（Vite，暴露端口）
cd ../frontend
npm run dev &
FRONTEND_PID=$!

# 退出时清理
trap "kill $BACKEND_PID $FRONTEND_PID" EXIT

wait
