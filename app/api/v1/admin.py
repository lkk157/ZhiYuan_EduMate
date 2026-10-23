"""Administrator endpoints.

P1.2 only provides a permission probe used to verify RBAC; P1.3 expands this
module into full user/role/audit management.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends

from app.api.deps import require_permission
from app.core.errors import success
from app.db.models.rbac import User

router = APIRouter(prefix="/admin", tags=["admin"])


@router.get("/ping")
async def ping(user: User = Depends(require_permission("user:manage"))) -> dict:
    return success({"pong": True, "operator": user.username})
