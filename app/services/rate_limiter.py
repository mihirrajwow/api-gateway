"""
Sliding-window rate limiter backed by Redis.

Algorithm
---------
Uses a sorted set per (user_id, endpoint) key.
  • Score  = arrival timestamp in milliseconds
  • Member = unique request ID

On each request:
  1. Remove all members with score < (now - window_ms)  → prune old entries
  2. Count remaining members                            → current usage
  3. If count >= limit  → REJECT (429)
  4. Otherwise add new member with score=now and set TTL → ALLOW

The entire check-and-increment is executed as an atomic Lua script to
prevent race conditions under high concurrency.
"""

import time
import uuid

from redis.asyncio import Redis

from app.core.logging import logger

# Atomic Lua script — executes as a single Redis command
_SLIDING_WINDOW_SCRIPT = """
local key       = KEYS[1]
local now       = tonumber(ARGV[1])
local window_ms = tonumber(ARGV[2])
local limit     = tonumber(ARGV[3])
local req_id    = ARGV[4]

-- 1. Remove expired entries
redis.call('ZREMRANGEBYSCORE', key, 0, now - window_ms)

-- 2. Count current requests in window
local count = redis.call('ZCARD', key)

if count >= limit then
    -- 3. Rejected — return remaining TTL info
    local oldest = redis.call('ZRANGE', key, 0, 0, 'WITHSCORES')
    local reset_at = 0
    if #oldest > 0 then
        reset_at = tonumber(oldest[2]) + window_ms
    end
    return {0, count, reset_at}
end

-- 4. Add this request
redis.call('ZADD', key, now, req_id)
redis.call('PEXPIRE', key, window_ms)

return {1, count + 1, 0}
"""


class RateLimiter:
    """Sliding-window rate limiter. One instance is shared across the app."""

    def __init__(self, redis: Redis) -> None:
        self._redis = redis
        self._script_sha: str | None = None

    async def _load_script(self) -> str:
        """Load the Lua script into Redis and cache its SHA."""
        if self._script_sha is None:
            self._script_sha = await self._redis.script_load(_SLIDING_WINDOW_SCRIPT)
        return self._script_sha

    async def is_allowed(
        self,
        user_id: str,
        endpoint: str,
        limit: int,
        window_seconds: int,
    ) -> tuple[bool, dict]:
        """
        Check whether this request is within the rate limit.

        Returns
        -------
        allowed : bool
        info    : dict with keys remaining, limit, reset_at (epoch ms)
        """
        key = f"rl:{user_id}:{endpoint}"
        now_ms = int(time.time() * 1000)
        window_ms = window_seconds * 1000
        req_id = str(uuid.uuid4())

        try:
            sha = await self._load_script()
            result = await self._redis.evalsha(
                sha, 1, key, now_ms, window_ms, limit, req_id
            )
            allowed_flag, current_count, reset_at_ms = result

            allowed = bool(allowed_flag)
            remaining = max(0, limit - int(current_count))
            info = {
                "limit": limit,
                "remaining": remaining,
                "used": int(current_count),
                "window_seconds": window_seconds,
                "reset_at_ms": int(reset_at_ms),
            }
            logger.debug(
                f"Rate check | user={user_id} endpoint={endpoint} "
                f"allowed={allowed} used={current_count}/{limit}"
            )
            return allowed, info

        except Exception as exc:
            # Fail open — don't block requests if Redis is temporarily unavailable
            logger.error(f"Rate limiter Redis error: {exc} — failing open")
            return True, {"limit": limit, "remaining": limit, "used": 0,
                          "window_seconds": window_seconds, "reset_at_ms": 0}

    async def reset(self, user_id: str, endpoint: str) -> None:
        """Delete the rate limit key for a user+endpoint (admin/test use)."""
        key = f"rl:{user_id}:{endpoint}"
        await self._redis.delete(key)
        logger.info(f"Rate limit reset | user={user_id} endpoint={endpoint}")
