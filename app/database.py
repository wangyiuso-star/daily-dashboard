"""
数据库操作模块

使用 SQLite 存储任务数据，提供 CRUD 操作。
采用异步方式（aiosqlite）以配合 FastAPI 的异步特性。
"""

import sqlite3
from datetime import date, datetime
from pathlib import Path
from typing import Optional

import aiosqlite

from app.models import TaskCreate, TaskResponse, TaskUpdate

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
DB_PATH = DATA_DIR / "tasks.db"

# ---------- 建表 ----------

CREATE_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS tasks (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    title           TEXT    NOT NULL,
    priority        INTEGER NOT NULL DEFAULT 2,
    estimated_minutes INTEGER,
    deadline        TEXT,
    status          TEXT    NOT NULL DEFAULT 'pending',
    created_at      TEXT    NOT NULL,
    completed_at    TEXT
);
"""


async def init_db() -> None:
    """初始化数据库：创建目录和表结构。"""
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    async with aiosqlite.connect(str(DB_PATH)) as db:
        await db.execute(CREATE_TABLE_SQL)
        await db.commit()


# ---------- 辅助函数 ----------


def _row_to_task(row: sqlite3.Row) -> TaskResponse:
    """将 SQLite 行对象转换为 TaskResponse。"""
    return TaskResponse(
        id=row["id"],
        title=row["title"],
        priority=row["priority"],
        estimated_minutes=row["estimated_minutes"],
        deadline=(
            date.fromisoformat(row["deadline"]) if row["deadline"] else None
        ),
        status=row["status"],
        created_at=datetime.fromisoformat(row["created_at"]),
        completed_at=(
            datetime.fromisoformat(row["completed_at"])
            if row["completed_at"]
            else None
        ),
    )


# ---------- CRUD ----------


async def create_task(data: TaskCreate) -> TaskResponse:
    """创建新任务并返回。"""
    now = datetime.now().isoformat()
    async with aiosqlite.connect(str(DB_PATH)) as db:
        db.row_factory = sqlite3.Row
        cursor = await db.execute(
            """INSERT INTO tasks (title, priority, estimated_minutes, deadline, created_at)
               VALUES (?, ?, ?, ?, ?)""",
            (
                data.title,
                data.priority,
                data.estimated_minutes,
                data.deadline.isoformat() if data.deadline else None,
                now,
            ),
        )
        await db.commit()
        row = await db.execute(
            "SELECT * FROM tasks WHERE id = ?", (cursor.lastrowid,)
        )
        return _row_to_task(await row.fetchone())


async def list_today_tasks() -> list[TaskResponse]:
    """获取今日待办任务（未完成 + 截止日期在今天或之前）。"""
    today = date.today().isoformat()
    async with aiosqlite.connect(str(DB_PATH)) as db:
        db.row_factory = sqlite3.Row
        cursor = await db.execute(
            """SELECT * FROM tasks
               WHERE status = 'pending'
                 AND (deadline IS NULL OR deadline <= ?)
               ORDER BY
                 priority ASC,
                 deadline ASC,
                 estimated_minutes ASC""",
            (today,),
        )
        rows = await cursor.fetchall()
        return [_row_to_task(r) for r in rows]


async def list_all_tasks() -> list[TaskResponse]:
    """获取所有任务（用于历史页面）。"""
    async with aiosqlite.connect(str(DB_PATH)) as db:
        db.row_factory = sqlite3.Row
        cursor = await db.execute(
            "SELECT * FROM tasks ORDER BY created_at DESC"
        )
        rows = await cursor.fetchall()
        return [_row_to_task(r) for r in rows]


async def complete_task(task_id: int) -> Optional[TaskResponse]:
    """标记任务为已完成。返回更新后的任务，不存在则返回 None。"""
    now = datetime.now().isoformat()
    async with aiosqlite.connect(str(DB_PATH)) as db:
        db.row_factory = sqlite3.Row
        cursor = await db.execute(
            "UPDATE tasks SET status = 'completed', completed_at = ? WHERE id = ?",
            (now, task_id),
        )
        await db.commit()
        if cursor.rowcount == 0:
            return None
        row = await db.execute("SELECT * FROM tasks WHERE id = ?", (task_id,))
        return _row_to_task(await row.fetchone())


async def uncomplete_task(task_id: int) -> Optional[TaskResponse]:
    """将已完成任务重新标记为待办。"""
    async with aiosqlite.connect(str(DB_PATH)) as db:
        db.row_factory = sqlite3.Row
        cursor = await db.execute(
            "UPDATE tasks SET status = 'pending', completed_at = NULL WHERE id = ?",
            (task_id,),
        )
        await db.commit()
        if cursor.rowcount == 0:
            return None
        row = await db.execute("SELECT * FROM tasks WHERE id = ?", (task_id,))
        return _row_to_task(await row.fetchone())


async def delete_task(task_id: int) -> bool:
    """删除任务。返回是否成功删除。"""
    async with aiosqlite.connect(str(DB_PATH)) as db:
        cursor = await db.execute("DELETE FROM tasks WHERE id = ?", (task_id,))
        await db.commit()
        return cursor.rowcount > 0


async def get_task_by_id(task_id: int) -> Optional[TaskResponse]:
    """根据 ID 获取单个任务。"""
    async with aiosqlite.connect(str(DB_PATH)) as db:
        db.row_factory = sqlite3.Row
        cursor = await db.execute("SELECT * FROM tasks WHERE id = ?", (task_id,))
        row = await cursor.fetchone()
        return _row_to_task(row) if row else None


async def get_tasks_by_date(target_date: str) -> list[TaskResponse]:
    """获取指定日期的待办任务。

    Args:
        target_date: ISO 格式日期字符串 (YYYY-MM-DD)。

    Returns:
        该日期 deadline 的所有 pending 任务列表。
    """
    async with aiosqlite.connect(str(DB_PATH)) as db:
        db.row_factory = sqlite3.Row
        cursor = await db.execute(
            """SELECT * FROM tasks
               WHERE status = 'pending'
                 AND deadline = ?
               ORDER BY
                 priority ASC,
                 estimated_minutes ASC""",
            (target_date,),
        )
        rows = await cursor.fetchall()
        return [_row_to_task(r) for r in rows]


async def get_all_task_dates() -> list[str]:
    """获取所有有 pending 任务的日期列表。

    Returns:
        去重后的日期字符串列表 (YYYY-MM-DD)，按日期升序排列。
    """
    async with aiosqlite.connect(str(DB_PATH)) as db:
        cursor = await db.execute(
            """SELECT DISTINCT deadline FROM tasks
               WHERE status = 'pending'
                 AND deadline IS NOT NULL
               ORDER BY deadline ASC"""
        )
        rows = await cursor.fetchall()
        return [r[0] for r in rows]


async def get_daily_stats() -> dict:
    """获取今日统计信息。"""
    today = date.today().isoformat()
    async with aiosqlite.connect(str(DB_PATH)) as db:
        # 今日待办数
        cursor = await db.execute(
            """SELECT COUNT(*) FROM tasks
               WHERE status = 'pending'
                 AND (deadline IS NULL OR deadline <= ?)""",
            (today,),
        )
        pending = (await cursor.fetchone())[0]

        # 今日已完成数（今天完成的）
        cursor = await db.execute(
            """SELECT COUNT(*) FROM tasks
               WHERE status = 'completed'
                 AND date(completed_at) = ?""",
            (today,),
        )
        completed = (await cursor.fetchone())[0]

        # 今日待办总预计耗时
        cursor = await db.execute(
            """SELECT COALESCE(SUM(estimated_minutes), 0) FROM tasks
               WHERE status = 'pending'
                 AND (deadline IS NULL OR deadline <= ?)""",
            (today,),
        )
        total_est = (await cursor.fetchone())[0]

        return {
            "total": pending + completed,
            "completed": completed,
            "pending": pending,
            "total_estimated_minutes": total_est,
        }
    
async def update_task(task_id: int, data: TaskUpdate) -> Optional[TaskResponse]:
    """部分更新任务字段。

    只更新请求中显式传入的字段（exclude_unset），
    返回更新后的完整任务，不存在则返回 None。
    """
    update_dict = data.model_dump(exclude_unset=True)
    if not update_dict:
        # 未传入任何字段，直接返回原任务
        return await get_task_by_id(task_id)

    # 处理 deadline 转字符串
    if "deadline" in update_dict and update_dict["deadline"] is not None:
        update_dict["deadline"] = update_dict["deadline"].isoformat()

    set_clauses = ", ".join(f"{k} = ?" for k in update_dict)
    values = list(update_dict.values())

    async with aiosqlite.connect(str(DB_PATH)) as db:
        db.row_factory = sqlite3.Row
        cursor = await db.execute(
            f"UPDATE tasks SET {set_clauses} WHERE id = ?",
            (*values, task_id),
        )
        await db.commit()
        if cursor.rowcount == 0:
            return None
        row = await db.execute("SELECT * FROM tasks WHERE id = ?", (task_id,))
        return _row_to_task(await row.fetchone())
