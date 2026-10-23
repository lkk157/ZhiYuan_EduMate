# EduMate 需求说明

> 版本：v1.1（2026-10-23）
> 来源：`项目规划.md`、`智课学伴 EduMate 项目规划（双服务架构）.md`、现有 RAG 服务勘察结果，以及 2026-10-23 的需求扩展（学生自助注册、课程邀请码/选课、个人知识库）。

## 1. 项目概述

- **名称**：智课学伴 EduMate
- **定位**：基于 FastAPI 与 RAG 的 AI 个性化学习与课程教学平台
- **性质**：本科毕业设计，分两阶段交付，每阶段有可演示成品
- **角色**：学生（可自助注册）、教师、管理员
- **核心能力**：
  1. 课程知识库 RAG 问答（带引用来源）
  2. 个性化学习推荐（习题、资料、学习路径）
  3. 教师学情分析看板
  4. 管理员系统治理（用户、权限、审核、配置、审计、监控）
  5. 课程邀请码与选课（教师生成邀请码/直接拉人，学生凭码加入）
  6. 学生个人知识库（学生自建知识库并上传自己的学习资料）

## 2. 总体架构

采用双服务架构：

```
Vue3 SPA → EduMate API（FastAPI）→ RagClient → 知源 RAG 服务（现有）
                     │
                MySQL 8 + Redis
```

- **EduMate 主服务**：用户/权限、课程/章节/知识点、资料元数据、问答记录、行为采集、掌握度、推荐、学习路径、学情看板、管理员治理、审计、监控。
- **RAG 服务**：文档解析、分块、Embedding、向量库、检索、Rerank、LLM 生成；返回答案 + 引用 + 耗时。
- **边界**：EduMate 不直接操作向量库，只保存 `material.vector_doc_id` 与 `rag_filename`；RAG 不保存业务数据。

## 3. RAG 服务真实契约（适配基线）

| 能力 | 方法/路径 | 说明 |
|---|---|---|
| 鉴权 | `X-API-Key: zy_...` | API Key 绑定一个系统账号，数据按账号隔离 |
| 建分组 | `POST /v1/kb/groups` `{name}` | 同名 409 |
| 列分组 | `GET /v1/kb/groups` | 含 `doc_count` |
| 列文档 | `GET /v1/kb/groups/{gid}/documents` | 状态/页数/切块数 |
| 上传/索引 | `POST /v1/kb/groups/{gid}/documents` | multipart `file`，≤5 个/批、≤200MB；支持 pdf/docx/pptx/png/jpg/jpeg；同步解析、分块、向量化 |
| 纯检索 | `POST /v1/rag/retrieve` `{query,group_ids,top_k}` | `top_k` 1–20；返回 `hits[].file_name/page_no/text/score/group_id` |
| 同步问答 | `POST /v1/rag/ask` `{question,group_ids,guide_mode}` | 返回 `answer/sources/hit/intent/scope_note` |
| 流式问答 | `POST /v1/rag/ask/stream` | SSE `delta/done/error` |
| 健康 | `GET /healthz` | 免鉴权，仅存活探针 |

限制：

- 同一时刻只处理 1 个推理请求；排队超时返回 429（`Retry-After`）。
- 无 `/v1` 文档删除接口；无 `course_id/chapter_id/knowledge_id/material_id` 元数据；无 Prometheus 指标。
- 错误体为 `{"error":{"code","message"}}`；成功响应为裸对象/数组。
- `sources` 仅含 `file_name/page_no/snippet/score`。

## 4. 适配方案

| EduMate 语义 | 适配方式 |
|---|---|
| 课程知识库 | 每课程一个 RAG 分组；`course.rag_group_id`；课程资料审核通过后索引 |
| 个人知识库 | 每个学生知识库一个 RAG 分组；`knowledge_base.rag_group_id`；按 owner 隔离；个人资料直接索引、无需管理员审核 |
| 资料索引 | 课程资料审核通过后上传；个人资料由本人上传；`rag_filename = m{material_id}__{原文件名}`；保存 `doc_id` |
| 引用回映射 | 正则 `^m(\d+)__(.+)$` → material → 课程章节/个人知识库；失败时原始展示 |
| 问答范围 | `scope=course` 用课程分组；`scope=personal` 用本人知识库分组；`scope=all` 合并已选课程 + 本人知识库分组 |
| 删除 | 业务软删除；说明向量残留限制 |
| 健康 | `/healthz` + 鉴权分组列表，返回 `reachable/auth_ok/latency_ms` |
| 限流 | 429 退避重试 1 次；问答 300s；失败降级 |

## 5. 阶段范围

### 5.1 第一阶段（MVP）

1. 用户/角色/权限：学生自助注册；三角色登录与基础 RBAC。
2. 管理员基础：用户管理、角色分配、课程/资料审核、操作日志。
3. 课程管理：教师建课、章节、知识点、资料上传。
4. 选课：课程邀请码、学生凭码加入、教师按用户名添加/移除学生。
5. 知识库：课程资料审核后索引；学生可创建个人知识库并上传自己的资料。
6. RAG 问答：课程/个人知识库/全部范围检索 + LLM 生成 + 引用来源。
7. 问答记录：保存问题、回答、引用、耗时、范围。
8. 基础推荐：已选课程内的热门资源、同章节资源、相似资源。
9. 三端前端：学生端、教师端、管理员端基础页面。
10. Docker Compose 部署：MySQL、Redis、API、Web。

**非目标**：直播、支付、复杂考试、EduMate 内自研向量检索/LLM 生成。

### 5.2 第二阶段（完整平台）

1. 行为采集：答题、浏览、问答、完成率。
2. 知识追踪：规则/简化 BKT 掌握度。
3. 个性化推荐：混合召回 + 排序 + 推荐理由。
4. 学习路径：知识图谱 + 拓扑排序 + 动态调整。
5. 教师学情看板：高频问题、薄弱知识点、班级掌握度。
6. 管理员高级：细粒度 RBAC、系统配置、审计查询、备份、监控、A/B。
7. RAG 优化：流式问答、混合检索接入、引用增强。
8. 评估实验：Recall@K、NDCG、答题正确率、用户测试。
9. 完整部署与答辩材料。

## 6. 核心数据模型

阶段一：`roles`、`permissions`、`role_permissions`、`users`、`courses`、`chapters`、`knowledges`、`course_enrollments`、`knowledge_bases`、`materials`、`qa_records`、`audit_logs`。

关键字段扩展：
- `courses`：`invite_code`（唯一）、`invite_code_enabled`、`rag_group_id`。
- `course_enrollments`：`course_id`、`student_id`、`source`（`invite_code` / `teacher_add`）、`status`、`created_at`；唯一约束 `(course_id, student_id)`。
- `knowledge_bases`：`owner_id`、`name`、`description`、`rag_group_id`、`is_default`、`status`。
- `materials`：`scope`（`course` / `personal`）、`knowledge_base_id`（个人资料）、`owner_id`、`course_id`/`chapter_id` 可空；`index_status ∈ pending/indexing/indexed/failed`。
- `qa_records`：`scope`、`knowledge_base_id`（可空）、`references_json`。

阶段二：`exercises`、`answer_records`、`learning_events`、`knowledge_mastery`、`knowledge_edges`、`recommend_logs`、`system_configs`、`ab_tests`。

约定：主键 bigint 自增；utf8mb4；软删除用 `status`；JSON 字段用 MySQL JSON 类型；课程/个人资料共用索引流程，但访问权限与审核策略不同。

## 7. 技术栈

| 类别 | 选型 |
|---|---|
| 语言 | Python 3.11+ |
| Web | FastAPI |
| ORM | SQLAlchemy 2.0 async（asyncmy / 测试 aiosqlite） |
| 数据库 | MySQL 8.0 + Redis 7 |
| 迁移 | Alembic |
| 校验 | Pydantic v2 |
| 认证 | JWT + passlib[bcrypt] |
| HTTP 客户端 | httpx |
| 前端 | Vue 3 + Vite + Element Plus + Pinia + Vue Router + Axios + ECharts |
| 测试 | pytest + pytest-asyncio + httpx；Vitest + Vue Test Utils |
| 部署 | Docker + Docker Compose |

## 8. 验收标准

- 学生可自助注册并自动登录；三角色可登录、权限隔离；管理员可管用户/课程/资料/日志。
- 教师可建课并生成邀请码；学生凭邀请码或教师添加加入课程；未选学生不能访问课程内容。
- 课程资料审核后可索引；学生个人知识库可创建并上传资料；问答覆盖课程/个人库范围，引用可溯源、记录可查。
- 基础推荐有结果并带理由，仅覆盖已选课程。
- 阶段二推荐随掌握度变化且有理由；教师看板有数据；学习路径可动态调整；管理员可治理；RAG 流式可用；评估有可复现指标。
- 两阶段均可用 Docker Compose 启动并演示。
