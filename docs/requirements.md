# EduMate 需求说明

> 版本：v1.0（2026-10-22）
> 来源：`项目规划.md`、`智课学伴 EduMate 项目规划（双服务架构）.md` 与现有 RAG 服务勘察结果。

## 1. 项目概述

- **名称**：智课学伴 EduMate
- **定位**：基于 FastAPI 与 RAG 的 AI 个性化学习与课程教学平台
- **性质**：本科毕业设计，分两阶段交付，每阶段有可演示成品
- **角色**：学生、教师、管理员
- **核心能力**：
  1. 课程知识库 RAG 问答（带引用来源）
  2. 个性化学习推荐（习题、资料、学习路径）
  3. 教师学情分析看板
  4. 管理员系统治理（用户、权限、审核、配置、审计、监控）

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
| 课程知识库 | 每课程一个 RAG 分组；`course.rag_group_id` |
| 资料索引 | 审核通过后上传；`rag_filename = m{material_id}__{原文件名}`；保存 `doc_id` |
| 引用回映射 | 正则 `^m(\d+)__(.+)$` → material → chapter/knowledge；失败时原始展示 |
| 删除 | 业务软删除；说明向量残留限制 |
| 健康 | `/healthz` + 鉴权分组列表，返回 `reachable/auth_ok/latency_ms` |
| 限流 | 429 退避重试 1 次；问答 300s；失败降级 |

## 5. 阶段范围

### 5.1 第一阶段（MVP）

1. 用户/角色/权限：学生、教师、管理员登录与基础 RBAC。
2. 管理员基础：用户管理、角色分配、课程/资料审核、操作日志。
3. 课程管理：教师建课、章节、知识点、资料上传。
4. 知识库：文档上传、解析、分块、向量化、索引状态。
5. RAG 问答：检索 + LLM 生成 + 引用来源。
6. 问答记录：保存问题、回答、引用、耗时。
7. 基础推荐：热门资源、同章节资源、相似资源。
8. 三端前端：学生端、教师端、管理员端基础页面。
9. Docker Compose 部署：MySQL、Redis、API、Web。

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

阶段一：`roles`、`permissions`、`role_permissions`、`users`、`courses`、`chapters`、`knowledges`、`materials`、`qa_records`、`audit_logs`。

阶段二：`exercises`、`answer_records`、`learning_events`、`knowledge_mastery`、`knowledge_edges`、`recommend_logs`、`system_configs`、`ab_tests`。

约定：主键 bigint 自增；utf8mb4；软删除用 `status`；JSON 字段用 MySQL JSON 类型；`material.index_status ∈ pending/indexing/indexed/failed`。

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

- 三角色可登录、权限隔离；管理员可管用户/课程/资料/日志。
- 资料上传后可索引；问答可用、引用可溯源、记录可查。
- 基础推荐有结果并带理由。
- 阶段二推荐随掌握度变化且有理由；教师看板有数据；学习路径可动态调整；管理员可治理；RAG 流式可用；评估有可复现指标。
- 两阶段均可用 Docker Compose 启动并演示。
