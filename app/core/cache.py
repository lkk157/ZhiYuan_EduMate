"""Redis helpers.

Redis is an optional cache. Every helper degrades gracefully: an unreachable
Redis must never take down a business request.
"""

from __future__ import annotations

import logging

import redis.asyncio as redis_async

from app.core.config import get_settings

logger = logging.getLogger(__name__)


def create_redis_client() -> redis_async.Redis | None:
    settings = get_settings()
    if not settings.redis_enabled:
        return None
    return redis_async.from_url(
        settings.redis_url,
        socket_connect_timeout=1,
        socket_timeout=1,
        decode_responses=True,
    )


async def check_redis() -> str:
    """Return ``ok`` / ``error`` / ``disabled``."""
    client = create_redis_client()
    if client is None:
        return "disabled"
    try:
        await client.ping()
        return "ok"
    except Exception as exc:  # pragma: no cover - depends on runtime state
        logger.warning("redis health check failed: %s", exc)
        return "error"
    finally:
        await client.aclose()
