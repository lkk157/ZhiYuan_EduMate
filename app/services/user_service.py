"""Administrator-facing user, role and audit business logic."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from sqlalchemy import func, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.errors import ConflictError, NotFoundError, ValidationError
from app.core.security import hash_password, normalize_username
from app.db.models.audit import AuditLog
from app.db.models.rbac import (
    ROLE_ADMIN,
    USER_STATUS_ACTIVE,
    USER_STATUS_DISABLED,
    Permission,
    Role,
    User,
)
from app.services.audit_service import (
    ACTION_USER_CREATE,
    ACTION_USER_DISABLE,
    ACTION_USER_ENABLE,
    ACTION_USER_PASSWORD_RESET,
    ACTION_USER_UPDATE,
    record_audit,
)

USER_WITH_PERMISSIONS = selectinload(User.role).selectinload(Role.permissions)


async def _get_role(db: AsyncSession, name: str) -> Role:
    role = await db.scalar(
        select(Role).options(selectinload(Role.permissions)).where(Role.name == name)
    )
    if role is None:
        raise ValidationError("角色不存在")
    return role


async def get_user(db: AsyncSession, user_id: int) -> User:
    user = await db.scalar(select(User).options(USER_WITH_PERMISSIONS).where(User.id == user_id))
    if user is None:
        raise NotFoundError("用户不存在")
    return user


async def _count_active_admins(db: AsyncSession) -> int:
    total = await db.scalar(
        select(func.count(User.id))
        .select_from(User)
        .join(Role, User.role_id == Role.id)
        .where(Role.name == ROLE_ADMIN, User.status == USER_STATUS_ACTIVE)
    )
    return int(total or 0)


async def list_users(
    db: AsyncSession,
    *,
    page: int = 1,
    page_size: int = 20,
    keyword: str | None = None,
    role: str | None = None,
    status: str | None = None,
) -> tuple[list[User], int]:
    conditions = []
    if keyword and keyword.strip():
        pattern = f"%{keyword.strip().lower()}%"
        conditions.append(
            or_(
                User.username.like(pattern),
                func.lower(func.coalesce(User.email, "")).like(pattern),
            )
        )
    if status:
        conditions.append(User.status == status)

    count_stmt = select(func.count(User.id)).select_from(User)
    list_stmt = select(User).options(USER_WITH_PERMISSIONS)
    if role:
        count_stmt = count_stmt.join(Role, User.role_id == Role.id).where(Role.name == role)
        list_stmt = list_stmt.join(Role, User.role_id == Role.id).where(Role.name == role)

    total = await db.scalar(count_stmt.where(*conditions))
    result = await db.scalars(
        list_stmt.where(*conditions)
        .order_by(User.created_at.desc(), User.id.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    return list(result), int(total or 0)


async def create_user(
    db: AsyncSession,
    actor: User,
    *,
    username: str,
    password: str,
    role_name: str,
    email: str | None = None,
    ip: str | None = None,
) -> User:
    normalized = normalize_username(username)
    normalized_email = email.strip().lower() if email and email.strip() else None

    if await db.scalar(select(User.id).where(User.username == normalized)):
        raise ConflictError("用户名已被注册")
    if normalized_email and await db.scalar(select(User.id).where(User.email == normalized_email)):
        raise ConflictError("邮箱已被注册")

    role = await _get_role(db, role_name)
    user = User(
        username=normalized,
        email=normalized_email,
        password_hash=hash_password(password),
        role=role,
        status=USER_STATUS_ACTIVE,
    )
    db.add(user)
    try:
        await db.flush()
    except IntegrityError as exc:
        await db.rollback()
        raise ConflictError("用户名或邮箱已被注册") from exc

    await record_audit(
        db,
        action=ACTION_USER_CREATE,
        actor=actor,
        target_type="user",
        target_id=user.id,
        detail={"username": user.username, "role": role.name, "email": normalized_email},
        ip=ip,
    )
    try:
        await db.commit()
    except IntegrityError as exc:
        await db.rollback()
        raise ConflictError("用户名或邮箱已被注册") from exc
    return user


async def update_user(
    db: AsyncSession,
    actor: User,
    target: User,
    *,
    role_name: str | None = None,
    email: str | None = None,
    update_email: bool = False,
    ip: str | None = None,
) -> User:
    changes: dict[str, Any] = {}

    if role_name and role_name != target.role.name:
        if (
            target.role.name == ROLE_ADMIN
            and target.status == USER_STATUS_ACTIVE
            and await _count_active_admins(db) <= 1
        ):
            raise ConflictError("至少保留一个启用状态的管理员")
        role = await _get_role(db, role_name)
        changes["role"] = {"from": target.role.name, "to": role.name}
        target.role = role
        # A role change alters permissions, so existing tokens must be invalidated.
        target.token_version += 1

    if update_email:
        normalized_email = email.strip().lower() if email and email.strip() else None
        if normalized_email and await db.scalar(
            select(User.id).where(User.email == normalized_email, User.id != target.id)
        ):
            raise ConflictError("邮箱已被注册")
        if normalized_email != target.email:
            changes["email"] = normalized_email
            target.email = normalized_email

    if not changes:
        return target

    await record_audit(
        db,
        action=ACTION_USER_UPDATE,
        actor=actor,
        target_type="user",
        target_id=target.id,
        detail={"username": target.username, "changes": changes},
        ip=ip,
    )
    try:
        await db.commit()
    except IntegrityError as exc:
        await db.rollback()
        raise ConflictError("邮箱已被注册") from exc
    return target


async def set_user_status(
    db: AsyncSession,
    actor: User,
    target: User,
    *,
    status: str,
    ip: str | None = None,
) -> User:
    if status not in {USER_STATUS_ACTIVE, USER_STATUS_DISABLED}:
        raise ValidationError("无效的用户状态")
    if target.status == status:
        return target

    if target.id == actor.id and status == USER_STATUS_DISABLED:
        raise ConflictError("不能禁用自己的账号")
    if (
        status == USER_STATUS_DISABLED
        and target.role.name == ROLE_ADMIN
        and await _count_active_admins(db) <= 1
    ):
        raise ConflictError("至少保留一个启用状态的管理员")

    target.status = status
    if status == USER_STATUS_DISABLED:
        # Defensive: get_current_user already checks status, this also
        # invalidates any token that might be replayed after re-enabling.
        target.token_version += 1

    await record_audit(
        db,
        action=ACTION_USER_ENABLE if status == USER_STATUS_ACTIVE else ACTION_USER_DISABLE,
        actor=actor,
        target_type="user",
        target_id=target.id,
        detail={"username": target.username, "status": status},
        ip=ip,
    )
    await db.commit()
    return target


async def reset_user_password(
    db: AsyncSession,
    actor: User,
    target: User,
    *,
    new_password: str,
    ip: str | None = None,
) -> None:
    target.password_hash = hash_password(new_password)
    target.token_version += 1
    await record_audit(
        db,
        action=ACTION_USER_PASSWORD_RESET,
        actor=actor,
        target_type="user",
        target_id=target.id,
        detail={"username": target.username},
        ip=ip,
    )
    await db.commit()


async def roles_overview(db: AsyncSession) -> tuple[list[Role], list[Permission], dict[int, int]]:
    roles = list(
        await db.scalars(select(Role).options(selectinload(Role.permissions)).order_by(Role.id))
    )
    permissions = list(await db.scalars(select(Permission).order_by(Permission.code)))
    rows = await db.execute(select(User.role_id, func.count(User.id)).group_by(User.role_id))
    counts = {role_id: int(count) for role_id, count in rows.all()}
    return roles, permissions, counts


async def admin_stats(db: AsyncSession) -> dict[str, Any]:
    total_users = await db.scalar(select(func.count(User.id)))
    active_users = await db.scalar(
        select(func.count(User.id)).where(User.status == USER_STATUS_ACTIVE)
    )
    role_rows = await db.execute(
        select(Role.name, func.count(User.id))
        .select_from(Role)
        .outerjoin(User, User.role_id == Role.id)
        .group_by(Role.name)
    )
    role_counts = {name: int(count) for name, count in role_rows.all()}

    start_of_day = datetime.now(UTC).replace(hour=0, minute=0, second=0, microsecond=0)
    today_audits = await db.scalar(
        select(func.count(AuditLog.id)).where(AuditLog.created_at >= start_of_day)
    )
    return {
        "total_users": int(total_users or 0),
        "active_users": int(active_users or 0),
        "role_counts": role_counts,
        "today_audits": int(today_audits or 0),
    }
