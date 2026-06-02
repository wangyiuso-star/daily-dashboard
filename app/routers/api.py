"""
JSON API 路由模块（前缀 /api，与 HTML/HTMX 路由分离）
"""
from typing import Optional
from fastapi import APIRouter, Form, HTTPException, Query
from fastapi.responses import JSONResponse
from app.database import (
    complete_task, create_task, delete_task,
    get_task_by_id, list_all_tasks, update_task,
)
from app.models import TaskCreate, TaskResponse, TaskUpdate
from app.nlp_parser import parse_task

router = APIRouter(prefix="/api")


@router.post("/tasks", response_model=TaskResponse, status_code=201)
async def api_create_task(task_data: TaskCreate):
    """创建新任务 → 201 Created"""
    return await create_task(task_data)


@router.get("/tasks", response_model=list[TaskResponse])
async def api_list_tasks(status: Optional[str] = Query(default=None)):
    """获取任务列表，?status=pending|completed"""
    tasks = await list_all_tasks()
    if status:
        if status not in ("pending", "completed"):
            raise HTTPException(status_code=400, detail="status 只能是 'pending' 或 'completed'")
        tasks = [t for t in tasks if t.status == status]
    return tasks


@router.get("/tasks/{task_id}", response_model=TaskResponse)
async def api_get_task(task_id: int):
    """获取单个任务 → 200 / 404"""
    task = await get_task_by_id(task_id)
    if task is None:
        raise HTTPException(status_code=404, detail=f"任务 #{task_id} 不存在")
    return task


@router.patch("/tasks/{task_id}", response_model=TaskResponse)
async def api_patch_task(task_id: int, task_data: TaskUpdate):
    """部分更新任务 → 200 / 404"""
    task = await update_task(task_id, task_data)
    if task is None:
        raise HTTPException(status_code=404, detail=f"任务 #{task_id} 不存在")
    return task


@router.delete("/tasks/{task_id}")
async def api_delete_task(task_id: int):
    """删除任务 → 204 / 404"""
    deleted = await delete_task(task_id)
    if not deleted:
        raise HTTPException(status_code=404, detail=f"任务 #{task_id} 不存在")
    return JSONResponse(status_code=204, content=None)


@router.patch("/tasks/{task_id}/complete", response_model=TaskResponse)
async def api_complete_task(task_id: int):
    """快捷标记完成 → 200 / 404"""
    task = await complete_task(task_id)
    if task is None:
        raise HTTPException(status_code=404, detail=f"任务 #{task_id} 不存在")
    return task


@router.post("/tasks/parse", response_model=TaskResponse, status_code=201)
async def api_parse_and_create(data: dict):
    """自然语言解析并创建任务 → 201 Created

    接收 {"text": "..."} ，调用 NLP 解析器提取任务信息后创建。
    """
    text = data.get("text", "")
    if not text or not text.strip():
        raise HTTPException(status_code=400, detail="text 字段不能为空")
    task_data = await parse_task(text.strip())
    return await create_task(task_data)


@router.post("/tasks/form", response_model=TaskResponse, status_code=201)
async def api_create_task_form(
    title: str = Form(..., min_length=1, max_length=200),
    priority: int = Form(default=2, ge=1, le=3),
    estimated_minutes: Optional[int] = Form(default=None, ge=1),
    deadline: Optional[str] = Form(default=None),
):
    """兼容 HTML 表单（form-urlencoded）创建任务 → 201 Created"""
    from datetime import date as date_type, datetime as dt_type

    task_data = TaskCreate(
        title=title,
        priority=priority,
        estimated_minutes=estimated_minutes,
        deadline=date_type.fromisoformat(deadline) if deadline else None,
    )
    return await create_task(task_data)
