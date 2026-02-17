# Scholar Agent 部署指南

## 前置要求

- 阿里云服务器（或其他云服务器）
- 已安装 Python 3.8+
- 已安装 Node.js 18+
- 已安装 Nginx（可选，推荐）

## 快速部署

### 1. 上传项目到服务器

将整个项目上传到服务器，例如 `/home/ubuntu/Agent`

### 2. 配置环境变量

```bash
cd backend
cp .env.example .env
# 编辑 .env 文件，填入你的 API Key
nano .env
```

### 3. 执行部署脚本

```bash
cd deploy
chmod +x deploy.sh
./deploy.sh
```

### 4. 配置 Nginx（推荐）

```bash
# 复制配置文件
sudo cp deploy/nginx.conf /etc/nginx/sites-available/scholar-agent
sudo ln -s /etc/nginx/sites-available/scholar-agent /etc/nginx/sites-enabled/

# 测试配置
sudo nginx -t

# 重启 Nginx
sudo systemctl restart nginx
```

**注意**：需要修改 `nginx.conf` 中的路径为你的实际项目路径。

## 手动部署步骤

### 后端部署

```bash
cd backend
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# 创建数据目录
mkdir -p data/uploads

# 使用 PM2 启动
pm2 start server.py --name scholar-backend --interpreter python3
```

### 前端部署

```bash
cd frontend
npm install
npm run build

# 使用 PM2 启动
pm2 start npm --name scholar-frontend -- start
```

### PM2 常用命令

```bash
# 查看状态
pm2 status

# 查看日志
pm2 logs scholar-backend
pm2 logs scholar-frontend

# 重启服务
pm2 restart scholar-backend
pm2 restart scholar-frontend

# 停止服务
pm2 stop scholar-backend
pm2 stop scholar-frontend

# 开机自启
pm2 startup
pm2 save
```

## 阿里云安全组配置

需要在阿里云控制台开放以下端口：

- **80** - HTTP（Nginx）
- **443** - HTTPS（可选）
- **3000** - 前端（如不使用 Nginx）
- **8088** - 后端 API（如不使用 Nginx）

## 目录结构

```
deploy/
├── nginx.conf          # Nginx 配置文件
├── ecosystem.config.js # PM2 配置文件
├── deploy.sh           # 一键部署脚本
└── README.md           # 部署文档
```
