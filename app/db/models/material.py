"""Course/personal material metadata and RAG indexing state."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import ID_TYPE, Base, PkMixin, TimestampMixin, utc_now

MATERIAL_STATUS_PENDING = "pending"
MATERIAL_STATUS_APPROVED = "approved"
MATERIAL_STATUS_REJECTED = "rejected"
MATERIAL_STATUS_DELETED = "deleted"

MATERIAL_STATUSES = {
    MATERIAL_STATUS_PENDING,
    MATERIAL_STATUS_APPROVED,
    MATERIAL_STATUS_REJECTED,
    MATERIAL_STATUS_DELETED,
}

MATERIAL_SCOPE_COURSE = "course"
MATERIAL_SCOPE_PERSONAL = "personal"

MATERIAL_SCOPES = {MATERIAL_SCOPE_COURSE, MATERIAL_SCOPE_PERSONAL}

INDEX_STATUS_PENDING = "pending"
INDEX_STATUS_INDEXING = "indexing"
INDEX_STATUS_INDEXED = "indexed"
INDEX_STATUS_FAILED = "failed"

INDEX_STATUSES = {
    INDEX_STATUS_PENDING,
    INDEX_STATUS_INDEXING,
    INDEX_STATUS_INDEXED,
    INDEX_STATUS_FAILED,
}

ALLOWED_MATERIAL_SUFFIXES = {
    ".pdf": "application/pdf",
    ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    ".pptx": "application/vnd.openxmlformats-officedocument.presentationml.presentation",
    ".png": "image/png",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
}


class Material(PkMixin, TimestampMixin, Base):
    __tablename__ = "materials"

    scope: Mapped[str] = mapped_column(
        String(16), default=MATERIAL_SCOPE_COURSE, nullable=False, index=True
    )
    course_id: Mapped[int | None] = mapped_column(
        ID_TYPE,
        ForeignKey("courses.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )
    knowledge_base_id: Mapped[int | None] = mapped_column(
        ID_TYPE,
        ForeignKey("knowledge_bases.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    owner_id: Mapped[int | None] = mapped_column(
        ID_TYPE,
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    chapter_id: Mapped[int | None] = mapped_column(
        ID_TYPE,
        ForeignKey("chapters.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    knowledge_id: Mapped[int | None] = mapped_column(
        ID_TYPE,
        ForeignKey("knowledges.id", ondelete="SET NULL"),
        nullable=True,
    )
    uploader_id: Mapped[int] = mapped_column(
        ID_TYPE, ForeignKey("users.id"), nullable=False, index=True
    )
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    source_filename: Mapped[str] = mapped_column(String(255), nullable=False)
    rag_filename: Mapped[str] = mapped_column(String(255), nullable=False)
    file_path: Mapped[str] = mapped_column(String(500), nullable=False)
    file_type: Mapped[str] = mapped_column(String(16), nullable=False)
    file_size: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    vector_doc_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    index_status: Mapped[str] = mapped_column(
        String(16), default=INDEX_STATUS_PENDING, nullable=False, index=True
    )
    index_error: Mapped[str | None] = mapped_column(String(500), nullable=True)
    indexed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    status: Mapped[str] = mapped_column(
        String(16), default=MATERIAL_STATUS_PENDING, nullable=False, index=True
    )
    review_comment: Mapped[str | None] = mapped_column(String(500), nullable=True)
    reviewed_by_id: Mapped[int | None] = mapped_column(
        ID_TYPE, ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    view_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    download_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    course = relationship("Course", lazy="selectin")
    knowledge_base = relationship("KnowledgeBase", lazy="selectin")
    owner = relationship("User", foreign_keys=[owner_id], lazy="selectin")
    chapter = relationship("Chapter", lazy="selectin")
    knowledge = relationship("Knowledge", lazy="selectin")
    uploader = relationship("User", foreign_keys=[uploader_id], lazy="selectin")
    reviewed_by = relationship("User", foreign_keys=[reviewed_by_id], lazy="selectin")


class MaterialView(PkMixin, Base):
    """Latest time a student opened a material.

    One row per (student, material) pair keeps the table bounded while still
    giving home recommendations a stable "most recently browsed" seed.
    """

    __tablename__ = "material_views"
    __table_args__ = (
        UniqueConstraint("user_id", "material_id", name="uq_material_view_user_material"),
    )

    user_id: Mapped[int] = mapped_column(
        ID_TYPE, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    material_id: Mapped[int] = mapped_column(
        ID_TYPE, ForeignKey("materials.id", ondelete="CASCADE"), nullable=False, index=True
    )
    viewed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, nullable=False, index=True
    )

    material = relationship("Material", lazy="selectin")
