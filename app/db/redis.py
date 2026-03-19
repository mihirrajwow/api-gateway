from typing import AsyncGenerator

import redis.asyncio as aioredis
from redis.asyncio import Redis

from app.core.config import settings
from app.core.logging import logger

# Module-level pool — created once during app startup
_redis_pool: Redis | None = None


async def init_redis() -> None:
    """Initialise the Redis connection pool."""
    global _redis_pool
    _redis_pool = aioredis.from_url(
        settings.redis_url,
        max_connections=settings.redis_max_connections,
        encoding="utf-8",
        decode_responses=True,
    )
    # Verify connectivity
    await _redis_pool.ping()
    logger.info(f"Redis connected | url={settings.redis_url}")


async def close_redis() -> None:
    """Gracefully close the Redis pool."""
    global _redis_pool
    if _redis_pool:
        await _redis_pool.aclose()
        _redis_pool = None
        logger.info("Redis connection closed")


def get_redis_pool() -> Redis:
    """Return the live Redis pool (raises if not initialised)."""
    if _redis_pool is None:
        raise RuntimeError("Redis pool is not initialised. Call init_redis() first.")
    return _redis_pool


# FastAPI dependency
async def get_redis() -> AsyncGenerator[Redis, None]:
    yield get_redis_pool()
