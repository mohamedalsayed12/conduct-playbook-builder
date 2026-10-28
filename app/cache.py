"""Redis client and connectivity helpers."""

from __future__ import annotations

from functools import lru_cache
from typing import TYPE_CHECKING

from redis import Redis
from redis.exceptions import RedisError

from app.config import get_settings

if TYPE_CHECKING:
    RedisClient = Redis[str]
else:
    RedisClient = Redis


@lru_cache
def get_redis() -> RedisClient:
    """Create (and cache) a Redis client from settings."""
    return Redis.from_url(
        get_settings().redis_url,
        decode_responses=True,
        socket_connect_timeout=1,
        socket_timeout=1,
    )


def check_redis(client: RedisClient | None = None) -> bool:
    """Return True when Redis responds to PING."""
    target = client if client is not None else get_redis()
    try:
        return bool(target.ping())
    except (RedisError, OSError):
        return False


def reset_redis_cache() -> None:
    """Clear the cached Redis client so tests can rebind settings."""
    get_redis.cache_clear()
