"""
Telegram Bot 集成模块

通过 Telegram Bot 实现自然语言任务管理：
- /ping → 快速验证 Bot 是否在线
- /today → 查看今日任务清单
- /done <id> → 标记任务完成
- /help → 显示帮助信息

Bot Token 从环境变量 TELEGRAM_BOT_TOKEN 读取。
"""

import logging
import os
import traceback
from typing import Optional

from telegram import Update
from telegram.ext import (
    Application,
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    filters,
    ContextTypes,
)
from telegram.request import HTTPXRequest

from app.database import complete_task, create_task, get_task_by_id, list_today_tasks
from app.nlp_parser import parse_task

# 配置 logging 输出到 stdout
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
    stream=__import__("sys").stdout,
)
logger = logging.getLogger(__name__)

PRIORITY_LABEL = {1: "高", 2: "中", 3: "低"}


def _mask_token(token: str) -> str:
    """脱敏显示 Token：前 10 位 + *** + 后 5 位。"""
    if len(token) <= 15:
        return token[:8] + "***" + token[-4:]
    return token[:10] + "***" + token[-5:]


async def _verify_token(token: str) -> dict | None:
    """通过 getMe 验证 Token 有效性。

    Returns:
        Bot 信息字典，失败返回 None。
    """
    request = HTTPXRequest(
        connect_timeout=10,
        read_timeout=10,
        httpx_kwargs={"trust_env": False},
    )
    try:
        from telegram import Bot
        bot = Bot(token=token, request=request)
        me = await bot.get_me()
        info = {
            "username": me.username,
            "name": me.first_name,
            "id": me.id,
        }
        print(f"[Telegram Bot] ✅ getMe 成功：@{info['username']} ({info['name']})", flush=True)
        return info
    except Exception as e:
        print(f"[Telegram Bot] ❌ getMe 失败：{e}", flush=True)
        return None


def _build_app(token: str) -> Application:
    """构建 Telegram Bot Application 实例。"""
    # trust_env=False 绕过系统代理环境变量
    request = HTTPXRequest(
        connect_timeout=15,
        read_timeout=30,
        httpx_kwargs={"trust_env": False},
    )
    app = (
        ApplicationBuilder()
        .token(token)
        .request(request)
        .build()
    )

    # 注册命令处理器
    app.add_handler(CommandHandler("start", _cmd_start))
    print("[Telegram Bot] ✅ 已注册 handler: /start", flush=True)
    app.add_handler(CommandHandler("help", _cmd_help))
    print("[Telegram Bot] ✅ 已注册 handler: /help", flush=True)
    app.add_handler(CommandHandler("ping", _cmd_ping))
    print("[Telegram Bot] ✅ 已注册 handler: /ping", flush=True)
    app.add_handler(CommandHandler("today", _cmd_today))
    print("[Telegram Bot] ✅ 已注册 handler: /today", flush=True)
    app.add_handler(CommandHandler("done", _cmd_done))
    print("[Telegram Bot] ✅ 已注册 handler: /done", flush=True)

    # 普通消息
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, _handle_message))
    print("[Telegram Bot] ✅ 已注册 handler: 普通消息", flush=True)

    # 全局错误处理
    app.add_error_handler(_error_handler)
    print("[Telegram Bot] ✅ 已注册 handler: 全局错误", flush=True)

    return app


async def _error_handler(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    """全局错误处理器。"""
    print(f"[Telegram Bot] ❌ 发生错误！", flush=True)
    print(f"[Telegram Bot] error: {context.error}", flush=True)
    traceback.print_exception(
        type(context.error), context.error, context.error.__traceback__
    )
    if update and isinstance(update, Update) and update.effective_message:
        try:
            await update.effective_message.reply_text("❌ 处理消息时出错，请稍后重试。")
        except Exception:
            pass


# ---------- 命令处理器 ----------


async def _cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(
        "👋 你好！我是任务管理助手。\n\n"
        "直接发送消息，我会用 AI 帮你解析并创建任务。\n"
        "发送 /help 查看所有命令。"
    )


async def _cmd_help(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(
        "📋 **可用命令列表**\n\n"
        "• /ping — 检查 Bot 是否在线\n\n"
        "• 直接发送消息 — AI 解析并创建任务\n"
        "  例：`明天下午3点和导师开会`\n\n"
        "• /today — 查看今日待办任务\n\n"
        "• /done <任务ID> — 标记任务完成\n"
        "  例：`/done 3`\n\n"
        "• /help — 显示此帮助信息"
    )


async def _cmd_ping(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    print(f"[Telegram Bot] 📩 收到 /ping 来自 @{update.effective_user.username}", flush=True)
    await update.message.reply_text("pong 🏓")


async def _cmd_today(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    print(f"[Telegram Bot] 📩 收到 /today 来自 @{update.effective_user.username}", flush=True)
    try:
        tasks = await list_today_tasks()
    except Exception:
        logger.exception("获取今日任务失败")
        await update.message.reply_text("❌ 获取任务列表失败，请稍后重试。")
        return

    if not tasks:
        await update.message.reply_text("📭 今天没有待办任务。")
        return

    lines = ["📅 **今日待办任务**\n"]
    for t in tasks:
        pl = PRIORITY_LABEL.get(t.priority, "?")
        dl = f"截止：{t.deadline}" if t.deadline else "无截止日期"
        est = f"预计：{t.estimated_minutes}分钟" if t.estimated_minutes else ""
        detail = " | ".join(filter(None, [f"[{pl}]", dl, est]))
        lines.append(f"• #{t.id} {t.title}")
        if detail:
            lines.append(f"  _{detail}_")

    await update.message.reply_text("\n".join(lines))


async def _cmd_done(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    print(f"[Telegram Bot] 📩 收到 /done 来自 @{update.effective_user.username}", flush=True)
    if not context.args:
        await update.message.reply_text("⚠️ 请提供任务 ID，例如：`/done 3`")
        return

    try:
        task_id = int(context.args[0])
    except ValueError:
        await update.message.reply_text("⚠️ 任务 ID 必须是数字，例如：`/done 3`")
        return

    try:
        task = await get_task_by_id(task_id)
    except Exception:
        logger.exception("查询任务失败")
        await update.message.reply_text("❌ 查询任务失败，请稍后重试。")
        return

    if task is None:
        await update.message.reply_text(f"❌ 任务 #{task_id} 不存在。")
        return
    if task.status == "completed":
        await update.message.reply_text(f"⚠️ 任务 #{task_id}【{task.title}】已经是完成状态。")
        return

    try:
        await complete_task(task_id)
    except Exception:
        logger.exception("完成任务失败")
        await update.message.reply_text(f"❌ 完成任务 #{task_id} 失败，请稍后重试。")
        return

    await update.message.reply_text(f"✅ 任务 #{task_id}【{task.title}】已标记为完成！")


# ---------- 消息处理器 ----------


async def _handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    text = update.message.text.strip()
    print(f"[Telegram Bot] 📩 收到消息来自 @{update.effective_user.username}: {text[:50]}", flush=True)

    try:
        task_data = await parse_task(text)
        task = await create_task(task_data)
    except Exception:
        logger.exception("解析或创建任务失败")
        await update.message.reply_text("❌ 无法解析，请重新描述。")
        return

    pl = PRIORITY_LABEL.get(task.priority, "?")
    dl = f"{task.deadline}" if task.deadline else "无截止日期"
    await update.message.reply_text(
        f"✅ 已添加任务：【{task.title}】，优先级：【{pl}】，截止日期：【{dl}】"
    )


# ---------- 生命周期管理 ----------


_tg_app: Optional[Application] = None


async def start_bot() -> None:
    """启动 Telegram Bot（在 FastAPI startup 事件中调用）。"""
    global _tg_app

    token = os.environ.get("TELEGRAM_BOT_TOKEN", "").strip().strip('"').strip("'")
    if not token:
        print("[Telegram Bot] ⚠️ TELEGRAM_BOT_TOKEN 未设置，跳过", flush=True)
        return

    print(f"[Telegram Bot] Token: {_mask_token(token)}", flush=True)

    # 检查代理环境变量
    for var in ("HTTPS_PROXY", "ALL_PROXY", "HTTP_PROXY"):
        val = os.environ.get(var, "")
        if val:
            print(f"[Telegram Bot] ⚠️ 检测到代理 {var}={val}, 但 Bot 将绕过代理直连 API", flush=True)

    # 验证 Token
    bot_info = await _verify_token(token)
    if bot_info is None:
        print("[Telegram Bot] ❌ Token 无效！请从 @BotFather 重新获取", flush=True)
        return

    expected = "Daily_Dashboard_bot"
    if bot_info["username"] != expected:
        print(f"[Telegram Bot] ⚠️ Token 对应的 Bot 是 @{bot_info['username']}，不是 @{expected}", flush=True)
        print(f"[Telegram Bot] ⚠️ 请更新 .env 文件中的 TELEGRAM_BOT_TOKEN", flush=True)
        return

    # 清除 webhook
    try:
        from telegram import Bot as _Bot
        wh_bot = _Bot(token, request=HTTPXRequest(
            connect_timeout=10,
            read_timeout=10,
            httpx_kwargs={"trust_env": False},
        ))
        wh_info = await wh_bot.get_webhook_info()
        if wh_info.url:
            print(f"[Telegram Bot] 检测到旧 webhook: {wh_info.url}，正在清除...", flush=True)
            await wh_bot.delete_webhook(drop_pending_updates=False)
            print("[Telegram Bot] ✅ webhook 已清除", flush=True)
        else:
            print("[Telegram Bot] ℹ️  当前无 webhook", flush=True)
    except Exception as e:
        print(f"[Telegram Bot] ⚠️ webhook 检查失败: {e}", flush=True)

    # 构建并启动
    try:
        _tg_app = _build_app(token)
        await _tg_app.initialize()
        await _tg_app.start()
        await _tg_app.updater.start_polling(drop_pending_updates=False)

        print("[Telegram Bot] ✅ 启动完毕 — polling 进行中", flush=True)
        print("[Telegram Bot]    → 在 Telegram 发送 /ping 验证", flush=True)

        # 额外提示：如果 getMe 成功但 getUpdates 一直空
        print("[Telegram Bot]    → 如果发消息后仍无反应，Token 可能需要重新生成", flush=True)
        print("[Telegram Bot]    → 去 @BotFather 用 /revoke 重发 Token，更新 .env", flush=True)

    except Exception:
        print("[Telegram Bot] ❌ 启动失败！", flush=True)
        traceback.print_exc()
        _tg_app = None


async def stop_bot() -> None:
    """停止 Telegram Bot。"""
    global _tg_app
    if _tg_app is None:
        return

    print("[Telegram Bot] 正在停止...", flush=True)
    for step in ("updater.stop", "stop", "shutdown"):
        try:
            if step == "updater.stop":
                await _tg_app.updater.stop()
            elif step == "stop":
                await _tg_app.stop()
            else:
                await _tg_app.shutdown()
        except Exception:
            logger.exception(f"停止 {step} 时出错")
    _tg_app = None
    print("[Telegram Bot] ✅ 已停止", flush=True)