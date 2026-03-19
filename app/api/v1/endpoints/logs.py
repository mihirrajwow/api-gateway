from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models.user import User
from app.schemas.auth import RequestLogPage
from app.services.log_service import get_logs_for_user

router = APIRouter(prefix="/logs", tags=["Request Logs"])


@router.get(
    "",
    response_model=RequestLogPage,
    summary="Paginated request log for the current user",
)
async def get_my_logs(
    page: int = Query(default=1, ge=1, description="Page number"),
    page_size: int = Query(default=50, ge=1, le=200, description="Items per page"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await get_logs_for_user(db, current_user.id, page=page, page_size=page_size)
