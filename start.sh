#!/bin/bash

echo "======================================"
echo "  Scholar Agent - 启动"
echo "======================================"

# 启动后端
echo "启动后端..."
cd backend
python server.py &
BACKEND_PID=$!
cd ..

# 等待一下
sleep 2

# 启动前端
echo "启动前端..."
cd frontend
npm run dev &
FRONTEND_PID=$!
cd ..

# 等待服务启动
echo "⏳ 等待服务启动..."
sleep 1

# 打开浏览器
echo "🌐 打开浏览器..."
open http://localhost:3000
open http://localhost:8088

echo ""
echo "======================================"
echo "  服务已启动！"
echo "  前端: http://localhost:3000"
echo "  后端: http://localhost:8088"
echo ""
echo "  按 Ctrl+C 停止所有服务"
echo "======================================"
echo ""

# 等待用户中断
trap "echo ''; echo '正在停止...'; kill $BACKEND_PID $FRONTEND_PID 2>/dev/null; echo '已停止'; exit" INT TERM

# 保持脚本运行
wait
