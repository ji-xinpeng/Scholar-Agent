#!/bin/bash

set -e

SERVER_IP="8.140.209.232"
GIT_REPO="https://github.com/ji-xinpeng/Scholar-Agent.git"
BRANCH="react"
PROJECT_DIR="/root/Scholar-Agent"

echo "======================================"
echo "  开始部署到阿里云ECS服务器"
echo "  服务器IP: $SERVER_IP"
echo "======================================"

ssh root@$SERVER_IP << 'ENDSSH'
set -e

echo "=== 更新系统 ==="
apt update -y && apt upgrade -y

echo "=== 安装必要的软件 ==="
apt install -y git python3 python3-pip python3-venv nginx nodejs npm

echo "=== 安装 Node.js 18 ==="
curl -fsSL https://deb.nodesource.com/setup_18.x | bash -
apt install -y nodejs

echo "=== 克隆项目 ==="
PROJECT_DIR="/root/Scholar-Agent"
if [ -d "$PROJECT_DIR" ]; then
    echo "项目已存在，更新代码..."
    cd $PROJECT_DIR
    git fetch origin
    git checkout react
    git reset --hard origin/react
else
    echo "克隆新项目..."
    git clone -b react https://github.com/ji-xinpeng/Scholar-Agent.git $PROJECT_DIR
fi

cd $PROJECT_DIR

echo "=== 配置后端环境 ==="
cd backend
python3 -m venv venv
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt

echo "=== 配置前端环境 ==="
cd ../frontend
npm install
npm run build

echo "=== 配置Nginx ==="
cp $PROJECT_DIR/nginx.conf /etc/nginx/nginx.conf
nginx -t
systemctl restart nginx
systemctl enable nginx

echo "=== 创建systemd服务 ==="
# 后端服务
cat > /etc/systemd/system/scholar-agent-backend.service << 'EOF'
[Unit]
Description=Scholar Agent Backend
After=network.target

[Service]
Type=simple
User=root
WorkingDirectory=/root/Scholar-Agent/backend
Environment="PATH=/root/Scholar-Agent/backend/venv/bin"
ExecStart=/root/Scholar-Agent/backend/venv/bin/python server.py
Restart=always

[Install]
WantedBy=multi-user.target
EOF

# 前端服务
cat > /etc/systemd/system/scholar-agent-frontend.service << 'EOF'
[Unit]
Description=Scholar Agent Frontend
After=network.target

[Service]
Type=simple
User=root
WorkingDirectory=/root/Scholar-Agent/frontend
Environment="PATH=/usr/bin"
ExecStart=/usr/bin/npm start
Restart=always

[Install]
WantedBy=multi-user.target
EOF

echo "=== 启动服务 ==="
systemctl daemon-reload
systemctl enable scholar-agent-backend
systemctl enable scholar-agent-frontend
systemctl restart scholar-agent-backend
systemctl restart scholar-agent-frontend

echo "=== 配置防火墙 ==="
ufw allow 22/tcp
ufw allow 80/tcp
ufw allow 443/tcp
echo "y" | ufw enable

echo "=== 检查服务状态 ==="
systemctl status scholar-agent-backend --no-pager || true
systemctl status scholar-agent-frontend --no-pager || true
systemctl status nginx --no-pager || true

echo ""
echo "======================================"
echo "  部署完成！"
echo "  访问地址: http://8.140.209.232"
echo "======================================"
ENDSSH

echo ""
echo "部署脚本执行完毕！"
