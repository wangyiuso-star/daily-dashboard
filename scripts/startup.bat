@echo off
chcp 65001 >nul
title 每日任务仪表盘

cd /d "%~dp0.."

echo ============================
echo   每日任务仪表盘 启动中...
echo ============================

:: 激活虚拟环境并启动 FastAPI
call .\venv\Scripts\activate.bat
start "" http://127.0.0.1:8000
python -m uvicorn main:app --host 127.0.0.1 --port 8000

pause