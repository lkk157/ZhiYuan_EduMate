# RAG 服务契约与 EduMate 适配说明

EduMate **不修改** `D:\python\ClaudeProject\ZhiYuan_EduMind` 源码，仅通过 HTTP `/v1` 接口集成。RAG 服务的真实契约以本文档和其 `/docs` 为准。

## 连接信息

| 项 | 值 |
|---|---|
| 本机地址 | `http://127.0.0.1:18000`（容器内 8000） |
| Docker 内地址 | `http://host.docker.internal:18000` |
| 鉴权 | 请求头 `X-API-Key: zy_...` |
| 健康检查 | `GET /healthz` |

首次接入运行：

```bash
python scripts/register_rag_key.py --base-url http://127.0.0.1:18000
```

脚本注册 `edumate_service` 并签发 API Key，只写入本地 `.env`，不提交仓库。

## 使用到的接口

| 方法 | 路径 | 说明 |
|---|---|---|
| GET | `/healthz` | 存活检查，无需 API Key |
| GET | `/v1/kb/groups` | 分组列表，同时用于校验 API Key |
| POST | `/v1/kb/groups` | 创建分组，`{"name": "..."}`；同名返回 409 |
| GET | `/v1/kb/groups/{gid}/documents` | 分组文档列表 |
| POST | `/v1/kb/groups/{gid}/documents` | multipart 上传 `file`；单次 ≤5 个、总量 ≤200MB |
| POST | `/v1/rag/ask` | `{question, group_ids, guide_mode}` → `{answer, sources, hit, intent, scope_note}` |
| POST | `/v1/rag/retrieve` | 检索接口（EduMate 阶段一未使用） |
| POST | `/v1/rag/ask/stream` | 流式问答（EduMate 阶段二接入） |

支持文件类型：PDF、DOCX、PPTX、PNG、JPG、JPEG。

## 错误格式

```json
{ "error": { "code": "rate_limited", "message": "..." } }
```

- `401`：API Key 无效
- `404`：分组/文档不存在
- `409`：分组名称冲突
- `429`：服务繁忙，可能带 `Retry-After`
- `5xx`：服务异常；RAG 单并发推理，问答可能较慢

## EduMate 适配规则

| EduMate 语义 | RAG 实现 | 说明 |
|---|---|---|
| 课程知识库 | 每课程一个分组 `edumate-course-{course_id}` | 首次索引懒创建，`courses.rag_group_id` 持久化 |
| 个人知识库 | 每知识库一个分组 `edumate-kb-{kb_id}` | 学生个人资料直接索引 |
| 资料索引 | 上传文件到课程/个人分组 | 文件名固定 `m{material_id}__{sanitized_original}` |
| 引用回映射 | `sources[].file_name` 按 `^m(\d+)__(.+)$` 解析 | 映射资料、章节、页码、相似度；无法映射时保留原始文件名 |
| 审核时机 | 课程资料审核通过后才索引 | 避免未发布内容进入课程 RAG 分组；自动审核通过后立即索引 |
| 问答范围 | `group_ids` 传课程组、个人组或合并去重 | 学生必须已选课程 / 拥有知识库 |
| 健康检查 | `/healthz` + 鉴权 `GET /v1/kb/groups` | 30 秒缓存，返回 `reachable/auth_ok/latency_ms` |
| 故障处理 | 问答超时/429/5xx/连接失败 → 友好提示 | 记录 `qa_records.status=degraded`，HTTP 仍返回 200 |
| 重试 | 429 按 `Retry-After` 最多 1 次；索引 5xx 可重试 | 问答不对 5xx 重试；索引失败可手动重试 |

## 已知限制

- RAG `/v1` **没有删除文档接口**：EduMate 删除资料/知识库仅做业务软删除，向量仍然保留。
- 没有课程/章节元数据接口：章节、知识点映射由 EduMate 的 MySQL 维护。
- 没有指标接口：耗时、hit 率、失败率由 EduMate 的 `qa_records` 记录。
- 单并发推理：问答可能等待较久，EduMate 客户端超时为 300 秒。
- 同名资料重传视为增量更新，因此文件名必须包含稳定的 `material_id`。

## 环境变量

```env
RAG_BASE_URL=http://127.0.0.1:18000
RAG_BASE_URL_DOCKER=http://host.docker.internal:18000
RAG_API_KEY=zy_...
RAG_TIMEOUT_SECONDS=300
RAG_CONNECT_TIMEOUT_SECONDS=10
RAG_MAX_RETRIES=1
RAG_HEALTH_TIMEOUT_SECONDS=3
```

真实 `.env` 已被 `.gitignore` 忽略，API Key 不得提交仓库。
