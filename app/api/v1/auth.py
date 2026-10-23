"""Authentication endpoints."""

from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.core.errors import success
from app.db.models.rbac import User
from app.db.session import get_db
from app.schemas.auth import (
    ChangePasswordRequest,
    LoginRequest,
    LoginResponse,
    UserOut,
)
from app.services.auth_service import authenticate, change_password, issue_token

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/login")
async def login(body: LoginRequest, db: AsyncSession = Depends(get_db)) -> dict:
    user = await authenticate(db, body.username, body.password)
    token, expires_in = issue_token(user)
    payload = LoginResponse(
        access_token=token,
        expires_in=expires_in,
        user=UserOut.from_user(user),
    )
    return success(payload.model_dump())


@router.get("/me")
async def me(user: User = Depends(get_current_user)) -> dict:
    return success(UserOut.from_user(user).model_dump())


@router.put("/password")
async def update_password(
    body: ChangePasswordRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    await change_password(db, user, body.old_password, body.new_password)
    return success(
        {"changed": True, "relogin_required": True},
        "密码已修改，请使用新密码重新登录",
    )
