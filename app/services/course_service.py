"""Course hierarchy, review workflow, invitations and enrollment."""

from __future__ import annotations

import logging
import secrets
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.config import get_settings
from app.core.errors import (
    ConflictError,
    ForbiddenError,
    NotFoundError,
    ServiceUnavailableError,
    ValidationError,
)
from app.db.base import utc_now
from app.db.models.course import (
    COURSE_EDITABLE_STATUSES,
    COURSE_STATUS_APPROVED,
    COURSE_STATUS_DRAFT,
    COURSE_STATUS_PENDING,
    COURSE_STATUS_REJECTED,
    COURSE_SUBMITTABLE_STATUSES,
    ENROLLMENT_SOURCE_INVITE,
    ENROLLMENT_SOURCE_TEACHER,
    Chapter,
    Course,
    CourseEnrollment,
    Knowledge,
)
from app.db.models.rbac import ROLE_ADMIN, ROLE_STUDENT, ROLE_TEACHER, User
from app.services.audit_service import (
    ACTION_COURSE_APPROVE,
    ACTION_COURSE_AUTO_APPROVE,
    ACTION_COURSE_CREATE,
    ACTION_COURSE_INVITE_ROTATE,
    ACTION_COURSE_INVITE_TOGGLE,
    ACTION_COURSE_JOIN,
    ACTION_COURSE_REJECT,
    ACTION_COURSE_STUDENT_ADD,
    ACTION_COURSE_STUDENT_REMOVE,
    ACTION_COURSE_SUBMIT,
    ACTION_COURSE_UPDATE,
    record_audit,
)

logger = logging.getLogger(__name__)

INVITE_ALPHABET = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"
INVITE_LENGTH = 8

COURSE_LOAD = (
    selectinload(Course.teacher),
    selectinload(Course.reviewed_by),
    selectinload(Course.chapters).selectinload(Chapter.knowledges),
    selectinload(Course.enrollments).selectinload(CourseEnrollment.student),
)

AUTO_REVIEW_COMMENT = "系统自动审核通过"


def course_auto_review_issue(course: Course) -> str | None:
    """Return why a course needs manual review, or ``None`` when safe."""
    if not get_settings().auto_review_enabled:
        return "自动审核未启用"
    if not (course.description or "").strip():
        return "课程简介不能为空"
    if not course.chapters:
        return "至少需要一个章节"
    titles: set[str] = set()
    knowledge_total = 0
    for chapter in course.chapters:
        title = (chapter.title or "").strip()
        if not title:
            return "章节标题不能为空"
        if title.lower() in titles:
            return "章节标题不能重复"
        titles.add(title.lower())
        knowledge_total += len(chapter.knowledges)
    if knowledge_total == 0:
        return "至少需要一个知识点"
    return None


async def get_course(db: AsyncSession, course_id: int) -> Course:
    course = await db.scalar(select(Course).options(*COURSE_LOAD).where(Course.id == course_id))
    if course is None:
        raise NotFoundError("课程不存在")
    return course


def _is_admin(user: User) -> bool:
    return user.role.name == ROLE_ADMIN


def ensure_manage_access(course: Course, user: User) -> None:
    if _is_admin(user):
        return
    if user.role.name != ROLE_TEACHER or course.teacher_id != user.id:
        raise ForbiddenError("只能管理自己创建的课程")


def ensure_view_access(course: Course, user: User) -> None:
    if _is_admin(user):
        return
    if user.role.name == ROLE_TEACHER:
        if course.teacher_id != user.id:
            raise ForbiddenError("无权访问该课程")
        return
    if user.role.name != ROLE_STUDENT:
        raise ForbiddenError("无权访问该课程")
    if course.status != COURSE_STATUS_APPROVED:
        raise ForbiddenError("课程尚未发布")
    if not any(item.student_id == user.id for item in course.enrollments):
        raise ForbiddenError("请先加入课程")


def ensure_editable(course: Course) -> None:
    if course.status not in COURSE_EDITABLE_STATUSES:
        raise ConflictError("当前状态的课程不可编辑，请等待审核或重新提交")


async def get_accessible_course(
    db: AsyncSession, user: User, course_id: int, *, for_management: bool = False
) -> Course:
    course = await get_course(db, course_id)
    if for_management:
        ensure_manage_access(course, user)
    else:
        ensure_view_access(course, user)
    return course


async def _generate_invite_code(db: AsyncSession) -> str:
    for _ in range(12):
        code = "".join(secrets.choice(INVITE_ALPHABET) for _ in range(INVITE_LENGTH))
        exists = await db.scalar(select(Course.id).where(Course.invite_code == code))
        if not exists:
            return code
    raise ServiceUnavailableError("邀请码生成失败，请稍后重试")


async def list_courses(
    db: AsyncSession,
    user: User,
    *,
    page: int = 1,
    page_size: int = 12,
    keyword: str | None = None,
    status: str | None = None,
) -> tuple[list[Course], int]:
    condition_list = []
    base = select(Course).options(*COURSE_LOAD)
    count_stmt = select(func.count(func.distinct(Course.id))).select_from(Course)

    if user.role.name == ROLE_ADMIN:
        pass
    elif user.role.name == ROLE_TEACHER:
        condition_list.append(Course.teacher_id == user.id)
    else:
        base = base.join(CourseEnrollment, CourseEnrollment.course_id == Course.id)
        count_stmt = count_stmt.join(CourseEnrollment, CourseEnrollment.course_id == Course.id)
        condition_list.append(CourseEnrollment.student_id == user.id)
        condition_list.append(Course.status == COURSE_STATUS_APPROVED)

    if keyword and keyword.strip():
        condition_list.append(Course.title.like(f"%{keyword.strip()}%"))
    if status and user.role.name != ROLE_STUDENT:
        condition_list.append(Course.status == status)

    total = await db.scalar(count_stmt.where(*condition_list))
    result = await db.scalars(
        base.where(*condition_list)
        .order_by(Course.created_at.desc(), Course.id.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    return list(result), int(total or 0)


async def create_course(
    db: AsyncSession,
    teacher: User,
    *,
    title: str,
    description: str | None = None,
    cover_url: str | None = None,
    ip: str | None = None,
) -> Course:
    course = Course(
        title=title,
        description=description or None,
        cover_url=cover_url or None,
        teacher=teacher,
        invite_code=await _generate_invite_code(db),
        invite_enabled=True,
        status=COURSE_STATUS_DRAFT,
    )
    db.add(course)
    await db.flush()
    await record_audit(
        db,
        action=ACTION_COURSE_CREATE,
        actor=teacher,
        target_type="course",
        target_id=course.id,
        detail={"title": course.title},
        ip=ip,
    )
    await db.commit()
    # Re-load eager relationships: a freshly inserted object can still trigger
    # a lazy load (and therefore MissingGreenlet) when serialised.
    return await get_course(db, course.id)


async def update_course(
    db: AsyncSession,
    actor: User,
    course: Course,
    *,
    changes: dict[str, Any],
    ip: str | None = None,
) -> Course:
    ensure_editable(course)
    applied: dict[str, Any] = {}
    for field in ("title", "description", "cover_url"):
        if field not in changes:
            continue
        value = changes[field]
        if field == "title":
            if not value:
                continue
        elif value == "":
            value = None
        if getattr(course, field) != value:
            setattr(course, field, value)
            applied[field] = value

    if applied:
        await record_audit(
            db,
            action=ACTION_COURSE_UPDATE,
            actor=actor,
            target_type="course",
            target_id=course.id,
            detail={"title": course.title, "changes": applied},
            ip=ip,
        )
    await db.commit()
    return course


async def submit_course(
    db: AsyncSession, actor: User, course: Course, *, ip: str | None = None
) -> Course:
    if course.status not in COURSE_SUBMITTABLE_STATUSES:
        raise ConflictError("当前状态的课程无需提交审核")

    issue = course_auto_review_issue(course)
    auto_approved = issue is None
    course.submitted_at = utc_now()
    if auto_approved:
        course.status = COURSE_STATUS_APPROVED
        course.review_comment = AUTO_REVIEW_COMMENT
        course.reviewed_by = None
        course.reviewed_at = utc_now()
    else:
        course.status = COURSE_STATUS_PENDING
        course.review_comment = None
    await record_audit(
        db,
        action=ACTION_COURSE_AUTO_APPROVE if auto_approved else ACTION_COURSE_SUBMIT,
        actor=actor,
        target_type="course",
        target_id=course.id,
        detail={
            "title": course.title,
            "auto_review": auto_approved,
            **({"manual_reason": issue} if issue else {}),
        },
        ip=ip,
    )
    await db.commit()
    return course


async def review_course(
    db: AsyncSession,
    reviewer: User,
    course: Course,
    *,
    decision: str,
    comment: str | None,
    ip: str | None = None,
) -> Course:
    if course.status != COURSE_STATUS_PENDING:
        raise ConflictError("只有待审核状态的课程可以审核")
    if decision == "reject" and not (comment or "").strip():
        raise ValidationError("驳回课程时必须填写审核意见")

    approved = decision == "approve"
    course.status = COURSE_STATUS_APPROVED if approved else COURSE_STATUS_REJECTED
    course.review_comment = (comment or "").strip() or None
    course.reviewed_by = reviewer
    course.reviewed_at = utc_now()
    await record_audit(
        db,
        action=ACTION_COURSE_APPROVE if approved else ACTION_COURSE_REJECT,
        actor=reviewer,
        target_type="course",
        target_id=course.id,
        detail={"title": course.title, "comment": course.review_comment},
        ip=ip,
    )
    await db.commit()
    return course


async def rotate_invite_code(
    db: AsyncSession, actor: User, course: Course, *, ip: str | None = None
) -> Course:
    course.invite_code = await _generate_invite_code(db)
    await record_audit(
        db,
        action=ACTION_COURSE_INVITE_ROTATE,
        actor=actor,
        target_type="course",
        target_id=course.id,
        detail={"title": course.title},
        ip=ip,
    )
    await db.commit()
    return course


async def toggle_invite(
    db: AsyncSession,
    actor: User,
    course: Course,
    *,
    enabled: bool,
    ip: str | None = None,
) -> Course:
    course.invite_enabled = enabled
    await record_audit(
        db,
        action=ACTION_COURSE_INVITE_TOGGLE,
        actor=actor,
        target_type="course",
        target_id=course.id,
        detail={"title": course.title, "enabled": enabled},
        ip=ip,
    )
    await db.commit()
    return course


def get_chapter(course: Course, chapter_id: int) -> Chapter:
    chapter = next((item for item in course.chapters if item.id == chapter_id), None)
    if chapter is None:
        raise NotFoundError("章节不存在")
    return chapter


def get_knowledge(chapter: Chapter, knowledge_id: int) -> Knowledge:
    knowledge = next((item for item in chapter.knowledges if item.id == knowledge_id), None)
    if knowledge is None:
        raise NotFoundError("知识点不存在")
    return knowledge


async def create_chapter(
    db: AsyncSession,
    course: Course,
    *,
    title: str,
    description: str | None = None,
    order_no: int | None = None,
) -> Chapter:
    ensure_editable(course)
    if order_no is None:
        order_no = max((item.order_no for item in course.chapters), default=-1) + 1
    chapter = Chapter(
        course=course,
        title=title,
        description=description or None,
        order_no=order_no,
    )
    db.add(chapter)
    await db.commit()
    refreshed = await get_course(db, course.id)
    return get_chapter(refreshed, chapter.id)


async def update_chapter(
    db: AsyncSession,
    course: Course,
    chapter: Chapter,
    *,
    changes: dict[str, Any],
) -> Chapter:
    ensure_editable(course)
    for field in ("title", "description", "order_no"):
        if field not in changes:
            continue
        value = changes[field]
        if field == "title" and not value:
            continue
        if field == "description" and value == "":
            value = None
        setattr(chapter, field, value)
    await db.commit()
    return chapter


async def delete_chapter(db: AsyncSession, course: Course, chapter: Chapter) -> None:
    ensure_editable(course)
    await db.delete(chapter)
    await db.commit()


async def create_knowledge(
    db: AsyncSession,
    course: Course,
    chapter: Chapter,
    *,
    name: str,
    description: str | None = None,
    difficulty: int = 3,
) -> Knowledge:
    ensure_editable(course)
    knowledge = Knowledge(
        course_id=course.id,
        chapter=chapter,
        name=name,
        description=description or None,
        difficulty=difficulty,
    )
    db.add(knowledge)
    await db.commit()
    return knowledge


async def update_knowledge(
    db: AsyncSession,
    course: Course,
    knowledge: Knowledge,
    *,
    changes: dict[str, Any],
) -> Knowledge:
    ensure_editable(course)
    for field in ("name", "description", "difficulty"):
        if field not in changes:
            continue
        value = changes[field]
        if field == "name" and not value:
            continue
        if field == "description" and value == "":
            value = None
        setattr(knowledge, field, value)
    await db.commit()
    return knowledge


async def delete_knowledge(db: AsyncSession, course: Course, knowledge: Knowledge) -> None:
    ensure_editable(course)
    await db.delete(knowledge)
    await db.commit()


async def join_course_by_code(
    db: AsyncSession,
    student: User,
    *,
    invite_code: str,
    ip: str | None = None,
) -> tuple[Course, bool]:
    code = invite_code.strip().upper()
    course = await db.scalar(select(Course).options(*COURSE_LOAD).where(Course.invite_code == code))
    if course is None:
        raise NotFoundError("邀请码无效")
    if course.status != COURSE_STATUS_APPROVED:
        raise ConflictError("课程尚未发布，暂时无法加入")
    if not course.invite_enabled:
        raise ConflictError("课程邀请码已停用")

    existing = next((item for item in course.enrollments if item.student_id == student.id), None)
    if existing is not None:
        return course, False

    enrollment = CourseEnrollment(
        course=course,
        student=student,
        source=ENROLLMENT_SOURCE_INVITE,
    )
    db.add(enrollment)
    await record_audit(
        db,
        action=ACTION_COURSE_JOIN,
        actor=student,
        target_type="course",
        target_id=course.id,
        detail={"title": course.title, "source": ENROLLMENT_SOURCE_INVITE},
        ip=ip,
    )
    await db.commit()
    return await get_course(db, course.id), True


async def list_course_students(
    db: AsyncSession,
    course: Course,
    *,
    page: int = 1,
    page_size: int = 20,
) -> tuple[list[CourseEnrollment], int]:
    where = CourseEnrollment.course_id == course.id
    total = await db.scalar(select(func.count(CourseEnrollment.id)).where(where))
    result = await db.scalars(
        select(CourseEnrollment)
        .options(selectinload(CourseEnrollment.student))
        .where(where)
        .order_by(CourseEnrollment.created_at.desc(), CourseEnrollment.id.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    return list(result), int(total or 0)


async def add_student_to_course(
    db: AsyncSession,
    actor: User,
    course: Course,
    *,
    username: str,
    ip: str | None = None,
) -> tuple[CourseEnrollment, bool]:
    if course.status != COURSE_STATUS_APPROVED:
        raise ConflictError("课程发布后才能添加学生")
    student = await db.scalar(
        select(User)
        .options(selectinload(User.role))
        .where(User.username == username.strip().lower())
    )
    if student is None:
        raise NotFoundError("学生账号不存在")
    if student.role.name != ROLE_STUDENT:
        raise ValidationError("只能添加学生账号")

    existing = next((item for item in course.enrollments if item.student_id == student.id), None)
    if existing is not None:
        return existing, False

    enrollment = CourseEnrollment(
        course=course,
        student=student,
        source=ENROLLMENT_SOURCE_TEACHER,
    )
    db.add(enrollment)
    await record_audit(
        db,
        action=ACTION_COURSE_STUDENT_ADD,
        actor=actor,
        target_type="course",
        target_id=course.id,
        detail={
            "title": course.title,
            "student": student.username,
            "source": ENROLLMENT_SOURCE_TEACHER,
        },
        ip=ip,
    )
    await db.commit()
    return enrollment, True


async def remove_student_from_course(
    db: AsyncSession,
    actor: User,
    course: Course,
    *,
    student_id: int,
    ip: str | None = None,
) -> None:
    enrollment = next((item for item in course.enrollments if item.student_id == student_id), None)
    if enrollment is None:
        raise NotFoundError("该学生未加入课程")
    student_name = enrollment.student.username if enrollment.student else str(student_id)
    await db.delete(enrollment)
    await record_audit(
        db,
        action=ACTION_COURSE_STUDENT_REMOVE,
        actor=actor,
        target_type="course",
        target_id=course.id,
        detail={"title": course.title, "student": student_name},
        ip=ip,
    )
    await db.commit()
