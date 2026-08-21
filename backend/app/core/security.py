"""Password hashing and JWT primitives for authentication services."""

from datetime import datetime, timedelta, timezone
from uuid import UUID

import jwt
from jwt import InvalidTokenError
from pwdlib import PasswordHash

from app.core.config import Settings, get_settings

password_hash = PasswordHash.recommended()


def hash_password(password: str) -> str:
    """Hash a password using the recommended Argon2 configuration."""

    return password_hash.hash(password)


def verify_password(password: str, hashed_password: str) -> bool:
    """Verify a password against a stored hash without exposing hash details."""

    try:
        return password_hash.verify(password, hashed_password)
    except (ValueError, TypeError):
        return False


def create_access_token(subject: UUID | str, settings: Settings | None = None) -> str:
    """Create a short-lived HS256 JWT for a user subject."""

    runtime_settings = settings or get_settings()
    now = datetime.now(timezone.utc)
    expires_at = now + timedelta(minutes=runtime_settings.jwt_access_token_expire_minutes)
    payload = {"sub": str(subject), "iat": now, "exp": expires_at}
    return jwt.encode(payload, runtime_settings.require_jwt_secret(), algorithm=runtime_settings.jwt_algorithm)


def decode_access_token(token: str, settings: Settings | None = None) -> UUID:
    """Decode and validate a JWT, returning its UUID subject."""

    runtime_settings = settings or get_settings()
    try:
        payload = jwt.decode(
            token,
            runtime_settings.require_jwt_secret(),
            algorithms=[runtime_settings.jwt_algorithm],
            options={"require": ["sub", "exp"]},
        )
        return UUID(str(payload["sub"]))
    except (InvalidTokenError, KeyError, TypeError, ValueError, RuntimeError) as exc:
        raise ValueError("Invalid access token") from exc
