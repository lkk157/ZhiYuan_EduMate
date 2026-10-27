# EduMate 阶段一演示脚本

## 1. 启动

```bash
# RAG 服务（独立项目，不在 EduMate compose 内）
cd D:/python/ClaudeProject/ZhiYuan_EduMind
docker compose up -d api

# EduMate
cd D:/python/ClaudeProject/EduMate
cp .env.example .env          # 设置 SECRET_KEY、RAG_API_KEY
docker compose up -d --build
docker compose exec edumate-api python scripts/seed_demo.py --with-rag
```

访问：

- Web：<http://localhost:8080>
- API 文档：<http://localhost:8001/docs>
- 健康检查：<http://localhost:8001/api/v1/health/ready>

## 2. 演示账号

密码统一为 `SEED_DEMO_PASSWORD`（默认 `EduMate@2026`）。

| 账号 | 角色 |
|---|---|
| `admin` | 管理员 |
| `teacher` | 教师 |
| `teacher2` | 教师 |
| `student` | 学生 |
| `student2` | 学生 |

演示课程与邀请码：

| 课程 | 教师 | 邀请码 |
|---|---|---|
| 人工智能基础入门 | teacher | `AI2026AA` |
| 数据结构与算法 | teacher | `DS2026BB` |
| Python 程序设计入门 | teacher2 | `PY2026CC` |

## 3. 推荐演示流程

1. **管理员**登录 → 仪表盘、用户管理、角色权限、课程审核、资料审核、审计日志。
2. **教师**登录 → 课程管理 → 编辑已发布课程，添加章节/知识点 → 上传资料（可批量），选择章节 → 观察自动审核与索引状态。
3. **学生**登录 → 我的课程 → 点击章节查看章节资料 → 在线预览 PDF/DOCX/PPTX/图片。
4. **学生**进入 AI 学伴 → 选择课程或个人知识库提问 → 展开“引用来源”查看资料/章节/页码 → 问答记录。
5. 学生首页查看热门、同章节、相似推荐与理由；知识库最近资料。
6. **管理员**审核页勾选多条记录，演示批量通过/驳回。
7. 停止 RAG 容器后，问答显示友好降级；课程、资料、推荐、审核、审计仍可正常使用。

## 4. 冒烟检查

```bash
# 宿主机 Python
python scripts/smoke_phase1.py \
  --base-url http://127.0.0.1:8001 \
  --web-url http://127.0.0.1:8080 \
  --with-rag

# 或进入 API 容器
docker compose exec edumate-api python scripts/smoke_phase1.py --with-rag
```

## 5. 阶段一验收清单

- [x] 学生自助注册，三角色登录与权限隔离
- [x] 管理员用户/角色/审计/课程审核/资料审核
- [x] 教师建课、邀请码、添加学生、章节/知识点、资料上传
- [x] 已发布课程可继续维护，资料可关联章节
- [x] 课程/资料自动审核 + 人工兜底 + 批量审核
- [x] 资料审核后真实 RAG 索引
- [x] 学生选课、章节资料、在线预览、问答与引用
- [x] 个人知识库与个人资料问答
- [x] 基础推荐与学生首页
- [x] RAG 停止时非问答功能正常
- [x] Docker Compose 一键启动与冒烟脚本
