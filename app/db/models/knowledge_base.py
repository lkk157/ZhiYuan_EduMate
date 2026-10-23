"""Student-owned personal knowledge bases."""

from __future__ import annotations

from sqlalchemy import Boolean, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import ID_TYPE, Base, PkMixin, TimestampMixin

KB_STATUS_ACTIVE = "active"
KB_STATUS_DELETED = "deleted"

KB_STATUSES = {KB_STATUS_ACTIVE, KB_STATUS_DELETED}


class KnowledgeBase(PkMixin, TimestampMixin, Base):
    __tablename__ = "knowledge_bases"

    owner_id: Mapped[int] = mapped_column(
        ID_TYPE, ForeignKey("users.id"), nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    description: Mapped[str | None] = mapped_column(String(500), nullable=True)
    rag_group_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    is_default: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    status: Mapped[str] = mapped_column(
        String(16), default=KB_STATUS_ACTIVE, nullable=False, index=True
    )

    owner = relationship("User", foreign_keys=[owner_id], lazy="selectin")
