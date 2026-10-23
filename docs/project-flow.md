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
| P1.2b | 学生自助注册 | 已完成 | `a37c2f3` · `feat(auth): student self-registration` |
| P1.3 | 管理员治理：用户、角色、审计 | 已完成 | `0c2110e` · `feat(admin): user, role and audit management` |
| P1.4 | 课程体系、邀请码与选课 | 已完成 | `e4f6464` · `feat(course): course hierarchy, review and enrollment via invite code` |
| P1.5 | 课程资料上传、审核与 RAG 索引 | 待开始 | — |
| P1.6 | 学生个人知识库与资料索引 | 待开始 | — |
| P1.7 | 问答、引用与问答记录（课程/个人库） | 待开始 | — |
| P1.8 | 基础推荐与学生首页（已选课程） | 待开始 | — |
| P1.9 | 部署、种子数据与阶段一验收 | 待开始 | — |
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
  - 前端 `npm run test:unit -- --run`：**5 个测试文件 / 11 个测试通过**；`npm run build`：成功。
  - 修复记录：`AuthLayout` 原先使用 `<slot />`，导致嵌套登录子路由不渲染、右侧面板为空；已改为 `<router-view />` 并新增 `AuthLayout.spec.js` 回归测试。浏览器实测登录表单正常显示。
  - 数据库：`alembic upgrade head` 在 MySQL 与 SQLite 上均成功；`alembic downgrade base` 在 SQLite 上成功；`scripts/seed.py` 幂等执行成功（3 角色、12 权限、3 演示账号）。
  - 运行时：admin 登录 12 项权限、teacher 5 项、student 2 项；`/auth/me` 正常；`/admin/ping` 对 admin=200、teacher/student=403。
  - 安全：错误密码与未知用户返回同一提示；禁用用户、旧 token、伪造/过期 token 均被拒绝；改密后旧 token 失效。

### P1.2b 学生自助注册

- **目标**：学生可自助创建账号并自动登录；教师/管理员账号仍由管理员创建。
- **交付**：`POST /api/v1/auth/register`；用户名大小写不敏感、唯一性校验；邮箱选填且格式校验；密码 8-64 位；默认 `student` 角色；注册成功直接签发 JWT；登录页“登录 / 注册”切换、确认密码、注册后跳转学生首页。
- **测试**：注册成功并自动登录、默认学生角色、大小写不敏感登录、重复用户名/邮箱 409、密码不一致/弱密码/邮箱格式 422。
- **验证**：浏览器注册新学生 → 自动进入学生首页；重复注册被拒绝。
- **提交**：`feat(auth): student self-registration`
- **验收记录（2026-10-23）**：
  - 后端 `pytest -q`：**30 passed**；`ruff check` / `ruff format --check`：通过。
  - 前端 `npm run test:unit -- --run`：**5 个测试文件 / 16 个测试通过**；`npm run build`：成功。
  - 运行时：注册新学生返回 201、JWT、`student` 角色；用户名大小写不敏感登录成功；重复用户名返回 409。
  - 前端：登录页“登录 / 注册”切换正常，注册后自动进入学生首页；邮箱可选，密码 8-64 位且需二次确认。

### P1.3 管理员治理：用户、角色、审计

- **交付**：用户分页/搜索/创建/编辑/启禁用/角色分配/重置密码；角色权限查看；审计服务与查询；登录成功/失败写审计；禁止禁用自己/最后一个管理员；审计详情脱敏。
- **前端**：用户管理页、角色权限页、审计时间线（对齐参考图）。
- **测试**：重复用户名、非法角色、自我禁用、最后管理员、权限矩阵、审计分页与脱敏。
- **验证**：创建教师 → 改角色 → 禁用 → 查审计闭环。
- **提交**：`feat(admin): user, role and audit management`
- **验收记录（2026-10-23）**：
  - 后端 `pytest -q`：**45 passed**；`ruff check app tests` / `ruff format --check app tests`：通过。
  - 前端 `npm run test:unit -- --run`：**8 个测试文件 / 20 个测试通过**；`npm run build`：成功。
  - 数据库：新增 `audit_logs` 表迁移 `8f7e6d5c4b3a`，已在 MySQL 与 SQLite 测试库验证。
  - 新增接口：`GET /admin/stats`、`GET/POST /admin/users`、`PUT /admin/users/{id}`、`PUT /admin/users/{id}/status`、`POST /admin/users/{id}/reset-password`、`GET /admin/roles`、`GET /admin/audit-logs`；均受 `user:manage` / `role:manage` / `audit:view` 权限保护。
  - 安全：登录成功/失败均写审计；创建/改角色/启禁用/重置密码写审计；密码、token、API Key 等敏感字段递归脱敏；禁止禁用自己；禁止禁用或降级最后一个启用管理员；改角色、禁用、重置密码均递增 `token_version`，旧令牌立即失效。
  - 运行时闭环：管理员登录 → 创建教师 `p13check*` → 改为学生并修改邮箱 → 旧令牌 401 → 禁用后登录 401 → 启用 → 角色矩阵返回 3 角色/12 权限 → 审计日志出现 `auth.login.success/failed`、`user.create/update/disable/enable`；创建审计详情不含密码。
  - 前端：管理员仪表盘接入真实用户/角色/今日操作统计；用户管理页支持搜索、角色/状态筛选、分页、创建、编辑角色与邮箱、重置密码、启禁用；角色权限页展示角色卡片与权限矩阵；审计页以时间线展示操作人、动作、对象、IP、结果与脱敏详情。

### P1.4 课程体系、邀请码与选课

- **交付**：
  - 课程/章节/知识点 CRUD；教师仅操作自己的课程；提交审核；管理员通过/驳回。
  - 课程邀请码：每门课程唯一、可轮换、可启停；仅 `approved` 课程可加入。
  - `course_enrollments`：学生凭邀请码加入；教师按用户名添加/移除学生；重复加入幂等；记录来源（`invite_code` / `teacher_add`）。
  - 学生“我的课程”仅返回已选课程；课程详情、章节、资料访问必须校验已选关系（教师本人/管理员例外）。
- **前端**：教师课程列表/编辑、邀请码展示/复制/轮换、学生名单管理；管理员课程审核；学生“加入课程”输入邀请码与我的课程列表。
- **测试**：课程归属、审核状态机、邀请码唯一/轮换/停用、加入已发布课程、重复加入幂等、教师添加/移除、未选学生访问 403、非本人课程不可编辑。
- **验证**：教师建课并通过审核 → 生成邀请码 → 学生注册后凭码加入 → 我的课程出现该课程；教师也能直接添加学生。
- **提交**：`feat(course): course hierarchy, review and enrollment via invite code`
- **验收记录（2026-10-23，提交 `e4f6464`）**：
  - 后端 `pytest -q`：**51 passed**；`ruff check app tests` / `ruff format --check app tests`：通过。
  - 前端 `npm run test:unit -- --run`：**12 个测试文件 / 24 个测试通过**；`npm run build`：成功。
  - 数据库：新增 `courses`、`chapters`、`knowledges`、`course_enrollments` 四张表，迁移 `b2c3d4e5f6a7` 已在 MySQL 与 SQLite 测试库验证。
  - 新增接口：`GET/POST /courses`、`GET/PUT /courses/{id}`、`POST /courses/{id}/submit`、`POST /courses/{id}/review`、`POST /courses/{id}/invite/rotate`、`PUT /courses/{id}/invite`、`POST /courses/join`、章节/知识点 CRUD、`GET/POST /courses/{id}/students`、`DELETE /courses/{id}/students/{student_id}`。
  - 状态机：`draft/rejected` 可编辑并提交审核；`pending` 锁定；管理员通过后为 `approved`，驳回必须填写意见；仅 `approved` 课程允许加入/添加学生；`approved` 后课程结构锁定。
  - 权限与隔离：教师仅能读写自己的课程；学生仅能访问“已选 + 已发布”课程；学生看到的课程详情不返回邀请码；管理员可查看/审核全部课程。
  - 邀请码：每课程唯一 8 位代码；可轮换、可启停；轮换后旧码立即失效；重复加入幂等；加入来源记录 `invite_code` / `teacher_add`。
  - 审计：`course.create/update/submit/approve/reject/invite.rotate/invite.toggle/join/student.add/student.remove` 写入审计。
  - 运行时闭环：教师创建课程 → 添加章节/知识点 → 提交 → 管理员通过 → 学生凭码加入 → 我的课程出现该课程 → 学生详情不返回邀请码 → 教师名单显示学生 → 新注册学生未加入时访问 403 → 教师按用户名添加后可访问 → 轮换后旧码 404。
  - 前端：教师课程卡片与编辑器（章节、知识点、邀请码、学生名单）、管理员课程审核弹窗、学生“我的课程”与加入课程、学生课程详情页；侧栏在课程子页面保持高亮。

> 说明：当前 `approved` 课程结构锁定，避免审核后内容发生变化；如需修改已发布课程，纳入后续“课程修订/重新审核”能力。运行时验证在本地演示库留下课程 `P1.4 Demo Course 32998` 与学生 `p14student32998`。

### P1.5 课程资料上传、审核与 RAG 索引

- **交付**：课程资料的 multipart 上传（pdf/docx/pptx/png/jpg/jpeg，≤200MB）；路径清洗与磁盘存储；RAG client（超时、429 重试、错误归一化）；每课程一个 RAG 分组；管理员审核通过后后台索引；`indexed/failed` 与重试；下载与软删除；RAG 健康检查。仅课程教师可上传，仅已选学生可查看已审核资料。
- **前端**：教师资料上传/列表/状态/重试；管理员资料审核。
- **测试**：类型/大小/路径穿越；分组幂等；审核→索引状态机；RAG 成功/失败/429/超时；引用前缀；软删除；未选学生 403。
- **联调**：启动 RAG 容器、注册账号/API Key，上传示例 docx 并确认 `indexed`。
- **提交**：`feat(material): course material upload, review and RAG indexing`

### P1.6 学生个人知识库与资料索引

- **交付**：
  - `knowledge_bases` 表：owner、名称、描述、RAG 分组、默认库标记、状态；学生可创建、重命名、软删除多个个人知识库；首次进入自动创建“我的知识库”。
  - 资料模型扩展：`scope=course|personal`、`knowledge_base_id`、`owner_id`，课程资料与个人资料共用索引流程。
  - 个人资料上传/列表/下载/软删除/重试索引；个人资料**不经过管理员审核**，但必须做 owner 隔离。
  - 每个个人知识库独立 RAG 分组；文件名仍使用 `m<material_id>__` 前缀以支持引用回映射。
- **前端**：学生“我的知识库”页面（知识库卡片、创建/重命名、上传资料、索引状态、删除），与课程资料明确分区。
- **测试**：默认库创建幂等；owner 隔离（他人不可读写）；分组懒创建；个人资料直接索引；失败重试；软删除；文件类型/大小校验。
- **验证**：学生创建知识库 → 上传自己的学习资料 → 索引成功 → 在问答中选择个人知识库提问并获得引用。
- **提交**：`feat(kb): personal knowledge bases and material indexing`

### P1.7 问答、引用与问答记录（课程/个人库）

- **交付**：
  - `POST /qa/ask` 支持 `scope=course|personal|all`、`course_id`、`knowledge_base_id`。
  - 校验学生已选课程 / 知识库 owner；按范围组装 RAG `group_ids`（课程分组 + 个人库分组）。
  - 保存问题、答案、引用、耗时、hit、范围；引用映射资料/章节/页码/相似度，区分课程资料与个人资料。
  - `GET /qa/history` 支持按课程/知识库过滤；RAG 故障友好降级；资料未就绪提示。
- **前端**：学生 AI 问答页（范围选择器、气泡、引用卡、加载态、降级提示）、问答记录页。
- **测试**：课程未选 403、他人知识库 403/404、`all` 分组合并、`hit=false`、429/502/超时、引用映射、历史归属、未就绪 409。
- **验证**：学生分别对课程资料、个人知识库提问，答案引用正确来源。
- **提交**：`feat(qa): scoped Q&A over course and personal knowledge bases`

### P1.8 基础推荐与学生首页（已选课程）

- **交付**：已选课程内的热门、同章节、相似资料推荐 + 理由；个人知识库最近资料；浏览/下载计数；Redis 可选缓存与降级；学生首页聚合已选课程、热门资料、推荐。
- **前端**：学生首页课程卡片 + 热门资料 + 推荐区块（对齐参考图），无已选课程时展示加入课程引导。
- **测试**：排序稳定、章节过滤、相似度、无数据兜底、跨课程隔离、仅已发布且已索引、未选课程不出现。
- **验证**：新学生加入课程后看到课程与热门资料；浏览后出现同章节/相似推荐及理由。
- **提交**：`feat(recommend): recommendations for enrolled courses and student home`

### P1.9 部署、种子数据与阶段一验收

- **交付**：前后端 Dockerfile、Nginx、完整 compose、示例 docx、演示种子（5 账号、3 课程、邀请码、选课关系、章节/知识点、已审核资料、示例个人知识库、可选 RAG 索引）、冒烟脚本、README/CLAUDE、`docs/{requirements,api,rag-contract}.md`、演示脚本；tag `v0.1.0-phase1`。
- **测试**：全量 pytest、前端 Vitest/build、真实 RAG 集成测试、compose 冒烟。
- **验证**：完成第 9 节阶段一验收流程。
- **提交**：`chore(release): phase 1 deployment, demo data and acceptance docs`

**阶段一完成定义**：学生可自助注册；三角色可登录且权限隔离；管理员管用户/审核/查审计；教师建课、生成邀请码、添加学生、传资料、提审；学生凭邀请码或教师添加进入课程；资料审核后索引成功；学生可创建个人知识库并上传资料；学生可对课程/个人知识库提问并获得引用；记录可查；基础推荐有结果；RAG 停止时非问答功能正常；compose 一键启动。

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

- 召回（薄弱知识点、热门、同章节、相似，限定已选课程与个人知识库）→ 规则排序 → 多样性重排 → 理由模板；`recommend_logs`；A/B 读取；首页个性化与反馈。
- 测试：召回集合、排序稳定、多样性、理由、冷启动、A/B 分流。
- 提交：`feat(recommend): personalized recall, ranking and explanations`

### P2.4 知识图谱与学习路径

- `knowledge_edges`、环检测、拓扑排序、按掌握度动态调整；教师维护先修关系；学生路径可视化。
- 测试：环检测、拓扑序、先修约束、重规划、课程边界。
- 提交：`feat(path): knowledge graph and adaptive learning path`

### P2.5 教师学情看板

- 课程概览、掌握率柱状图、薄弱点排行、问题分布饼图；统计范围限定课程已选学生；ECharts；课程教师/管理员可见；CSV 导出。
- 测试：聚合口径、空数据、日期边界、越权。
- 提交：`feat(analytics): teacher learning analytics dashboard`

### P2.6 管理员高级治理

- 细粒度角色权限、系统配置、审计高级查询/导出、数据备份、健康监控、A/B 配置；敏感值脱敏；可选 Prometheus `/metrics`。
- 测试：权限即时生效、最后管理员保护、配置脱敏、备份产物、审计过滤。
- 提交：`feat(admin): fine-grained RBAC, config, backup and monitoring`

### P2.7 RAG 流式问答与检索增强

- 后端 SSE 代理 `/qa/ask/stream`（保持课程/个人知识库范围参数）；前端流式回答/停止/引用渐显；`/v1/rag/retrieve` 引用增强；索引批量/重试；指标记录。
- 测试：SSE delta/done/error、断流、429、引用映射、前端流式渲染。
- 提交：`feat(qa): streaming answers and enhanced retrieval`

### P2.8 评估实验与完整交付

- ≥20 问评测集；Recall@5、引用准确率、hit 率、延迟；推荐 NDCG@10；`docs/evaluation.md`；完整 compose、演示脚本、答辩材料；tag `v1.0.0`。
- 测试：指标计算、评估可重复、全量回归。
- 提交：`chore(release): evaluation, full deployment and v1.0.0`

## 6. 固定验收流程（阶段一）

1. `docker compose up -d --build`：四容器 healthy；`GET /api/v1/health/ready` 返回 DB/Redis/RAG 状态。
2. 新学生访问登录页 → 切换“注册” → 创建账号 → 自动登录进入学生首页。
3. 管理员登录 → 建/禁用用户 → 分配角色 → 审核课程与资料 → 审计日志出现记录。
4. 教师登录 → 建课“人工智能基础入门” → 章节/知识点 → 提交审核 → 管理员通过 → 获取邀请码 → 上传示例 docx → 管理员通过 → 后台索引状态 `indexed`。
5. 学生凭邀请码加入课程（或教师按用户名添加）→ 我的课程出现该课程 → 对课程资料提问 → 答案 + 引用 → 记录可查。
6. 学生创建个人知识库 → 上传自己的学习资料 → 索引成功 → 选择个人知识库提问 → 引用指向个人资料。
7. 学生首页展示已选课程、热门资料与推荐（带理由）。
8. RAG 停止：问答友好降级，首页/课程/推荐/审计正常。
9. 全量测试与构建通过；推送成功；tag `v0.1.0-phase1`。

## 7. 变更记录

| 日期 | 版本 | 变更 |
|---|---|---|
| 2026-10-22 | v1.0 | 初始流程落库；16 个小阶段；确认 RAG 适配现有 `/v1` API |
| 2026-10-23 | v1.1 | 新增学生自助注册（P1.2b）；新增课程邀请码/教师拉人/选课（P1.4）；新增学生个人知识库（P1.6）；原问答/推荐/部署顺延为 P1.7-P1.9，共 18 个小阶段 |
| 2026-10-23 | v1.2 | 完成 P1.3 管理员治理：用户管理、角色权限矩阵、审计日志与脱敏、最后管理员保护；新增 `audit_logs` 迁移 |
| 2026-10-23 | v1.3 | 完成 P1.4 课程体系、审核流、邀请码与选课；新增课程/章节/知识点/选课表与课程审计动作；已发布课程结构锁定 |
