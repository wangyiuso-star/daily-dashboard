# 每日任务仪表盘 (Daily Dashboard)

基于 FastAPI 的任务管理应用，支持 Web 界面和 Telegram Bot 交互。

## 快速开始

```bash
# 1. 进入项目目录
cd daily-dashboard

# 2. 安装依赖
pip install -r requirements.txt

# 3. 启动服务
python main.py
```

访问 http://localhost:8000 打开 Web 仪表盘。

## 环境变量

| 变量名 | 必需 | 说明 |
|---|---|---|
| `DEEPSEEK_API_KEY` | 否 | DeepSeek API Key，用于 AI 自然语言解析。未设置时所有消息将原样创建任务 |
| `TELEGRAM_BOT_TOKEN` | 否 | Telegram Bot Token，用于启用 Telegram Bot。未设置时 Bot 功能静默跳过 |

## API 接口

| 方法 | 路径 | 说明 |
|---|---|---|
| `POST` | `/api/tasks` | 创建任务（JSON body 包含 title/priority/deadline 等） |
| `GET` | `/api/tasks` | 获取所有任务，支持 `?status=pending\|completed` |
| `GET` | `/api/tasks/{id}` | 获取单个任务 |
| `PATCH` | `/api/tasks/{id}` | 更新任务 |
| `DELETE` | `/api/tasks/{id}` | 删除任务 |
| `PATCH` | `/api/tasks/{id}/complete` | 标记任务完成 |
| `POST` | `/api/tasks/parse` | 自然语言解析并创建任务 `{"text": "..."}` |
| `POST` | `/api/tasks/form` | HTML 表单方式创建任务 |

### 测试示例

```bash
# AI 解析创建任务（需要 DEEPSEEK_API_KEY）
curl -X POST http://localhost:8000/api/tasks/parse \
  -H "Content-Type: application/json" \
  -d '{"text": "明天下午3点和导师开会讨论毕业设计"}'

# 获取今日任务
curl http://localhost:8000/api/tasks?status=pending

# 标记任务完成
curl -X PATCH http://localhost:8000/api/tasks/1/complete
```

## Telegram Bot

### 创建 Bot

1. 在 Telegram 中搜索 [@BotFather](https://t.me/BotFather)
2. 发送 `/newbot` 并按照提示创建 Bot
3. 获取 Bot Token（格式：`123456:ABC-DEF1234ghikl-zyx57W2v1u123ew11`）

### 配置与启动

```bash
# Windows CMD
set TELEGRAM_BOT_TOKEN=your-bot-token-here
set DEEPSEEK_API_KEY=your-deepseek-key-here
python main.py

# Windows PowerShell
$env:TELEGRAM_BOT_TOKEN="your-bot-token-here"
$env:DEEPSEEK_API_KEY="your-deepseek-key-here"
python main.py

# Linux / macOS
export TELEGRAM_BOT_TOKEN="your-bot-token-here"
export DEEPSEEK_API_KEY="your-deepseek-key-here"
python main.py
```

### Bot 命令

| 命令 | 说明 |
|---|---|
| `/start` | 开始使用，显示欢迎信息 |
| `/help` | 显示可用命令列表 |
| `/today` | 查看今日待办任务清单 |
| `/done <任务ID>` | 标记指定任务为完成（例：`/done 3`） |
| 直接发送消息 | AI 解析自然语言并自动创建任务 |

### 使用示例

```
用户: 明天下午3点和导师开会讨论毕业设计
Bot:  ✅ 已添加任务：【和导师开会讨论毕业设计】，优先级：【高】，截止日期：【2026-03-07】

用户: /today
Bot:  📅 今日待办任务
      • #1 和导师开会讨论毕业设计
        [高] | 截止：2026-03-07

用户: /done 1
Bot:  ✅ 任务 #1【和导师开会讨论毕业设计】已标记为完成！
```

### 注意事项

- 如果未设置 `DEEPSEEK_API_KEY`，Bot 收到的消息会直接以原文作为标题创建任务（优先级=中，无截止日期）
- 如果未设置 `TELEGRAM_BOT_TOKEN`，Bot 功能会静默跳过，不影响 Web 服务正常使用
- Bot 使用长轮询（polling）方式接收消息，无需配置 Webhook

## 项目结构

```
daily-dashboard/
├── main.py                 # 应用入口
├── requirements.txt        # Python 依赖
├── README.md
├── app/
│   ├── models.py           # Pydantic 数据模型
│   ├── database.py         # SQLite 数据库 CRUD
│   ├── nlp_parser.py       # DeepSeek AI 任务解析
│   ├── telegram_bot.py     # Telegram Bot 集成
│   └── routers/
│       └── api.py          # JSON API 路由
├── data/                   # SQLite 数据库文件
├── static/                 # 静态文件
├── templates/              # Jinja2 模板
└── scripts/                # 启动脚本