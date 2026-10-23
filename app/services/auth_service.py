"""Authentication and account security business logic."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.config import get_settings
from app.core.errors import (
    AuthError,
    ConflictError,
    ServiceUnavailableError,
    ValidationError,
)
from app.core.security import (
    create_access_token,
    hash_password,
    normalize_username,
    verify_password,
)
from app.db.base import utc_now
from app.db.models.rbac import ROLE_STUDENT, USER_STATUS_ACTIVE, Role, User

USER_WITH_PERMISSIONS = selectinload(User.role).selectinload(Role.permissions)


async def get_user_by_username(db: AsyncSession, username: str) -> User | None:
    return await db.scalar(
        select(User)
        .options(USER_WITH_PERMISSIONS)
        .where(User.username == normalize_username(username))
    )


async def register_student(
    db: AsyncSession,
    *,
    username: str,
    password: str,
    email: str | None = None,
) -> User:
    """Self-registration is limited to the student role."""
    normalized = normalize_username(username)
    if await db.scalar(select(User).where(User.username == normalized)):
        raise ConflictError("用户名已被注册")

    if email:
        if await db.scalar(select(User).where(User.email == email)):
            raise ConflictError("邮箱已被注册")

    role = await db.scalar(
        select(Role).options(selectinload(Role.permissions)).where(Role.name == ROLE_STUDENT)
    )
    if role is None:
        raise ServiceUnavailableError("学生角色未初始化，请联系管理员")

    user = User(
        username=normalized,
        email=email,
        password_hash=hash_password(password),
        role=role,
        status=USER_STATUS_ACTIVE,
    )
    db.add(user)
    try:
        await db.commit()
    except IntegrityError as exc:
        await db.rollback()
        raise ConflictError("用户名或邮箱已被注册") from exc
    return user


async def authenticate(db: AsyncSession, username: str, password: str) -> User:
    user = await get_user_by_username(db, username)
    if user is None or not verify_password(password, user.password_hash):
        # Same message for unknown user and wrong password to prevent enumeration.
        raise AuthError("用户名或密码错误")

    if user.status != "active":
        raise AuthError("账号已被禁用，请联系管理员")

    user.last_login_at = utc_now()
    await db.commit()
    return user


def issue_token(user: User) -> tuple[str, int]:
    settings = get_settings()
    token = create_access_token(
        user_id=user.id,
        username=user.username,
        role=user.role.name,
        token_version=user.token_version,
    )
    return token, settings.access_token_expire_minutes * 60


async def change_password(
    db: AsyncSession, user: User, old_password: str, new_password: str
) -> None:
    if not verify_password(old_password, user.password_hash):
        raise AuthError("原密码不正确")
    if old_password == new_password:
        raise ValidationError("新密码不能与原密码相同")

    user.password_hash = hash_password(new_password)
    user.token_version += 1
    await db.commit()


def permission_codes(user: User) -> list[str]:
    return sorted(permission.code for permission in user.role.permissions)
