"""HTTP routes for the Phase 1 API."""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.core.database import get_db

router = APIRouter()


@router.get("/health", tags=["system"])
def health_check() -> dict[str, str]:
    """Report whether the API process is available."""

    return {"status": "healthy", "service": "enterprise-knowledge-ai"}


@router.get("/health/db", tags=["system"])
def database_health_check(db: Session = Depends(get_db)) -> dict[str, str]:
    """Check database reachability without affecting the application health route."""

    try:
        db.execute(text("SELECT 1"))
    except SQLAlchemyError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database is unavailable.",
        ) from exc
    return {"status": "healthy", "database": "connected"}
