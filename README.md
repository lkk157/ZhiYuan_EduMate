# 智课学伴 EduMate

基于 FastAPI 与 RAG 的 AI 个性化学习与课程教学平台（本科毕业设计，双服务架构）。

- **EduMate 主服务**：用户/权限、课程体系、资料元数据、问答记录、推荐、学情与治理。
- **知源 RAG 服务**（已有，独立部署）：文档解析、向量检索与 LLM 生成，通过 `/v1` HTTP API 接入。

> 当前进度：**P1.8 基础推荐与学生首页已完成**。学生首页聚合已选课程、热门资料、同章节/相似推荐及理由、个人知识库最近资料；推荐限定已选且已发布、已索引的课程资料，热门列表使用 Redis 可选缓存并自动降级；浏览与下载计数、个人资料与问答统计均已接入。下一步 P1.9 部署、种子数据与阶段一验收。完整阶段计划见 [docs/project-flow.md](docs/project-flow.md)，需求见 [docs/requirements.md](docs/requirements.md)。

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

学生也可以在登录页切换到“注册”，自助创建学生账号并自动登录。教师与管理员账号仍由管理员创建。

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
# 本机 compose 将容器 8000 映射到宿主 18000：
# 等待 http://127.0.0.1:18000/healthz 返回 {"status":"ok"}
```

EduMate 使用 `X-API-Key` 鉴权。首次接入时运行：

```bash
.venv/Scripts/python.exe scripts/register_rag_key.py --base-url http://127.0.0.1:18000
```

脚本会注册 `edumate_service` 账号、签发 API Key，并只写入本地 `.env`（已 gitignore），不会提交仓库。

示例资料位于 `samples/`，可通过 `scripts/generate_samples.py` 重新生成。

## 端口约定

| 服务 | 端口 |
|---|---|
| EduMate API | 8001 |
| Vite 开发服务器 | 5173 |
| RAG API | 18000（容器内 8000） |
| MySQL | 3307（容器内 3306） |
| Redis | 6379 |
| Docker Web（阶段一末） | 8080 |

## 故障排查

- **前端登录返回 502**：通常是 EduMate 后端未启动或已退出，Vite 代理 `127.0.0.1:8001` 失败。确认后端进程存在，并访问 <http://127.0.0.1:8001/api/v1/health/live>；如未启动，重新执行后端启动命令。
- **`/health/ready` 返回 `database=error`**：检查 MySQL 容器（`docker compose up -d mysql redis`）。若后端日志出现 `'cryptography' package is required for sha256_password or caching_sha2_password`，执行 `.venv/Scripts/python.exe -m pip install -e ".[dev]"` 安装依赖后重启后端。MySQL 8 默认使用 `caching_sha2_password`，`cryptography` 已在项目依赖中声明。
- **端口占用**：EduMate API 固定 8001，RAG 占用 8000/宿主 18000，MySQL 3307，Redis 6379；修改端口时同步更新 `.env` 与 Vite 代理。

## 开发约定

- 每个小阶段：实现 → 单测 → 全量测试 → 验证 → 提交 → 推送 → 汇报。
- 推送前必须通过 `pytest -q`、`npm run test:unit -- --run`、`npm run build`。
- 统一响应 `{code,message,data}`；错误走 `app/core/errors.py`。
- 所有资源查询必须校验归属；学生只能访问已发布内容。
- 不修改 `ZhiYuan_EduMind` 源码，只通过 HTTP 集成。
