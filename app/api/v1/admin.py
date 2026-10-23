"""Administrator governance endpoints: users, roles and audit logs."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import require_permission
from app.core.errors import success
from app.db.models.rbac import User
from app.db.session import get_db
from app.schemas.admin import (
    AdminUserOut,
    AuditLogOut,
    ResetPasswordRequest,
    RoleOut,
    UserCreateRequest,
    UserStatusRequest,
    UserUpdateRequest,
    permission_out,
)
from app.services import user_service
from app.services.audit_service import client_ip, list_audit_logs

router = APIRouter(prefix="/admin", tags=["admin"])


@router.get("/ping")
async def ping(user: User = Depends(require_permission("user:manage"))) -> dict:
    return success({"pong": True, "operator": user.username})


@router.get("/stats")
async def stats(
    user: User = Depends(require_permission("user:manage")),
    db: AsyncSession = Depends(get_db),
) -> dict:
    return success(await user_service.admin_stats(db))


@router.get("/users")
async def list_users(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    keyword: str | None = Query(default=None, max_length=64),
    role: str | None = Query(default=None, max_length=32),
    status_filter: str | None = Query(default=None, alias="status", pattern="^(active|disabled)$"),
    user: User = Depends(require_permission("user:manage")),
    db: AsyncSession = Depends(get_db),
) -> dict:
    items, total = await user_service.list_users(
        db,
        page=page,
        page_size=page_size,
        keyword=keyword,
        role=role,
        status=status_filter,
    )
    return success(
        {
            "items": [AdminUserOut.from_user(item).model_dump() for item in items],
            "total": total,
            "page": page,
            "page_size": page_size,
        }
    )


@router.post("/users", status_code=status.HTTP_201_CREATED)
async def create_user(
    body: UserCreateRequest,
    request: Request,
    user: User = Depends(require_permission("user:manage")),
    db: AsyncSession = Depends(get_db),
) -> dict:
    created = await user_service.create_user(
        db,
        user,
        username=body.username,
        password=body.password,
        role_name=body.role,
        email=body.email,
        ip=client_ip(request),
    )
    return success(AdminUserOut.from_user(created).model_dump(), "用户创建成功")


@router.put("/users/{user_id}")
async def update_user(
    user_id: int,
    body: UserUpdateRequest,
    request: Request,
    user: User = Depends(require_permission("user:manage")),
    db: AsyncSession = Depends(get_db),
) -> dict:
    target = await user_service.get_user(db, user_id)
    updated = await user_service.update_user(
        db,
        user,
        target,
        role_name=body.role,
        email=body.email,
        update_email="email" in body.model_fields_set,
        ip=client_ip(request),
    )
    return success(AdminUserOut.from_user(updated).model_dump(), "用户信息已更新")


@router.put("/users/{user_id}/status")
async def update_user_status(
    user_id: int,
    body: UserStatusRequest,
    request: Request,
    user: User = Depends(require_permission("user:manage")),
    db: AsyncSession = Depends(get_db),
) -> dict:
    target = await user_service.get_user(db, user_id)
    updated = await user_service.set_user_status(
        db,
        user,
        target,
        status=body.status,
        ip=client_ip(request),
    )
    message = "账号已启用" if updated.status == "active" else "账号已禁用"
    return success(AdminUserOut.from_user(updated).model_dump(), message)


@router.post("/users/{user_id}/reset-password")
async def reset_password(
    user_id: int,
    body: ResetPasswordRequest,
    request: Request,
    user: User = Depends(require_permission("user:manage")),
    db: AsyncSession = Depends(get_db),
) -> dict:
    target = await user_service.get_user(db, user_id)
    await user_service.reset_user_password(
        db,
        user,
        target,
        new_password=body.new_password,
        ip=client_ip(request),
    )
    return success({"reset": True, "user_id": target.id}, "密码已重置，请通知用户重新登录")


@router.get("/roles")
async def roles(
    user: User = Depends(require_permission("role:manage")),
    db: AsyncSession = Depends(get_db),
) -> dict:
    roles_list, permissions_list, counts = await user_service.roles_overview(db)
    return success(
        {
            "roles": [
                RoleOut.from_role(role, counts.get(role.id, 0)).model_dump() for role in roles_list
            ],
            "permissions": [
                permission_out(permission).model_dump() for permission in permissions_list
            ],
        }
    )


@router.get("/audit-logs")
async def audit_logs(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    keyword: str | None = Query(default=None, max_length=64),
    action: str | None = Query(default=None, max_length=64),
    status_filter: str | None = Query(default=None, alias="status", pattern="^(success|failure)$"),
    target_type: str | None = Query(default=None, max_length=32),
    username: str | None = Query(default=None, max_length=32),
    user: User = Depends(require_permission("audit:view")),
    db: AsyncSession = Depends(get_db),
) -> dict:
    items, total = await list_audit_logs(
        db,
        page=page,
        page_size=page_size,
        keyword=keyword,
        action=action,
        status=status_filter,
        target_type=target_type,
        username=username,
    )
    return success(
        {
            "items": [AuditLogOut.model_validate(item).model_dump() for item in items],
            "total": total,
            "page": page,
            "page_size": page_size,
        }
    )
