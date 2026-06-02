"""
自然语言任务解析器

调用 DeepSeek API 将用户自然语言消息解析为 TaskCreate 对象。
解析失败时返回默认 TaskCreate（标题=原消息，优先级=medium）。
"""

import json
import os
from datetime import date
from typing import Optional

import httpx

from app.models import TaskCreate

# DeepSeek API 配置
DEEPSEEK_API_URL = "https://api.deepseek.com/v1/chat/completions"
DEEPSEEK_API_KEY = os.environ.get("DEEPSEEK_API_KEY", "")

SYSTEM_PROMPT = """你是一个任务解析助手。从用户的消息中提取任务信息并返回 JSON。
如果消息中没有明确时间，默认使用今天。
如果内容是参加活动或会议，优先级设为高。
JSON 格式：{"title": "...", "priority": "high|medium|low", "deadline": "YYYY-MM-DD", "notes": "..."}"""

# 优先级映射：字符串 -> TaskCreate 的 int 优先级
PRIORITY_MAP = {
    "high": 1,
    "medium": 2,
    "low": 3,
}


async def parse_task(text: str) -> TaskCreate:
    """调用 DeepSeek API 解析用户自然语言消息为 TaskCreate。

    Args:
        text: 用户输入的自然语言消息。

    Returns:
        TaskCreate 对象。解析失败时返回默认值（title=text, priority=2）。
    """
    if not DEEPSEEK_API_KEY:
        return _default_task(text)

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
                        {"role": "system", "content": SYSTEM_PROMPT},
                        {"role": "user", "content": f"用户消息：{text}"},
                    ],
                    "temperature": 0.1,
                    "max_tokens": 500,
                },
            )
            response.raise_for_status()
            data = response.json()

        # 提取助手回复中的 JSON
        content = data["choices"][0]["message"]["content"]
        parsed = _extract_json(content)

        return _build_task_create(text, parsed)

    except (httpx.HTTPError, json.JSONDecodeError, KeyError, IndexError, ValueError) as e:
        # 任何解析异常都返回默认值，确保接口不崩溃
        return _default_task(text)


def _extract_json(content: str) -> dict:
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