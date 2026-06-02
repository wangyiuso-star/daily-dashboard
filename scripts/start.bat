@echo off
REM 每日任务仪表盘 — 启动脚本
REM 激活虚拟环境并启动 FastAPI 服务，然后打开浏览器

cd /d "%~dp0.."

REM 检查虚拟环境是否存在，不存在则创建
if not exist "venv\Scripts\activate.bat" (
    echo [INFO] 正在创建虚拟环境...
    python -m venv venv
    echo [INFO] 正在安装依赖...
    call venv\Scripts\activate.bat
    pip install -r requirements.txt
) else (
    call venv\Scripts\activate.bat
)

echo [INFO] 启动每日任务仪表盘...
echo [INFO] 访问 http://localhost:8000

REM 启动服务（后台运行，不占用终端）
start "" http://localhost:8000
uvicorn main:app --host 127.0.0.1 --port 8000 --reload
