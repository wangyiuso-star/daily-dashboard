"""
任务路由模块

处理所有与任务相关的 HTTP 请求。
返回 HTML 片段（用于 HTMX 局部刷新）或完整页面。
"""

from datetime import date

from fastapi import APIRouter, Form, HTTPException, Query, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates

from app.database import (
    complete_task,
    create_task,
    delete_task,
    get_daily_stats,
    get_task_by_id,
    list_all_tasks,
    list_today_tasks,
    uncomplete_task,
)
from app.models import TaskCreate

router = APIRouter()
templates = Jinja2Templates(directory="app/templates")

PRIORITY_MAP = {"1": "高", "2": "中", "3": "低"}
PRIORITY_COLOR = {"1": "red", "2": "yellow", "3": "green"}


# ---------- 页面路由 ----------


@router.get("/", response_class=HTMLResponse)
async def index_page(request: Request):
    """渲染今日仪表盘主页。"""
    tasks = await list_today_tasks()
    stats = await get_daily_stats()
    today_str = date.today().isoformat()
    weekday_map = ["周一", "周二", "周三", "周四", "周五", "周六", "周日"]
    weekday = weekday_map[date.today().weekday()]

    return templates.TemplateResponse(
        "index.html",
        {
            "request": request,
            "tasks": tasks,
            "stats": stats,
            "today": today_str,
            "weekday": weekday,
            "priority_map": PRIORITY_MAP,
            "priority_color": PRIORITY_COLOR,
        },
    )


@router.get("/history", response_class=HTMLResponse)
async def history_page(
    request: Request,
    date_filter: str = Query(default=None, alias="date"),
):
    """渲染历史记录页面，可按日期筛选。"""
    all_tasks = await list_all_tasks()

    # 按日期分组
    from collections import defaultdict

    grouped: dict[str, list] = defaultdict(list)
    for t in all_tasks:
        key = t.created_at.strftime("%Y-%m-%d")
        grouped[key].append(t)

    # 如果指定了日期筛选
    if date_filter:
        grouped = {k: v for k, v in grouped.items() if k == date_filter}

    # 按日期降序排序
    sorted_groups = sorted(grouped.items(), key=lambda x: x[0], reverse=True)

    return templates.TemplateResponse(
        "history.html",
        {
            "request": request,
            "groups": sorted_groups,
            "date_filter": date_filter or "",
            "priority_map": PRIORITY_MAP,
            "priority_color": PRIORITY_COLOR,
        },
    )


# ---------- API 路由（HTMX 交互） ----------


@router.post("/tasks", response_class=HTMLResponse)
async def add_task(
    request: Request,
    title: str = Form(...),
    priority: int = Form(default=2),
    estimated_minutes: int = Form(default=None),
    deadline: str = Form(default=None),
):
    """添加新任务（表单提交 → HTMX 局部刷新任务列表）。"""
    task_data = TaskCreate(
        title=title,
        priority=priority,
        estimated_minutes=estimated_minutes or None,
        deadline=date.fromisoformat(deadline) if deadline else None,
    )
    await create_task(task_data)

    # 重新渲染任务列表部分
    tasks = await list_today_tasks()
    stats = await get_daily_stats()
    return templates.TemplateResponse(
        "partials/_task_list.html",
        {
            "request": request,
            "tasks": tasks,
            "stats": stats,
            "priority_map": PRIORITY_MAP,
            "priority_color": PRIORITY_COLOR,
        },
    )


@router.put("/tasks/{task_id}/toggle", response_class=HTMLResponse)
async def toggle_task(request: Request, task_id: int):
    """切换任务完成/未完成状态。"""
    task = await get_task_by_id(task_id)
    if task is None:
        raise HTTPException(status_code=404, detail="任务不存在")

    if task.status == "pending":
        await complete_task(task_id)
    else:
        await uncomplete_task(task_id)

    tasks = await list_today_tasks()
    stats = await get_daily_stats()
    return templates.TemplateResponse(
        "partials/_task_list.html",
        {
            "request": request,
            "tasks": tasks,
            "stats": stats,
            "priority_map": PRIORITY_MAP,
            "priority_color": PRIORITY_COLOR,
        },
    )


@router.delete("/tasks/{task_id}", response_class=HTMLResponse)
async def remove_task(request: Request, task_id: int):
    """删除任务。"""
    deleted = await delete_task(task_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="任务不存在")

    tasks = await list_today_tasks()
    stats = await get_daily_stats()
    return templates.TemplateResponse(
        "partials/_task_list.html",
        {
            "request": request,
            "tasks": tasks,
            "stats": stats,
            "priority_map": PRIORITY_MAP,
            "priority_color": PRIORITY_COLOR,
        },
    )
