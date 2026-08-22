"""Centralized environment-backed application settings."""

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict

from app.core.constants import VECTOR_DIMENSION


class Settings(BaseSettings):
    """Runtime configuration loaded from environment variables and .env."""

    app_env: str = "development"
    app_name: str = "enterprise-knowledge-ai"
    api_host: str = "127.0.0.1"
    api_port: int = 8000
    frontend_url: str = "http://localhost:5173"
    database_url: str | None = None
    ollama_base_url: str = "http://localhost:11434"
    ollama_model: str = "qwen2.5:7b"
    embedding_model: str = "sentence-transformers/all-MiniLM-L6-v2"
    embedding_dimension: int = VECTOR_DIMENSION
    embedding_batch_size: int = 32
    chunk_size_words: int = 600
    chunk_overlap_words: int = 100
    log_level: str = "INFO"
    jwt_secret_key: str | None = None
    jwt_algorithm: str = "HS256"
    jwt_access_token_expire_minutes: int = 60
    upload_dir: str = "uploads"
    max_upload_size_mb: int = 25

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    @property
    def cors_origins(self) -> list[str]:
        """Return configured frontend origins for CORS."""

        return [origin.strip() for origin in self.frontend_url.split(",") if origin.strip()]

    def require_jwt_secret(self) -> str:
        """Return the JWT secret or fail clearly at the first auth operation."""

        if not self.jwt_secret_key:
            raise RuntimeError(
                "JWT_SECRET_KEY is required for authentication. "
                "Set it in backend/.env or the process environment."
            )
        if len(self.jwt_secret_key) < 32:
            raise RuntimeError("JWT_SECRET_KEY must be at least 32 characters long.")
        return self.jwt_secret_key

    def validate_embedding_configuration(self) -> None:
        """Ensure runtime embedding output matches the pgvector schema."""

        if self.embedding_dimension != VECTOR_DIMENSION:
            raise RuntimeError(
                f"EMBEDDING_DIMENSION={self.embedding_dimension} does not match the database vector dimension "
                f"({VECTOR_DIMENSION})."
            )
        if self.embedding_batch_size < 1:
            raise RuntimeError("EMBEDDING_BATCH_SIZE must be greater than zero.")
        if self.chunk_size_words < 1:
            raise RuntimeError("CHUNK_SIZE_WORDS must be greater than zero.")
        if self.chunk_overlap_words < 0 or self.chunk_overlap_words >= self.chunk_size_words:
            raise RuntimeError("CHUNK_OVERLAP_WORDS must be non-negative and smaller than CHUNK_SIZE_WORDS.")


@lru_cache
def get_settings() -> Settings:
    """Return a cached settings instance for dependency injection."""

    return Settings()
