from datetime import datetime

from pydantic import BaseModel, Field


class APIKeyCreate(BaseModel):
    name: str = Field(default="Default Key", max_length=100)
    rate_limit: int = Field(default=100, ge=1, le=100_000)
    rate_limit_window: int = Field(default=60, ge=1, le=86_400, description="Window in seconds")


class APIKeyUpdate(BaseModel):
    name: str | None = Field(default=None, max_length=100)
    rate_limit: int | None = Field(default=None, ge=1, le=100_000)
    rate_limit_window: int | None = Field(default=None, ge=1, le=86_400)
    is_active: bool | None = None


class APIKeyResponse(BaseModel):
    id: str
    key: str
    user_id: str
    name: str
    rate_limit: int
    rate_limit_window: int
    usage_count: int
    is_active: bool
    created_at: datetime
    last_used_at: datetime | None

    model_config = {"from_attributes": True}


class APIKeyPublic(BaseModel):
    """Redacted view — hides the raw key after initial creation."""
    id: str
    name: str
    user_id: str
    rate_limit: int
    rate_limit_window: int
    usage_count: int
    is_active: bool
    created_at: datetime
    last_used_at: datetime | None
    key_preview: str  # e.g. "gw_abc...xyz"

    model_config = {"from_attributes": True}
