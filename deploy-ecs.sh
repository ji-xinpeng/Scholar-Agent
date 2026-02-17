#!/bin/bash

set -e

echo "======================================"
echo "  Scholar Agent - ECS 一键部署脚本"
echo "  域名: aiacademic.cn"
echo "======================================"

DOMAIN="aiacademic.cn"
WWW_DOMAIN="www.aiacademic.cn"

echo ""
echo "[1/10] 更新系统..."
apt update && apt upgrade -y

echo ""
echo "[2/10] 安装依赖软件..."
apt install -y python3 python3-pip python3-venv nginx certbot python3-certbot-nginx nodejs npm git curl

echo ""
echo "[3/10] 安装Node.js 20..."
curl -fsSL https://deb.nodesource.com/setup_20.x | bash -
apt install -y nodejs

echo ""
echo "[4/10] 克隆代码..."
cd /root
if [ -d "Scholar-Agent" ]; then
    echo "仓库已存在，正在更新..."
    cd Scholar-Agent
    git pull
else
    git clone https://github.com/ji-xinpeng/Scholar-Agent.git
    cd Scholar-Agent
fi

echo ""
echo "[5/10] 配置后端..."
cd backend
python3 -m venv venv
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt

echo ""
echo "[6/10] 配置前端..."
cd ../frontend
npm install
npm run build

echo ""
echo "[7/10] 创建systemd服务..."

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

cat > /etc/systemd/system/scholar-agent-frontend.service << 'EOF'
[Unit]
Description=Scholar Agent Frontend
After=network.target

[Service]
Type=simple
User=root
WorkingDirectory=/root/Scholar-Agent/frontend
ExecStart=/usr/bin/npm start
Restart=always

[Install]
WantedBy=multi-user.target
EOF

systemctl daemon-reload
systemctl enable scholar-agent-backend
systemctl enable scholar-agent-frontend
systemctl restart scholar-agent-backend
systemctl restart scholar-agent-frontend

echo ""
echo "[8/10] 配置Nginx..."

cat > /etc/nginx/sites-available/scholar-agent << 'EOF'
server {
    listen 80;
    server_name aiacademic.cn www.aiacademic.cn;

    location / {
        proxy_pass http://localhost:3000;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
    }

    location /api {
        proxy_pass http://localhost:8088;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
    }
}
EOF

ln -sf /etc/nginx/sites-available/scholar-agent /etc/nginx/sites-enabled/
rm -f /etc/nginx/sites-enabled/default
nginx -t
systemctl reload nginx

echo ""
echo "[9/10] 服务状态..."
systemctl status scholar-agent-backend --no-pager
systemctl status scholar-agent-frontend --no-pager

echo ""
echo "======================================"
echo "  部署基本完成！"
echo ""
echo "  接下来请手动执行以下步骤："
echo ""
echo "  1. 确认域名解析已生效"
echo "  2. 申请SSL证书: certbot --nginx -d aiacademic.cn -d www.aiacademic.cn"
echo ""
echo "  访问地址:"
echo "  http://aiacademic.cn"
echo "======================================"
