"""Redis cache helpers for tenant rollout summaries."""

from __future__ import annotations

import logging
import uuid

from redis.exceptions import RedisError

from app.cache import RedisClient, get_redis

logger = logging.getLogger(__name__)

_SUMMARY_KEY_PREFIX = "summary:v1:"


def summary_cache_key(tenant_id: uuid.UUID) -> str:
    """Return the versioned Redis key for a tenant summary."""
    return f"{_SUMMARY_KEY_PREFIX}{tenant_id}"


def read_summary_cache(
    tenant_id: uuid.UUID,
    *,
    client: RedisClient | None = None,
) -> str | None:
    """Return cached JSON for the tenant summary, or None on miss/Redis failure."""
    try:
        redis = client if client is not None else get_redis()
        value = redis.get(summary_cache_key(tenant_id))
    except (RedisError, OSError):
        logger.warning(
            "summary_cache_read_failed",
            extra={"tenant_id": str(tenant_id)},
        )
        return None
    if value is None:
        return None
    return str(value)


def write_summary_cache(
    tenant_id: uuid.UUID,
    payload: str,
    *,
    ttl_seconds: int,
    client: RedisClient | None = None,
) -> None:
    """Store summary JSON in Redis; log and continue if Redis is down."""
    try:
        redis = client if client is not None else get_redis()
        redis.set(
            summary_cache_key(tenant_id),
            payload,
            ex=ttl_seconds,
        )
    except (RedisError, OSError):
        logger.warning(
            "summary_cache_write_failed",
            extra={"tenant_id": str(tenant_id)},
        )


def invalidate_summary_cache(
    tenant_id: uuid.UUID,
    *,
    client: RedisClient | None = None,
) -> None:
    """Delete the tenant summary cache key after a committed state change."""
    try:
        redis = client if client is not None else get_redis()
        redis.delete(summary_cache_key(tenant_id))
    except (RedisError, OSError):
        logger.warning(
            "summary_cache_invalidate_failed",
            extra={"tenant_id": str(tenant_id)},
        )
