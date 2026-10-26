"""Course material upload, review, indexing and download endpoints."""

from __future__ import annotations

import logging
from pathlib import Path

from fastapi import (
    APIRouter,
    BackgroundTasks,
    Depends,
    File,
    Form,
    Query,
    Request,
    UploadFile,
    status,
)
from fastapi.responses import FileResponse
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.api.deps import get_current_user, require_permission
from app.core.config import get_settings
from app.core.errors import AppError, NotFoundError, ValidationError, success
from app.db.models.material import (
    ALLOWED_MATERIAL_SUFFIXES,
    INDEX_STATUS_PENDING,
    INDEX_STATUSES,
    MATERIAL_SCOPE_PERSONAL,
    MATERIAL_STATUS_APPROVED,
    MATERIAL_STATUSES,
)
from app.db.models.rbac import ROLE_ADMIN, ROLE_TEACHER, User
from app.db.session import get_db, get_session_factory
from app.schemas.material import (
    MaterialMappingRequest,
    MaterialReviewRequest,
    material_list_out,
)
from app.schemas.review import BatchReviewRequest
from app.services import course_service, material_service
from app.services.audit_service import client_ip
from app.services.material_service import index_material
from app.services.rag_client import RagClient, get_rag_client

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/materials", tags=["materials"])

MATERIAL_STATUS_PATTERN = f"^({'|'.join(sorted(MATERIAL_STATUSES))})$"
INDEX_STATUS_PATTERN = f"^({'|'.join(sorted(INDEX_STATUSES))})$"


def _management_view(user: User) -> bool:
    return user.role.name in {ROLE_ADMIN, ROLE_TEACHER}


@router.get("")
async def list_materials(
    course_id: int | None = Query(default=None, ge=1),
    chapter_id: int | None = Query(default=None, ge=1),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    keyword: str | None = Query(default=None, max_length=100),
    status_filter: str | None = Query(
        default=None, alias="status", pattern=MATERIAL_STATUS_PATTERN
    ),
    index_status: str | None = Query(default=None, pattern=INDEX_STATUS_PATTERN),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    if course_id is not None:
        # Raises 403 for non-owners / students who have not joined, and 403 for
        # students when the course is not approved yet.
        course = await course_service.get_accessible_course(db, user, course_id)
        if chapter_id is not None:
            # 404 when the chapter does not belong to this course.
            course_service.get_chapter(course, chapter_id)
    items, total = await material_service.list_materials(
        db,
        user,
        course_id=course_id,
        chapter_id=chapter_id,
        page=page,
        page_size=page_size,
        keyword=keyword,
        status=status_filter,
        index_status=index_status,
    )
    management = _management_view(user)
    return success(
        {
            "items": [material_list_out(item, management=management) for item in items],
            "total": total,
            "page": page,
            "page_size": page_size,
        }
    )


@router.get("/rag-health")
async def rag_health(
    user: User = Depends(get_current_user),
    rag_client: RagClient = Depends(get_rag_client),
) -> dict:
    return success(await rag_client.health())


@router.post("", status_code=status.HTTP_201_CREATED)
async def upload_material(
    request: Request,
    background_tasks: BackgroundTasks,
    course_id: int = Form(...),
    file: UploadFile = File(...),
    title: str | None = Form(default=None),
    chapter_id: int | None = Form(default=None),
    knowledge_id: int | None = Form(default=None),
    user: User = Depends(require_permission("material:upload")),
    db: AsyncSession = Depends(get_db),
    session_factory: async_sessionmaker = Depends(get_session_factory),
    rag_client: RagClient = Depends(get_rag_client),
) -> dict:
    course = await course_service.get_accessible_course(db, user, course_id, for_management=True)
    material = await material_service.create_material(
        db,
        course=course,
        uploader=user,
        upload=file,
        title=title,
        chapter_id=chapter_id,
        knowledge_id=knowledge_id,
        ip=client_ip(request),
    )
    auto_approved = (
        material.status == MATERIAL_STATUS_APPROVED
        and material.index_status == INDEX_STATUS_PENDING
    )
    if auto_approved:
        background_tasks.add_task(index_material, material.id, session_factory, rag_client)
    message = "资料已自动审核通过，正在后台索引" if auto_approved else "资料已上传，等待管理员审核"
    return success(material_list_out(material, management=True), message)


@router.post("/batch", status_code=status.HTTP_201_CREATED)
async def upload_materials_batch(
    request: Request,
    background_tasks: BackgroundTasks,
    course_id: int = Form(...),
    files: list[UploadFile] = File(...),
    title: str | None = Form(default=None),
    chapter_id: int | None = Form(default=None),
    knowledge_id: int | None = Form(default=None),
    user: User = Depends(require_permission("material:upload")),
    db: AsyncSession = Depends(get_db),
    session_factory: async_sessionmaker = Depends(get_session_factory),
    rag_client: RagClient = Depends(get_rag_client),
) -> dict:
    if not files:
        raise ValidationError("请选择要上传的资料文件")
    if len(files) > material_service.MAX_BATCH_FILES:
        raise ValidationError(f"单次最多上传 {material_service.MAX_BATCH_FILES} 个文件")

    settings = get_settings()
    invalid_type = [
        upload.filename or ""
        for upload in files
        if Path(upload.filename or "").suffix.lower() not in ALLOWED_MATERIAL_SUFFIXES
    ]
    if invalid_type:
        raise ValidationError(
            "部分文件类型不支持",
            data={
                "errors": [
                    {"filename": name, "message": "不支持的文件类型"} for name in invalid_type
                ]
            },
        )
    too_large = [
        upload.filename or ""
        for upload in files
        if int(getattr(upload, "size", 0) or 0) > settings.max_upload_bytes
    ]
    if too_large:
        raise ValidationError(
            f"单个文件不能超过 {settings.max_upload_mb}MB",
            data={
                "errors": [{"filename": name, "message": "文件超过大小限制"} for name in too_large]
            },
        )

    course = await course_service.get_accessible_course(db, user, course_id, for_management=True)
    if chapter_id is not None:
        chapter = next((item for item in course.chapters if item.id == chapter_id), None)
        if chapter is None:
            raise ValidationError("章节不属于该课程")
        if knowledge_id is not None and not any(
            item.id == knowledge_id for item in chapter.knowledges
        ):
            raise ValidationError("知识点不属于所选章节")
    elif knowledge_id is not None:
        raise ValidationError("选择知识点前请先选择章节")

    shared_title = title.strip() if title and title.strip() else None
    items = []
    errors = []
    auto_ids: list[int] = []
    for index, upload in enumerate(files):
        filename = upload.filename or ""
        try:
            material = await material_service.create_material(
                db,
                course=course,
                uploader=user,
                upload=upload,
                # A shared title would be ambiguous for a batch; each file
                # falls back to its own filename in that case.
                title=shared_title if len(files) == 1 else None,
                chapter_id=chapter_id,
                knowledge_id=knowledge_id,
                ip=client_ip(request),
            )
            items.append(material_list_out(material, management=True))
            if (
                material.status == MATERIAL_STATUS_APPROVED
                and material.index_status == INDEX_STATUS_PENDING
            ):
                auto_ids.append(material.id)
        except AppError as exc:
            await db.rollback()
            errors.append({"filename": filename, "code": exc.code, "message": exc.message})
            # The rollback expires ORM instances; stop rather than reuse them.
            for rest in files[index + 1 :]:
                errors.append(
                    {
                        "filename": rest.filename or "",
                        "code": exc.code,
                        "message": "前一个文件失败，未处理",
                    }
                )
                await rest.close()
            break
        except Exception:  # noqa: BLE001 - record and stop the batch safely
            await db.rollback()
            logger.exception("batch material upload failed: %s", filename)
            errors.append({"filename": filename, "code": 5000, "message": "上传失败，请重试"})
            for rest in files[index + 1 :]:
                errors.append(
                    {
                        "filename": rest.filename or "",
                        "code": 5000,
                        "message": "前一个文件失败，未处理",
                    }
                )
                await rest.close()
            break
        finally:
            await upload.close()

    if not items:
        message = errors[0]["message"] if errors else "资料上传失败"
        raise ValidationError(message, data={"errors": errors})

    for material_id in auto_ids:
        background_tasks.add_task(index_material, material_id, session_factory, rag_client)

    if errors:
        message = f"成功上传 {len(items)} 个资料，{len(errors)} 个失败"
    elif auto_ids:
        message = f"成功上传 {len(items)} 个资料并自动审核通过，正在后台索引"
    else:
        message = f"成功上传 {len(items)} 个资料，等待管理员审核"
    return success(
        {
            "items": items,
            "succeeded": len(items),
            "failed": len(errors),
            "errors": errors,
            "auto_approved": len(auto_ids),
        },
        message,
    )


@router.post("/batch/review")
async def batch_review_materials(
    body: BatchReviewRequest,
    request: Request,
    background_tasks: BackgroundTasks,
    reviewer: User = Depends(require_permission("material:review")),
    db: AsyncSession = Depends(get_db),
    session_factory: async_sessionmaker = Depends(get_session_factory),
    rag_client: RagClient = Depends(get_rag_client),
) -> dict:
    succeeded: list[dict] = []
    errors: list[dict] = []
    approved_ids: list[int] = []
    for material_id in body.ids:
        try:
            material = await material_service.get_material(db, material_id)
            reviewed = await material_service.review_material(
                db,
                reviewer,
                material,
                decision=body.decision,
                comment=body.comment,
                ip=client_ip(request),
            )
            succeeded.append({"id": reviewed.id, "title": reviewed.title})
            if body.decision == "approve":
                approved_ids.append(reviewed.id)
        except AppError as exc:
            await db.rollback()
            errors.append({"id": material_id, "code": exc.code, "message": exc.message})
        except Exception:  # noqa: BLE001 - batch keeps processing after one failure
            await db.rollback()
            errors.append({"id": material_id, "code": 5000, "message": "审核失败，请重试"})

    for material_id in approved_ids:
        background_tasks.add_task(index_material, material_id, session_factory, rag_client)

    action = "通过" if body.decision == "approve" else "驳回"
    message = f"已{action} {len(succeeded)} 份资料"
    if errors:
        message += f"，{len(errors)} 份失败"
    if approved_ids:
        message += "，正在后台索引"
    return success(
        {"succeeded": succeeded, "failed": errors, "count": len(succeeded)},
        message,
    )


@router.get("/{material_id}")
async def get_material(
    material_id: int,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    material = await material_service.get_material(db, material_id)
    await material_service.ensure_material_access(db, material, user)
    management = _management_view(user) or material.scope == MATERIAL_SCOPE_PERSONAL
    return success(material_list_out(material, management=management))


@router.put("/{material_id}/mapping")
async def update_material_mapping(
    material_id: int,
    body: MaterialMappingRequest,
    request: Request,
    user: User = Depends(require_permission("material:upload")),
    db: AsyncSession = Depends(get_db),
) -> dict:
    material = await material_service.get_material(db, material_id)
    await material_service.ensure_material_access(db, material, user, management=True)
    updated = await material_service.update_material_mapping(
        db,
        user,
        material,
        chapter_id=body.chapter_id,
        knowledge_id=body.knowledge_id,
        ip=client_ip(request),
    )
    return success(material_list_out(updated, management=True), "资料关联章节已更新")


@router.post("/{material_id}/review")
async def review_material(
    material_id: int,
    body: MaterialReviewRequest,
    request: Request,
    background_tasks: BackgroundTasks,
    reviewer: User = Depends(require_permission("material:review")),
    db: AsyncSession = Depends(get_db),
    session_factory: async_sessionmaker = Depends(get_session_factory),
    rag_client: RagClient = Depends(get_rag_client),
) -> dict:
    material = await material_service.get_material(db, material_id)
    reviewed = await material_service.review_material(
        db,
        reviewer,
        material,
        decision=body.decision,
        comment=body.comment,
        ip=client_ip(request),
    )
    if body.decision == "approve":
        background_tasks.add_task(index_material, reviewed.id, session_factory, rag_client)
    message = "资料审核通过，正在后台索引" if body.decision == "approve" else "资料已驳回"
    return success(material_list_out(reviewed, management=True), message)


@router.post("/{material_id}/index/retry")
async def retry_index(
    material_id: int,
    request: Request,
    background_tasks: BackgroundTasks,
    user: User = Depends(require_permission("material:upload")),
    db: AsyncSession = Depends(get_db),
    session_factory: async_sessionmaker = Depends(get_session_factory),
    rag_client: RagClient = Depends(get_rag_client),
) -> dict:
    material = await material_service.get_material(db, material_id)
    await material_service.ensure_material_access(db, material, user, management=True)
    retried = await material_service.retry_material_index(db, user, material, ip=client_ip(request))
    background_tasks.add_task(index_material, retried.id, session_factory, rag_client)
    return success(material_list_out(retried, management=True), "已重新提交索引，请稍候刷新")


@router.delete("/{material_id}")
async def delete_material(
    material_id: int,
    request: Request,
    user: User = Depends(require_permission("material:upload")),
    db: AsyncSession = Depends(get_db),
) -> dict:
    material = await material_service.get_material(db, material_id)
    await material_service.ensure_material_access(db, material, user, management=True)
    await material_service.soft_delete_material(db, user, material, ip=client_ip(request))
    return success({"deleted": True, "material_id": material_id}, "资料已删除")


@router.post("/{material_id}/view")
async def view_material(
    material_id: int,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    material = await material_service.get_material(db, material_id)
    await material_service.ensure_material_access(db, material, user)
    view_count = await material_service.register_view(db, material, user)
    return success(
        {"material_id": material_id, "view_count": view_count},
        "已记录浏览",
    )


@router.get("/{material_id}/preview")
async def preview_material(
    material_id: int,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> FileResponse:
    """Stream the original file inline without counting a download."""
    material = await material_service.get_material(db, material_id)
    await material_service.ensure_material_access(db, material, user)
    path = material_service.material_absolute_path(material)
    if not path.exists():
        raise NotFoundError("资料文件不存在")
    return FileResponse(
        path=path,
        media_type=ALLOWED_MATERIAL_SUFFIXES.get(material.file_type),
        headers={"Content-Disposition": "inline"},
    )


@router.get("/{material_id}/download")
async def download_material(
    material_id: int,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> FileResponse:
    material = await material_service.get_material(db, material_id)
    await material_service.ensure_material_access(db, material, user)
    path = material_service.material_absolute_path(material)
    if not path.exists():
        raise NotFoundError("资料文件不存在")
    await material_service.register_download(db, material, user)
    return FileResponse(
        path=path,
        filename=material.source_filename,
        media_type=ALLOWED_MATERIAL_SUFFIXES.get(material.file_type),
    )
