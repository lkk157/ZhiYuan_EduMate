"""Recommendations inside enrolled courses and the student home aggregate."""

from __future__ import annotations

import logging
from datetime import timedelta
from typing import Any

from sqlalchemy import and_, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.cache import cache_get_json, cache_set_json
from app.core.errors import ValidationError
from app.db.base import utc_now
from app.db.models.course import (
    COURSE_STATUS_APPROVED,
    Course,
    CourseEnrollment,
)
from app.db.models.knowledge_base import KB_STATUS_ACTIVE, KnowledgeBase
from app.db.models.material import (
    INDEX_STATUS_INDEXED,
    MATERIAL_SCOPE_COURSE,
    MATERIAL_SCOPE_PERSONAL,
    MATERIAL_STATUS_APPROVED,
    MATERIAL_STATUS_DELETED,
    Material,
    MaterialView,
)
from app.db.models.qa import QARecord
from app.db.models.rbac import User
from app.schemas.course import course_out
from app.schemas.material import material_list_out
from app.services import course_service
from app.services.material_service import MATERIAL_LOAD, ensure_material_access, get_material

logger = logging.getLogger(__name__)

RECOMMEND_KIND_HOT = "hot"
RECOMMEND_KIND_SAME_CHAPTER = "same_chapter"
RECOMMEND_KIND_SIMILAR = "similar"

RECOMMEND_DEFAULT_LIMIT = 5
RECOMMEND_MAX_LIMIT = 20
HOT_CACHE_TTL_SECONDS = 60


def _clamp_limit(limit: int) -> int:
    return max(1, min(limit, RECOMMEND_MAX_LIMIT))


def _visibility_conditions() -> list[Any]:
    """Materials a student may see: enrolled, approved and indexed courses."""
    return [
        Material.scope == MATERIAL_SCOPE_COURSE,
        Material.status == MATERIAL_STATUS_APPROVED,
        Material.index_status == INDEX_STATUS_INDEXED,
        Course.status == COURSE_STATUS_APPROVED,
    ]


def _visible_query(user: User):
    return (
        select(Material)
        .join(Course, Material.course_id == Course.id)
        .join(
            CourseEnrollment,
            and_(
                CourseEnrollment.course_id == Course.id,
                CourseEnrollment.student_id == user.id,
            ),
        )
        .options(*MATERIAL_LOAD)
        .where(*_visibility_conditions())
    )


def _hot_score(material: Material) -> int:
    return int(material.view_count or 0) + int(material.download_count or 0) * 2


def _hot_reason(material: Material) -> str:
    if material.view_count or material.download_count:
        return f"热门资料 · 浏览 {material.view_count} 次 / 下载 {material.download_count} 次"
    return "新上架资料"


def _item(material: Material, *, kind: str, reason: str, score: int) -> dict[str, Any]:
    payload = material_list_out(material, management=False)
    payload.update({"kind": kind, "reason": reason, "score": score})
    return payload


async def hot_materials(
    db: AsyncSession,
    user: User,
    *,
    course_id: int | None = None,
    limit: int = RECOMMEND_DEFAULT_LIMIT,
) -> list[dict[str, Any]]:
    """Most viewed/downloaded materials in the student's enrolled courses."""
    limit = _clamp_limit(limit)
    cache_key = f"edumate:recommend:hot:{user.id}:{course_id or 0}:{limit}"
    cached = await cache_get_json(cache_key)
    if isinstance(cached, list):
        return cached

    stmt = _visible_query(user)
    if course_id is not None:
        stmt = stmt.where(Material.course_id == course_id)
    score = Material.view_count + Material.download_count * 2
    rows = await db.scalars(
        stmt.order_by(
            score.desc(),
            Material.view_count.desc(),
            Material.created_at.desc(),
            Material.id.desc(),
        ).limit(limit)
    )
    items = [
        _item(
            material,
            kind=RECOMMEND_KIND_HOT,
            reason=_hot_reason(material),
            score=_hot_score(material),
        )
        for material in rows
    ]
    await cache_set_json(cache_key, items, ttl=HOT_CACHE_TTL_SECONDS)
    return items


async def _latest_viewed_material_id(db: AsyncSession, user: User) -> int | None:
    stmt = (
        select(MaterialView.material_id)
        .join(Material, Material.id == MaterialView.material_id)
        .join(Course, Material.course_id == Course.id)
        .join(
            CourseEnrollment,
            and_(
                CourseEnrollment.course_id == Course.id,
                CourseEnrollment.student_id == user.id,
            ),
        )
        .where(MaterialView.user_id == user.id, *_visibility_conditions())
        .order_by(MaterialView.viewed_at.desc(), MaterialView.id.desc())
        .limit(1)
    )
    material_id = await db.scalar(stmt)
    return int(material_id) if material_id is not None else None


async def _resolve_seed(db: AsyncSession, user: User, material_id: int | None) -> Material | None:
    if material_id is not None:
        material = await get_material(db, material_id)
        await ensure_material_access(db, material, user)
        if material.scope != MATERIAL_SCOPE_COURSE:
            raise ValidationError("推荐仅支持课程资料")
        return material

    seed_id = await _latest_viewed_material_id(db, user)
    if seed_id is None:
        return None
    return await get_material(db, seed_id)


def _seed_brief(material: Material) -> dict[str, Any]:
    return {
        "id": material.id,
        "title": material.title,
        "course_id": material.course_id,
        "course_title": material.course.title if material.course else None,
        "chapter_id": material.chapter_id,
        "chapter_title": material.chapter.title if material.chapter else None,
        "knowledge_id": material.knowledge_id,
        "knowledge_name": material.knowledge.name if material.knowledge else None,
    }


async def _same_chapter(
    db: AsyncSession,
    user: User,
    seed: Material,
    *,
    limit: int,
) -> list[dict[str, Any]]:
    if seed.chapter_id is None:
        return []
    chapter_title = seed.chapter.title if seed.chapter else ""
    stmt = _visible_query(user).where(
        Material.course_id == seed.course_id,
        Material.chapter_id == seed.chapter_id,
        Material.id != seed.id,
    )
    if seed.knowledge_id is not None:
        # Materials sharing the exact knowledge point are surfaced as
        # "similar" instead of "same chapter" to keep the groups distinct.
        stmt = stmt.where(
            or_(
                Material.knowledge_id.is_(None),
                Material.knowledge_id != seed.knowledge_id,
            )
        )
    score = Material.view_count + Material.download_count * 2
    rows = await db.scalars(
        stmt.order_by(
            score.desc(),
            Material.view_count.desc(),
            Material.created_at.desc(),
            Material.id.desc(),
        ).limit(limit)
    )
    reason = f"同章节推荐 · 与你浏览的《{seed.title}》同属「{chapter_title}」"
    return [
        _item(
            material,
            kind=RECOMMEND_KIND_SAME_CHAPTER,
            reason=reason,
            score=_hot_score(material),
        )
        for material in rows
    ]


async def _similar(
    db: AsyncSession,
    user: User,
    seed: Material,
    *,
    limit: int,
    exclude_ids: set[int],
) -> list[dict[str, Any]]:
    if seed.knowledge_id is None:
        return []
    knowledge_name = seed.knowledge.name if seed.knowledge else ""
    stmt = _visible_query(user).where(
        Material.knowledge_id == seed.knowledge_id,
        Material.id != seed.id,
    )
    if exclude_ids:
        stmt = stmt.where(Material.id.notin_(exclude_ids))
    score = Material.view_count + Material.download_count * 2
    rows = await db.scalars(
        stmt.order_by(
            score.desc(),
            Material.view_count.desc(),
            Material.created_at.desc(),
            Material.id.desc(),
        ).limit(limit)
    )
    reason = f"相似资料 · 与你浏览的《{seed.title}》共享知识点「{knowledge_name}」"
    return [
        _item(
            material,
            kind=RECOMMEND_KIND_SIMILAR,
            reason=reason,
            score=_hot_score(material),
        )
        for material in rows
    ]


async def get_recommendations(
    db: AsyncSession,
    user: User,
    *,
    course_id: int | None = None,
    material_id: int | None = None,
    limit: int = RECOMMEND_DEFAULT_LIMIT,
) -> dict[str, Any]:
    """Hot, same-chapter and similar materials with human-readable reasons."""
    limit = _clamp_limit(limit)
    if course_id is not None:
        await course_service.get_accessible_course(db, user, course_id)

    seed = await _resolve_seed(db, user, material_id)
    if seed is not None and course_id is not None and seed.course_id != course_id:
        # Recommendations are scoped to one course: a seed from another course
        # cannot produce same-chapter or same-knowledge candidates here.
        seed = None

    hot = await hot_materials(db, user, course_id=course_id, limit=limit)
    if seed is not None:
        hot = [item for item in hot if item["id"] != seed.id]

    same_chapter: list[dict[str, Any]] = []
    similar: list[dict[str, Any]] = []
    if seed is not None:
        same_chapter = await _same_chapter(db, user, seed, limit=limit)
        exclude_ids = {seed.id, *(item["id"] for item in same_chapter)}
        similar = await _similar(
            db,
            user,
            seed,
            limit=limit,
            exclude_ids=exclude_ids,
        )

    unique_ids = {
        *(item["id"] for item in hot),
        *(item["id"] for item in same_chapter),
        *(item["id"] for item in similar),
    }
    return {
        "seed": _seed_brief(seed) if seed is not None else None,
        "groups": {
            "hot": hot,
            "same_chapter": same_chapter,
            "similar": similar,
        },
        "total": len(unique_ids),
    }


async def recent_personal_materials(
    db: AsyncSession, user: User, *, limit: int = 5
) -> list[dict[str, Any]]:
    limit = _clamp_limit(limit)
    rows = await db.scalars(
        select(Material)
        .join(KnowledgeBase, Material.knowledge_base_id == KnowledgeBase.id)
        .options(*MATERIAL_LOAD)
        .where(
            Material.scope == MATERIAL_SCOPE_PERSONAL,
            Material.owner_id == user.id,
            Material.status != MATERIAL_STATUS_DELETED,
            KnowledgeBase.status == KB_STATUS_ACTIVE,
        )
        .order_by(Material.created_at.desc(), Material.id.desc())
        .limit(limit)
    )
    return [material_list_out(material, management=False) for material in rows]


async def student_home(db: AsyncSession, user: User) -> dict[str, Any]:
    courses, course_total = await course_service.list_courses(db, user, page=1, page_size=6)
    recommendations = await get_recommendations(db, user, limit=RECOMMEND_DEFAULT_LIMIT)
    recent_personal = await recent_personal_materials(db, user, limit=5)

    week_start = utc_now() - timedelta(days=7)
    weekly_questions = await db.scalar(
        select(func.count(QARecord.id)).where(
            QARecord.user_id == user.id,
            QARecord.created_at >= week_start,
        )
    )
    personal_count = await db.scalar(
        select(func.count(func.distinct(Material.id)))
        .select_from(Material)
        .join(KnowledgeBase, Material.knowledge_base_id == KnowledgeBase.id)
        .where(
            Material.scope == MATERIAL_SCOPE_PERSONAL,
            Material.owner_id == user.id,
            Material.status != MATERIAL_STATUS_DELETED,
            KnowledgeBase.status == KB_STATUS_ACTIVE,
        )
    )

    return {
        "stats": {
            "course_count": int(course_total or 0),
            "weekly_questions": int(weekly_questions or 0),
            "recommendation_count": recommendations["total"],
            "personal_material_count": int(personal_count or 0),
            "average_mastery": None,
        },
        "courses": [course_out(course, include_invite=False) for course in courses],
        "hot": recommendations["groups"]["hot"],
        "recommendations": {
            "seed": recommendations["seed"],
            "same_chapter": recommendations["groups"]["same_chapter"],
            "similar": recommendations["groups"]["similar"],
        },
        "recent_personal": recent_personal,
    }
