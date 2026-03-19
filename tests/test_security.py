import pytest
from fastapi import HTTPException

from app.core.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
    get_subject,
)


def test_create_and_decode_access_token():
    token = create_access_token(subject="user-123")
    payload = decode_token(token)
    assert payload["sub"] == "user-123"
    assert payload["type"] == "access"


def test_create_and_decode_refresh_token():
    token = create_refresh_token(subject="user-456")
    payload = decode_token(token)
    assert payload["sub"] == "user-456"
    assert payload["type"] == "refresh"


def test_get_subject():
    token = create_access_token(subject="user-789")
    sub = get_subject(token)
    assert sub == "user-789"


def test_invalid_token_raises_401():
    with pytest.raises(HTTPException) as exc_info:
        decode_token("this.is.not.valid")
    assert exc_info.value.status_code == 401


def test_tampered_token_raises_401():
    token = create_access_token(subject="user-1")
    tampered = token[:-5] + "XXXXX"
    with pytest.raises(HTTPException) as exc_info:
        decode_token(tampered)
    assert exc_info.value.status_code == 401


def test_extra_claims_preserved():
    token = create_access_token(subject="user-1", extra_claims={"role": "admin"})
    payload = decode_token(token)
    assert payload["role"] == "admin"
