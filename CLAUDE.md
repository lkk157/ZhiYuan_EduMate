# EduMate 开发约定

## 项目定位

智课学伴 EduMate：FastAPI + Vue3 的 AI 个性化学习与课程教学平台。双服务架构：EduMate 主服务 + 既有 RAG 服务（`D:\python\ClaudeProject\ZhiYuan_EduMind`）。分两阶段交付，流程与状态见 `docs/project-flow.md`。

## 强制规则

1. **不修改 RAG 项目源码**。只通过 HTTP API（`/v1/...`，`X-API-Key`）和启动脚本集成。
2. **每个小阶段完成后暂停**：实现 → 补单测 → 全量测试 → 运行验证 → commit → push → 汇报 → 等确认。
3. **推送前必须通过**：
   - `.venv/Scripts/python.exe -m pytest -q`
   - `cd web && npm run test:unit -- --run`
   - `cd web && npm run build`
4. 不伪造测试或推送结果；失败如实报告。
5. 更新 `docs/project-flow.md` 的阶段状态、产物、测试结果与提交哈希。

## 技术约定

- Python 3.11、FastAPI async、SQLAlchemy 2.0 async（运行时 asyncmy，测试 aiosqlite）、Alembic、Pydantic v2。
- 统一成功响应 `{"code":0,"message":"ok","data":...}`；错误使用 `app/core/errors.py` 的 `AppError` 体系（401/403/404/409/422/502/503）。
- 请求 ID 通过 `X-Request-ID` 透传，日志格式含 `[request_id]`。
- Redis 仅作可选缓存，任何 Redis 故障必须降级，不得阻塞业务。
- 所有资源接口必须做归属/角色校验；学生只能访问“已选且 `approved`”的课程与资料；禁止只靠前端隐藏。
- 学生可自助注册，默认 `student` 角色；教师/管理员账号由管理员创建，禁止自助注册为高权限角色。
- 课程访问必须校验 `course_enrollments`；教师可生成邀请码或按用户名添加学生；邀请码仅对 `approved` 课程有效。
- 学生个人知识库按 `owner_id` 隔离；个人资料直接索引、无需管理员审核；每个知识库独立 RAG 分组。
- 课程资料审核通过后才索引，避免未发布内容进入课程 RAG 分组。
- 资料/知识库软删除必须同步调用 RAG `DELETE /v1/kb/groups/{gid}/documents...`；404 视为已删，优先按 `vector_doc_id`、兜底按 `rag_filename`，成功后清空 `vector_doc_id`；索引中返回 409，RAG 失败返回 502 且不落库。
- JWT 载荷 `sub/ver/role/iat/exp`；角色/密码变更递增 `token_version`。
- RAG 资料文件名固定 `m{material_id}__{sanitized_original}`；引用解析正则 `^m(\d+)__(.+)$`。
- RAG 429 按 `Retry-After` 最多重试 1 次；问答超时 300s；失败降级并记录。
- 后端端口 8001，RAG 容器 8000 / 本机映射 18000，MySQL 宿主 3307，Web Docker 8080。
- 自动审核规则：课程简介非空且至少 1 章节/1 知识点；资料关联章节且为 PDF/DOCX/PPTX；其余进入人工待审核队列。`AUTO_REVIEW_ENABLED` 控制。
- 已发布课程允许教师继续维护章节、知识点和资料章节映射，修改即时生效；不允许重复提交审核。
- 资料在线预览使用 `GET /materials/{id}/preview`（inline、不计下载）；前端 PDF/图片原生预览，DOCX/PPTX 使用按需加载的前端解析库。
- Docker 部署：`deploy/Dockerfile.api`、`deploy/Dockerfile.web`、`deploy/nginx.conf`、`docker-compose.yml`；上传文件使用 `uploads_data` 卷。

## 常用命令

```bash
# 后端
.venv/Scripts/python.exe -m pip install -e ".[dev]"
docker compose up -d mysql redis
.venv/Scripts/python.exe -m alembic upgrade head
.venv/Scripts/python.exe -m uvicorn app.main:app --reload --port 8001
.venv/Scripts/python.exe -m pytest -q
.venv/Scripts/python.exe -m ruff check app tests

# 前端
cd web
npm install
npm run dev
npm run test:unit -- --run
npm run build

# Docker / 演示数据 / 冒烟
docker compose up -d --build
docker compose exec edumate-api python scripts/seed_demo.py --with-rag
docker compose exec edumate-api python scripts/smoke_phase1.py \
  --base-url http://127.0.0.1:8000 --web-url http://edumate-web --with-rag
```

## 代码风格

- 后端：类型注解、async-first、service 层承载业务、路由层保持薄、错误统一出口。
- 前端：Vue 3 `<script setup>`、Element Plus、Pinia、Axios；中文 UI；视觉参考项目规划中的效果图（浅蓝白、左侧栏、圆角卡片）。
- 不引入未使用依赖；不扩大阶段范围。
