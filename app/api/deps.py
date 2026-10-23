"""Shared FastAPI dependencies: current user and authorisation guards."""

from __future__ import annotations

from collections.abc import Callable

from fastapi import Depends, Header
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.errors import AuthError, ForbiddenError
from app.core.security import decode_access_token
from app.db.models.rbac import Role, User
from app.db.session import get_db


async def get_current_user(
    authorization: str | None = Header(None),
    db: AsyncSession = Depends(get_db),
) -> User:
    scheme, _, token = (authorization or "").partition(" ")
    if scheme.lower() != "bearer" or not token:
        raise AuthError("请携带 Bearer 令牌")

    payload = decode_access_token(token)
    try:
        user_id = int(payload["sub"])
    except (KeyError, TypeError, ValueError) as exc:
        raise AuthError("无效的登录凭证") from exc

    user = await db.scalar(
        select(User)
        .options(selectinload(User.role).selectinload(Role.permissions))
        .where(User.id == user_id)
    )
    if user is None:
        raise AuthError("用户不存在")
    if user.status != "active":
        raise AuthError("账号已被禁用，请联系管理员")
    if int(payload.get("ver", -1)) != user.token_version:
        raise AuthError("登录状态已失效，请重新登录")
    return user


def require_permission(code: str) -> Callable:
    async def dependency(user: User = Depends(get_current_user)) -> User:
        if code not in {permission.code for permission in user.role.permissions}:
            raise ForbiddenError(f"缺少权限：{code}")
        return user

    return dependency


def require_role(*role_names: str) -> Callable:
    async def dependency(user: User = Depends(get_current_user)) -> User:
        if user.role.name not in role_names:
            raise ForbiddenError("当前角色无权访问该资源")
        return user

    return dependency
