from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models.user import User
from app.schemas.api_key import APIKeyCreate, APIKeyPublic, APIKeyResponse, APIKeyUpdate
from app.services.api_key_service import (
    create_api_key,
    get_api_keys_for_user,
    revoke_api_key,
    update_api_key,
)
from app.core.config import settings

router = APIRouter(prefix="/api-keys", tags=["API Keys"])


def _to_public(api_key) -> APIKeyPublic:
    """Convert a full APIKey to a redacted public view."""
    raw = api_key.key
    preview = f"{raw[:6]}...{raw[-4:]}" if len(raw) > 10 else raw
    return APIKeyPublic(
        id=api_key.id,
        name=api_key.name,
        user_id=api_key.user_id,
        rate_limit=api_key.rate_limit,
        rate_limit_window=api_key.rate_limit_window,
        usage_count=api_key.usage_count,
        is_active=api_key.is_active,
        created_at=api_key.created_at,
        last_used_at=api_key.last_used_at,
        key_preview=preview,
    )


@router.post(
    "",
    response_model=APIKeyResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Generate a new API key for the current user",
)
async def create_key(
    payload: APIKeyCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Returns the **full key once** — store it securely, it won't be shown again.
    """
    api_key = await create_api_key(db, user_id=current_user.id, data=payload)
    return api_key


@router.get(
    "",
    response_model=list[APIKeyPublic],
    summary="List all API keys for the current user (keys are redacted)",
)
async def list_keys(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    keys = await get_api_keys_for_user(db, current_user.id)
    return [_to_public(k) for k in keys]


@router.patch(
    "/{key_id}",
    response_model=APIKeyPublic,
    summary="Update rate limit or name for a specific API key",
)
async def update_key(
    key_id: str,
    payload: APIKeyUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    keys = await get_api_keys_for_user(db, current_user.id)
    api_key = next((k for k in keys if k.id == key_id), None)
    if not api_key:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="API key not found")

    updated = await update_api_key(db, api_key, payload)
    return _to_public(updated)


@router.delete(
    "/{key_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Revoke an API key",
)
async def revoke_key(
    key_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    keys = await get_api_keys_for_user(db, current_user.id)
    api_key = next((k for k in keys if k.id == key_id), None)
    if not api_key:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="API key not found")
    await revoke_api_key(db, api_key)
