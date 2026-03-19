from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.request_log import RequestLog
from app.schemas.auth import RequestLogPage, RequestLogResponse


async def create_request_log(
    db: AsyncSession,
    *,
    user_id: str,
    api_key_id: str,
    endpoint: str,
    method: str,
    status_code: int,
    response_time_ms: int | None = None,
    ip_address: str | None = None,
) -> RequestLog:
    log = RequestLog(
        user_id=user_id,
        api_key_id=api_key_id,
        endpoint=endpoint,
        method=method,
        status_code=status_code,
        response_time_ms=response_time_ms,
        ip_address=ip_address,
    )
    db.add(log)
    await db.flush()
    return log


async def get_logs_for_user(
    db: AsyncSession,
    user_id: str,
    page: int = 1,
    page_size: int = 50,
) -> RequestLogPage:
    offset = (page - 1) * page_size

    count_result = await db.execute(
        select(func.count()).select_from(RequestLog).where(RequestLog.user_id == user_id)
    )
    total = count_result.scalar_one()

    result = await db.execute(
        select(RequestLog)
        .where(RequestLog.user_id == user_id)
        .order_by(RequestLog.timestamp.desc())
        .limit(page_size)
        .offset(offset)
    )
    items = [RequestLogResponse.model_validate(r) for r in result.scalars().all()]

    return RequestLogPage(total=total, page=page, page_size=page_size, items=items)
