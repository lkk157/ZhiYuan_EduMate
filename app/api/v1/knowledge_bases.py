"""Student personal knowledge base endpoints."""

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
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.api.deps import require_role
from app.core.errors import NotFoundError, success
from app.db.models.knowledge_base import KnowledgeBase
from app.db.models.material import (
    INDEX_STATUSES,
    MATERIAL_SCOPE_PERSONAL,
    MATERIAL_STATUS_DELETED,
    Material,
)
from app.db.models.rbac import ROLE_STUDENT, User
from app.db.session import get_db, get_session_factory
from app.schemas.knowledge_base import (
    KnowledgeBaseCreateRequest,
    KnowledgeBaseUpdateRequest,
    knowledge_base_out,
)
from app.schemas.material import material_list_out
from app.services import knowledge_base_service, material_service
from app.services.audit_service import client_ip
from app.services.material_service import index_material
from app.services.rag_client import RagClient, get_rag_client

router = APIRouter(prefix="/knowledge-bases", tags=["knowledge-bases"])

INDEX_STATUS_PATTERN = f"^({'|'.join(sorted(INDEX_STATUSES))})$"


async def _load_personal_material(
    db: AsyncSession, kb: KnowledgeBase, material_id: int
) -> Material:
    material = await material_service.get_material(db, material_id)
    if (
        material.scope != MATERIAL_SCOPE_PERSONAL
        or material.knowledge_base_id != kb.id
        or material.status == MATERIAL_STATUS_DELETED
    ):
        raise NotFoundError("资料不存在")
    return material


@router.get("")
async def list_knowledge_bases(
    user: User = Depends(require_role(ROLE_STUDENT)),
    db: AsyncSession = Depends(get_db),
) -> dict:
    entries = await knowledge_base_service.list_knowledge_bases(db, user)
    return success(
        {
            "items": [
                knowledge_base_out(kb, material_count=count, indexed_count=indexed)
                for kb, count, indexed in entries
            ]
        }
    )


@router.post("", status_code=status.HTTP_201_CREATED)
async def create_knowledge_base(
    body: KnowledgeBaseCreateRequest,
    request: Request,
    user: User = Depends(require_role(ROLE_STUDENT)),
    db: AsyncSession = Depends(get_db),
) -> dict:
    kb = await knowledge_base_service.create_knowledge_base(
        db,
        user,
        name=body.name,
        description=body.description,
        ip=client_ip(request),
    )
    return success(knowledge_base_out(kb), "知识库创建成功")


@router.put("/{kb_id}")
async def update_knowledge_base(
    kb_id: int,
    body: KnowledgeBaseUpdateRequest,
    request: Request,
    user: User = Depends(require_role(ROLE_STUDENT)),
    db: AsyncSession = Depends(get_db),
) -> dict:
    kb = await knowledge_base_service.get_owned_kb(db, user, kb_id)
    updated = await knowledge_base_service.update_knowledge_base(
        db,
        user,
        kb,
        changes=body.model_dump(exclude_unset=True),
        ip=client_ip(request),
    )
    return success(knowledge_base_out(updated), "知识库已更新")


@router.delete("/{kb_id}")
async def delete_knowledge_base(
    kb_id: int,
    request: Request,
    user: User = Depends(require_role(ROLE_STUDENT)),
    db: AsyncSession = Depends(get_db),
) -> dict:
    kb = await knowledge_base_service.get_owned_kb(db, user, kb_id)
    await knowledge_base_service.soft_delete_knowledge_base(db, user, kb, ip=client_ip(request))
    return success({"deleted": True, "knowledge_base_id": kb_id}, "知识库已删除")


@router.get("/{kb_id}/materials")
async def list_personal_materials(
    kb_id: int,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    index_status: str | None = Query(default=None, pattern=INDEX_STATUS_PATTERN),
    user: User = Depends(require_role(ROLE_STUDENT)),
    db: AsyncSession = Depends(get_db),
) -> dict:
    kb = await knowledge_base_service.get_owned_kb(db, user, kb_id)
    items, total = await knowledge_base_service.list_personal_materials(
        db, kb, page=page, page_size=page_size, index_status=index_status
    )
    return success(
        {
            "items": [material_list_out(item, management=True) for item in items],
            "total": total,
            "page": page,
            "page_size": page_size,
        }
    )


@router.post("/{kb_id}/materials", status_code=status.HTTP_201_CREATED)
async def upload_personal_material(
    kb_id: int,
    request: Request,
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    title: str | None = Form(default=None),
    user: User = Depends(require_role(ROLE_STUDENT)),
    db: AsyncSession = Depends(get_db),
    session_factory: async_sessionmaker = Depends(get_session_factory),
    rag_client: RagClient = Depends(get_rag_client),
) -> dict:
    kb = await knowledge_base_service.get_owned_kb(db, user, kb_id)
    material = await material_service.create_material(
        db,
        knowledge_base=kb,
        uploader=user,
        upload=file,
        title=title,
        ip=client_ip(request),
    )
    background_tasks.add_task(index_material, material.id, session_factory, rag_client)
    return success(
        material_list_out(material, management=True),
        "资料已上传，正在后台索引",
    )


@router.delete("/{kb_id}/materials/{material_id}")
async def delete_personal_material(
    kb_id: int,
    material_id: int,
    request: Request,
    user: User = Depends(require_role(ROLE_STUDENT)),
    db: AsyncSession = Depends(get_db),
) -> dict:
    kb = await knowledge_base_service.get_owned_kb(db, user, kb_id)
    material = await _load_personal_material(db, kb, material_id)
    await material_service.ensure_material_access(db, material, user, management=True)
    await material_service.soft_delete_material(db, user, material, ip=client_ip(request))
    return success({"deleted": True, "material_id": material_id}, "资料已删除")


@router.post("/{kb_id}/materials/{material_id}/index/retry")
async def retry_personal_material(
    kb_id: int,
    material_id: int,
    request: Request,
    background_tasks: BackgroundTasks,
    user: User = Depends(require_role(ROLE_STUDENT)),
    db: AsyncSession = Depends(get_db),
    session_factory: async_sessionmaker = Depends(get_session_factory),
    rag_client: RagClient = Depends(get_rag_client),
) -> dict:
    kb = await knowledge_base_service.get_owned_kb(db, user, kb_id)
    material = await _load_personal_material(db, kb, material_id)
    await material_service.ensure_material_access(db, material, user, management=True)
    retried = await material_service.retry_material_index(db, user, material, ip=client_ip(request))
    background_tasks.add_task(index_material, retried.id, session_factory, rag_client)
    return success(material_list_out(retried, management=True), "已重新提交索引")
