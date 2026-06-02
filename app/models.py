"""
数据模型模块

定义 Task 的 Pydantic 模型，用于请求/响应校验。
"""

from datetime import date, datetime
from typing import Optional

from pydantic import BaseModel, Field


class TaskCreate(BaseModel):
    """创建任务时的请求模型。"""

    title: str = Field(..., min_length=1, max_length=200, description="任务标题")
    priority: int = Field(default=2, ge=1, le=3, description="优先级：1=高, 2=中, 3=低")
    estimated_minutes: Optional[int] = Field(
        default=None, ge=1, description="预计耗时（分钟）"
    )
    deadline: Optional[date] = Field(default=None, description="截止日期")


class TaskUpdate(BaseModel):
    """更新任务时的请求模型（全部可选）。"""

    title: Optional[str] = Field(default=None, min_length=1, max_length=200)
    priority: Optional[int] = Field(default=None, ge=1, le=3)
    estimated_minutes: Optional[int] = Field(default=None, ge=1)
    deadline: Optional[date] = None


class TaskResponse(BaseModel):
    """返回给前端的任务模型。"""

    id: int
    title: str
    priority: int
    estimated_minutes: Optional[int]
    deadline: Optional[date]
    status: str  # "pending" | "completed"
    created_at: datetime
    completed_at: Optional[datetime]

    model_config = {"from_attributes": True}


class DailyStats(BaseModel):
    """今日统计信息。"""

    total: int = 0
    completed: int = 0
    pending: int = 0
    total_estimated_minutes: int = 0
