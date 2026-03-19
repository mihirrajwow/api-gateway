from datetime import datetime, timezone

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import logger
from app.models.api_key import APIKey
from app.schemas.api_key import APIKeyCreate, APIKeyUpdate


async def create_api_key(db: AsyncSession, user_id: str, data: APIKeyCreate) -> APIKey:
    api_key = APIKey(
        user_id=user_id,
        name=data.name,
        rate_limit=data.rate_limit,
        rate_limit_window=data.rate_limit_window,
    )
    db.add(api_key)
    await db.flush()
    logger.info(f"API key created | id={api_key.id} user={user_id}")
    return api_key


async def get_api_key_by_key(db: AsyncSession, key: str) -> APIKey | None:
    result = await db.execute(
        select(APIKey).where(APIKey.key == key, APIKey.is_active == True)  # noqa: E712
    )
    return result.scalar_one_or_none()


async def get_api_keys_for_user(db: AsyncSession, user_id: str) -> list[APIKey]:
    result = await db.execute(
        select(APIKey).where(APIKey.user_id == user_id).order_by(APIKey.created_at.desc())
    )
    return list(result.scalars().all())


async def update_api_key(db: AsyncSession, api_key: APIKey, data: APIKeyUpdate) -> APIKey:
    if data.name is not None:
        api_key.name = data.name
    if data.rate_limit is not None:
        api_key.rate_limit = data.rate_limit
    if data.rate_limit_window is not None:
        api_key.rate_limit_window = data.rate_limit_window
    if data.is_active is not None:
        api_key.is_active = data.is_active
    await db.flush()
    logger.info(f"API key updated | id={api_key.id}")
    return api_key


async def revoke_api_key(db: AsyncSession, api_key: APIKey) -> None:
    api_key.is_active = False
    await db.flush()
    logger.info(f"API key revoked | id={api_key.id}")


async def record_api_key_usage(db: AsyncSession, api_key_id: str) -> None:
    """Increment usage count and update last_used_at (fire-and-forget style)."""
    await db.execute(
        update(APIKey)
        .where(APIKey.id == api_key_id)
        .values(
            usage_count=APIKey.usage_count + 1,
            last_used_at=datetime.now(timezone.utc),
        )
    )
