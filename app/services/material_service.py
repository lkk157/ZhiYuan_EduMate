"""Course material upload, review, RAG indexing and download."""

from __future__ import annotations

import logging
import re
from pathlib import Path

from fastapi import UploadFile
from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
from sqlalchemy.orm import selectinload

from app.core.config import get_settings
from app.core.errors import (
    ConflictError,
    ForbiddenError,
    NotFoundError,
    RagError,
    ValidationError,
)
from app.db.base import utc_now
from app.db.models.course import (
    COURSE_STATUS_APPROVED,
    Chapter,
    Course,
    CourseEnrollment,
    Knowledge,
)
from app.db.models.knowledge_base import KB_STATUS_ACTIVE, KnowledgeBase
from app.db.models.material import (
    ALLOWED_MATERIAL_SUFFIXES,
    INDEX_STATUS_FAILED,
    INDEX_STATUS_INDEXED,
    INDEX_STATUS_INDEXING,
    INDEX_STATUS_PENDING,
    MATERIAL_SCOPE_COURSE,
    MATERIAL_SCOPE_PERSONAL,
    MATERIAL_STATUS_APPROVED,
    MATERIAL_STATUS_DELETED,
    MATERIAL_STATUS_PENDING,
    MATERIAL_STATUS_REJECTED,
    Material,
    MaterialView,
)
from app.db.models.rbac import ROLE_ADMIN, ROLE_STUDENT, ROLE_TEACHER, User
from app.services.audit_service import (
    ACTION_MATERIAL_APPROVE,
    ACTION_MATERIAL_AUTO_APPROVE,
    ACTION_MATERIAL_DELETE,
    ACTION_MATERIAL_INDEX_RETRY,
    ACTION_MATERIAL_MAPPING,
    ACTION_MATERIAL_REJECT,
    ACTION_MATERIAL_UPLOAD,
    record_audit,
)
from app.services.rag_client import RagClient

logger = logging.getLogger(__name__)

MATERIAL_LOAD = (
    selectinload(Material.course),
    selectinload(Material.knowledge_base),
    selectinload(Material.owner),
    selectinload(Material.chapter),
    selectinload(Material.knowledge),
    selectinload(Material.uploader),
)

CHUNK_SIZE = 1024 * 1024
MAX_BATCH_FILES = 10
AUTO_REVIEW_COMMENT = "系统自动审核通过"
AUTO_REVIEW_SUFFIXES = {".pdf", ".docx", ".pptx"}


def material_auto_review_issue(
    *,
    course: Course | None,
    chapter: Chapter | None,
    file_type: str,
    file_size: int,
    title: str,
) -> str | None:
    """Return why a material needs manual review, or ``None`` when safe."""
    if not get_settings().auto_review_enabled:
        return "自动审核未启用"
    if course is None or course.status != COURSE_STATUS_APPROVED:
        return "课程未发布"
    if chapter is None:
        return "资料未关联章节"
    if file_type not in AUTO_REVIEW_SUFFIXES:
        return "图片资料需人工审核"
    if file_size <= 0:
        return "文件内容为空"
    if len((title or "").strip()) < 2:
        return "资料标题过短"
    return None


def sanitize_filename(filename: str, fallback: str = "material") -> str:
    raw = Path(filename or "").name
    suffix = Path(raw).suffix.lower()
    stem = Path(raw).stem if raw else ""
    stem = re.sub(r"[^\w\-. 一-鿿]+", "_", stem, flags=re.UNICODE)
    stem = stem.strip(" ._")[:100]
    if not stem:
        stem = fallback
    return f"{stem}{suffix}"


def material_absolute_path(material: Material) -> Path:
    return get_settings().upload_path / material.file_path


async def get_material(db: AsyncSession, material_id: int) -> Material:
    material = await db.scalar(
        select(Material).options(*MATERIAL_LOAD).where(Material.id == material_id)
    )
    if material is None:
        raise NotFoundError("资料不存在")
    return material


async def _is_enrolled(db: AsyncSession, course_id: int, student_id: int) -> bool:
    enrollment = await db.scalar(
        select(CourseEnrollment.id).where(
            CourseEnrollment.course_id == course_id,
            CourseEnrollment.student_id == student_id,
        )
    )
    return bool(enrollment)


async def ensure_material_access(
    db: AsyncSession, material: Material, user: User, *, management: bool = False
) -> None:
    if material.status == MATERIAL_STATUS_DELETED:
        raise NotFoundError("资料不存在")

    if material.scope == MATERIAL_SCOPE_PERSONAL:
        if user.role.name != ROLE_STUDENT or material.owner_id != user.id:
            # Personal knowledge bases are private, including from admins.
            raise ForbiddenError("无权访问该资料")
        kb = material.knowledge_base
        if kb is None or kb.status != KB_STATUS_ACTIVE:
            raise NotFoundError("知识库不存在或已删除")
        return

    if user.role.name == ROLE_ADMIN:
        return
    if user.role.name == ROLE_TEACHER:
        if material.course is None or material.course.teacher_id != user.id:
            raise ForbiddenError("只能管理自己课程的资料")
        return
    if user.role.name != ROLE_STUDENT or management:
        raise ForbiddenError("无权访问该资料")
    if material.status != MATERIAL_STATUS_APPROVED:
        raise ForbiddenError("资料尚未发布")
    if material.course is None or material.course.status != COURSE_STATUS_APPROVED:
        raise ForbiddenError("课程尚未发布")
    if material.course_id is None or not await _is_enrolled(db, material.course_id, user.id):
        raise ForbiddenError("请先加入课程")


def _management_view(user: User) -> bool:
    return user.role.name in {ROLE_ADMIN, ROLE_TEACHER}


async def list_materials(
    db: AsyncSession,
    user: User,
    *,
    course_id: int | None = None,
    chapter_id: int | None = None,
    page: int = 1,
    page_size: int = 20,
    keyword: str | None = None,
    status: str | None = None,
    index_status: str | None = None,
) -> tuple[list[Material], int]:
    conditions = [Material.scope == MATERIAL_SCOPE_COURSE]

    base = select(Material).options(*MATERIAL_LOAD)
    count_stmt = select(func.count(func.distinct(Material.id))).select_from(Material)

    if user.role.name == ROLE_ADMIN:
        pass
    elif user.role.name == ROLE_TEACHER:
        base = base.join(Course, Material.course_id == Course.id)
        count_stmt = count_stmt.join(Course, Material.course_id == Course.id)
        conditions.append(Course.teacher_id == user.id)
    else:
        base = base.join(Course, Material.course_id == Course.id).join(
            CourseEnrollment, CourseEnrollment.course_id == Material.course_id
        )
        count_stmt = count_stmt.join(Course, Material.course_id == Course.id).join(
            CourseEnrollment, CourseEnrollment.course_id == Material.course_id
        )
        conditions.extend(
            [
                CourseEnrollment.student_id == user.id,
                Course.status == COURSE_STATUS_APPROVED,
                Material.status == MATERIAL_STATUS_APPROVED,
            ]
        )

    if course_id is not None:
        conditions.append(Material.course_id == course_id)
    if chapter_id is not None:
        conditions.append(Material.chapter_id == chapter_id)
    if keyword and keyword.strip():
        pattern = f"%{keyword.strip()}%"
        conditions.append(or_(Material.title.like(pattern), Material.source_filename.like(pattern)))
    if status and user.role.name != ROLE_STUDENT:
        conditions.append(Material.status == status)
    elif not status:
        conditions.append(Material.status != MATERIAL_STATUS_DELETED)
    if index_status:
        conditions.append(Material.index_status == index_status)

    total = await db.scalar(count_stmt.where(*conditions))
    result = await db.scalars(
        base.where(*conditions)
        .order_by(Material.created_at.desc(), Material.id.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    return list(result), int(total or 0)


async def create_material(
    db: AsyncSession,
    *,
    uploader: User,
    upload: UploadFile,
    title: str | None,
    course: Course | None = None,
    knowledge_base: KnowledgeBase | None = None,
    chapter_id: int | None = None,
    knowledge_id: int | None = None,
    ip: str | None = None,
) -> Material:
    if (course is None) == (knowledge_base is None):
        raise ValidationError("必须指定课程或个人知识库")
    personal = knowledge_base is not None

    if knowledge_base is not None:
        if knowledge_base.status != KB_STATUS_ACTIVE:
            raise NotFoundError("知识库不存在或已删除")
        if knowledge_base.owner_id != uploader.id:
            raise ForbiddenError("只能向自己的知识库上传资料")
        if chapter_id is not None or knowledge_id is not None:
            raise ValidationError("个人知识库资料不支持关联课程章节")
    if course is not None and course.status != COURSE_STATUS_APPROVED:
        raise ConflictError("课程发布后才能上传资料")

    original = Path(upload.filename or "").name
    if not original:
        raise ValidationError("文件名不能为空")
    suffix = Path(original).suffix.lower()
    if suffix not in ALLOWED_MATERIAL_SUFFIXES:
        allowed = "PDF、DOCX、PPTX、PNG、JPG、JPEG"
        raise ValidationError(f"不支持的文件类型，仅支持 {allowed}")

    chapter: Chapter | None = None
    knowledge: Knowledge | None = None
    if course is not None:
        if chapter_id is not None:
            chapter = next((item for item in course.chapters if item.id == chapter_id), None)
            if chapter is None:
                raise ValidationError("章节不属于该课程")
        if knowledge_id is not None:
            if chapter is None:
                raise ValidationError("选择知识点前请先选择章节")
            knowledge = next((item for item in chapter.knowledges if item.id == knowledge_id), None)
            if knowledge is None:
                raise ValidationError("知识点不属于所选章节")

    settings = get_settings()
    material_title = (title or "").strip() or Path(original).stem[:200] or original
    material = Material(
        scope=MATERIAL_SCOPE_PERSONAL if personal else MATERIAL_SCOPE_COURSE,
        course=course,
        knowledge_base=knowledge_base,
        owner=uploader,
        chapter=chapter,
        knowledge=knowledge,
        uploader=uploader,
        title=material_title[:200],
        source_filename=original[:255],
        rag_filename="",
        file_path="",
        file_type=suffix,
        file_size=0,
        status=MATERIAL_STATUS_APPROVED if personal else MATERIAL_STATUS_PENDING,
        index_status=INDEX_STATUS_PENDING,
    )
    db.add(material)
    await db.flush()

    sanitized = sanitize_filename(original)
    rag_filename = f"m{material.id}__{sanitized}"
    if personal:
        base_dir = Path("personal") / str(uploader.id) / str(knowledge_base.id)
    else:
        base_dir = Path("courses") / str(course.id)
    relative = base_dir / rag_filename
    destination = settings.upload_path / relative
    destination.parent.mkdir(parents=True, exist_ok=True)

    size = 0
    try:
        with destination.open("wb") as handle:
            while True:
                chunk = await upload.read(CHUNK_SIZE)
                if not chunk:
                    break
                size += len(chunk)
                if size > settings.max_upload_bytes:
                    raise ValidationError(f"文件大小不能超过 {settings.max_upload_mb}MB")
                handle.write(chunk)
        if size == 0:
            raise ValidationError("文件不能为空")
    except Exception:
        destination.unlink(missing_ok=True)
        await db.rollback()
        raise
    finally:
        await upload.close()

    material.rag_filename = rag_filename
    material.file_path = relative.as_posix()
    material.file_size = size

    auto_issue: str | None = None
    if not personal:
        auto_issue = material_auto_review_issue(
            course=course,
            chapter=chapter,
            file_type=suffix,
            file_size=size,
            title=material_title,
        )
        if auto_issue is None:
            material.status = MATERIAL_STATUS_APPROVED
            material.review_comment = AUTO_REVIEW_COMMENT
            material.reviewed_at = utc_now()

    await record_audit(
        db,
        action=ACTION_MATERIAL_UPLOAD,
        actor=uploader,
        target_type="material",
        target_id=material.id,
        detail={
            "title": material.title,
            "scope": material.scope,
            "course": course.title if course is not None else None,
            "knowledge_base": knowledge_base.name if knowledge_base is not None else None,
            "filename": material.source_filename,
            "size": size,
            "auto_review_issue": auto_issue,
        },
        ip=ip,
    )
    if not personal and auto_issue is None:
        await record_audit(
            db,
            action=ACTION_MATERIAL_AUTO_APPROVE,
            actor=uploader,
            target_type="material",
            target_id=material.id,
            detail={
                "title": material.title,
                "course": course.title if course is not None else None,
                "auto_review": True,
            },
            ip=ip,
        )
    try:
        await db.commit()
    except Exception:
        destination.unlink(missing_ok=True)
        await db.rollback()
        raise
    return await get_material(db, material.id)


async def update_material_mapping(
    db: AsyncSession,
    actor: User,
    material: Material,
    *,
    chapter_id: int | None,
    knowledge_id: int | None,
    ip: str | None = None,
) -> Material:
    """Attach a course material to a chapter/knowledge point (or clear it)."""
    if material.scope != MATERIAL_SCOPE_COURSE:
        raise ValidationError("个人知识库资料不支持关联课程章节")
    if material.status == MATERIAL_STATUS_DELETED:
        raise NotFoundError("资料不存在")
    course = material.course
    if course is None:
        raise ValidationError("资料未关联课程")

    chapter: Chapter | None = None
    knowledge: Knowledge | None = None
    if chapter_id is not None:
        chapter = next((item for item in course.chapters if item.id == chapter_id), None)
        if chapter is None:
            raise ValidationError("章节不属于该课程")
    if knowledge_id is not None:
        if chapter is None:
            raise ValidationError("选择知识点前请先选择章节")
        knowledge = next((item for item in chapter.knowledges if item.id == knowledge_id), None)
        if knowledge is None:
            raise ValidationError("知识点不属于所选章节")

    previous = {
        "chapter_id": material.chapter_id,
        "knowledge_id": material.knowledge_id,
    }
    # Assign relationships (not only ids) so the eager-loaded objects on this
    # session reflect the new mapping without a stale identity-map hit.
    material.chapter = chapter
    material.knowledge = knowledge
    await record_audit(
        db,
        action=ACTION_MATERIAL_MAPPING,
        actor=actor,
        target_type="material",
        target_id=material.id,
        detail={
            "title": material.title,
            "previous": previous,
            "chapter_id": material.chapter_id,
            "knowledge_id": material.knowledge_id,
        },
        ip=ip,
    )
    await db.commit()
    return await get_material(db, material.id)


async def review_material(
    db: AsyncSession,
    reviewer: User,
    material: Material,
    *,
    decision: str,
    comment: str | None,
    ip: str | None = None,
) -> Material:
    if material.status != MATERIAL_STATUS_PENDING:
        raise ConflictError("只有待审核状态的资料可以审核")
    if decision == "reject" and not (comment or "").strip():
        raise ValidationError("驳回资料时必须填写审核意见")

    approved = decision == "approve"
    material.status = MATERIAL_STATUS_APPROVED if approved else MATERIAL_STATUS_REJECTED
    material.review_comment = (comment or "").strip() or None
    material.reviewed_by = reviewer
    material.reviewed_at = utc_now()
    if approved:
        material.index_status = INDEX_STATUS_PENDING
        material.index_error = None
    await record_audit(
        db,
        action=ACTION_MATERIAL_APPROVE if approved else ACTION_MATERIAL_REJECT,
        actor=reviewer,
        target_type="material",
        target_id=material.id,
        detail={
            "title": material.title,
            "course": material.course.title if material.course else None,
            "comment": material.review_comment,
        },
        ip=ip,
    )
    await db.commit()
    return material


async def retry_material_index(
    db: AsyncSession,
    actor: User,
    material: Material,
    *,
    ip: str | None = None,
) -> Material:
    if material.status != MATERIAL_STATUS_APPROVED:
        raise ConflictError("只有审核通过的资料可以索引")
    if material.index_status == INDEX_STATUS_INDEXING:
        raise ConflictError("资料正在索引中，请稍候")
    if material.index_status == INDEX_STATUS_INDEXED:
        raise ConflictError("资料已索引成功，无需重试")

    material.index_status = INDEX_STATUS_PENDING
    material.index_error = None
    await record_audit(
        db,
        action=ACTION_MATERIAL_INDEX_RETRY,
        actor=actor,
        target_type="material",
        target_id=material.id,
        detail={"title": material.title},
        ip=ip,
    )
    await db.commit()
    return material


def material_rag_group_id(material: Material) -> int | None:
    """Return the RAG group holding this material's vectors, if any."""
    if material.scope == MATERIAL_SCOPE_PERSONAL:
        knowledge_base = material.knowledge_base
        return knowledge_base.rag_group_id if knowledge_base is not None else None
    course = material.course
    return course.rag_group_id if course is not None else None


async def delete_material_rag_document(
    material: Material,
    rag_client: RagClient,
    *,
    group_id: int | None = None,
) -> bool:
    """Delete the material from its RAG group; 404 counts as already deleted.

    RAG vectors are a derived index, so a business soft delete must remove
    them as well. The helper returns whether a RAG call was attempted.
    """
    indexed = material.index_status in {INDEX_STATUS_INDEXED, INDEX_STATUS_FAILED}
    if not indexed and not material.vector_doc_id:
        # Never uploaded (pending upload or rejected before indexing).
        return False

    group = group_id if group_id is not None else material_rag_group_id(material)
    if group is None:
        return False

    doc_id = material.vector_doc_id
    if doc_id and str(doc_id).isdigit():
        removed = await rag_client.delete_document(group, int(doc_id))
        if not removed:
            # A stale/missing id may hide a document re-created by a retried
            # upload; fall back to the stable per-material filename.
            await rag_client.delete_document_by_name(group, material.rag_filename)
    else:
        await rag_client.delete_document_by_name(group, material.rag_filename)

    material.vector_doc_id = None
    return True


async def soft_delete_material(
    db: AsyncSession,
    actor: User,
    material: Material,
    *,
    rag_client: RagClient,
    ip: str | None = None,
) -> None:
    if material.status == MATERIAL_STATUS_DELETED:
        raise NotFoundError("资料不存在")
    if material.index_status == INDEX_STATUS_INDEXING:
        raise ConflictError("资料正在索引中，请稍后再删除")

    previous_doc_id = material.vector_doc_id
    rag_synced = await delete_material_rag_document(material, rag_client)

    material.status = MATERIAL_STATUS_DELETED
    await record_audit(
        db,
        action=ACTION_MATERIAL_DELETE,
        actor=actor,
        target_type="material",
        target_id=material.id,
        detail={
            "title": material.title,
            "course": material.course.title if material.course else None,
            "vector_doc_id": previous_doc_id,
            "rag_vector_deleted": rag_synced,
        },
        ip=ip,
    )
    await db.commit()


async def _touch_material_view(db: AsyncSession, user: User, material: Material) -> None:
    """Record the latest time this user opened the material."""
    view = await db.scalar(
        select(MaterialView).where(
            MaterialView.user_id == user.id,
            MaterialView.material_id == material.id,
        )
    )
    if view is None:
        db.add(MaterialView(user_id=user.id, material_id=material.id))
    else:
        view.viewed_at = utc_now()


async def register_view(
    db: AsyncSession, material: Material, user: User, *, increment: bool = True
) -> int:
    if increment:
        material.view_count += 1
    await _touch_material_view(db, user, material)
    await db.commit()
    return material.view_count


async def register_download(db: AsyncSession, material: Material, user: User | None = None) -> None:
    material.download_count += 1
    if user is not None:
        await _touch_material_view(db, user, material)
    await db.commit()


async def index_material(
    material_id: int,
    session_factory: async_sessionmaker[AsyncSession],
    rag_client: RagClient,
) -> None:
    """Background indexer: mark indexing, ensure the course group, upload the file."""
    async with session_factory() as db:
        material = await db.scalar(
            select(Material).options(*MATERIAL_LOAD).where(Material.id == material_id)
        )
        if material is None or material.status != MATERIAL_STATUS_APPROVED:
            return

        material.index_status = INDEX_STATUS_INDEXING
        material.index_error = None
        await db.commit()

        try:
            if material.scope == MATERIAL_SCOPE_PERSONAL:
                knowledge_base = material.knowledge_base
                if knowledge_base is None or knowledge_base.status != KB_STATUS_ACTIVE:
                    raise RagError("知识库不存在或已删除")
                if knowledge_base.rag_group_id is None:
                    group_id = await rag_client.ensure_group(f"edumate-kb-{knowledge_base.id}")
                    knowledge_base.rag_group_id = group_id
                    await db.commit()
                else:
                    group_id = knowledge_base.rag_group_id
                group_label = f"kb={knowledge_base.id}"
            else:
                course = material.course
                if course is None:
                    raise RagError("课程不存在")
                if course.rag_group_id is None:
                    group_id = await rag_client.ensure_group(f"edumate-course-{course.id}")
                    course.rag_group_id = group_id
                    await db.commit()
                else:
                    group_id = course.rag_group_id
                group_label = f"course={course.id}"

            path = material_absolute_path(material)
            result = await rag_client.upload_document(
                group_id,
                filename=material.rag_filename,
                path=path,
                content_type=ALLOWED_MATERIAL_SUFFIXES.get(material.file_type),
            )
            material.vector_doc_id = str(result.get("doc_id"))
            material.index_status = INDEX_STATUS_INDEXED
            material.index_error = None
            material.indexed_at = utc_now()
            await db.commit()
            logger.info(
                "material indexed: id=%s %s doc_id=%s",
                material.id,
                group_label,
                material.vector_doc_id,
            )
        except Exception as exc:  # noqa: BLE001 - all RAG failures must be recorded
            logger.exception("material indexing failed: id=%s", material_id)
            await db.rollback()
            failed = await db.get(Material, material_id)
            if failed is not None:
                failed.index_status = INDEX_STATUS_FAILED
                failed.index_error = str(exc)[:500]
                await db.commit()
