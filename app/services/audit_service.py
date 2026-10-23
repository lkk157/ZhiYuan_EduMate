"""Audit trail helpers: redaction, writing and querying."""

from __future__ import annotations

import logging
from typing import Any

from fastapi import Request
from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.audit import AUDIT_STATUS_SUCCESS, AuditLog
from app.db.models.rbac import User

logger = logging.getLogger(__name__)

ACTION_LOGIN_SUCCESS = "auth.login.success"
ACTION_LOGIN_FAILED = "auth.login.failed"
ACTION_USER_CREATE = "user.create"
ACTION_USER_UPDATE = "user.update"
ACTION_USER_ENABLE = "user.enable"
ACTION_USER_DISABLE = "user.disable"
ACTION_USER_PASSWORD_RESET = "user.password.reset"
ACTION_COURSE_CREATE = "course.create"
ACTION_COURSE_UPDATE = "course.update"
ACTION_COURSE_SUBMIT = "course.submit"
ACTION_COURSE_APPROVE = "course.approve"
ACTION_COURSE_REJECT = "course.reject"
ACTION_COURSE_INVITE_ROTATE = "course.invite.rotate"
ACTION_COURSE_INVITE_TOGGLE = "course.invite.toggle"
ACTION_COURSE_STUDENT_ADD = "course.student.add"
ACTION_COURSE_STUDENT_REMOVE = "course.student.remove"
ACTION_COURSE_JOIN = "course.join"
ACTION_MATERIAL_UPLOAD = "material.upload"
ACTION_MATERIAL_APPROVE = "material.approve"
ACTION_MATERIAL_REJECT = "material.reject"
ACTION_MATERIAL_INDEX_RETRY = "material.index.retry"
ACTION_MATERIAL_DELETE = "material.delete"
ACTION_KB_CREATE = "knowledge_base.create"
ACTION_KB_UPDATE = "knowledge_base.update"
ACTION_KB_DELETE = "knowledge_base.delete"

SENSITIVE_KEYS = {
    "password",
    "old_password",
    "new_password",
    "confirm_password",
    "password_hash",
    "token",
    "access_token",
    "refresh_token",
    "secret",
    "secret_key",
    "api_key",
    "apikey",
    "authorization",
    "credential",
    "credentials",
}

MASK = "***"


def _is_sensitive(key: str) -> bool:
    normalized = key.strip().lower().replace("-", "_")
    return (
        normalized in SENSITIVE_KEYS
        or normalized.endswith("_password")
        or normalized.endswith("_token")
        or normalized.endswith("_secret")
        or normalized.endswith("_api_key")
    )


def redact_sensitive(value: Any) -> Any:
    """Recursively mask credential-like fields before persisting audit details."""
    if isinstance(value, dict):
        return {
            key: MASK if _is_sensitive(str(key)) else redact_sensitive(item)
            for key, item in value.items()
        }
    if isinstance(value, (list, tuple)):
        return [redact_sensitive(item) for item in value]
    return value


def client_ip(request: Request | None) -> str | None:
    if request is None or request.client is None:
        return None
    return request.client.host


async def record_audit(
    db: AsyncSession,
    *,
    action: str,
    actor: User | None = None,
    username: str | None = None,
    target_type: str | None = None,
    target_id: int | str | None = None,
    detail: dict[str, Any] | None = None,
    ip: str | None = None,
    status: str = AUDIT_STATUS_SUCCESS,
    commit: bool = False,
) -> AuditLog:
    """Add an audit row.

    ``commit=False`` lets callers commit the business change and its audit row
    atomically. Callers that already committed (for example login) pass
    ``commit=True``.
    """
    entry = AuditLog(
        user_id=actor.id if actor is not None else None,
        username=(actor.username if actor is not None else username),
        action=action,
        target_type=target_type,
        target_id=str(target_id) if target_id is not None else None,
        detail=redact_sensitive(detail) if detail is not None else None,
        ip=ip,
        status=status,
    )
    db.add(entry)
    if commit:
        await db.commit()
    return entry


async def record_audit_safely(
    db: AsyncSession,
    *,
    action: str,
    actor: User | None = None,
    username: str | None = None,
    target_type: str | None = None,
    target_id: int | str | None = None,
    detail: dict[str, Any] | None = None,
    ip: str | None = None,
    status: str = AUDIT_STATUS_SUCCESS,
) -> None:
    """Best-effort audit write used on paths where auditing must not block."""
    try:
        await record_audit(
            db,
            action=action,
            actor=actor,
            username=username,
            target_type=target_type,
            target_id=target_id,
            detail=detail,
            ip=ip,
            status=status,
            commit=True,
        )
    except Exception:  # noqa: BLE001 - auditing must never break authentication
        logger.exception("failed to write audit log for action %s", action)
        try:
            await db.rollback()
        except Exception:  # noqa: BLE001
            logger.exception("failed to rollback after audit failure")


async def list_audit_logs(
    db: AsyncSession,
    *,
    page: int = 1,
    page_size: int = 20,
    keyword: str | None = None,
    action: str | None = None,
    status: str | None = None,
    target_type: str | None = None,
    username: str | None = None,
) -> tuple[list[AuditLog], int]:
    conditions = []
    if keyword and keyword.strip():
        pattern = f"%{keyword.strip().lower()}%"
        conditions.append(
            or_(
                func.lower(AuditLog.username).like(pattern),
                func.lower(AuditLog.action).like(pattern),
                func.lower(func.coalesce(AuditLog.target_type, "")).like(pattern),
            )
        )
    if action:
        conditions.append(AuditLog.action == action)
    if status:
        conditions.append(AuditLog.status == status)
    if target_type:
        conditions.append(AuditLog.target_type == target_type)
    if username:
        conditions.append(AuditLog.username == username.strip().lower())

    total = await db.scalar(select(func.count()).select_from(AuditLog).where(*conditions))
    result = await db.scalars(
        select(AuditLog)
        .where(*conditions)
        .order_by(AuditLog.created_at.desc(), AuditLog.id.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    items = list(result)
    for item in items:
        item.detail = redact_sensitive(item.detail) if item.detail else item.detail
    return items, int(total or 0)
