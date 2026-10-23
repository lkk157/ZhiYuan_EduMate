"""Authentication and account security business logic."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.config import get_settings
from app.core.errors import AuthError, ValidationError
from app.core.security import create_access_token, hash_password, verify_password
from app.db.base import utc_now
from app.db.models.rbac import Role, User

USER_WITH_PERMISSIONS = selectinload(User.role).selectinload(Role.permissions)


async def get_user_by_username(db: AsyncSession, username: str) -> User | None:
    return await db.scalar(
        select(User).options(USER_WITH_PERMISSIONS).where(User.username == username)
    )


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
