"""HTTP routes for the Phase 1 API."""

from fastapi import APIRouter

router = APIRouter()


@router.get("/health", tags=["system"])
def health_check() -> dict[str, str]:
    """Report whether the API process is available."""

    return {"status": "healthy", "service": "enterprise-knowledge-ai"}
