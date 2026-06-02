#!/bin/bash
# ============================================================
# daily-dashboard 云端更新脚本
# 用法：ssh ubuntu@<VM_IP> 'bash -s' < scripts/update.sh
# 或在 VM 上直接运行：bash /opt/daily-dashboard/scripts/update.sh
# ============================================================

set -euo pipefail

APP_DIR="/opt/daily-dashboard"
LOG_PREFIX="[update]"

echo "$LOG_PREFIX 开始更新 daily-dashboard ..."

cd "$APP_DIR"

# 1. 拉取最新代码
echo "$LOG_PREFIX git pull ..."
git pull origin main

# 2. 安装/更新 Python 依赖
echo "$LOG_PREFIX pip install ..."
source venv/bin/activate
pip install -r requirements.txt

# 3. 重启服务
echo "$LOG_PREFIX 重启 systemd 服务 ..."
sudo systemctl restart daily-dashboard

# 4. 等待服务启动
sleep 3

# 5. 检查服务状态
if systemctl is-active --quiet daily-dashboard; then
    echo "$LOG_PREFIX ✅ 更新成功，服务运行中"
    sudo journalctl -u daily-dashboard -n 5 --no-pager
else
    echo "$LOG_PREFIX ❌ 服务未能正常启动！"
    sudo journalctl -u daily-dashboard -n 20 --no-pager
    exit 1
fi