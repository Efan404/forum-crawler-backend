# Backend Development Guide - Tech Forum Monitor MVP

## 项目概述

**设计理念：简化优先，渐进迭代**

- 🎯 **MVP 目标**：1 周内上线可用版本
- 📦 **技术栈**：FastAPI + Celery + PostgreSQL + Redis
- 🚀 **部署方式**：Coolify (Docker Compose + Traefik)
- 🔄 **迭代策略**：MVP → 基础功能 → 优化增强

## 技术栈

### 核心依赖
```python
# Web 框架
fastapi==0.104.1
uvicorn[standard]==0.24.0
python-multipart==0.0.6

# 数据库
sqlalchemy[asyncio]==2.0.23
alembic==1.12.1
asyncpg==0.29.0

# 任务队列
celery==5.3.4
redis==5.0.1

# HTTP 客户端和解析
httpx==0.25.2
feedparser==6.0.10
beautifulsoup4==4.12.2

# 数据验证和配置
pydantic==2.5.0
pydantic-settings==2.1.0
python-dotenv==1.0.0

# 工具库
structlog==23.2.0
```

### 开发依赖
```python
pytest==7.4.3
pytest-asyncio==0.21.1
black==23.11.0
```

## 项目结构（极简版）

```
backend/
├── app/
│   ├── __init__.py
│   ├── main.py              # FastAPI 应用 + 所有路由
│   ├── config.py            # 配置管理（Settings）
│   ├── database.py          # 数据库连接和会话
│   ├── models.py            # SQLAlchemy 模型（Topic, Post, PushLog）
│   ├── schemas.py           # Pydantic 模型（请求/响应）
│   ├── crud.py              # 数据库操作（CRUD 函数）
│   ├── tasks.py             # Celery 任务 + Beat 配置
│   └── fetchers.py          # RSS 抓取逻辑（简单函数）
│
├── alembic/
│   ├── versions/
│   ├── env.py
│   └── alembic.ini
│
├── tests/
│   ├── test_api.py
│   ├── test_crud.py
│   └── test_fetchers.py
│
├── .env.example
├── .gitignore
├── requirements.txt
├── Dockerfile
├── docker-compose.yml       # 本地开发
├── docker-compose.prod.yml  # Coolify 部署
└── README.md
```

**核心文件数量：7 个**（相比原设计的 30+ 文件）

## 架构设计

### 系统架构图

```
┌─────────────────────────────────────────────────────┐
│                    Coolify VPS                       │
├─────────────────────────────────────────────────────┤
│  Traefik (自动 HTTPS)                                │
│     ↓                                                │
│  FastAPI Container (port 8000)                      │
│     ↓                                                │
│  PostgreSQL Container                                │
│  Redis Container                                     │
│  Celery Worker Container                             │
│  Celery Beat Container                               │
└─────────────────────────────────────────────────────┘
```

### 数据流

```
┌──────────┐
│ Celery   │ (每 5 分钟)
│ Beat     │
└────┬─────┘
     ↓
┌────────────────┐
│ Celery Worker  │
│ fetch_all_     │
│ topics()       │
└────┬───────────┘
     ↓
┌────────────────┐      ┌──────────────┐
│ Fetchers       │ ───→ │ PostgreSQL   │
│ - V2EX         │      │ - Topics     │
│ - NodeSeek     │      │ - Posts      │
│ - Linux.do     │      │ - PushLogs   │
└────────────────┘      └──────────────┘
     ↓
┌────────────────┐
│ Keyword Match  │ (简单字符串匹配)
└────┬───────────┘
     ↓
┌────────────────┐
│ Save Post      │
│ Create Log     │
└────────────────┘
```

## 数据模型设计

### Topic（话题）
```python
id: int (PK)
name: str                # "V2EX Python"
source: str              # "v2ex" | "nodeseek" | "linux.do"
feed_url: str            # RSS 地址
keywords: List[str]      # JSON ["python", "django"]
is_active: bool          # 是否启用
created_at: datetime
updated_at: datetime
```

### Post（帖子）
```python
id: int (PK)
topic_id: int (FK)
title: str
content: str             # 可能为空（RSS 可能只有摘要）
link: str                # 原帖链接
uid: str                 # 唯一标识（用于去重）
published_at: datetime   # 发布时间
is_pushed: bool          # 是否已推送（预留）
created_at: datetime
```

### PushLog（推送日志）
```python
id: int (PK)
post_id: int (FK)
status: str              # "pending" | "success" | "failed"
message: str             # 错误信息或备注
created_at: datetime
```

## API 设计

### 接口列表（与前端对齐）

```
Health Check:
GET  /health                            # 健康检查

Topics:
GET    /api/v1/topics?skip=0&limit=20  # 获取话题列表
POST   /api/v1/topics                   # 创建话题
GET    /api/v1/topics/{id}              # 获取话题详情
PUT    /api/v1/topics/{id}              # 更新话题
DELETE /api/v1/topics/{id}              # 删除话题

Posts:
GET  /api/v1/posts?skip=0&limit=20&topic_id=1&source=v2ex
                                        # 获取帖子列表（支持筛选）

Logs:
GET  /api/v1/logs?skip=0&limit=20&status=success
                                        # 获取推送日志

System:
GET  /api/v1/system/stats               # 系统统计
```

### 响应格式

**列表响应：**
```json
{
  "items": [...],
  "total": 100,
  "skip": 0,
  "limit": 20
}
```

**单个资源：**
```json
{
  "id": 1,
  "name": "V2EX Python",
  "source": "v2ex",
  ...
}
```

**错误响应：**
```json
{
  "detail": "Resource not found"
}
```

## 核心逻辑设计

### 1. RSS 抓取（fetchers.py）

```python
# 三个简单函数，不用类和继承
async def fetch_v2ex_feed(feed_url: str) -> List[Dict]
async def fetch_nodeseek_feed(feed_url: str) -> List[Dict]
async def fetch_linux_do_feed(feed_url: str) -> List[Dict]

# 工厂函数
async def fetch_feed(source: str, feed_url: str) -> List[Dict]

# 关键词匹配
def match_keywords(text: str, keywords: List[str]) -> bool
```

**抓取逻辑：**
- 使用 `feedparser` 解析 RSS
- 提取 title, link, published, summary
- 生成 uid（`source:link` 或 RSS guid）
- 简单字符串匹配关键词

### 2. Celery 任务（tasks.py）

```python
@celery_app.task
def fetch_all_topics():
    """主任务：抓取所有活跃话题"""
    # 1. 查询所有 is_active=True 的 topics
    # 2. 遍历每个 topic
    # 3. 调用对应的 fetcher
    # 4. 检查 uid 是否存在（去重）
    # 5. 关键词匹配
    # 6. 保存 Post + 创建 PushLog

# Beat 配置
celery_app.conf.beat_schedule = {
    'fetch-every-5-minutes': {
        'task': 'app.tasks.fetch_all_topics',
        'schedule': crontab(minute='*/5'),
    }
}
```

### 3. 去重策略

**MVP 阶段：**
- 使用 `Post.uid` 字段（唯一索引）
- 插入前检查 `SELECT id FROM posts WHERE uid = ?`
- 存在则跳过，不存在则插入

**未来优化：**
- Redis Set 缓存已抓取的 uid（Week 3）
- TTL 7 天

## 开发任务清单

### Phase 1: 项目初始化（Day 1）

#### 1.1 环境搭建
- [x] 创建虚拟环境和安装依赖
- [x] 配置 `.env` 文件
- [x] 初始化 Git 仓库
- [x] 配置 `.gitignore`

#### 1.2 数据库配置
- [x] 创建 `app/database.py`（异步引擎和会话）
- [x] 创建 `app/models.py`（3 个模型）
- [x] 初始化 Alembic
- [x] 生成初始迁移文件
- [x] 执行迁移（创建表）

#### 1.3 基础配置
- [x] 创建 `app/config.py`（Settings 类）
- [x] 创建 `app/schemas.py`（Pydantic 模型）

### Phase 2: API 开发（Day 2-3）

#### 2.1 CRUD 层
- [x] 创建 `app/crud.py`
  - [x] Topic CRUD 函数
  - [x] Post 查询函数
  - [x] PushLog 查询函数

#### 2.2 FastAPI 路由
- [x] 创建 `app/main.py`
  - [x] 健康检查 `/health`
  - [x] Topics 路由（5 个端点）
  - [x] Posts 路由（1 个端点）
  - [x] Logs 路由（1 个端点）
  - [x] System 路由（1 个端点）
- [x] CORS 中间件配置
- [x] 异常处理

#### 2.3 测试
- [x] 测试 Topics CRUD
- [x] 测试 Posts 查询
- [x] 测试分页和筛选

### Phase 3: 抓取和任务（Day 4-5）

#### 3.1 RSS 抓取器
- [ ] 创建 `app/fetchers.py`
  - [ ] `fetch_v2ex_feed()`
  - [ ] `fetch_nodeseek_feed()`
  - [ ] `fetch_linux_do_feed()`
  - [ ] `fetch_feed()` 工厂函数
  - [ ] `match_keywords()` 关键词匹配

#### 3.2 Celery 配置
- [ ] 创建 `app/tasks.py`
  - [ ] Celery app 配置
  - [ ] `fetch_all_topics` 任务
  - [ ] Beat schedule 配置

#### 3.3 测试任务
- [ ] 手动触发任务测试
- [ ] 验证数据保存
- [ ] 验证去重逻辑

### Phase 4: Docker 化（Day 6）

#### 4.1 容器配置
- [ ] 创建 `Dockerfile`（多阶段构建）
- [ ] 创建 `docker-compose.yml`（开发环境）
- [ ] 创建 `docker-compose.prod.yml`（生产环境）

#### 4.2 本地测试
- [ ] 使用 docker-compose 启动所有服务
- [ ] 测试服务间通信
- [ ] 测试数据持久化

### Phase 5: 部署（Day 7）

#### 5.1 Coolify 配置
- [ ] 准备生产环境变量
- [ ] 配置数据库持久化卷
- [ ] 配置 Traefik 标签（自动 HTTPS）

#### 5.2 部署和验证
- [ ] 推送代码到 Git
- [ ] 在 Coolify 创建项目
- [ ] 部署服务
- [ ] 验证 API 可访问
- [ ] 验证定时任务运行

#### 5.3 监控
- [ ] 查看日志
- [ ] 测试前端连接
- [ ] 验证完整流程

## Coolify 部署配置

### docker-compose.prod.yml

```yaml
version: '3.8'

services:
  postgres:
    image: postgres:15-alpine
    environment:
      POSTGRES_DB: ${DB_NAME}
      POSTGRES_USER: ${DB_USER}
      POSTGRES_PASSWORD: ${DB_PASSWORD}
    volumes:
      - postgres_data:/var/lib/postgresql/data
    restart: unless-stopped
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U ${DB_USER}"]
      interval: 10s
      timeout: 5s
      retries: 5

  redis:
    image: redis:7-alpine
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 10s
      timeout: 5s
      retries: 5

  backend:
    build:
      context: .
      dockerfile: Dockerfile
    command: uvicorn app.main:app --host 0.0.0.0 --port 8000
    environment:
      DATABASE_URL: postgresql+asyncpg://${DB_USER}:${DB_PASSWORD}@postgres:5432/${DB_NAME}
      REDIS_URL: redis://redis:6379/0
      CELERY_BROKER_URL: redis://redis:6379/0
      CELERY_RESULT_BACKEND: redis://redis:6379/0
    depends_on:
      postgres:
        condition: service_healthy
      redis:
        condition: service_healthy
    restart: unless-stopped
    labels:
      - "traefik.enable=true"
      - "traefik.http.routers.backend.rule=Host(`api.yourdomain.com`)"
      - "traefik.http.routers.backend.entrypoints=websecure"
      - "traefik.http.routers.backend.tls.certresolver=letsencrypt"
      - "traefik.http.services.backend.loadbalancer.server.port=8000"

  celery_worker:
    build:
      context: .
      dockerfile: Dockerfile
    command: celery -A app.tasks.celery_app worker --loglevel=info
    environment:
      DATABASE_URL: postgresql://${DB_USER}:${DB_PASSWORD}@postgres:5432/${DB_NAME}
      REDIS_URL: redis://redis:6379/0
      CELERY_BROKER_URL: redis://redis:6379/0
      CELERY_RESULT_BACKEND: redis://redis:6379/0
    depends_on:
      - postgres
      - redis
    restart: unless-stopped

  celery_beat:
    build:
      context: .
      dockerfile: Dockerfile
    command: celery -A app.tasks.celery_app beat --loglevel=info
    environment:
      DATABASE_URL: postgresql://${DB_USER}:${DB_PASSWORD}@postgres:5432/${DB_NAME}
      REDIS_URL: redis://redis:6379/0
      CELERY_BROKER_URL: redis://redis:6379/0
      CELERY_RESULT_BACKEND: redis://redis:6379/0
    depends_on:
      - postgres
      - redis
    restart: unless-stopped

volumes:
  postgres_data:

networks:
  default:
    name: coolify
    external: true
```

### Dockerfile

```dockerfile
FROM python:3.11-slim

WORKDIR /app

# 安装系统依赖
RUN apt-get update && apt-get install -y \
    gcc \
    postgresql-client \
    && rm -rf /var/lib/apt/lists/*

# 安装 Python 依赖
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 复制应用代码
COPY . .

# 运行迁移（可选，也可以手动执行）
# RUN alembic upgrade head

EXPOSE 8000

# 默认命令（会被 docker-compose 覆盖）
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

### 环境变量配置

```bash
# Coolify 中设置这些环境变量

# 数据库
DB_NAME=tech_monitor
DB_USER=postgres
DB_PASSWORD=your_secure_password

# API Keys（预留，第二周使用）
# ANTHROPIC_API_KEY=your_key
# TELEGRAM_BOT_TOKEN=your_token
# TELEGRAM_CHAT_ID=your_chat_id

# 应用配置
DEBUG=False
LOG_LEVEL=INFO
```

## 开发规范

### 代码风格
```bash
# 使用 Black 格式化
black app/

# 测试
pytest tests/
```

### Git 提交规范
```
feat: add topic CRUD endpoints
fix: resolve RSS parsing issue
docs: update deployment guide
```

### 分支策略
```
main      # 生产环境
develop   # 开发环境（可选）
```

## 本地开发

### 启动服务
```bash
# 启动所有服务（PostgreSQL + Redis + FastAPI）
docker-compose up -d

# 查看日志
docker-compose logs -f backend

# 停止服务
docker-compose down
```

### 手动运行（不用 Docker）
```bash
# 启动 FastAPI
uvicorn app.main:app --reload --port 8000

# 启动 Celery Worker
celery -A app.tasks.celery_app worker --loglevel=info

# 启动 Celery Beat
celery -A app.tasks.celery_app beat --loglevel=info
```

### 数据库迁移
```bash
# 生成迁移
alembic revision --autogenerate -m "init tables"

# 执行迁移
alembic upgrade head

# 回滚
alembic downgrade -1
```

## 迭代计划

### Week 1: MVP ✅
- 话题 CRUD
- RSS 抓取（3 个论坛）
- 关键词匹配
- 定时任务
- Coolify 部署

### Week 2: 增强功能
- [ ] Telegram Bot 推送
  - 发送新帖子通知
  - 格式化消息
- [ ] Claude API 智能筛选
  - 判断帖子价值
  - 生成推荐理由
- [ ] 推送日志优化
  - 记录推送内容
  - 错误重试

### Week 3: 优化
- [ ] Redis 缓存
  - 缓存已抓取的 uid（7 天 TTL）
  - 减少数据库查询
- [ ] 性能优化
  - 数据库索引优化
  - 批量操作
- [ ] 监控和日志
  - 结构化日志
  - Sentry 错误追踪（可选）

## 常见问题

### 数据库连接失败
```python
# 检查 DATABASE_URL 格式
# 异步：postgresql+asyncpg://user:pass@host/db
# 同步：postgresql://user:pass@host/db（Alembic 和 Celery）
```

### Celery 任务不执行
```bash
# 检查 Redis 连接
redis-cli ping

# 检查 Beat 是否运行
docker-compose logs celery_beat

# 手动触发任务测试
celery -A app.tasks.celery_app call app.tasks.fetch_all_topics
```

### Coolify 部署失败
```bash
# 检查 Traefik 标签配置
# 确保域名正确指向 VPS
# 查看容器日志
docker logs <container_id>
```

## 下一步行动

1. ✅ 确认方案无误
2. 🚀 开始 Phase 1: 项目初始化
3. 📝 按照 Todo List 逐步实现
4. 🧪 每个 Phase 完成后测试
5. 🚢 部署到 Coolify

---

**设计理念：Keep It Simple, Ship It Fast, Iterate Smart** 🎯
