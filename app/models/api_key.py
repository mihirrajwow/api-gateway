import secrets
import uuid
from datetime import datetime, timezone

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.session import Base


def _generate_api_key() -> str:
    """Generate a cryptographically secure, prefixed API key."""
    return f"gw_{secrets.token_urlsafe(32)}"


class APIKey(Base):
    __tablename__ = "api_keys"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    key: Mapped[str] = mapped_column(
        String(64), unique=True, nullable=False, index=True, default=_generate_api_key
    )
    user_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(100), nullable=False, default="Default Key")
    rate_limit: Mapped[int] = mapped_column(Integer, nullable=False, default=100)
    rate_limit_window: Mapped[int] = mapped_column(
        Integer, nullable=False, default=60, comment="Window in seconds"
    )
    usage_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    last_used_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="api_keys")  # noqa: F821

    def __repr__(self) -> str:
        return f"<APIKey id={self.id} user_id={self.user_id} rate_limit={self.rate_limit}>"
