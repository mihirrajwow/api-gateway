from datetime import datetime

from pydantic import BaseModel, EmailStr


# ---------------------------------------------------------------------------
# Auth
# ---------------------------------------------------------------------------
class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int  # seconds


class RefreshRequest(BaseModel):
    refresh_token: str


# ---------------------------------------------------------------------------
# Request Log
# ---------------------------------------------------------------------------
class RequestLogResponse(BaseModel):
    id: str
    user_id: str
    api_key_id: str
    endpoint: str
    method: str
    status_code: int
    response_time_ms: int | None
    ip_address: str | None
    timestamp: datetime

    model_config = {"from_attributes": True}


class RequestLogPage(BaseModel):
    total: int
    page: int
    page_size: int
    items: list[RequestLogResponse]
