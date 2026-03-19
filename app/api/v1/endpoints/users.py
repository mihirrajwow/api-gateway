from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_current_superuser
from app.db.session import get_db
from app.models.user import User
from app.schemas.user import UserResponse, UserUpdate, UserWithKeys
from app.services.user_service import get_user_by_id, update_user

router = APIRouter(prefix="/users", tags=["Users"])


@router.get(
    "/me",
    response_model=UserWithKeys,
    summary="Get the authenticated user's profile and API keys",
)
async def get_me(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    from sqlalchemy.orm import selectinload
    from sqlalchemy import select
    from app.models.user import User as UserModel

    result = await db.execute(
        select(UserModel)
        .where(UserModel.id == current_user.id)
        .options(selectinload(UserModel.api_keys))
    )
    user = result.scalar_one()
    return user


@router.patch(
    "/me",
    response_model=UserResponse,
    summary="Update the authenticated user's email or password",
)
async def update_me(
    payload: UserUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    user = await update_user(db, current_user, payload)
    return user


@router.delete(
    "/me",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Deactivate (soft-delete) the authenticated user's account",
)
async def deactivate_me(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    current_user.is_active = False
    await db.flush()


# ------------------------------------------------------------------ #
# Admin endpoints
# ------------------------------------------------------------------ #
@router.get(
    "/{user_id}",
    response_model=UserResponse,
    summary="[Admin] Fetch any user by ID",
)
async def get_user(
    user_id: str,
    _admin: User = Depends(get_current_superuser),
    db: AsyncSession = Depends(get_db),
):
    user = await get_user_by_id(db, user_id)
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    return user
