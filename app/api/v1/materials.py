"""Course material upload, review, indexing and download endpoints."""

from __future__ import annotations

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
from app.core.errors import NotFoundError, success
from app.db.models.material import ALLOWED_MATERIAL_SUFFIXES, INDEX_STATUSES, MATERIAL_STATUSES
from app.db.models.rbac import ROLE_ADMIN, ROLE_TEACHER, User
from app.db.session import get_db, get_session_factory
from app.schemas.material import MaterialReviewRequest, material_list_out
from app.services import course_service, material_service
from app.services.audit_service import client_ip
from app.services.material_service import index_material
from app.services.rag_client import RagClient, get_rag_client

router = APIRouter(prefix="/materials", tags=["materials"])

MATERIAL_STATUS_PATTERN = f"^({'|'.join(sorted(MATERIAL_STATUSES))})$"
INDEX_STATUS_PATTERN = f"^({'|'.join(sorted(INDEX_STATUSES))})$"


def _management_view(user: User) -> bool:
    return user.role.name in {ROLE_ADMIN, ROLE_TEACHER}


@router.get("")
async def list_materials(
    course_id: int | None = Query(default=None, ge=1),
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
        await course_service.get_accessible_course(db, user, course_id)
    items, total = await material_service.list_materials(
        db,
        user,
        course_id=course_id,
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
    course_id: int = Form(...),
    file: UploadFile = File(...),
    title: str | None = Form(default=None),
    chapter_id: int | None = Form(default=None),
    knowledge_id: int | None = Form(default=None),
    user: User = Depends(require_permission("material:upload")),
    db: AsyncSession = Depends(get_db),
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
    return success(material_list_out(material, management=True), "资料已上传，等待管理员审核")


@router.get("/{material_id}")
async def get_material(
    material_id: int,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    material = await material_service.get_material(db, material_id)
    await material_service.ensure_material_access(db, material, user)
    return success(material_list_out(material, management=_management_view(user)))


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
    await material_service.register_download(db, material)
    return FileResponse(
        path=path,
        filename=material.source_filename,
        media_type=ALLOWED_MATERIAL_SUFFIXES.get(material.file_type),
    )
