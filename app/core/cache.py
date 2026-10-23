"""Redis helpers.

Redis is an optional cache. Every helper degrades gracefully: an unreachable
Redis must never take down a business request.
"""

from __future__ import annotations

import json
import logging
from typing import Any

import redis.asyncio as redis_async

from app.core.config import get_settings

logger = logging.getLogger(__name__)

CACHE_TIMEOUT_SECONDS = 0.3
CACHE_DEFAULT_TTL = 60


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


def create_cache_client() -> redis_async.Redis | None:
    """Short-timeout client for optional request-path caching."""
    settings = get_settings()
    if not settings.redis_enabled:
        return None
    return redis_async.from_url(
        settings.redis_url,
        socket_connect_timeout=CACHE_TIMEOUT_SECONDS,
        socket_timeout=CACHE_TIMEOUT_SECONDS,
        decode_responses=True,
    )


async def cache_get_json(key: str) -> Any | None:
    """Return a cached JSON value, or ``None`` when Redis is unavailable."""
    client = create_cache_client()
    if client is None:
        return None
    try:
        raw = await client.get(key)
        return json.loads(raw) if raw else None
    except Exception as exc:  # noqa: BLE001 - cache failures must never break requests
        logger.debug("redis cache read skipped: %s", exc)
        return None
    finally:
        await client.aclose()


async def cache_set_json(key: str, value: Any, *, ttl: int = CACHE_DEFAULT_TTL) -> bool:
    """Store a JSON value; returns ``False`` when Redis is unavailable."""
    client = create_cache_client()
    if client is None:
        return False
    try:
        await client.set(key, json.dumps(value, ensure_ascii=False), ex=ttl)
        return True
    except Exception as exc:  # noqa: BLE001 - cache failures must never break requests
        logger.debug("redis cache write skipped: %s", exc)
        return False
    finally:
        await client.aclose()


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
