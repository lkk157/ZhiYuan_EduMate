"""Course hierarchy, invitation codes and student enrollment."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import ID_TYPE, Base, PkMixin, TimestampMixin

COURSE_STATUS_DRAFT = "draft"
COURSE_STATUS_PENDING = "pending"
COURSE_STATUS_APPROVED = "approved"
COURSE_STATUS_REJECTED = "rejected"

COURSE_STATUSES = {
    COURSE_STATUS_DRAFT,
    COURSE_STATUS_PENDING,
    COURSE_STATUS_APPROVED,
    COURSE_STATUS_REJECTED,
}
# Published courses stay editable so teachers can keep chapters, knowledge
# points and materials current without republishing the course.
COURSE_EDITABLE_STATUSES = {
    COURSE_STATUS_DRAFT,
    COURSE_STATUS_REJECTED,
    COURSE_STATUS_APPROVED,
}
COURSE_SUBMITTABLE_STATUSES = {COURSE_STATUS_DRAFT, COURSE_STATUS_REJECTED}

ENROLLMENT_SOURCE_INVITE = "invite_code"
ENROLLMENT_SOURCE_TEACHER = "teacher_add"


class Course(PkMixin, TimestampMixin, Base):
    __tablename__ = "courses"

    title: Mapped[str] = mapped_column(String(100), nullable=False)
    description: Mapped[str | None] = mapped_column(String(2000), nullable=True)
    cover_url: Mapped[str | None] = mapped_column(String(255), nullable=True)
    teacher_id: Mapped[int] = mapped_column(
        ID_TYPE, ForeignKey("users.id"), nullable=False, index=True
    )
    rag_group_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    invite_code: Mapped[str] = mapped_column(String(16), unique=True, nullable=False, index=True)
    invite_enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    status: Mapped[str] = mapped_column(
        String(16), default=COURSE_STATUS_DRAFT, nullable=False, index=True
    )
    review_comment: Mapped[str | None] = mapped_column(String(500), nullable=True)
    submitted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    reviewed_by_id: Mapped[int | None] = mapped_column(
        ID_TYPE, ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    teacher = relationship("User", foreign_keys=[teacher_id], lazy="selectin")
    reviewed_by = relationship("User", foreign_keys=[reviewed_by_id], lazy="selectin")
    chapters: Mapped[list[Chapter]] = relationship(
        back_populates="course",
        cascade="all, delete-orphan",
        order_by="Chapter.order_no, Chapter.id",
        lazy="selectin",
    )
    enrollments: Mapped[list[CourseEnrollment]] = relationship(
        back_populates="course",
        cascade="all, delete-orphan",
        order_by="CourseEnrollment.created_at",
        lazy="selectin",
    )


class Chapter(PkMixin, TimestampMixin, Base):
    __tablename__ = "chapters"

    course_id: Mapped[int] = mapped_column(
        ID_TYPE,
        ForeignKey("courses.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    title: Mapped[str] = mapped_column(String(100), nullable=False)
    description: Mapped[str | None] = mapped_column(String(500), nullable=True)
    order_no: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    course: Mapped[Course] = relationship(back_populates="chapters")
    knowledges: Mapped[list[Knowledge]] = relationship(
        back_populates="chapter",
        cascade="all, delete-orphan",
        order_by="Knowledge.id",
        lazy="selectin",
    )


class Knowledge(PkMixin, TimestampMixin, Base):
    __tablename__ = "knowledges"

    course_id: Mapped[int] = mapped_column(
        ID_TYPE,
        ForeignKey("courses.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    chapter_id: Mapped[int] = mapped_column(
        ID_TYPE,
        ForeignKey("chapters.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    description: Mapped[str | None] = mapped_column(String(500), nullable=True)
    difficulty: Mapped[int] = mapped_column(Integer, default=3, nullable=False)

    chapter: Mapped[Chapter] = relationship(back_populates="knowledges")


class CourseEnrollment(PkMixin, TimestampMixin, Base):
    __tablename__ = "course_enrollments"
    __table_args__ = (UniqueConstraint("course_id", "student_id", name="uq_course_enrollment"),)

    course_id: Mapped[int] = mapped_column(
        ID_TYPE,
        ForeignKey("courses.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    student_id: Mapped[int] = mapped_column(
        ID_TYPE,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    source: Mapped[str] = mapped_column(
        String(16), default=ENROLLMENT_SOURCE_INVITE, nullable=False
    )

    course: Mapped[Course] = relationship(back_populates="enrollments")
    student = relationship("User", foreign_keys=[student_id], lazy="selectin")
