# 智课学伴 EduMate

基于 FastAPI 与 RAG 的 AI 个性化学习与课程教学平台（本科毕业设计，双服务架构）。

- **EduMate 主服务**：用户/权限、课程体系、资料元数据、问答记录、推荐、学情与治理。
- **知源 RAG 服务**（已有，独立部署）：文档解析、向量检索与 LLM 生成，通过 `/v1` HTTP API 接入。

> 当前进度：**阶段一（P1.1–P1.9）已完成，tag `v0.1.0-phase1`**。三角色权限、课程/资料审核与真实 RAG 索引、选课与邀请码、个人知识库、带引用问答、基础推荐、资料在线预览、自动审核与批量审核均已交付；`docker compose up -d --build` 可一键启动，演示数据与冒烟脚本已通过验收。完整阶段计划见 [docs/project-flow.md](docs/project-flow.md)，需求见 [docs/requirements.md](docs/requirements.md)，API 见 [docs/api.md](docs/api.md)。

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
# 仅 RBAC 三角色账号
.venv/Scripts/python.exe scripts/seed.py

# 完整阶段一演示数据：5 账号、3 课程、章节/知识点、选课、资料、个人知识库
.venv/Scripts/python.exe scripts/seed_demo.py --with-rag
```

| 账号 | 角色 | 密码 |
|---|---|---|
| `admin` | 管理员 | `SEED_DEMO_PASSWORD`（默认 `EduMate@2026`） |
| `teacher` / `teacher2` | 教师 | 同上 |
| `student` / `student2` | 学生 | 同上 |

学生也可以在登录页切换到“注册”，自助创建学生账号并自动登录。教师与管理员账号仍由管理员创建。

> 演示密码仅用于本地开发，部署前务必修改 `SEED_DEMO_PASSWORD` 并重新执行 `seed_demo.py --reset-passwords`。

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

## Docker Compose 一键启动

先停止占用 8001 的本地后端进程，再执行：

```bash
cp .env.example .env
# 修改 SECRET_KEY、MYSQL_PASSWORD、SEED_DEMO_PASSWORD，填入 RAG_API_KEY
docker compose up -d --build
docker compose exec edumate-api python scripts/seed_demo.py --with-rag
```

- Web：<http://localhost:8080>
- API：<http://localhost:8001>
- Nginx 将 `/api/` 反向代理到 `edumate-api:8000`，上传上限 210MB，问答代理超时 310 秒。
- MySQL/Redis 由 compose 启动；RAG 服务不包含在 EduMate compose 内，容器通过 `host.docker.internal:18000` 访问宿主 RAG。
- 上传文件保存在 `uploads_data` 卷，MySQL/Redis 数据分别保存在 `mysql_data`、`redis_data` 卷。

冒烟检查：

```bash
docker compose exec edumate-api python scripts/smoke_phase1.py \
  --base-url http://127.0.0.1:8000 --web-url http://edumate-web --with-rag
```

更多演示步骤见 [docs/demo.md](docs/demo.md)，API 见 [docs/api.md](docs/api.md)，RAG 契约见 [docs/rag-contract.md](docs/rag-contract.md)。

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

## 资料在线预览

- 学生可在“学习资料”和章节资料页点击“预览”在线查看资料，无需先下载。
- PDF 与图片使用浏览器原生预览；DOCX 使用 `docx-preview`、PPTX 使用 `pptx-preview` 在浏览器内解析渲染。
- 预览接口 `GET /api/v1/materials/{id}/preview` 以 inline 方式返回原文件，并校验课程选课/个人库归属。
- 预览会记录浏览行为，但**不会增加下载次数**；预览弹窗内可直接下载原文件。

## 审核机制

- **自动审核（默认开启）**：`AUTO_REVIEW_ENABLED=true`。
  - 课程：简介非空、至少 1 个章节和 1 个知识点、章节标题不重复时，提交后自动发布。
  - 资料：课程已发布、资料关联章节、类型为 PDF/DOCX/PPTX 时，上传后自动通过并后台索引；图片资料仍需人工审核。
  - 不符合规则的课程/资料进入待审核队列，由管理员人工处理。
  - 自动审核记录审计动作 `course.auto_approve` / `material.auto_approve`。
- **人工兜底**：管理员审核页展示自动审核规则说明；课程和资料均支持勾选后批量通过/驳回，驳回必须填写意见。
- **已发布课程维护**：教师可继续修改章节、知识点和课程信息，修改即时生效；课程不需要重新提交审核。
- **资料章节映射**：教师可在资料列表“关联章节”中调整资料所属章节；学生课程页按章节查看资料。

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
