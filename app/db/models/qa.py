"""RAG question-answer records with citations."""

from __future__ import annotations

from typing import Any

from sqlalchemy import JSON, Boolean, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import ID_TYPE, Base, PkMixin, TimestampMixin

QA_STATUS_SUCCESS = "success"
QA_STATUS_DEGRADED = "degraded"

QA_STATUSES = {QA_STATUS_SUCCESS, QA_STATUS_DEGRADED}

QA_SCOPE_COURSE = "course"
QA_SCOPE_PERSONAL = "personal"
QA_SCOPE_ALL = "all"

QA_SCOPES = {QA_SCOPE_COURSE, QA_SCOPE_PERSONAL, QA_SCOPE_ALL}


class QARecord(PkMixin, TimestampMixin, Base):
    __tablename__ = "qa_records"

    user_id: Mapped[int] = mapped_column(
        ID_TYPE, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    course_id: Mapped[int | None] = mapped_column(
        ID_TYPE,
        ForeignKey("courses.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    knowledge_base_id: Mapped[int | None] = mapped_column(
        ID_TYPE,
        ForeignKey("knowledge_bases.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    scope: Mapped[str] = mapped_column(String(16), nullable=False)
    question: Mapped[str] = mapped_column(String(2000), nullable=False)
    answer: Mapped[str] = mapped_column(Text, nullable=False)
    references_json: Mapped[list[dict[str, Any]]] = mapped_column(
        JSON, default=list, nullable=False
    )
    hit: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    intent: Mapped[str | None] = mapped_column(String(32), nullable=True)
    scope_note: Mapped[str | None] = mapped_column(String(500), nullable=True)
    latency_ms: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    status: Mapped[str] = mapped_column(
        String(16), default=QA_STATUS_SUCCESS, nullable=False, index=True
    )

    course = relationship("Course", lazy="selectin")
    knowledge_base = relationship("KnowledgeBase", lazy="selectin")
