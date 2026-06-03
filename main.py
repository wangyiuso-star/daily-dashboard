"""
每日任务仪表盘 — 应用入口

启动 FastAPI 服务，提供今日任务管理界面。
访问 http://localhost:8000 即可使用。
"""

import uvicorn
from dotenv import load_dotenv
from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

# 在导入其他模块之前加载 .env 文件，
# 确保 telegram_bot.py 和 nlp_parser.py 中 os.environ.get() 能读取到值。
# 云部署时 .env 文件不存在（敏感信息通过 systemd EnvironmentFile 注入），
# 此时 load_dotenv() 静默返回 False，不影响服务运行。
load_dotenv(override=False)

from app.database import init_db, list_today_tasks, get_daily_stats, get_all_task_dates
from app.routers.api import router as api_router
from app.telegram_bot import start_bot, stop_bot

app = FastAPI(title="每日任务仪表盘", version="0.1.0")

# 挂载静态文件
app.mount("/static", StaticFiles(directory="static"), name="static")

# Jinja2 模板
templates = Jinja2Templates(directory="templates")

# 注册 API 路由
app.include_router(api_router)


@app.on_event("startup")
async def startup():
    """应用启动时初始化数据库并启动 Telegram Bot。"""
    await init_db()
    await start_bot()


@app.on_event("shutdown")
async def shutdown():
    """应用关闭时停止 Telegram Bot。"""
    await stop_bot()


@app.get("/")
async def index(request: Request):
    """今日仪表盘主页。"""
    tasks = await list_today_tasks()
    stats = await get_daily_stats()
    task_dates = await get_all_task_dates()
    return templates.TemplateResponse(
        "index.html",
        {
            "request": request,
            "tasks": tasks,
            "stats": stats,
            "task_dates": task_dates,
        },
    )


if __name__ == "__main__":
    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=False)
