from datetime import datetime, timezone
from uuid import uuid4

from app.core.config import Settings
from app.models.document import Document
from app.models.document_chunk import DocumentChunk
from app.models.document_page import DocumentPage
from app.models.enums import DocumentStatus
from app.services.chunking import DocumentChunker
from app.services.document_indexing import DocumentIndexingService


class FakeEmbeddingService:
    settings = Settings()
    dimension = 384

    def embed_texts(self, texts):
        return [[0.0] * self.dimension for _ in texts]


class Result:
    def __init__(self, values):
        self.values = values

    def all(self):
        return list(self.values)


class FakeIndexSession:
    def __init__(self, document, pages):
        self.document = document
        self.pages = pages
        self.chunks = []

    def get(self, model, identifier):
        return self.document if model is Document and identifier == self.document.id else None

    def scalars(self, statement):
        return Result(self.pages if "document_pages" in str(statement) else self.chunks)

    def scalar(self, _statement):
        return len(self.chunks)

    def execute(self, _statement):
        self.chunks.clear()

    def add_all(self, values):
        self.chunks.extend(values)

    def commit(self):
        return None

    def rollback(self):
        return None


def make_fixture():
    now = datetime.now(timezone.utc)
    document = Document(
        id=uuid4(), title="Index test", file_name="test.pdf", file_type="pdf", file_path="test.pdf", file_size=1,
        page_count=1, chunk_count=0, status=DocumentStatus.PROCESSED, processing_error=None, indexing_error=None,
        uploaded_by=uuid4(), created_at=now, updated_at=now,
    )
    page = DocumentPage(id=uuid4(), document_id=document.id, sequence_index=0, page_number=1, content="one two three", created_at=now)
    return document, [page]


def test_indexing_persists_vectors_and_replaces_previous_chunks(monkeypatch):
    document, pages = make_fixture()
    db = FakeIndexSession(document, pages)
    monkeypatch.setattr("app.services.document_indexing.get_settings", lambda: Settings())
    service = DocumentIndexingService(db, embeddings=FakeEmbeddingService(), chunker=DocumentChunker(10, 2))

    first = service.index(document.id)
    assert first.document.status == DocumentStatus.INDEXED
    assert first.chunk_count == 1
    assert db.chunks[0].embedding is not None
    assert len(db.chunks[0].embedding) == 384

    second = service.index(document.id)
    assert second.document.status == DocumentStatus.INDEXED
    assert len(db.chunks) == 1
    assert db.chunks[0].chunk_index == 0
