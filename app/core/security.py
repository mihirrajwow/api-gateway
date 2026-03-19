from datetime import datetime, timedelta, timezone
from typing import Any

from jose import JWTError, jwt
from fastapi import HTTPException, status

from app.core.config import settings
from app.core.logging import logger


CREDENTIALS_EXCEPTION = HTTPException(
    status_code=status.HTTP_401_UNAUTHORIZED,
    detail="Could not validate credentials",
    headers={"WWW-Authenticate": "Bearer"},
)


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def create_access_token(subject: str | int, extra_claims: dict[str, Any] | None = None) -> str:
    """Create a signed JWT access token."""
    expire = _utc_now() + timedelta(minutes=settings.jwt_access_token_expire_minutes)
    payload: dict[str, Any] = {
        "sub": str(subject),
        "iat": _utc_now(),
        "exp": expire,
        "type": "access",
    }
    if extra_claims:
        payload.update(extra_claims)

    token = jwt.encode(payload, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)
    logger.debug(f"Access token created | sub={subject} | exp={expire.isoformat()}")
    return token


def create_refresh_token(subject: str | int) -> str:
    """Create a signed JWT refresh token with a longer TTL."""
    expire = _utc_now() + timedelta(days=settings.jwt_refresh_token_expire_days)
    payload: dict[str, Any] = {
        "sub": str(subject),
        "iat": _utc_now(),
        "exp": expire,
        "type": "refresh",
    }
    token = jwt.encode(payload, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)
    logger.debug(f"Refresh token created | sub={subject} | exp={expire.isoformat()}")
    return token


def decode_token(token: str) -> dict[str, Any]:
    """Decode and validate a JWT. Raises HTTP 401 on any failure."""
    try:
        payload = jwt.decode(
            token,
            settings.jwt_secret_key,
            algorithms=[settings.jwt_algorithm],
        )
        return payload
    except JWTError as exc:
        logger.warning(f"JWT decode failed: {exc}")
        raise CREDENTIALS_EXCEPTION


def get_subject(token: str) -> str:
    """Return the 'sub' claim from a valid token."""
    payload = decode_token(token)
    sub: str | None = payload.get("sub")
    if sub is None:
        raise CREDENTIALS_EXCEPTION
    return sub
