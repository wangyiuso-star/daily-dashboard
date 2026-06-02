# 云端部署指南

本文档详细说明如何将 daily-dashboard 部署到免费云服务器上实现 24/7 在线。

## 平台方案对比

| 平台 | 免费额度 | 持久化存储 | 香港延迟 | 推荐指数 |
|---|---|---|---|---|
| **Oracle Cloud** | 永久免费 4核24G ARM | ✅ 200GB 块存储 | ~40ms（首尔） | ⭐⭐⭐⭐⭐ |
| **Fly.io** | 每月 $5 信用额 | ❌ 临时 FS | ~2ms（香港） | ⭐⭐⭐⭐ |
| **Render** | 750h/月 | ❌ 临时 FS | ~35ms（新加坡） | ⭐⭐⭐ |

**推荐：Oracle Cloud Always Free Tier** — 真正的永久免费，文件系统持久化，无需改动数据库。

---

## 一、Oracle Cloud 部署（推荐）

### 1.1 前置准备

1. 注册 [Oracle Cloud](https://signup.cloud.oracle.com)（需信用卡验证，不扣费）
2. 在 GitHub 上创建一个私有仓库，推送项目代码
3. 准备好你的 `TELEGRAM_BOT_TOKEN` 和 `DEEPSEEK_API_KEY`

### 1.2 创建 VM 实例

1. 登录 Oracle Cloud 控制台
2. 进入 **Compute → Instances → Create instance**
3. 配置：
   - **Name**: `daily-dashboard`
   - **Image**: Ubuntu 22.04
   - **Shape**: Ampere ARM — OCPU: 4, Memory: 24GB（免费限额内）
   - **SSH key**: 上传你的公钥（或让它自动生成）
   - **Boot volume**: 保持默认或调整到 200GB（免费额度内）
4. 点击 **Create**

### 1.3 网络配置

打开安全列表允许 Web 访问（可选，如果只需要 Bot 可跳过）：

1. **Networking → Virtual Cloud Networks → 你的 VCN**
2. 点击默认子网，找到 **Security Lists**
3. 添加入站规则：
   - Source: `0.0.0.0/0`
   - IP Protocol: TCP
   - Destination Port: `8000`
   - Description: `Allow FastAPI`

### 1.4 SSH 连接 + 初始化

```bash
# 连接到 VM（使用实例的公网 IP）
ssh -i ~/.ssh/oracle_key ubuntu@<你的公网IP>

# 更新系统
sudo apt update && sudo apt upgrade -y

# 安装 Python 3.12
sudo apt install -y python3.12 python3.12-venv python3-pip git nginx

# 创建应用目录
sudo mkdir -p /opt/daily-dashboard
sudo chown ubuntu:ubuntu /opt/daily-dashboard
```

### 1.5 克隆代码 + 安装依赖

```bash
cd /opt/daily-dashboard
git clone <你的GitHub仓库地址> .

# 创建虚拟环境
python3.12 -m venv venv
source venv/bin/activate

# 安装依赖
pip install -r requirements.txt
```

### 1.6 配置环境变量（安全方式）

敏感信息通过 systemd 的 `EnvironmentFile` 注入，不存放在项目目录内：

```bash
sudo mkdir -p /etc/daily-dashboard
sudo tee /etc/daily-dashboard/environment << 'EOF'
TELEGRAM_BOT_TOKEN=1234567890:ABCdefGHIJklmnOPQRSTuvwXYZ
DEEPSEEK_API_KEY=sk-your-deepseek-api-key
EOF
sudo chmod 600 /etc/daily-dashboard/environment
```

### 1.7 创建 systemd 服务

```bash
sudo tee /etc/systemd/system/daily-dashboard.service << 'EOF'
[Unit]
Description=Daily Dashboard - FastAPI + Telegram Bot
After=network.target

[Service]
Type=simple
User=ubuntu
WorkingDirectory=/opt/daily-dashboard
EnvironmentFile=/etc/daily-dashboard/environment
ExecStart=/opt/daily-dashboard/venv/bin/python main.py
Restart=always
RestartSec=5
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
EOF

sudo systemctl daemon-reload
sudo systemctl enable daily-dashboard
sudo systemctl start daily-dashboard
```

### 1.8 Nginx 反向代理（可选，只用于 Web 仪表盘）

```bash
sudo tee /etc/nginx/sites-available/daily-dashboard << 'EOF'
server {
    listen 80;
    server_name <你的公网IP或域名>;

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    }
}
EOF

sudo ln -s /etc/nginx/sites-available/daily-dashboard /etc/nginx/sites-enabled/
sudo rm -f /etc/nginx/sites-enabled/default
sudo nginx -t
sudo systemctl restart nginx
```

### 1.9 数据库持久化

Oracle Cloud 的块存储是永久持久化的，重启不会丢失 `data/tasks.db`。

**建议设置定时备份**：

```bash
# 添加 cron 任务，每天凌晨 3 点备份数据库
crontab -e

# 添加以下行：
0 3 * * * cp /opt/daily-dashboard/data/tasks.db /opt/daily-dashboard/data/backups/tasks_$(date +\%Y\%m\%d).db

# 同时可推送到 GitHub（如果仓库设为私有）
0 4 * * * cd /opt/daily-dashboard && git add data/backups/ && git commit -m "daily db backup $(date +\%Y\%m\%d)" && git push origin main
```

### 1.10 查看日志

```bash
# 实时日志
sudo journalctl -u daily-dashboard -f

# 最近 100 行
sudo journalctl -u daily-dashboard -n 100

# 只看错误
sudo journalctl -u daily-dashboard -p 3 -xb
```

### 1.11 更新代码（Git Pull + 自动重启）

```bash
# 方法 1：手动 SSH + 更新脚本
cd /opt/daily-dashboard && git pull origin main && \
  source venv/bin/activate && pip install -r requirements.txt && \
  sudo systemctl restart daily-dashboard

# 方法 2：使用 GitHub Actions 自动部署（推荐）
# 参见下面的 "自动部署" 章节
```

---

## 二、Fly.io 部署（备选方案）

如果你不想用信用卡注册 Oracle Cloud，Fly.io 是第二选择。

⚠️ **Fly.io 文件系统不持久**，SQLite 数据在每次部署/重启时会丢失。必须改用外部 SQLite 服务：

- [Turso](https://turso.tech) — 免费 9GB，serverless SQLite
- 需将 `app/database.py` 从 `aiosqlite` 改为 `libsql` 客户端

### 2.1 部署步骤概要

```bash
# 1. 安装 flyctl
curl -L https://fly.io/install.sh | sh

# 2. 登录
flyctl auth signup

# 3. 启动应用
flyctl launch

# 4. 设置环境变量
flyctl secrets set TELEGRAM_BOT_TOKEN=xxx DEEPSEEK_API_KEY=xxx

# 5. 部署
flyctl deploy
```

### 2.2 数据持久化（Turso 集成）

```bash
# 安装 Turso CLI
curl -sSfL https://get.tur.so/install.sh | bash

# 创建免费数据库
turso db create daily-dashboard

# 获取连接信息
turso db show daily-dashboard
turso db tokens create daily-dashboard
```

然后修改 `database.py` 使用 Turso 连接，详见下方代码改动部分。

---

## 三、自动部署（GitHub Actions）

在 GitHub 仓库中创建 `.github/workflows/deploy.yml`：

```yaml
name: Deploy to Oracle Cloud

on:
  push:
    branches: [main]

jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
      - name: SSH 并更新
        uses: appleboy/ssh-action@v1.0.0
        with:
          host: ${{ secrets.SSH_HOST }}
          username: ubuntu
          key: ${{ secrets.SSH_PRIVATE_KEY }}
          script: |
            cd /opt/daily-dashboard
            git pull origin main
            source venv/bin/activate
            pip install -r requirements.txt
            sudo systemctl restart daily-dashboard
```

在 GitHub 仓库 Settings → Secrets and variables → Actions 中添加：
- `SSH_HOST`：你的 VM 公网 IP
- `SSH_PRIVATE_KEY`：你的 SSH 私钥内容

这样 `git push` 到 main 分支后会自动部署。

---

## 四、本地 vs 云端 权衡建议

| 维度 | 本地运行 | Oracle Cloud |
|---|---|---|
| 在线时间 | 取决于开机时间 | 24/7 |
| 离线消息 | 关机 >24h 丢失 | 不丢失（除非服务崩溃） |
| 维护成本 | 零（无需额外操作） | 低（systemd 自动重启） |
| 成本 | 电费 | $0（免费） |
| 风险 | 断电、网络断 | 极少情况封号 |

**建议：优先上 Oracle Cloud**，一劳永逸解决离线消息和可靠性问题。

---

## 五、安全注意事项

1. **`.env` 文件永远不提交到 Git**（已在 `.gitignore` 中排除）
2. **Token 等敏感信息通过 systemd `EnvironmentFile` 注入**，文件权限设为 `600`
3. **`.env.example` 只包含示例占位符**，可以提交
4. **Git 仓库建议设为私有**
5. **定期轮换 Bot Token**（在 @BotFather 用 `/revoke`）