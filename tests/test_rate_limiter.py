import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from app.services.rate_limiter import RateLimiter


def _make_redis_mock(evalsha_return):
    mock = AsyncMock()
    mock.script_load = AsyncMock(return_value="fake_sha")
    mock.evalsha = AsyncMock(return_value=evalsha_return)
    return mock


@pytest.mark.asyncio
async def test_rate_limiter_allows_request():
    redis = _make_redis_mock([1, 5, 0])  # allowed=1, used=5, reset=0
    limiter = RateLimiter(redis)

    allowed, info = await limiter.is_allowed("user1", "/api/v1/gateway/ping", 100, 60)

    assert allowed is True
    assert info["remaining"] == 95
    assert info["used"] == 5
    assert info["limit"] == 100


@pytest.mark.asyncio
async def test_rate_limiter_blocks_when_exceeded():
    redis = _make_redis_mock([0, 100, 1700000000000])  # allowed=0
    limiter = RateLimiter(redis)

    allowed, info = await limiter.is_allowed("user1", "/api/v1/gateway/ping", 100, 60)

    assert allowed is False
    assert info["remaining"] == 0


@pytest.mark.asyncio
async def test_rate_limiter_fails_open_on_redis_error():
    redis = AsyncMock()
    redis.script_load = AsyncMock(side_effect=ConnectionError("Redis down"))
    limiter = RateLimiter(redis)

    # Should NOT raise — fail open
    allowed, info = await limiter.is_allowed("user1", "/endpoint", 100, 60)
    assert allowed is True


@pytest.mark.asyncio
async def test_rate_limiter_reset():
    redis = AsyncMock()
    redis.delete = AsyncMock()
    limiter = RateLimiter(redis)

    await limiter.reset("user1", "/endpoint")
    redis.delete.assert_called_once_with("rl:user1:/endpoint")


@pytest.mark.asyncio
async def test_rate_limiter_per_endpoint_isolation():
    """Different endpoints must use different Redis keys."""
    keys_called = []

    async def track_evalsha(sha, num_keys, key, *args):
        keys_called.append(key)
        return [1, 1, 0]

    redis = AsyncMock()
    redis.script_load = AsyncMock(return_value="sha")
    redis.evalsha = AsyncMock(side_effect=track_evalsha)
    limiter = RateLimiter(redis)

    await limiter.is_allowed("u1", "/endpoint/a", 10, 60)
    await limiter.is_allowed("u1", "/endpoint/b", 10, 60)

    assert keys_called[0] != keys_called[1]
    assert "endpoint/a" in keys_called[0]
    assert "endpoint/b" in keys_called[1]
