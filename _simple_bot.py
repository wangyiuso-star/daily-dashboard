"""
最小可复现脚本 — 纯 python-telegram-bot echo bot

不依赖 FastAPI、不依赖项目任何模块。
仅用于验证 Token + 网络是否能正常收发消息。

用法：
    cd daily-dashboard && python _simple_bot.py
    在 Telegram 向 Bot 发任意消息，Bot 应回声复述。
"""

import asyncio
import os

from dotenv import load_dotenv
from telegram import Update
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    filters,
    ContextTypes,
)
from telegram.request import HTTPXRequest

load_dotenv()


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("👋 Echo Bot 已启动！发任意消息我会复述。")


async def ping(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("pong 🏓")


async def echo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    print(f"[EchoBot] 收到: {text}", flush=True)
    await update.message.reply_text(f"你说了：{text}")


async def main():
    token = os.environ.get("TELEGRAM_BOT_TOKEN", "").strip().strip('"').strip("'")
    if not token:
        print("❌ TELEGRAM_BOT_TOKEN 未设置", flush=True)
        return

    print(f"[EchoBot] Token: {token[:10]}***{token[-5:]}", flush=True)

    # 绕过系统代理
    request = HTTPXRequest(
        connect_timeout=15,
        read_timeout=30,
        httpx_kwargs={"trust_env": False},
    )

    # 验证 Token
    from telegram import Bot
    try:
        bot = Bot(token=token, request=None)
        me = await bot.get_me()
        print(f"[EchoBot] ✅ Bot 身份：@{me.username} ({me.first_name})", flush=True)
    except Exception as e:
        print(f"[EchoBot] ❌ Token 无效：{e}", flush=True)
        return

    # 清除 webhook（保留 pending updates）
    try:
        wh = await bot.get_webhook_info()
        if wh.url:
            print(f"[EchoBot] 清除旧 webhook: {wh.url}", flush=True)
            await bot.delete_webhook(drop_pending_updates=False)
        print("[EchoBot] ✅ webhook 已清除", flush=True)
    except Exception as e:
        print(f"[EchoBot] ⚠️ webhook 清除失败: {e}", flush=True)

    # 构建 application
    app = (
        ApplicationBuilder()
        .token(token)
        .request(request)
        .build()
    )
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("ping", ping))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, echo))

    # 启动
    await app.initialize()
    await app.start()
    await app.updater.start_polling(drop_pending_updates=False)

    print("[EchoBot] ✅ 启动成功！在 Telegram 发消息测试...", flush=True)
    print("[EchoBot] 按 Ctrl+C 退出", flush=True)

    try:
        while True:
            await asyncio.sleep(1)
    except KeyboardInterrupt:
        pass

    print("[EchoBot] 正在退出...", flush=True)
    await app.updater.stop()
    await app.stop()
    await app.shutdown()
    print("[EchoBot] ✅ 已退出", flush=True)


if __name__ == "__main__":
    asyncio.run(main())