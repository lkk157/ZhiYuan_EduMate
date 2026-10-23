"""Recommendations and the student home aggregate."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import require_role
from app.core.errors import success
from app.db.models.rbac import ROLE_STUDENT, User
from app.db.session import get_db
from app.services import recommend_service

router = APIRouter(tags=["recommend"])


@router.get("/recommendations")
async def get_recommendations(
    course_id: int | None = Query(default=None, ge=1),
    material_id: int | None = Query(default=None, ge=1),
    limit: int = Query(
        recommend_service.RECOMMEND_DEFAULT_LIMIT,
        ge=1,
        le=recommend_service.RECOMMEND_MAX_LIMIT,
    ),
    user: User = Depends(require_role(ROLE_STUDENT)),
    db: AsyncSession = Depends(get_db),
) -> dict:
    data = await recommend_service.get_recommendations(
        db,
        user,
        course_id=course_id,
        material_id=material_id,
        limit=limit,
    )
    return success(data)


@router.get("/home/overview")
async def student_home(
    user: User = Depends(require_role(ROLE_STUDENT)),
    db: AsyncSession = Depends(get_db),
) -> dict:
    return success(await recommend_service.student_home(db, user))
