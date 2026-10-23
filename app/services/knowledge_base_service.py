"""Personal knowledge base CRUD and owner isolation."""

from __future__ import annotations

from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import ConflictError, NotFoundError
from app.db.models.knowledge_base import (
    KB_STATUS_ACTIVE,
    KB_STATUS_DELETED,
    KnowledgeBase,
)
from app.db.models.material import (
    INDEX_STATUS_INDEXED,
    MATERIAL_SCOPE_PERSONAL,
    MATERIAL_STATUS_DELETED,
    Material,
)
from app.db.models.rbac import User
from app.services.audit_service import (
    ACTION_KB_CREATE,
    ACTION_KB_DELETE,
    ACTION_KB_UPDATE,
    record_audit,
)
from app.services.material_service import MATERIAL_LOAD

DEFAULT_KB_NAME = "我的知识库"
DEFAULT_KB_DESCRIPTION = "个人学习资料默认知识库"


async def ensure_default_kb(db: AsyncSession, owner: User) -> KnowledgeBase:
    existing = await db.scalar(
        select(KnowledgeBase).where(
            KnowledgeBase.owner_id == owner.id,
            KnowledgeBase.status == KB_STATUS_ACTIVE,
            KnowledgeBase.is_default.is_(True),
        )
    )
    if existing is not None:
        return existing

    kb = KnowledgeBase(
        owner=owner,
        name=DEFAULT_KB_NAME,
        description=DEFAULT_KB_DESCRIPTION,
        is_default=True,
        status=KB_STATUS_ACTIVE,
    )
    db.add(kb)
    await db.commit()
    return kb


async def list_knowledge_bases(
    db: AsyncSession, owner: User
) -> list[tuple[KnowledgeBase, int, int]]:
    await ensure_default_kb(db, owner)
    result = await db.scalars(
        select(KnowledgeBase)
        .where(
            KnowledgeBase.owner_id == owner.id,
            KnowledgeBase.status == KB_STATUS_ACTIVE,
        )
        .order_by(KnowledgeBase.is_default.desc(), KnowledgeBase.created_at.asc())
    )
    kbs = list(result)
    if not kbs:
        return []

    counts: dict[int, list[int]] = {}
    rows = await db.execute(
        select(
            Material.knowledge_base_id,
            Material.index_status,
            func.count(Material.id),
        )
        .where(
            Material.scope == MATERIAL_SCOPE_PERSONAL,
            Material.status != MATERIAL_STATUS_DELETED,
            Material.knowledge_base_id.in_([kb.id for kb in kbs]),
        )
        .group_by(Material.knowledge_base_id, Material.index_status)
    )
    for kb_id, index_status, count in rows.all():
        bucket = counts.setdefault(int(kb_id), [0, 0])
        bucket[0] += int(count)
        if index_status == INDEX_STATUS_INDEXED:
            bucket[1] += int(count)

    return [(kb, counts.get(kb.id, [0, 0])[0], counts.get(kb.id, [0, 0])[1]) for kb in kbs]


async def get_owned_kb(db: AsyncSession, owner: User, kb_id: int) -> KnowledgeBase:
    kb = await db.scalar(
        select(KnowledgeBase).where(
            KnowledgeBase.id == kb_id,
            KnowledgeBase.owner_id == owner.id,
            KnowledgeBase.status == KB_STATUS_ACTIVE,
        )
    )
    if kb is None:
        # 404 also hides other owners' knowledge bases.
        raise NotFoundError("知识库不存在")
    return kb


async def _name_taken(
    db: AsyncSession, owner_id: int, name: str, *, exclude_id: int | None = None
) -> bool:
    stmt = select(KnowledgeBase.id).where(
        KnowledgeBase.owner_id == owner_id,
        KnowledgeBase.status == KB_STATUS_ACTIVE,
        func.lower(KnowledgeBase.name) == name.strip().lower(),
    )
    if exclude_id is not None:
        stmt = stmt.where(KnowledgeBase.id != exclude_id)
    return bool(await db.scalar(stmt))


async def create_knowledge_base(
    db: AsyncSession,
    owner: User,
    *,
    name: str,
    description: str | None = None,
    ip: str | None = None,
) -> KnowledgeBase:
    if await _name_taken(db, owner.id, name):
        raise ConflictError("知识库名称已存在")
    kb = KnowledgeBase(
        owner=owner,
        name=name.strip(),
        description=(description or "").strip() or None,
        is_default=False,
        status=KB_STATUS_ACTIVE,
    )
    db.add(kb)
    await db.flush()
    await record_audit(
        db,
        action=ACTION_KB_CREATE,
        actor=owner,
        target_type="knowledge_base",
        target_id=kb.id,
        detail={"name": kb.name},
        ip=ip,
    )
    await db.commit()
    return kb


async def update_knowledge_base(
    db: AsyncSession,
    owner: User,
    kb: KnowledgeBase,
    *,
    changes: dict[str, Any],
    ip: str | None = None,
) -> KnowledgeBase:
    applied: dict[str, Any] = {}
    if "name" in changes and changes["name"]:
        new_name = changes["name"].strip()
        if new_name != kb.name:
            if await _name_taken(db, owner.id, new_name, exclude_id=kb.id):
                raise ConflictError("知识库名称已存在")
            applied["name"] = {"from": kb.name, "to": new_name}
            kb.name = new_name
    if "description" in changes:
        new_description = (changes["description"] or "").strip() or None
        if new_description != kb.description:
            applied["description"] = new_description
            kb.description = new_description

    if applied:
        await record_audit(
            db,
            action=ACTION_KB_UPDATE,
            actor=owner,
            target_type="knowledge_base",
            target_id=kb.id,
            detail={"name": kb.name, "changes": applied},
            ip=ip,
        )
    await db.commit()
    return kb


async def soft_delete_knowledge_base(
    db: AsyncSession,
    owner: User,
    kb: KnowledgeBase,
    *,
    ip: str | None = None,
) -> None:
    if kb.is_default:
        raise ConflictError("默认知识库不可删除")
    kb.status = KB_STATUS_DELETED
    await record_audit(
        db,
        action=ACTION_KB_DELETE,
        actor=owner,
        target_type="knowledge_base",
        target_id=kb.id,
        detail={"name": kb.name},
        ip=ip,
    )
    await db.commit()


async def list_personal_materials(
    db: AsyncSession,
    kb: KnowledgeBase,
    *,
    page: int = 1,
    page_size: int = 20,
    index_status: str | None = None,
) -> tuple[list[Material], int]:
    conditions = [
        Material.scope == MATERIAL_SCOPE_PERSONAL,
        Material.knowledge_base_id == kb.id,
        Material.status != MATERIAL_STATUS_DELETED,
    ]
    if index_status:
        conditions.append(Material.index_status == index_status)

    total = await db.scalar(select(func.count(Material.id)).where(*conditions))
    result = await db.scalars(
        select(Material)
        .options(*MATERIAL_LOAD)
        .where(*conditions)
        .order_by(Material.created_at.desc(), Material.id.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    return list(result), int(total or 0)
