# EduMate API 参考（阶段一）

- 基础地址：`http://127.0.0.1:8001/api/v1`（本地）或 `http://localhost:8080/api/v1`（Docker Web）
- 交互文档：`/docs`、`/openapi.json`
- 认证：除登录、注册、健康检查外，均需 `Authorization: Bearer <JWT>`
- 请求追踪：可传 `X-Request-ID`，响应头会回显；未传时自动生成

## 统一响应

成功：

```json
{ "code": 0, "message": "ok", "data": {} }
```

失败：

```json
{ "code": 1004, "message": "资料不存在", "data": null }
```

常见错误码：`1001` 参数错误、`1002` 未认证、`1003` 无权限、`1004` 不存在、`1005` 冲突、`2001` 认证失败、`5030` 服务未就绪、`5000` 服务器错误。

## 认证与用户

| 方法 | 路径 | 说明 |
|---|---|---|
| POST | `/auth/register` | 学生自助注册，成功后返回 token |
| POST | `/auth/login` | 用户名密码登录 |
| GET | `/auth/me` | 当前用户与角色权限 |
| PUT | `/auth/password` | 修改密码，旧 token 失效 |

JWT 载荷包含 `sub/ver/role/iat/exp`；角色变更或改密会递增 `token_version`。

## 管理员

| 方法 | 路径 | 说明 |
|---|---|---|
| GET | `/admin/stats` | 用户、角色、审计统计 |
| GET | `/admin/users` | 用户分页、搜索、角色/状态筛选 |
| POST | `/admin/users` | 创建教师/管理员/学生 |
| PUT | `/admin/users/{id}` | 编辑用户/角色 |
| PUT | `/admin/users/{id}/status` | 启用/禁用 |
| POST | `/admin/users/{id}/reset-password` | 重置密码 |
| GET | `/admin/roles` | 角色与权限矩阵 |
| GET | `/admin/review-policy` | 自动审核开关与规则 |
| GET | `/admin/audit-logs` | 审计日志分页/筛选 |

保护规则：不能禁用自己，不能禁用最后一个管理员。

## 课程、章节与选课

| 方法 | 路径 | 说明 |
|---|---|---|
| GET | `/courses` | 角色化课程列表 |
| POST | `/courses` | 教师创建课程 |
| GET | `/courses/{id}` | 课程详情（含章节/知识点） |
| PUT | `/courses/{id}` | 编辑课程（草稿/驳回/已发布） |
| POST | `/courses/{id}/submit` | 提交审核；符合规则时自动发布 |
| POST | `/courses/{id}/review` | 管理员通过/驳回 |
| POST | `/courses/batch/review` | 批量通过/驳回 |
| GET/POST | `/courses/{id}/chapters` | 章节列表/创建 |
| PUT/DELETE | `/courses/{id}/chapters/{chapter_id}` | 章节修改/删除 |
| GET/POST | `/courses/{id}/chapters/{chapter_id}/knowledges` | 知识点列表/创建 |
| PUT/DELETE | `/courses/{id}/chapters/{chapter_id}/knowledges/{knowledge_id}` | 知识点修改/删除 |
| POST | `/courses/join` | 学生凭邀请码加入 |
| GET/POST | `/courses/{id}/students` | 学生名单与教师添加 |
| DELETE | `/courses/{id}/students/{student_id}` | 移出学生 |
| POST | `/courses/{id}/invite/rotate` | 轮换邀请码 |
| PUT | `/courses/{id}/invite` | 启停邀请码 |

学生只能访问已选且 `approved` 的课程；教师只能管理自己的课程。

## 课程资料

| 方法 | 路径 | 说明 |
|---|---|---|
| GET | `/materials` | 资料列表，支持 `course_id/chapter_id/status/index_status/keyword` |
| POST | `/materials` | 单文件上传（multipart） |
| POST | `/materials/batch` | 批量上传（≤10 个） |
| GET | `/materials/{id}` | 资料详情 |
| PUT | `/materials/{id}/mapping` | 关联/取消章节与知识点 |
| POST | `/materials/{id}/review` | 管理员审核 |
| POST | `/materials/batch/review` | 批量审核 |
| POST | `/materials/{id}/index/retry` | 重试 RAG 索引 |
| DELETE | `/materials/{id}` | 软删除 |
| POST | `/materials/{id}/view` | 记录浏览 |
| GET | `/materials/{id}/preview` | 在线预览（inline，不计下载） |
| GET | `/materials/{id}/download` | 下载（计下载次数） |
| GET | `/materials/rag-health` | RAG 健康状态 |

支持类型：PDF、DOCX、PPTX、PNG、JPG、JPEG；单文件上限 200MB。自动审核仅覆盖关联章节的 PDF/DOCX/PPTX。

## 个人知识库

| 方法 | 路径 | 说明 |
|---|---|---|
| GET/POST | `/knowledge-bases` | 我的知识库列表/创建；首次访问自动创建默认库 |
| PUT/DELETE | `/knowledge-bases/{id}` | 重命名/软删除（默认库不可删） |
| GET/POST | `/knowledge-bases/{id}/materials` | 个人资料列表/上传 |
| DELETE | `/knowledge-bases/{id}/materials/{material_id}` | 删除个人资料 |
| POST | `/knowledge-bases/{id}/materials/{material_id}/index/retry` | 重试索引 |

个人知识库按 `owner_id` 隔离，教师与管理员也不能访问。

## AI 问答

| 方法 | 路径 | 说明 |
|---|---|---|
| POST | `/qa/ask` | 课程/个人库/综合范围问答 |
| GET | `/qa/history` | 本人问答记录与筛选 |

`scope` 取值：`course`（必填 `course_id`）、`personal`（必填 `knowledge_base_id`）、`all`（至少一个）。RAG 故障降级为 HTTP 200 + `status=degraded`，不会返回 5xx。

## 推荐与首页

| 方法 | 路径 | 说明 |
|---|---|---|
| GET | `/recommendations` | 已选课程热门/同章节/相似推荐及理由 |
| GET | `/home/overview` | 学生首页聚合 |

推荐只使用已选、已发布且 `index_status=indexed` 的课程资料。热门列表使用 Redis 缓存，Redis 故障自动降级。

## 健康检查

| 方法 | 路径 | 说明 |
|---|---|---|
| GET | `/health/live` | 进程存活 |
| GET | `/health/ready` | 数据库必需、Redis 可选；返回组件状态 |
