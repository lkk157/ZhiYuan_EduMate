"""Liveness and readiness endpoints."""

from __future__ import annotations

import asyncio
import logging

from fastapi import APIRouter, Response

from app import __version__
from app.core.cache import check_redis
from app.core.config import get_settings
from app.core.errors import envelope, success
from app.db.session import check_database

logger = logging.getLogger(__name__)
router = APIRouter(tags=["health"])
settings = get_settings()


@router.get("/live")
async def liveness() -> dict:
    """Process liveness. Must not touch external dependencies."""
    return success(
        {
            "status": "ok",
            "service": settings.app_name,
            "version": __version__,
            "env": settings.app_env,
        }
    )


@router.get("/ready")
async def readiness(response: Response) -> dict:
    """Readiness: database is required, Redis is optional (degraded)."""
    database_status = "ok"
    redis_status = "ok"

    try:
        await asyncio.wait_for(check_database(), timeout=2.0)
    except Exception as exc:
        database_status = "error"
        logger.warning("database readiness check failed: %s", exc)

    try:
        redis_status = await asyncio.wait_for(check_redis(), timeout=2.0)
    except Exception as exc:
        redis_status = "error"
        logger.warning("redis readiness check failed: %s", exc)

    if database_status != "ok":
        overall = "unavailable"
        response.status_code = 503
    elif redis_status == "error":
        overall = "degraded"
    else:
        overall = "ok"

    payload = {
        "status": overall,
        "checks": {"database": database_status, "redis": redis_status},
        "version": __version__,
    }
    if overall == "unavailable":
        return envelope(payload, code=5030, message="服务未就绪")
    return success(payload)
