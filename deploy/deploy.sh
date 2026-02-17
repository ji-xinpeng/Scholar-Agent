#!/bin/bash

echo "======================================"
echo "  Scholar Agent - 生产环境部署"
echo "======================================"

PROJECT_DIR=$(pwd)

echo ""
echo "1. 检查环境..."
command -v python3 >/dev/null 2>&1 || { echo "需要安装 Python3"; exit 1; }
command -v npm >/dev/null 2>&1 || { echo "需要安装 Node.js 和 npm"; exit 1; }
command -v pm2 >/dev/null 2>&1 || { echo "正在安装 PM2..."; npm install -g pm2; }

echo ""
echo "2. 部署后端..."
cd "$PROJECT_DIR/backend"

if [ ! -f ".env" ]; then
    echo "警告: 未找到 .env 文件，请复制 .env.example 并配置 API Key"
    cp .env.example .env
fi

if [ ! -d "venv" ]; then
    echo "创建 Python 虚拟环境..."
    python3 -m venv venv
fi

source venv/bin/activate
pip install -r requirements.txt

mkdir -p data/uploads

echo ""
echo "3. 构建前端..."
cd "$PROJECT_DIR/frontend"
npm install
npm run build

echo ""
echo "4. 启动服务..."
cd "$PROJECT_DIR"

pm2 stop scholar-backend 2>/dev/null
pm2 stop scholar-frontend 2>/dev/null

pm2 start "$PROJECT_DIR/backend/server.py" --name scholar-backend --interpreter python3
pm2 start npm --name scholar-frontend -- start --prefix "$PROJECT_DIR/frontend"

pm2 save
pm2 startup

echo ""
echo "======================================"
echo "  部署完成！"
echo ""
echo "  服务状态:"
pm2 status
echo ""
echo "  访问地址:"
echo "  前端: http://服务器IP:3000"
echo "  后端: http://服务器IP:8088"
echo ""
echo "  如需配置 Nginx 反向代理，请参考 deploy/nginx.conf"
echo "======================================"
