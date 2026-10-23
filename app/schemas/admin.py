"""Schemas for the administrator governance endpoints."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.core.security import normalize_username
from app.db.models.audit import AuditLog
from app.db.models.rbac import Permission, Role, User
from app.schemas.auth import EMAIL_PATTERN, UserOut


def _normalize_email(value: str | None) -> str | None:
    if value is None or not value.strip():
        return None
    normalized = value.strip().lower()
    if not EMAIL_PATTERN.match(normalized):
        raise ValueError("邮箱格式不正确")
    return normalized


class UserCreateRequest(BaseModel):
    username: str = Field(min_length=3, max_length=32)
    password: str = Field(min_length=8, max_length=64)
    email: str | None = Field(default=None, max_length=128)
    role: str = Field(default="student", min_length=2, max_length=32)

    @field_validator("username", mode="before")
    @classmethod
    def normalize_name(cls, value: str) -> str:
        return normalize_username(value) if isinstance(value, str) else value

    @field_validator("email")
    @classmethod
    def validate_email(cls, value: str | None) -> str | None:
        return _normalize_email(value)


class UserUpdateRequest(BaseModel):
    email: str | None = Field(default=None, max_length=128)
    role: str | None = Field(default=None, min_length=2, max_length=32)

    @field_validator("email")
    @classmethod
    def validate_email(cls, value: str | None) -> str | None:
        return _normalize_email(value)


class UserStatusRequest(BaseModel):
    status: Literal["active", "disabled"]


class ResetPasswordRequest(BaseModel):
    new_password: str = Field(min_length=8, max_length=64)


class AdminUserOut(UserOut):
    created_at: datetime
    last_login_at: datetime | None = None

    @classmethod
    def from_user(cls, user: User) -> AdminUserOut:
        base = UserOut.from_user(user)
        return cls(
            **base.model_dump(),
            created_at=user.created_at,
            last_login_at=user.last_login_at,
        )


class PermissionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    code: str
    name: str
    description: str | None = None


class RoleOut(BaseModel):
    id: int
    name: str
    description: str | None = None
    user_count: int = 0
    permissions: list[str] = Field(default_factory=list)

    @classmethod
    def from_role(cls, role: Role, user_count: int = 0) -> RoleOut:
        return cls(
            id=role.id,
            name=role.name,
            description=role.description,
            user_count=user_count,
            permissions=sorted(permission.code for permission in role.permissions),
        )


class AuditLogOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: int | None = None
    username: str | None = None
    action: str
    target_type: str | None = None
    target_id: str | None = None
    detail: dict[str, Any] | None = None
    ip: str | None = None
    status: str
    created_at: datetime


def permission_out(permission: Permission) -> PermissionOut:
    return PermissionOut.model_validate(permission)


def audit_out(entry: AuditLog) -> AuditLogOut:
    return AuditLogOut.model_validate(entry)
