"""Course, chapter, knowledge and enrollment schemas."""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.core.security import normalize_username
from app.db.models.course import Chapter, Course, CourseEnrollment, Knowledge


class CourseCreateRequest(BaseModel):
    title: str = Field(min_length=2, max_length=100)
    description: str | None = Field(default=None, max_length=2000)
    cover_url: str | None = Field(default=None, max_length=255)

    @field_validator("title")
    @classmethod
    def strip_title(cls, value: str) -> str:
        value = value.strip()
        if len(value) < 2:
            raise ValueError("课程标题至少 2 个字符")
        return value


class CourseUpdateRequest(BaseModel):
    title: str | None = Field(default=None, min_length=2, max_length=100)
    description: str | None = Field(default=None, max_length=2000)
    cover_url: str | None = Field(default=None, max_length=255)

    @field_validator("title")
    @classmethod
    def strip_title(cls, value: str | None) -> str | None:
        if value is None:
            return None
        value = value.strip()
        if len(value) < 2:
            raise ValueError("课程标题至少 2 个字符")
        return value


class CourseReviewRequest(BaseModel):
    decision: Literal["approve", "reject"]
    comment: str | None = Field(default=None, max_length=500)

    @model_validator(mode="after")
    def reject_requires_comment(self) -> CourseReviewRequest:
        if self.decision == "reject" and not (self.comment or "").strip():
            raise ValueError("驳回课程时必须填写审核意见")
        return self


class ChapterCreateRequest(BaseModel):
    title: str = Field(min_length=1, max_length=100)
    description: str | None = Field(default=None, max_length=500)
    order_no: int | None = Field(default=None, ge=0)

    @field_validator("title")
    @classmethod
    def strip_title(cls, value: str) -> str:
        return value.strip()


class ChapterUpdateRequest(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=100)
    description: str | None = Field(default=None, max_length=500)
    order_no: int | None = Field(default=None, ge=0)


class KnowledgeCreateRequest(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    description: str | None = Field(default=None, max_length=500)
    difficulty: int = Field(default=3, ge=1, le=5)

    @field_validator("name")
    @classmethod
    def strip_name(cls, value: str) -> str:
        return value.strip()


class KnowledgeUpdateRequest(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=100)
    description: str | None = Field(default=None, max_length=500)
    difficulty: int | None = Field(default=None, ge=1, le=5)


class InviteToggleRequest(BaseModel):
    enabled: bool


class JoinCourseRequest(BaseModel):
    invite_code: str = Field(min_length=4, max_length=16)

    @field_validator("invite_code")
    @classmethod
    def normalize_code(cls, value: str) -> str:
        return value.strip().upper()


class AddStudentRequest(BaseModel):
    username: str = Field(min_length=3, max_length=32)

    @field_validator("username", mode="before")
    @classmethod
    def normalize_name(cls, value: str) -> str:
        return normalize_username(value) if isinstance(value, str) else value


class TeacherBrief(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    username: str


class KnowledgeOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    chapter_id: int
    name: str
    description: str | None = None
    difficulty: int


class ChapterOut(BaseModel):
    id: int
    title: str
    description: str | None = None
    order_no: int
    knowledges: list[KnowledgeOut] = Field(default_factory=list)


class CourseOut(BaseModel):
    id: int
    title: str
    description: str | None = None
    cover_url: str | None = None
    status: str
    teacher: TeacherBrief
    invite_code: str | None = None
    invite_enabled: bool
    review_comment: str | None = None
    submitted_at: datetime | None = None
    reviewed_at: datetime | None = None
    created_at: datetime
    updated_at: datetime
    chapter_count: int
    knowledge_count: int
    student_count: int


class CourseDetailOut(CourseOut):
    chapters: list[ChapterOut] = Field(default_factory=list)


class EnrollmentStudentOut(BaseModel):
    student_id: int
    username: str
    email: str | None = None
    source: str
    enrolled_at: datetime


def knowledge_out(knowledge: Knowledge) -> KnowledgeOut:
    return KnowledgeOut.model_validate(knowledge)


def chapter_out(chapter: Chapter) -> ChapterOut:
    return ChapterOut(
        id=chapter.id,
        title=chapter.title,
        description=chapter.description,
        order_no=chapter.order_no,
        knowledges=[knowledge_out(item) for item in chapter.knowledges],
    )


def course_out(course: Course, *, include_invite: bool, detail: bool = False) -> dict:
    chapters = [chapter_out(chapter) for chapter in course.chapters]
    payload = {
        "id": course.id,
        "title": course.title,
        "description": course.description,
        "cover_url": course.cover_url,
        "status": course.status,
        "teacher": TeacherBrief.model_validate(course.teacher).model_dump(),
        "invite_code": course.invite_code if include_invite else None,
        "invite_enabled": course.invite_enabled,
        "review_comment": course.review_comment,
        "submitted_at": course.submitted_at,
        "reviewed_at": course.reviewed_at,
        "created_at": course.created_at,
        "updated_at": course.updated_at,
        "chapter_count": len(course.chapters),
        "knowledge_count": sum(len(chapter.knowledges) for chapter in course.chapters),
        "student_count": len(course.enrollments),
    }
    if detail:
        return CourseDetailOut(**payload, chapters=chapters).model_dump()
    return CourseOut(**payload).model_dump()


def enrollment_student_out(enrollment: CourseEnrollment) -> EnrollmentStudentOut:
    return EnrollmentStudentOut(
        student_id=enrollment.student_id,
        username=enrollment.student.username,
        email=enrollment.student.email,
        source=enrollment.source,
        enrolled_at=enrollment.created_at,
    )
