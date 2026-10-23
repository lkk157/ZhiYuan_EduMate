"""Audit trail for governance and security-relevant actions."""

from __future__ import annotations

from typing import Any

from sqlalchemy import JSON, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import ID_TYPE, Base, PkMixin, TimestampMixin

AUDIT_STATUS_SUCCESS = "success"
AUDIT_STATUS_FAILURE = "failure"


class AuditLog(PkMixin, TimestampMixin, Base):
    __tablename__ = "audit_logs"

    # Nullable because failed logins may reference an unknown account.
    user_id: Mapped[int | None] = mapped_column(
        ID_TYPE,
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    # Snapshot of the operator (or attempted username) at write time. Keeps the
    # trail readable even if the account is later renamed.
    username: Mapped[str | None] = mapped_column(String(32), nullable=True, index=True)
    action: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    target_type: Mapped[str | None] = mapped_column(String(32), nullable=True)
    target_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    detail: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    ip: Mapped[str | None] = mapped_column(String(64), nullable=True)
    status: Mapped[str] = mapped_column(
        String(16),
        default=AUDIT_STATUS_SUCCESS,
        nullable=False,
        index=True,
    )
