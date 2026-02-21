#!/bin/bash

set -e

SERVER_IP="8.140.209.232"
GIT_REPO="https://github.com/ji-xinpeng/Scholar-Agent.git"
BRANCH="react"
PROJECT_DIR="/root/Agent"

echo "======================================"
echo "  开始部署到阿里云ECS服务器"
echo "  服务器IP: $SERVER_IP"
echo "  Git仓库: $GIT_REPO"
echo "  分支: $BRANCH"
echo "======================================"

ssh root@$SERVER_IP << 'ENDSSH'
set -e

SERVER_IP="8.140.209.232"
GIT_REPO="https://github.com/ji-xinpeng/Scholar-Agent.git"
BRANCH="react"
PROJECT_DIR="/root/Agent"

echo "=== 检查并安装必要的软件 ==="
if ! command -v git &> /dev/null; then
    echo "安装 git..."
    apt update -y
    apt install -y git
fi

if ! command -v python3 &> /dev/null; then
    echo "安装 python3..."
    apt update -y
    apt install -y python3 python3-pip python3-venv
fi

if ! command -v node &> /dev/null; then
    echo "安装 nodejs..."
    apt update -y
    curl -fsSL https://deb.nodesource.com/setup_18.x | bash -
    apt install -y nodejs
fi

if ! command -v nginx &> /dev/null; then
    echo "安装 nginx..."
    apt update -y
    apt install -y nginx
fi

echo "=== 从Git拉取最新代码 ==="
if [ -d "$PROJECT_DIR" ]; then
    echo "项目目录已存在，更新代码..."
    cd $PROJECT_DIR
    
    if [ -d ".git" ]; then
        echo "Git仓库已存在，拉取最新代码..."
        git fetch origin
        git checkout $BRANCH
        git reset --hard origin/$BRANCH
        # 不使用 git clean -fd，避免删除 backend/data/（数据库、上传文件、日志等会保留）
    else
        echo "目录存在但不是Git仓库，重新克隆..."
        cd ..
        rm -rf $PROJECT_DIR
        git clone -b $BRANCH $GIT_REPO $PROJECT_DIR
    fi
else
    echo "克隆新项目..."
    git clone -b $BRANCH $GIT_REPO $PROJECT_DIR
fi

cd $PROJECT_DIR
echo "当前分支: $(git rev-parse --abbrev-ref HEAD)"
echo "最新提交: $(git log -1 --oneline)"

echo "=== 配置后端环境 ==="
cd backend
if [ ! -d "venv" ]; then
    python3 -m venv venv
fi
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt

echo "=== 配置前端环境 ==="
cd ../frontend
if [ ! -d "node_modules" ]; then
    npm install
fi
npm run build

echo "=== 配置Nginx ==="
cp $PROJECT_DIR/nginx.conf /etc/nginx/nginx.conf
sed -i "s/server_name aiacademic.cn www.aiacademic.cn;/server_name $SERVER_IP aiacademic.cn www.aiacademic.cn;/" /etc/nginx/nginx.conf
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
WorkingDirectory=/root/Agent/backend
Environment="PATH=/root/Agent/backend/venv/bin"
ExecStart=/root/Agent/backend/venv/bin/python server.py
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
WorkingDirectory=/root/Agent/frontend
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
echo "y" | ufw enable || true

echo "=== 检查服务状态 ==="
sleep 5
systemctl status scholar-agent-backend --no-pager || true
systemctl status scholar-agent-frontend --no-pager || true
systemctl status nginx --no-pager || true

echo ""
echo "======================================"
echo "  部署完成！"
echo "  访问地址: http://$SERVER_IP"
echo "           http://aiacademic.cn"
echo "======================================"
ENDSSH

echo ""
echo "部署脚本执行完毕！"
