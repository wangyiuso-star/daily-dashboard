# Daily Dashboard — 智能任务管理与 Telegram 机器人

一个基于 FastAPI 的全栈任务管理系统，支持通过 Web 仪表盘和 Telegram Bot 进行自然语言任务添加、查询和标记完成。后端集成 DeepSeek API 实现消息解析，使用 SQLite 存储任务数据，前端采用 Jinja2 + HTMX 构建动态仪表盘。项目已配置 CI/CD，可一键部署至 Oracle Cloud 实现 24/7 在线服务。

## ✨ 核心功能

- 📝 **自然语言任务创建**：发送"明天下午3点开会"即可自动解析并添加任务
- 📱 **多终端交互**：Web 仪表盘 + Telegram Bot，数据实时同步
- ✅ **任务管理**：查看今日待办、标记完成、按优先级筛选
- 🤖 **智能解析**：基于 DeepSeek API 的消息理解，支持降级为默认处理
- 📬 **离线消息不丢失**：重启 Bot 后自动拉取 24 小时内积压消息
- ⏰ **定时推送**：每日自动通过 Telegram 发送待办清单（规划中）
- 🚀 **一键部署**：支持 Oracle Cloud 永久免费服务器，GitHub Actions 自动部署

## 🛠 技术栈

- **后端**: FastAPI, aiosqlite, Python 异步编程
- **AI 集成**: DeepSeek API (自然语言解析)
- **前端**: Jinja2 模板 + HTMX 动态交互
- **Bot**: python-telegram-bot 库 (polling 模式)
- **部署**: Oracle Cloud, systemd, GitHub Actions, uvicorn

## 📁 项目结构

```
daily-dashboard/
├── main.py                    # FastAPI 应用入口
├── _simple_bot.py             # 最小 echo bot 测试脚本
├── requirements.txt           # Python 依赖
├── .env.example               # 环境变量模板
├── DEPLOY.md                  # 详细部署指南
├── app/
│   ├── database.py            # 数据库连接与 CRUD
│   ├── models.py              # Pydantic 数据模型
│   ├── nlp_parser.py          # DeepSeek AI 自然语言解析器
│   ├── telegram_bot.py        # Telegram Bot 处理器
│   └── routers/
│       └── api.py             # RESTful API 路由
├── templates/                 # Jinja2 HTML 模板
├── static/                    # 静态文件 (CSS/JS)
├── data/                      # SQLite 数据库文件（本地）
├── scripts/                   # 部署脚本与服务文件
└── .github/
    └── workflows/
        └── deploy.yml         # GitHub Actions 自动部署
```

## 🚀 快速开始

### 1. 克隆仓库

```bash
git clone https://github.com/你的用户名/daily-dashboard.git
cd daily-dashboard
```

### 2. 安装依赖

```bash
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### 3. 配置环境变量

复制环境变量模板并填入实际值：

```bash
cp .env.example .env
```

编辑 `.env` 文件：

```ini
# Telegram Bot Token — 从 @BotFather 获取（可选，不填则跳过 Bot 功能）
TELEGRAM_BOT_TOKEN=1234567890:ABCdefGHIJklmnOPQRSTuvwXYZ

# DeepSeek API Key — 用于 AI 自然语言解析（可选，不填则消息原样创建任务）
DEEPSEEK_API_KEY=sk-your-deepseek-api-key
```

### 4. 启动服务

```bash
python main.py
```

访问 http://127.0.0.1:8000 查看仪表盘，同时在 Telegram 与你的 Bot 对话。

## 📖 详细部署

请参阅 [DEPLOY.md](DEPLOY.md) 了解如何将项目部署到 Oracle Cloud 并保持永久在线。

## 📋 API 接口

| 方法   | 路径                      | 说明                       |
|--------|---------------------------|----------------------------|
| POST   | `/api/tasks`              | 创建任务                   |
| GET    | `/api/tasks`              | 获取任务列表               |
| GET    | `/api/tasks/{id}`         | 获取单个任务               |
| PATCH  | `/api/tasks/{id}`         | 更新任务                   |
| DELETE | `/api/tasks/{id}`         | 删除任务                   |
| PATCH  | `/api/tasks/{id}/complete`| 标记完成                   |
| POST   | `/api/tasks/parse`        | 自然语言解析并创建任务     |

### 使用示例

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

## 🤖 Telegram Bot 命令

| 命令             | 说明                                |
|------------------|-------------------------------------|
| `/start`         | 开始使用，显示欢迎信息              |
| `/help`          | 显示可用命令列表                    |
| `/ping`          | 检查 Bot 是否在线                   |
| `/today`         | 查看今日待办任务清单                |
| `/done <任务ID>` | 标记指定任务为完成（例：`/done 3`） |
| 直接发送消息     | AI 解析自然语言并自动创建任务       |

## 🛡 安全提醒

- **永远不要将 `.env` 文件提交到 Git**（已在 `.gitignore` 中排除）
- 确保数据库文件 (`*.db`) 被 `.gitignore` 忽略
- 在服务器上使用 systemd EnvironmentFile 管理敏感信息（参见 `DEPLOY.md`）
- `.env.example` 仅包含示例占位符，可以安全提交

## 💼 项目经历

这个项目已作为个人作品用于技术简历，展示了全栈开发、API 设计、第三方集成和 DevOps 能力。

## 📝 许可证

MIT License