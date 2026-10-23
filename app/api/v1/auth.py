"""Authentication endpoints."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.core.errors import AuthError, success
from app.db.models.audit import AUDIT_STATUS_FAILURE
from app.db.models.rbac import User
from app.db.session import get_db
from app.schemas.auth import (
    ChangePasswordRequest,
    LoginRequest,
    LoginResponse,
    RegisterRequest,
    UserOut,
)
from app.services.audit_service import (
    ACTION_LOGIN_FAILED,
    ACTION_LOGIN_SUCCESS,
    client_ip,
    record_audit_safely,
)
from app.services.auth_service import (
    authenticate,
    change_password,
    issue_token,
    register_student,
)

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", status_code=201)
async def register(body: RegisterRequest, db: AsyncSession = Depends(get_db)) -> dict:
    user = await register_student(
        db,
        username=body.username,
        password=body.password,
        email=body.email,
    )
    token, expires_in = issue_token(user)
    payload = LoginResponse(
        access_token=token,
        expires_in=expires_in,
        user=UserOut.from_user(user),
    )
    return success(payload.model_dump(), "注册成功")


@router.post("/login")
async def login(
    body: LoginRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> dict:
    try:
        user = await authenticate(db, body.username, body.password)
    except AuthError as exc:
        await record_audit_safely(
            db,
            action=ACTION_LOGIN_FAILED,
            username=body.username,
            target_type="user",
            detail={"reason": exc.message},
            ip=client_ip(request),
            status=AUDIT_STATUS_FAILURE,
        )
        raise

    token, expires_in = issue_token(user)
    payload = LoginResponse(
        access_token=token,
        expires_in=expires_in,
        user=UserOut.from_user(user),
    )
    # Build the response before writing the audit row so an audit failure can
    # never invalidate objects needed by the successful login response.
    await record_audit_safely(
        db,
        action=ACTION_LOGIN_SUCCESS,
        actor=user,
        target_type="user",
        target_id=user.id,
        ip=client_ip(request),
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
