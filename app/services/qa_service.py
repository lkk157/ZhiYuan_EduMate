"""Scoped RAG Q&A, citation mapping and question history."""

from __future__ import annotations

import logging
import re
import time
from pathlib import Path
from typing import Any

from sqlalchemy import and_, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.errors import ConflictError, ForbiddenError, RagError
from app.db.models.course import Course
from app.db.models.knowledge_base import KnowledgeBase
from app.db.models.material import (
    MATERIAL_SCOPE_COURSE,
    MATERIAL_SCOPE_PERSONAL,
    Material,
)
from app.db.models.qa import (
    QA_SCOPE_ALL,
    QA_SCOPE_COURSE,
    QA_SCOPE_PERSONAL,
    QA_STATUS_DEGRADED,
    QA_STATUS_SUCCESS,
    QARecord,
)
from app.db.models.rbac import ROLE_STUDENT, User
from app.schemas.qa import AskRequest
from app.services import course_service, knowledge_base_service
from app.services.rag_client import RagClient

logger = logging.getLogger(__name__)

CITATION_PATTERN = re.compile(r"^m(\d+)__(.+)$")
DEGRADED_ANSWER = "智能问答服务暂时不可用，请稍后重试。你的问题已记录，可稍后在问答记录中查看。"
MATERIAL_LOAD = (
    selectinload(Material.course),
    selectinload(Material.knowledge_base),
    selectinload(Material.chapter),
)


async def _resolve_scope(
    db: AsyncSession,
    user: User,
    body: AskRequest,
) -> tuple[list[int], Course | None, KnowledgeBase | None]:
    groups: list[int] = []
    course: Course | None = None
    knowledge_base: KnowledgeBase | None = None

    if body.scope in {QA_SCOPE_COURSE, QA_SCOPE_ALL} and body.course_id is not None:
        course = await course_service.get_accessible_course(db, user, body.course_id)
        if course.rag_group_id is None:
            raise ConflictError("课程资料尚未建立索引，请等待教师上传并通过审核")
        groups.append(course.rag_group_id)

    if body.scope in {QA_SCOPE_PERSONAL, QA_SCOPE_ALL} and body.knowledge_base_id is not None:
        if user.role.name != ROLE_STUDENT:
            raise ForbiddenError("个人知识库问答仅限学生本人使用")
        knowledge_base = await knowledge_base_service.get_owned_kb(db, user, body.knowledge_base_id)
        if knowledge_base.rag_group_id is None:
            raise ConflictError("该知识库还没有已索引的资料，请先上传资料")
        groups.append(knowledge_base.rag_group_id)

    return list(dict.fromkeys(groups)), course, knowledge_base


async def _build_references(
    db: AsyncSession,
    sources: list[dict[str, Any]],
    *,
    course: Course | None,
    knowledge_base: KnowledgeBase | None,
) -> list[dict[str, Any]]:
    parsed: list[tuple[dict[str, Any], int | None, str]] = []
    material_ids: list[int] = []
    for source in sources:
        if not isinstance(source, dict):
            continue
        file_name = str(source.get("file_name") or "")
        match = CITATION_PATTERN.match(Path(file_name).name)
        material_id = int(match.group(1)) if match else None
        if material_id is not None:
            material_ids.append(material_id)
        parsed.append((source, material_id, file_name))

    materials: dict[int, Material] = {}
    if material_ids:
        conditions = [Material.id.in_(material_ids)]
        if course is not None and knowledge_base is not None:
            conditions.append(
                or_(
                    and_(
                        Material.scope == MATERIAL_SCOPE_COURSE,
                        Material.course_id == course.id,
                    ),
                    and_(
                        Material.scope == MATERIAL_SCOPE_PERSONAL,
                        Material.knowledge_base_id == knowledge_base.id,
                    ),
                )
            )
        elif course is not None:
            conditions.extend(
                [
                    Material.scope == MATERIAL_SCOPE_COURSE,
                    Material.course_id == course.id,
                ]
            )
        elif knowledge_base is not None:
            conditions.extend(
                [
                    Material.scope == MATERIAL_SCOPE_PERSONAL,
                    Material.knowledge_base_id == knowledge_base.id,
                ]
            )
        rows = await db.scalars(select(Material).options(*MATERIAL_LOAD).where(*conditions))
        materials = {row.id: row for row in rows}

    references: list[dict[str, Any]] = []
    for source, material_id, file_name in parsed:
        material = materials.get(material_id) if material_id is not None else None
        reference = {
            "material_id": material.id if material is not None else None,
            "file_name": file_name,
            "page_no": source.get("page_no"),
            "snippet": source.get("snippet"),
            "score": source.get("score"),
            "scope": material.scope if material is not None else None,
            "title": material.title if material is not None else file_name,
            "source_filename": (material.source_filename if material is not None else file_name),
            "course_id": material.course_id if material is not None else None,
            "course_title": (
                material.course.title if material is not None and material.course else None
            ),
            "knowledge_base_id": (material.knowledge_base_id if material is not None else None),
            "knowledge_base_name": (
                material.knowledge_base.name
                if material is not None and material.knowledge_base
                else None
            ),
            "chapter_title": (
                material.chapter.title if material is not None and material.chapter else None
            ),
        }
        references.append(reference)
    return references


async def ask_question(
    db: AsyncSession,
    user: User,
    body: AskRequest,
    rag_client: RagClient,
) -> QARecord:
    group_ids, course, knowledge_base = await _resolve_scope(db, user, body)

    started = time.perf_counter()
    try:
        result = await rag_client.ask(body.question, group_ids=group_ids)
        latency_ms = int((time.perf_counter() - started) * 1000)
        answer = str(result.get("answer") or "").strip()
        if not answer:
            raise RagError("RAG 未返回有效答案")
        sources = result.get("sources")
        if not isinstance(sources, list):
            sources = []
        status = QA_STATUS_SUCCESS
        hit = bool(result.get("hit"))
        intent = result.get("intent")
        scope_note = result.get("scope_note")
        references = await _build_references(
            db, sources, course=course, knowledge_base=knowledge_base
        )
    except RagError as exc:
        latency_ms = int((time.perf_counter() - started) * 1000)
        logger.warning("RAG ask degraded: %s", exc)
        status = QA_STATUS_DEGRADED
        answer = DEGRADED_ANSWER
        hit = False
        intent = None
        scope_note = None
        references = []

    record = QARecord(
        user_id=user.id,
        course=course,
        knowledge_base=knowledge_base,
        scope=body.scope,
        question=body.question,
        answer=answer,
        references_json=references,
        hit=hit,
        intent=str(intent)[:32] if intent is not None else None,
        scope_note=str(scope_note)[:500] if scope_note is not None else None,
        latency_ms=latency_ms,
        status=status,
    )
    db.add(record)
    await db.commit()
    return record


async def list_history(
    db: AsyncSession,
    user: User,
    *,
    page: int = 1,
    page_size: int = 20,
    course_id: int | None = None,
    knowledge_base_id: int | None = None,
    scope: str | None = None,
) -> tuple[list[QARecord], int]:
    conditions = [QARecord.user_id == user.id]
    if course_id is not None:
        conditions.append(QARecord.course_id == course_id)
    if knowledge_base_id is not None:
        conditions.append(QARecord.knowledge_base_id == knowledge_base_id)
    if scope:
        conditions.append(QARecord.scope == scope)

    total = await db.scalar(select(func.count(QARecord.id)).where(*conditions))
    result = await db.scalars(
        select(QARecord)
        .options(selectinload(QARecord.course), selectinload(QARecord.knowledge_base))
        .where(*conditions)
        .order_by(QARecord.created_at.desc(), QARecord.id.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    return list(result), int(total or 0)
