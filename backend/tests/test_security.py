from datetime import datetime, timedelta, timezone
from uuid import uuid4

import jwt
import pytest

from app.core.config import Settings
from app.core.security import create_access_token, decode_access_token, hash_password, verify_password


def test_password_hashing_and_verification() -> None:
    password = "SecurePassword123!"
    hashed = hash_password(password)

    assert hashed != password
    assert hashed.startswith("$argon2")
    assert verify_password(password, hashed)
    assert not verify_password("wrong-password", hashed)


def test_jwt_creation_and_decoding() -> None:
    settings = Settings(jwt_secret_key="test-secret-that-is-at-least-32-characters", jwt_access_token_expire_minutes=5)
    subject = uuid4()

    token = create_access_token(subject, settings)

    assert decode_access_token(token, settings) == subject


def test_malformed_and_expired_jwts_are_rejected() -> None:
    settings = Settings(jwt_secret_key="test-secret-that-is-at-least-32-characters")
    with pytest.raises(ValueError):
        decode_access_token("not-a-token", settings)

    expired = jwt.encode(
        {"sub": str(uuid4()), "exp": datetime.now(timezone.utc) - timedelta(minutes=1)},
        settings.jwt_secret_key,
        algorithm=settings.jwt_algorithm,
    )
    with pytest.raises(ValueError):
        decode_access_token(expired, settings)


def test_jwt_secret_is_required() -> None:
    with pytest.raises(RuntimeError, match="JWT_SECRET_KEY"):
        create_access_token(uuid4(), Settings(jwt_secret_key=None))
