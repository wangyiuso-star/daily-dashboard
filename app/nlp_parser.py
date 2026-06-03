"""
自然语言任务解析器

调用 DeepSeek API 将用户自然语言消息解析为 TaskCreate 对象。
支持单任务和多任务批量解析。
解析失败时返回默认 TaskCreate（标题=原消息，优先级=medium）。
"""

import json
import os
from datetime import date, timedelta
from typing import Optional

import httpx

from app.models import TaskCreate

# DeepSeek API 配置
DEEPSEEK_API_URL = "https://api.deepseek.com/v1/chat/completions"
DEEPSEEK_API_KEY = os.environ.get("DEEPSEEK_API_KEY", "")

SYSTEM_PROMPT_TEMPLATE = """你是一个任务解析助手。今天是 {today} ({today_weekday})。

从用户消息中提取所有任务信息，返回 JSON 数组。

## 日期解析规则（非常重要！）
- "6月6号"或"6月6日" → "{year}-06-06"
- "4月4号" → "{year}-04-04"
- "明天" → "{tomorrow}"
- "后天" → "{day_after_tomorrow}"
- "下周一" → 请正确计算下周一的日期
- **用户明确指定了日期时，绝对不要用今天代替**
- 只有用户完全没有提到任何日期时，才使用今天 {today}

## 多日期规则（同一任务在多个日期）
- "4号、5号、6号" → 生成 3 条任务，deadline 分别是相应日期
- "4号到6号" → 生成 3 条任务，deadline 分别是 4号、5号、6号
- 多条任务共享相同的 title、priority，仅 deadline 不同

## 时间信息处理
- "下午四点半到六点" → 将时间附加到 title，如"行程（16:30-18:00）"
- "下午3点" → 附加为"（15:00）"

## 优先级判断
- 活动/会议/面试/约会 → high
- 作业/复习/学习/工作 → medium
- 日常杂务 → low

## 返回格式
直接返回 JSON 数组（不要包裹在 markdown 代码块中）：
[
  {{
    "title": "任务标题",
    "priority": "high|medium|low",
    "deadline": "YYYY-MM-DD",
    "estimated_minutes": 数字或null,
    "notes": "补充信息或null"
  }}
]"""

# 优先级映射：字符串 -> TaskCreate 的 int 优先级
PRIORITY_MAP = {
    "high": 1,
    "medium": 2,
    "low": 3,
}


def _build_system_prompt() -> str:
    """根据当前日期构建动态 system prompt。"""
    today = date.today()
    weekdays = ["周一", "周二", "周三", "周四", "周五", "周六", "周日"]
    return SYSTEM_PROMPT_TEMPLATE.format(
        today=today.isoformat(),
        today_weekday=weekdays[today.weekday()],
        year=today.year,
        tomorrow=(today + timedelta(days=1)).isoformat(),
        day_after_tomorrow=(today + timedelta(days=2)).isoformat(),
    )


async def parse_tasks(text: str) -> list[TaskCreate]:
    """调用 DeepSeek API 解析用户消息为多个 TaskCreate 对象。

    支持单任务和多任务批量识别——同一任务多日期会展开为多条 TaskCreate。

    Args:
        text: 用户输入的自然语言消息。

    Returns:
        TaskCreate 列表。解析失败时返回只含默认值的单元素列表。
    """
    if not DEEPSEEK_API_KEY:
        return [_default_task(text)]

    try:
        async with httpx.AsyncClient(timeout=httpx.Timeout(30.0)) as client:
            response = await client.post(
                DEEPSEEK_API_URL,
                headers={
                    "Authorization": f"Bearer {DEEPSEEK_API_KEY}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": "deepseek-chat",
                    "messages": [
                        {"role": "system", "content": _build_system_prompt()},
                        {"role": "user", "content": f"用户消息：{text}"},
                    ],
                    "temperature": 0.1,
                    "max_tokens": 1000,
                },
            )
            response.raise_for_status()
            data = response.json()

        content = data["choices"][0]["message"]["content"]
        parsed = _extract_json(content)

        # 统一成列表
        if isinstance(parsed, dict):
            parsed = [parsed]

        if not isinstance(parsed, list):
            return [_default_task(text)]

        tasks = [_build_task_create(text, item) for item in parsed]
        tasks = [t for t in tasks if t is not None]
        return tasks if tasks else [_default_task(text)]

    except (httpx.HTTPError, json.JSONDecodeError, KeyError, IndexError, ValueError) as e:
        return [_default_task(text)]


async def parse_task(text: str) -> TaskCreate:
    """解析用户消息为单个 TaskCreate（兼容旧接口）。

    内部调用 parse_tasks() 取第一个结果。

    Args:
        text: 用户输入的自然语言消息。

    Returns:
        TaskCreate 对象。解析失败时返回默认值。
    """
    tasks = await parse_tasks(text)
    return tasks[0]


def _extract_json(content: str):
    """从 LLM 回复中提取 JSON 对象。

    LLM 可能在 JSON 前后包裹了 markdown 代码块标记，
    此函数会尝试多种方式提取纯 JSON。
    """
    content = content.strip()

    # 尝试去除 ```json ... ``` 包裹
    if content.startswith("```"):
        # 找到第一个换行后的内容，去掉结尾的 ```
        lines = content.split("\n")
        # 去掉首行 ```json 或 ```
        if lines[0].startswith("```"):
            lines = lines[1:]
        # 去掉末行 ```
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        content = "\n".join(lines).strip()

    return json.loads(content)


def _build_task_create(text: str, parsed: dict) -> TaskCreate:
    """根据 LLM 解析结果构建 TaskCreate 对象。

    Args:
        text: 原始用户消息（用于默认 title）。
        parsed: LLM 返回的 JSON 解析结果。

    Returns:
        TaskCreate 对象。
    """
    title = parsed.get("title", text).strip() or text
    priority_str = parsed.get("priority", "medium")
    priority = PRIORITY_MAP.get(priority_str, 2)

    deadline: Optional[date] = None
    deadline_str = parsed.get("deadline")
    if deadline_str:
        try:
            deadline = date.fromisoformat(deadline_str)
        except (ValueError, TypeError):
            deadline = None

    notes = parsed.get("notes", "")

    # 如果有 notes，追加到 title 后面（TaskCreate 无 notes 字段）
    # 或者用 notes 增强 title
    if notes:
        title = f"{title}（{notes}）"

    return TaskCreate(
        title=title[:200],  # 确保不超长
        priority=priority,
        deadline=deadline,
    )


def _default_task(text: str) -> TaskCreate:
    """解析失败时的默认 TaskCreate。

    Args:
        text: 原始用户消息。

    Returns:
        TaskCreate（title=text, priority=medium）。
    """
    return TaskCreate(
        title=text[:200],
        priority=2,
    )