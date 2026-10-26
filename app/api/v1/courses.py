"""Course hierarchy, review workflow, invitation and enrollment endpoints."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, require_permission, require_role
from app.core.errors import AppError, success
from app.db.models.course import COURSE_STATUS_APPROVED, COURSE_STATUSES
from app.db.models.rbac import ROLE_STUDENT, User
from app.db.session import get_db
from app.schemas.course import (
    AddStudentRequest,
    ChapterCreateRequest,
    ChapterUpdateRequest,
    CourseCreateRequest,
    CourseReviewRequest,
    CourseUpdateRequest,
    InviteToggleRequest,
    JoinCourseRequest,
    KnowledgeCreateRequest,
    KnowledgeUpdateRequest,
    chapter_out,
    course_out,
    enrollment_student_out,
    knowledge_out,
)
from app.schemas.review import BatchReviewRequest
from app.services import course_service
from app.services.audit_service import client_ip

router = APIRouter(prefix="/courses", tags=["courses"])


def _include_invite(user: User) -> bool:
    return user.role.name != ROLE_STUDENT


@router.post("/join")
async def join_course(
    body: JoinCourseRequest,
    request: Request,
    user: User = Depends(require_role(ROLE_STUDENT)),
    db: AsyncSession = Depends(get_db),
) -> dict:
    course, joined = await course_service.join_course_by_code(
        db,
        user,
        invite_code=body.invite_code,
        ip=client_ip(request),
    )
    message = "已加入课程" if joined else "你已在该课程中"
    return success(
        {**course_out(course, include_invite=False, detail=True), "joined": joined},
        message,
    )


@router.get("")
async def list_courses(
    page: int = Query(1, ge=1),
    page_size: int = Query(12, ge=1, le=100),
    keyword: str | None = Query(default=None, max_length=100),
    status_filter: str | None = Query(
        default=None,
        alias="status",
        pattern=f"^({'|'.join(sorted(COURSE_STATUSES))})$",
    ),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    items, total = await course_service.list_courses(
        db,
        user,
        page=page,
        page_size=page_size,
        keyword=keyword,
        status=status_filter,
    )
    return success(
        {
            "items": [course_out(item, include_invite=_include_invite(user)) for item in items],
            "total": total,
            "page": page,
            "page_size": page_size,
        }
    )


@router.post("", status_code=status.HTTP_201_CREATED)
async def create_course(
    body: CourseCreateRequest,
    request: Request,
    user: User = Depends(require_permission("course:create")),
    db: AsyncSession = Depends(get_db),
) -> dict:
    course = await course_service.create_course(
        db,
        user,
        title=body.title,
        description=body.description,
        cover_url=body.cover_url,
        ip=client_ip(request),
    )
    return success(course_out(course, include_invite=True), "课程创建成功")


@router.post("/batch/review")
async def batch_review_courses(
    body: BatchReviewRequest,
    request: Request,
    reviewer: User = Depends(require_permission("course:review")),
    db: AsyncSession = Depends(get_db),
) -> dict:
    succeeded: list[dict] = []
    errors: list[dict] = []
    for course_id in body.ids:
        try:
            course = await course_service.get_course(db, course_id)
            reviewed = await course_service.review_course(
                db,
                reviewer,
                course,
                decision=body.decision,
                comment=body.comment,
                ip=client_ip(request),
            )
            succeeded.append({"id": reviewed.id, "title": reviewed.title})
        except AppError as exc:
            await db.rollback()
            errors.append({"id": course_id, "code": exc.code, "message": exc.message})
        except Exception:  # noqa: BLE001 - batch keeps processing after one failure
            await db.rollback()
            errors.append({"id": course_id, "code": 5000, "message": "审核失败，请重试"})

    action = "通过" if body.decision == "approve" else "驳回"
    message = f"已{action} {len(succeeded)} 门课程"
    if errors:
        message += f"，{len(errors)} 门失败"
    return success(
        {"succeeded": succeeded, "failed": errors, "count": len(succeeded)},
        message,
    )


@router.get("/{course_id}")
async def get_course(
    course_id: int,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    course = await course_service.get_accessible_course(db, user, course_id)
    return success(course_out(course, include_invite=_include_invite(user), detail=True))


@router.put("/{course_id}")
async def update_course(
    course_id: int,
    body: CourseUpdateRequest,
    request: Request,
    user: User = Depends(require_permission("course:create")),
    db: AsyncSession = Depends(get_db),
) -> dict:
    course = await course_service.get_accessible_course(db, user, course_id, for_management=True)
    updated = await course_service.update_course(
        db,
        user,
        course,
        changes=body.model_dump(exclude_unset=True),
        ip=client_ip(request),
    )
    return success(course_out(updated, include_invite=True, detail=True), "课程信息已更新")


@router.post("/{course_id}/submit")
async def submit_course(
    course_id: int,
    request: Request,
    user: User = Depends(require_permission("course:create")),
    db: AsyncSession = Depends(get_db),
) -> dict:
    course = await course_service.get_accessible_course(db, user, course_id, for_management=True)
    submitted = await course_service.submit_course(db, user, course, ip=client_ip(request))
    message = (
        "课程符合自动审核规则，已直接发布"
        if submitted.status == COURSE_STATUS_APPROVED
        else "课程已提交审核"
    )
    return success(
        course_out(submitted, include_invite=True, detail=True),
        message,
    )


@router.post("/{course_id}/review")
async def review_course(
    course_id: int,
    body: CourseReviewRequest,
    request: Request,
    reviewer: User = Depends(require_permission("course:review")),
    db: AsyncSession = Depends(get_db),
) -> dict:
    course = await course_service.get_course(db, course_id)
    reviewed = await course_service.review_course(
        db,
        reviewer,
        course,
        decision=body.decision,
        comment=body.comment,
        ip=client_ip(request),
    )
    message = "课程审核通过" if body.decision == "approve" else "课程已驳回"
    return success(course_out(reviewed, include_invite=True, detail=True), message)


@router.post("/{course_id}/invite/rotate")
async def rotate_invite(
    course_id: int,
    request: Request,
    user: User = Depends(require_permission("course:create")),
    db: AsyncSession = Depends(get_db),
) -> dict:
    course = await course_service.get_accessible_course(db, user, course_id, for_management=True)
    rotated = await course_service.rotate_invite_code(db, user, course, ip=client_ip(request))
    return success(course_out(rotated, include_invite=True), "邀请码已轮换，旧邀请码立即失效")


@router.put("/{course_id}/invite")
async def toggle_invite(
    course_id: int,
    body: InviteToggleRequest,
    request: Request,
    user: User = Depends(require_permission("course:create")),
    db: AsyncSession = Depends(get_db),
) -> dict:
    course = await course_service.get_accessible_course(db, user, course_id, for_management=True)
    updated = await course_service.toggle_invite(
        db,
        user,
        course,
        enabled=body.enabled,
        ip=client_ip(request),
    )
    message = "邀请码已启用" if body.enabled else "邀请码已停用"
    return success(course_out(updated, include_invite=True), message)


@router.get("/{course_id}/chapters")
async def list_chapters(
    course_id: int,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    course = await course_service.get_accessible_course(db, user, course_id)
    return success({"items": [chapter_out(item) for item in course.chapters]})


@router.post("/{course_id}/chapters", status_code=status.HTTP_201_CREATED)
async def create_chapter(
    course_id: int,
    body: ChapterCreateRequest,
    user: User = Depends(require_permission("course:create")),
    db: AsyncSession = Depends(get_db),
) -> dict:
    course = await course_service.get_accessible_course(db, user, course_id, for_management=True)
    chapter = await course_service.create_chapter(
        db,
        course,
        title=body.title,
        description=body.description,
        order_no=body.order_no,
    )
    return success(chapter_out(chapter).model_dump(), "章节已创建")


@router.put("/{course_id}/chapters/{chapter_id}")
async def update_chapter(
    course_id: int,
    chapter_id: int,
    body: ChapterUpdateRequest,
    user: User = Depends(require_permission("course:create")),
    db: AsyncSession = Depends(get_db),
) -> dict:
    course = await course_service.get_accessible_course(db, user, course_id, for_management=True)
    chapter = course_service.get_chapter(course, chapter_id)
    updated = await course_service.update_chapter(
        db, course, chapter, changes=body.model_dump(exclude_unset=True)
    )
    return success(chapter_out(updated).model_dump(), "章节已更新")


@router.delete("/{course_id}/chapters/{chapter_id}")
async def delete_chapter(
    course_id: int,
    chapter_id: int,
    user: User = Depends(require_permission("course:create")),
    db: AsyncSession = Depends(get_db),
) -> dict:
    course = await course_service.get_accessible_course(db, user, course_id, for_management=True)
    chapter = course_service.get_chapter(course, chapter_id)
    await course_service.delete_chapter(db, course, chapter)
    return success({"deleted": True, "chapter_id": chapter_id}, "章节已删除")


@router.get("/{course_id}/chapters/{chapter_id}/knowledges")
async def list_knowledges(
    course_id: int,
    chapter_id: int,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    course = await course_service.get_accessible_course(db, user, course_id)
    chapter = course_service.get_chapter(course, chapter_id)
    return success({"items": [knowledge_out(item) for item in chapter.knowledges]})


@router.post(
    "/{course_id}/chapters/{chapter_id}/knowledges",
    status_code=status.HTTP_201_CREATED,
)
async def create_knowledge(
    course_id: int,
    chapter_id: int,
    body: KnowledgeCreateRequest,
    user: User = Depends(require_permission("course:create")),
    db: AsyncSession = Depends(get_db),
) -> dict:
    course = await course_service.get_accessible_course(db, user, course_id, for_management=True)
    chapter = course_service.get_chapter(course, chapter_id)
    knowledge = await course_service.create_knowledge(
        db,
        course,
        chapter,
        name=body.name,
        description=body.description,
        difficulty=body.difficulty,
    )
    return success(knowledge_out(knowledge).model_dump(), "知识点已创建")


@router.put("/{course_id}/chapters/{chapter_id}/knowledges/{knowledge_id}")
async def update_knowledge(
    course_id: int,
    chapter_id: int,
    knowledge_id: int,
    body: KnowledgeUpdateRequest,
    user: User = Depends(require_permission("course:create")),
    db: AsyncSession = Depends(get_db),
) -> dict:
    course = await course_service.get_accessible_course(db, user, course_id, for_management=True)
    chapter = course_service.get_chapter(course, chapter_id)
    knowledge = course_service.get_knowledge(chapter, knowledge_id)
    updated = await course_service.update_knowledge(
        db, course, knowledge, changes=body.model_dump(exclude_unset=True)
    )
    return success(knowledge_out(updated).model_dump(), "知识点已更新")


@router.delete("/{course_id}/chapters/{chapter_id}/knowledges/{knowledge_id}")
async def delete_knowledge(
    course_id: int,
    chapter_id: int,
    knowledge_id: int,
    user: User = Depends(require_permission("course:create")),
    db: AsyncSession = Depends(get_db),
) -> dict:
    course = await course_service.get_accessible_course(db, user, course_id, for_management=True)
    chapter = course_service.get_chapter(course, chapter_id)
    knowledge = course_service.get_knowledge(chapter, knowledge_id)
    await course_service.delete_knowledge(db, course, knowledge)
    return success({"deleted": True, "knowledge_id": knowledge_id}, "知识点已删除")


@router.get("/{course_id}/students")
async def list_students(
    course_id: int,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    user: User = Depends(require_permission("course:create")),
    db: AsyncSession = Depends(get_db),
) -> dict:
    course = await course_service.get_accessible_course(db, user, course_id, for_management=True)
    items, total = await course_service.list_course_students(
        db, course, page=page, page_size=page_size
    )
    return success(
        {
            "items": [enrollment_student_out(item).model_dump() for item in items],
            "total": total,
            "page": page,
            "page_size": page_size,
        }
    )


@router.post("/{course_id}/students", status_code=status.HTTP_201_CREATED)
async def add_student(
    course_id: int,
    body: AddStudentRequest,
    request: Request,
    user: User = Depends(require_permission("course:create")),
    db: AsyncSession = Depends(get_db),
) -> dict:
    course = await course_service.get_accessible_course(db, user, course_id, for_management=True)
    enrollment, created = await course_service.add_student_to_course(
        db, user, course, username=body.username, ip=client_ip(request)
    )
    message = "学生已加入课程" if created else "该学生已在课程中"
    return success(
        {**enrollment_student_out(enrollment).model_dump(), "created": created},
        message,
    )


@router.delete("/{course_id}/students/{student_id}")
async def remove_student(
    course_id: int,
    student_id: int,
    request: Request,
    user: User = Depends(require_permission("course:create")),
    db: AsyncSession = Depends(get_db),
) -> dict:
    course = await course_service.get_accessible_course(db, user, course_id, for_management=True)
    await course_service.remove_student_from_course(
        db, user, course, student_id=student_id, ip=client_ip(request)
    )
    return success({"removed": True, "student_id": student_id}, "学生已移出课程")
