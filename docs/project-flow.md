# EduMate 项目流程（唯一事实源）

> 版本：v1.0（2026-10-22）
> 适用：本科毕业设计 · 双服务架构
> 说明：本文档由批准后的实施计划落库，是项目阶段、产物、测试门禁与验收标准的唯一事实源。
> 每个小阶段完成后，必须更新本文档的状态、产物、测试结果与提交哈希，并随 Git 提交。

## 1. 总体目标

| 阶段 | 定位 | 产物 | 验收 |
|---|---|---|---|
| 第一阶段 | MVP：业务闭环 + RAG 服务化对接 | 可运行 MVP、`v0.1.0-phase1` | 三角色权限隔离；资料索引成功；问答带引用；记录可查；两服务 compose 启动 |
| 第二阶段 | 个性化与完整平台 | 完整平台、评估报告、`v1.0.0` | 推荐随掌握度变化且有理由；看板有数据；管理员可治理；流式 RAG；评估有指标 |

## 2. 执行协议

每个小阶段严格执行：

1. 实现本阶段交付物；
2. 新增/修改单元测试；
3. 运行后端全量 `pytest -q`；
4. 运行前端 `npm run test:unit -- --run` 与 `npm run build`（涉及前端时）；
5. 启动/调用相关服务做运行验证；
6. `git add` → `git commit`（约定式提交）；
7. `git push origin main`；
8. 向用户汇报：产物、测试输出、验证结果、提交哈希、遗留问题；
9. **暂停，等待用户确认后再进入下一阶段**。

任何一步失败必须如实汇报，不跳过测试、不伪造推送成功。

**质量门禁**：后端核心 service 覆盖率目标 80%；每个阶段至少覆盖正向、越权、失败路径；真实 RAG 测试标记 `integration`，默认跳过。

## 3. 进度总览

| 编号 | 阶段 | 状态 | 提交 |
|---|---|---|---|
| P1.1 | 工程骨架、设计系统与登录壳 | 已完成 | `7045b53` · `chore: bootstrap EduMate backend, frontend and local infrastructure` |
| P1.2 | 认证、RBAC 与三角色布局 | 已完成 | `1354042` · `feat(auth): JWT authentication, RBAC and three-role layouts` |
| P1.3 | 管理员治理：用户、角色、审计 | 待开始 | — |
| P1.4 | 课程体系与审核流 | 待开始 | — |
| P1.5 | 资料上传、审核与 RAG 索引 | 待开始 | — |
| P1.6 | 问答、引用与问答记录 | 待开始 | — |
| P1.7 | 基础推荐与学生首页 | 待开始 | — |
| P1.8 | 部署、种子数据与阶段一验收 | 待开始 | — |
| P2.1 | 题库与答题 | 待开始 | — |
| P2.2 | 行为采集与掌握度 | 待开始 | — |
| P2.3 | 个性化推荐 v2 | 待开始 | — |
| P2.4 | 知识图谱与学习路径 | 待开始 | — |
| P2.5 | 教师学情看板 | 待开始 | — |
| P2.6 | 管理员高级治理 | 待开始 | — |
| P2.7 | RAG 流式问答与检索增强 | 待开始 | — |
| P2.8 | 评估实验与完整交付 | 待开始 | — |

## 4. 第一阶段（MVP）细分

### P1.1 工程骨架、设计系统与登录壳

- **目标**：前后端可启动、可测试、可构建，确定视觉与工程基线。
- **交付**：
  - 本文档与 `docs/requirements.md`；
  - 后端配置、日志 request_id、统一 `{code,message,data}` 响应与错误出口、lifespan、CORS；
  - `GET /api/v1/health/live`、`GET /api/v1/health/ready`（检查 DB/Redis）；
  - SQLAlchemy async 基座、Alembic 基线、dev compose（MySQL 3307、Redis 6379）；
  - Vue3 + Vite + Element Plus 设计系统（主色 `#1677ff`、浅蓝白、圆角卡片、220px 侧栏）；
  - AuthLayout、MainLayout、登录页 UI、404、Pinia/Router/Axios 骨架、Vitest；
  - README、CLAUDE.md、`.env.example`、`.gitignore`。
- **测试**：health live/ready；统一 404/422/500；前端挂载、登录表单校验、布局渲染。
- **验证**：`pytest -q`；`npm run test:unit -- --run && npm run build`；mysql/redis healthy；ready 接口返回组件状态。
- **提交**：`chore: bootstrap EduMate backend, frontend and local infrastructure`
- **验收记录（2026-10-22）**：
  - 后端 `pytest -q`：10 passed；`ruff check`：通过；`ruff format --check`：通过。
  - 前端 `npm run test:unit -- --run`：4 个测试文件 / 9 个测试通过；`npm run build`：成功。
  - 运行时：`GET /api/v1/health/live` 200；`GET /api/v1/health/ready` 200（database=ok、redis=ok）。
  - 基础设施：`edumate-mysql`（mysql:8.0，3307）与 `edumate-redis`（redis:7-alpine，6379）均为 healthy；`alembic upgrade head` 已在 MySQL 上成功执行。

### P1.2 认证、RBAC 与三角色布局

- **交付**：用户/角色/权限表与迁移；bcrypt + JWT（`sub/ver/role/iat/exp`）；`/auth/login`、`/auth/me`、`/auth/password`；`get_current_user`、`require_permission`；禁用用户与 `token_version` 失效；三角色菜单/布局/路由守卫；Axios 401 自动登出。
- **测试**：登录成功/失败/禁用；过期/伪造 token；改密后旧 token 失效；角色越权 403；前端 store 持久化、守卫跳转。
- **验证**：三账号分别进入正确端；学生访问管理员接口 403。
- **提交**：`feat(auth): JWT authentication, RBAC and three-role layouts`
- **验收记录（2026-10-23）**：
  - 后端 `pytest -q`：**25 passed**；`ruff check` / `ruff format --check`：通过。
  - 前端 `npm run test:unit -- --run`：**4 个测试文件 / 10 个测试通过**；`npm run build`：成功。
  - 数据库：`alembic upgrade head` 在 MySQL 与 SQLite 上均成功；`alembic downgrade base` 在 SQLite 上成功；`scripts/seed.py` 幂等执行成功（3 角色、12 权限、3 演示账号）。
  - 运行时：admin 登录 12 项权限、teacher 5 项、student 2 项；`/auth/me` 正常；`/admin/ping` 对 admin=200、teacher/student=403。
  - 安全：错误密码与未知用户返回同一提示；禁用用户、旧 token、伪造/过期 token 均被拒绝；改密后旧 token 失效。

### P1.3 管理员治理：用户、角色、审计

- **交付**：用户分页/搜索/创建/编辑/启禁用/角色分配/重置密码；角色权限查看；审计服务与查询；登录成功/失败写审计；禁止禁用自己/最后一个管理员；审计详情脱敏。
- **前端**：用户管理页、角色权限页、审计时间线（对齐参考图）。
- **测试**：重复用户名、非法角色、自我禁用、最后管理员、权限矩阵、审计分页与脱敏。
- **验证**：创建教师 → 改角色 → 禁用 → 查审计闭环。
- **提交**：`feat(admin): user, role and audit management`

### P1.4 课程体系与审核流

- **交付**：课程/章节/知识点 CRUD；教师仅操作自己的课程；提交审核；管理员通过/驳回；学生仅见 `approved`；课程详情聚合。
- **前端**：教师课程列表/编辑、管理员课程审核、学生课程列表/详情骨架。
- **测试**：归属校验、状态机、学生可见性、排序、级联。
- **验证**：教师建课 → 提交 → 管理员通过 → 学生可见。
- **提交**：`feat(course): course hierarchy and review workflow`

### P1.5 资料上传、审核与 RAG 索引

- **交付**：multipart 上传（pdf/docx/pptx/png/jpg/jpeg，≤200MB）；路径清洗与磁盘存储；RAG client（超时、429 重试、错误归一化）；课程分组懒创建；审核通过后后台索引；`indexed/failed` 与重试；下载与软删除；RAG 健康检查。
- **前端**：教师资料上传/列表/状态/重试；管理员资料审核。
- **测试**：类型/大小/路径穿越；分组幂等；审核→索引状态机；RAG 成功/失败/429/超时；引用前缀；软删除。
- **联调**：启动 RAG 容器、注册账号/API Key，上传示例 docx 并确认 `indexed`。
- **提交**：`feat(material): upload, review and RAG indexing`

### P1.6 问答、引用与问答记录

- **交付**：`POST /qa/ask` 调用 `/v1/rag/ask`；保存问答与引用；引用映射资料/章节/页码/相似度；`GET /qa/history`；RAG 故障降级；资料未就绪提示。
- **前端**：学生 AI 问答页（气泡、引用卡、加载态、降级提示）、问答记录页。
- **测试**：成功、`hit=false`、429/502/超时、引用映射、历史归属、未就绪 409。
- **验证**：提问“什么是监督学习？”返回答案 + ≥1 条引用。
- **提交**：`feat(qa): RAG Q&A with citations and history`

### P1.7 基础推荐与学生首页

- **交付**：热门、同章节、相似三类推荐 + 理由；浏览/下载计数；Redis 可选缓存与降级；学生首页聚合。
- **前端**：课程卡片 + 热门资料 + 推荐区块（对齐参考图）。
- **测试**：排序稳定、章节过滤、相似度、无数据兜底、跨课程隔离、仅已发布且已索引。
- **验证**：新用户看到热门；有浏览后出现同章节/相似推荐及理由。
- **提交**：`feat(recommend): basic recommendations and student home`

### P1.8 部署、种子数据与阶段一验收

- **交付**：前后端 Dockerfile、Nginx、完整 compose、示例 docx、演示种子（5 账号、3 课程、章节/知识点、已审核资料、可选 RAG 索引）、冒烟脚本、README/CLAUDE、`docs/{requirements,api,rag-contract}.md`、演示脚本；tag `v0.1.0-phase1`。
- **测试**：全量 pytest、前端 Vitest/build、真实 RAG 集成测试、compose 冒烟。
- **验证**：完成第 9 节阶段一验收流程。
- **提交**：`chore(release): phase 1 deployment, demo data and acceptance docs`

**阶段一完成定义**：三角色可登录且权限隔离；管理员管用户/审核/查审计；教师建课/传资料/提审；资料审核后索引成功；学生提问带引用、记录可查；基础推荐有结果；RAG 停止时非问答功能正常；compose 一键启动。

## 5. 第二阶段（完整平台）细分

### P2.1 题库与答题

- 教师题库 CRUD（单选/多选/判断/简答）、学生练习/提交/判分/解析/错题；`exercises`、`answer_records`；前端题库管理与答题页。
- 测试：判分、重复提交、权限、错题筛选。
- 提交：`feat(exercise): exercise bank and answering`

### P2.2 行为采集与掌握度

- `learning_events`（浏览/答题/问答/完成）、`knowledge_mastery`；规则 + 简化 BKT；冷启动默认值；掌握度查询与学生页面。
- 测试：BKT 更新、边界 [0,1]、事件去重、冷启动。
- 提交：`feat(mastery): behavior events and knowledge mastery`

### P2.3 个性化推荐 v2

- 召回（薄弱知识点、热门、同章节、相似）→ 规则排序 → 多样性重排 → 理由模板；`recommend_logs`；A/B 读取；首页个性化与反馈。
- 测试：召回集合、排序稳定、多样性、理由、冷启动、A/B 分流。
- 提交：`feat(recommend): personalized recall, ranking and explanations`

### P2.4 知识图谱与学习路径

- `knowledge_edges`、环检测、拓扑排序、按掌握度动态调整；教师维护先修关系；学生路径可视化。
- 测试：环检测、拓扑序、先修约束、重规划、课程边界。
- 提交：`feat(path): knowledge graph and adaptive learning path`

### P2.5 教师学情看板

- 课程概览、掌握率柱状图、薄弱点排行、问题分布饼图；ECharts；课程教师/管理员可见；CSV 导出。
- 测试：聚合口径、空数据、日期边界、越权。
- 提交：`feat(analytics): teacher learning analytics dashboard`

### P2.6 管理员高级治理

- 细粒度角色权限、系统配置、审计高级查询/导出、数据备份、健康监控、A/B 配置；敏感值脱敏；可选 Prometheus `/metrics`。
- 测试：权限即时生效、最后管理员保护、配置脱敏、备份产物、审计过滤。
- 提交：`feat(admin): fine-grained RBAC, config, backup and monitoring`

### P2.7 RAG 流式问答与检索增强

- 后端 SSE 代理 `/qa/ask/stream`；前端流式回答/停止/引用渐显；`/v1/rag/retrieve` 引用增强；索引批量/重试；指标记录。
- 测试：SSE delta/done/error、断流、429、引用映射、前端流式渲染。
- 提交：`feat(qa): streaming answers and enhanced retrieval`

### P2.8 评估实验与完整交付

- ≥20 问评测集；Recall@5、引用准确率、hit 率、延迟；推荐 NDCG@10；`docs/evaluation.md`；完整 compose、演示脚本、答辩材料；tag `v1.0.0`。
- 测试：指标计算、评估可重复、全量回归。
- 提交：`chore(release): evaluation, full deployment and v1.0.0`

## 6. 固定验收流程（阶段一）

1. `docker compose up -d --build`：四容器 healthy；`GET /api/v1/health/ready` 返回 DB/Redis/RAG 状态。
2. 管理员登录 → 建/禁用用户 → 分配角色 → 审核课程与资料 → 审计日志出现记录。
3. 教师登录 → 建课“人工智能基础入门” → 章节/知识点 → 上传示例 docx → 提审。
4. 管理员通过资料 → 后台索引 → 状态 `indexed`。
5. 学生登录 → 首页课程/热门资料 → 课程详情 → 提问“什么是监督学习？” → 答案 + 引用 → 记录可查 → 推荐有理由。
6. RAG 停止：问答友好降级，首页/课程/推荐/审计正常。
7. 全量测试与构建通过；推送成功；tag `v0.1.0-phase1`。

## 7. 变更记录

| 日期 | 版本 | 变更 |
|---|---|---|
| 2026-10-22 | v1.0 | 初始流程落库；16 个小阶段；确认 RAG 适配现有 `/v1` API |
