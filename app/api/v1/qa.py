"""Scoped RAG Q&A and personal question history endpoints."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import require_permission
from app.core.errors import success
from app.db.models.qa import QA_SCOPES, QA_STATUS_SUCCESS
from app.db.models.rbac import User
from app.db.session import get_db
from app.schemas.qa import AskRequest, qa_record_out
from app.services import qa_service
from app.services.rag_client import RagClient, get_rag_client

router = APIRouter(prefix="/qa", tags=["qa"])

SCOPE_PATTERN = f"^({'|'.join(sorted(QA_SCOPES))})$"


@router.post("/ask")
async def ask(
    body: AskRequest,
    user: User = Depends(require_permission("qa:ask")),
    db: AsyncSession = Depends(get_db),
    rag_client: RagClient = Depends(get_rag_client),
) -> dict:
    record = await qa_service.ask_question(db, user, body, rag_client)
    message = (
        "问答完成" if record.status == QA_STATUS_SUCCESS else "智能问答服务暂时不可用，已降级并记录"
    )
    return success(qa_record_out(record), message)


@router.get("/history")
async def history(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    course_id: int | None = Query(default=None, ge=1),
    knowledge_base_id: int | None = Query(default=None, ge=1),
    scope: str | None = Query(default=None, pattern=SCOPE_PATTERN),
    user: User = Depends(require_permission("qa:ask")),
    db: AsyncSession = Depends(get_db),
) -> dict:
    items, total = await qa_service.list_history(
        db,
        user,
        page=page,
        page_size=page_size,
        course_id=course_id,
        knowledge_base_id=knowledge_base_id,
        scope=scope,
    )
    return success(
        {
            "items": [qa_record_out(item) for item in items],
            "total": total,
            "page": page,
            "page_size": page_size,
        }
    )
