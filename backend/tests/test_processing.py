from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

import pymupdf as fitz

from app.core.storage import FileStorageService
from app.models.document import Document
from app.models.document_page import DocumentPage
from app.models.enums import DocumentStatus
from app.services.document_processing import DocumentProcessingService


class FakeProcessingSession:
    def __init__(self, document: Document):
        self.document = document
        self.pages: list[DocumentPage] = []

    def get(self, model, identifier):
        if model is Document and identifier == self.document.id:
            return self.document
        return None

    def commit(self):
        return None

    def rollback(self):
        return None

    def execute(self, statement):
        self.pages.clear()
        return None

    def add_all(self, pages):
        self.pages.extend(pages)

    def scalar(self, _statement):
        return len(self.pages)

    def scalars(self, _statement):
        return type("Result", (), {"all": lambda self: list(self.pages)})()


def make_text_pdf(path: Path) -> None:
    document = fitz.open()
    document.new_page().insert_text((72, 72), "A processable document.")
    document.save(path)
    document.close()


def make_document(relative_path: str) -> Document:
    now = datetime.now(timezone.utc)
    return Document(
        id=uuid4(),
        title="Test document",
        file_name="test.pdf",
        file_type="pdf",
        file_path=relative_path,
        file_size=10,
        page_count=None,
        chunk_count=0,
        status=DocumentStatus.UPLOADED,
        processing_error=None,
        uploaded_by=uuid4(),
        created_at=now,
        updated_at=now,
    )


def test_processing_lifecycle_and_reprocessing_replaces_pages(tmp_path: Path) -> None:
    storage = FileStorageService(tmp_path)
    path = tmp_path / "source.pdf"
    make_text_pdf(path)
    document = make_document("source.pdf")
    db = FakeProcessingSession(document)

    result = DocumentProcessingService(db, storage).process(document.id)

    assert result.document.status == DocumentStatus.PROCESSED
    assert result.document.processing_error is None
    assert result.document.page_count == 1
    assert result.block_count == 1
    assert len(db.pages) == 1
    assert db.pages[0].page_number == 1
    assert path.exists()

    result = DocumentProcessingService(db, storage).process(document.id)
    assert result.document.status == DocumentStatus.PROCESSED
    assert len(db.pages) == 1


def test_processing_failure_is_safe_and_retry_can_succeed(tmp_path: Path) -> None:
    storage = FileStorageService(tmp_path)
    path = tmp_path / "source.pdf"
    path.write_bytes(b"corrupt")
    document = make_document("source.pdf")
    db = FakeProcessingSession(document)

    failed = DocumentProcessingService(db, storage).process(document.id)

    assert failed.document.status == DocumentStatus.FAILED
    assert failed.document.processing_error == "The PDF could not be parsed."
    assert db.pages == []

    make_text_pdf(path)
    succeeded = DocumentProcessingService(db, storage).process(document.id)
    assert succeeded.document.status == DocumentStatus.PROCESSED
    assert succeeded.document.processing_error is None
    assert len(db.pages) == 1
