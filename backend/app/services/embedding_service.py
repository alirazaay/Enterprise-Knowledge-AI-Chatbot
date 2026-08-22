"""Lazy local sentence-transformer embedding service."""

from __future__ import annotations

import math
from functools import lru_cache
from typing import Any

from app.core.config import Settings, get_settings
from app.core.constants import VECTOR_DIMENSION


class EmbeddingError(RuntimeError):
    """Raised when local embedding output is unavailable or invalid."""


class EmbeddingService:
    def __init__(self, settings: Settings | None = None, model: Any | None = None) -> None:
        self.settings = settings or get_settings()
        self.settings.validate_embedding_configuration()
        self._model = model

    @property
    def dimension(self) -> int:
        return self.settings.embedding_dimension

    def _load_model(self) -> Any:
        if self._model is None:
            from sentence_transformers import SentenceTransformer

            self._model = SentenceTransformer(self.settings.embedding_model)
        actual = self._model.get_sentence_embedding_dimension()
        if actual != self.dimension:
            raise EmbeddingError(
                f"Embedding model dimension {actual} does not match configured dimension {self.dimension}."
            )
        return self._model

    def embed_texts(self, texts: list[str]) -> list[list[float]]:
        if not texts:
            return []
        model = self._load_model()
        try:
            encoded = model.encode(
                texts,
                batch_size=self.settings.embedding_batch_size,
                show_progress_bar=False,
                convert_to_numpy=True,
                normalize_embeddings=True,
            )
        except Exception as exc:
            raise EmbeddingError("The local embedding model could not encode the document.") from exc

        vectors = [row.tolist() for row in encoded]
        if len(vectors) != len(texts):
            raise EmbeddingError("The embedding model returned an unexpected number of vectors.")
        for vector in vectors:
            if len(vector) != self.dimension or not all(math.isfinite(float(value)) for value in vector):
                raise EmbeddingError("The embedding model returned an invalid vector.")
        return [[float(value) for value in vector] for vector in vectors]

    def embed_text(self, text: str) -> list[float]:
        return self.embed_texts([text])[0]


@lru_cache
def get_embedding_service() -> EmbeddingService:
    """Return one lazy model holder for the application process."""

    return EmbeddingService()
