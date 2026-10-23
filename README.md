# 智课学伴 EduMate

基于 FastAPI 与 RAG 的 AI 个性化学习与课程教学平台（本科毕业设计，双服务架构）。

- **EduMate 主服务**：用户/权限、课程体系、资料元数据、问答记录、推荐、学情与治理。
- **知源 RAG 服务**（已有，独立部署）：文档解析、向量检索与 LLM 生成，通过 `/v1` HTTP API 接入。

> 当前进度：**P1.2 认证、RBAC 与三角色布局已完成**，下一步 P1.3 管理员治理。完整阶段计划见 [docs/project-flow.md](docs/project-flow.md)，需求见 [docs/requirements.md](docs/requirements.md)。

## 技术栈

| 层 | 选型 |
|---|---|
| 后端 | Python 3.11、FastAPI、SQLAlchemy 2.0 async、Alembic、Pydantic v2 |
| 数据 | MySQL 8.0（宿主端口 3307）、Redis 7（可选缓存） |
| 认证 | JWT + passlib[bcrypt] |
| 前端 | Vue 3 + Vite + Element Plus + Pinia + Vue Router + Axios + ECharts |
| 测试 | pytest + pytest-asyncio + httpx；Vitest + Vue Test Utils |
| 部署 | Docker + Docker Compose |

## 目录

```
app/               FastAPI 后端
  core/            配置、日志、错误、中间件、缓存
  db/              SQLAlchemy 基座与模型
  api/v1/          路由
  services/        RAG 客户端、索引、问答、推荐等
  schemas/         Pydantic
tests/             pytest（unit / integration）
web/               Vue 3 前端
docs/              项目流程、需求、API、RAG 契约、评估
scripts/           种子数据、冒烟、RAG Key 注册
deploy/            Dockerfile / Nginx
samples/           示例课程文档
```

## 本地启动

### 1. 环境变量

```bash
cp .env.example .env
# 按需修改 SECRET_KEY、数据库密码、RAG_API_KEY
```

### 2. 后端

```bash
# 已有 .venv（Python 3.11）
.venv/Scripts/python.exe -m pip install -e ".[dev]"
docker compose up -d mysql redis
.venv/Scripts/python.exe -m alembic upgrade head
.venv/Scripts/python.exe -m uvicorn app.main:app --reload --port 8001
```

- 健康检查：<http://127.0.0.1:8001/api/v1/health/live>
- 就绪检查：<http://127.0.0.1:8001/api/v1/health/ready>
- API 文档：<http://127.0.0.1:8001/docs>

初始化演示账号：

```bash
.venv/Scripts/python.exe scripts/seed.py
```

| 账号 | 角色 | 密码 |
|---|---|---|
| `admin` | 管理员 | `SEED_DEMO_PASSWORD`（默认 `EduMate@2026`） |
| `teacher` | 教师 | 同上 |
| `student` | 学生 | 同上 |

> 演示密码仅用于本地开发，部署前务必修改 `SEED_DEMO_PASSWORD` 并重新执行 `seed.py --reset-passwords`。

### 3. 前端

```bash
cd web
npm install
npm run dev          # http://localhost:5173
```

### 4. 测试与构建

```bash
# 后端
.venv/Scripts/python.exe -m pytest -q

# 前端
cd web
npm run test:unit -- --run
npm run build
```

## RAG 服务

RAG 项目位于 `D:\python\ClaudeProject\ZhiYuan_EduMind`，EduMate **不修改其源码**，仅通过 HTTP 调用。

```bash
cd D:/python/ClaudeProject/ZhiYuan_EduMind
docker compose up -d api
# 等待 http://127.0.0.1:8000/healthz 返回 {"status":"ok"}
```

EduMate 使用 `X-API-Key` 鉴权；服务账号与 Key 通过 `scripts/register_rag_key.py` 注册，写入本地 `.env`，不会提交仓库。

## 端口约定

| 服务 | 端口 |
|---|---|
| EduMate API | 8001 |
| Vite 开发服务器 | 5173 |
| RAG API | 8000 |
| MySQL | 3307（容器内 3306） |
| Redis | 6379 |
| Docker Web（阶段一末） | 8080 |

## 开发约定

- 每个小阶段：实现 → 单测 → 全量测试 → 验证 → 提交 → 推送 → 汇报。
- 推送前必须通过 `pytest -q`、`npm run test:unit -- --run`、`npm run build`。
- 统一响应 `{code,message,data}`；错误走 `app/core/errors.py`。
- 所有资源查询必须校验归属；学生只能访问已发布内容。
- 不修改 `ZhiYuan_EduMind` 源码，只通过 HTTP 集成。
