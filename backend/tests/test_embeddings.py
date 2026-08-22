import pytest

from app.core.config import Settings
from app.services.embedding_service import EmbeddingError, EmbeddingService


class Row:
    def __init__(self, values):
        self.values = values

    def tolist(self):
        return self.values


class FakeModel:
    def __init__(self, dimension=384):
        self.dimension = dimension
        self.calls = []

    def get_sentence_embedding_dimension(self):
        return self.dimension

    def encode(self, texts, **kwargs):
        self.calls.append((texts, kwargs))
        return [Row([float(index % 3) for index in range(self.dimension)]) for _ in texts]


def test_embedding_service_batches_and_validates_dimension() -> None:
    model = FakeModel()
    service = EmbeddingService(Settings(embedding_batch_size=8), model=model)

    vectors = service.embed_texts(["one", "two"])

    assert len(vectors) == 2
    assert all(len(vector) == 384 for vector in vectors)
    assert model.calls[0][1]["batch_size"] == 8
    assert model.calls[0][1]["normalize_embeddings"] is True


def test_embedding_service_rejects_model_dimension_mismatch() -> None:
    with pytest.raises(EmbeddingError, match="dimension"):
        EmbeddingService(Settings(), model=FakeModel(3)).embed_texts(["text"])
