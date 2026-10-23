from __future__ import annotations

import pytest

from app.core.errors import AuthError
from app.core.security import (
    create_access_token,
    decode_access_token,
    hash_password,
    verify_password,
)


def test_password_hash_roundtrip():
    hashed = hash_password("Secret123!")

    assert hashed != "Secret123!"
    assert verify_password("Secret123!", hashed) is True
    assert verify_password("wrong-password", hashed) is False


def test_access_token_roundtrip():
    token = create_access_token(
        user_id=7,
        username="student1",
        role="student",
        token_version=3,
        expires_minutes=60,
    )

    payload = decode_access_token(token)

    assert payload["sub"] == "7"
    assert payload["username"] == "student1"
    assert payload["role"] == "student"
    assert payload["ver"] == 3
    assert payload["type"] == "access"


def test_expired_token_is_rejected():
    token = create_access_token(
        user_id=1,
        username="admin",
        role="admin",
        token_version=0,
        expires_minutes=-1,
    )

    with pytest.raises(AuthError):
        decode_access_token(token)


def test_tampered_token_is_rejected():
    token = create_access_token(
        user_id=1,
        username="admin",
        role="admin",
        token_version=0,
        expires_minutes=60,
    )

    with pytest.raises(AuthError):
        decode_access_token(token + "tampered")
