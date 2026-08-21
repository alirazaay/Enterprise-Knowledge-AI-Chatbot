"""Synchronous SQLAlchemy engine, sessions, and FastAPI dependency."""

from collections.abc import Generator
from functools import lru_cache

from fastapi import HTTPException, status
from sqlalchemy import Engine, create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import get_settings


def _database_url() -> str:
    """Return the configured database URL or explain how to configure it."""

    database_url = get_settings().database_url
    if not database_url:
        raise RuntimeError(
            "DATABASE_URL is required for database operations. "
            "Set it in backend/.env or the process environment."
        )
    return database_url


@lru_cache
def get_engine() -> Engine:
    """Create one application engine, lazily, from environment configuration."""

    return create_engine(
        _database_url(),
        pool_pre_ping=True,
        future=True,
    )


@lru_cache
def get_session_factory() -> sessionmaker[Session]:
    """Return the application session factory."""

    return sessionmaker(bind=get_engine(), autoflush=False, autocommit=False, expire_on_commit=False)


def get_db() -> Generator[Session, None, None]:
    """Yield a request-scoped session and always close it afterwards."""

    try:
        session = get_session_factory()()
    except RuntimeError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database configuration is unavailable.",
        ) from exc

    try:
        yield session
    finally:
        session.close()
