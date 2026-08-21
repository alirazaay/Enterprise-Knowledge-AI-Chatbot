"""FastAPI dependency for the configured local storage service."""

from functools import lru_cache

from app.core.config import get_settings
from app.core.storage import FileStorageService


@lru_cache
def get_storage_service() -> FileStorageService:
    """Return one configured storage service."""

    return FileStorageService(get_settings().upload_dir)
