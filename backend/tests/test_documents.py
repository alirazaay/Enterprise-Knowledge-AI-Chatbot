from datetime import datetime, timedelta, timezone
from uuid import uuid4

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient

from app.api.dependencies import require_admin
import app.api.documents as documents_api
from app.core.database import get_db
from app.core.config import Settings
from app.core.storage import FileStorageService
from app.core.storage_dependencies import get_storage_service
from app.main import app
from app.models.enums import DocumentStatus, UserRole
from app.models.user import User


class FakeResult:
    def __init__(self, items):
        self.items = items

    def all(self):
        return self.items


class FakeDocumentSession:
    def __init__(self):
        self.documents = []

    def add(self, document):
        self.documents.append(document)

    def commit(self):
        return None

    def rollback(self):
        return None

    def refresh(self, document):
        document.id = document.id or uuid4()
        now = datetime.now(timezone.utc)
        document.created_at = document.created_at or now
        document.updated_at = now

    def scalar(self, statement):
        if "count(*)" in str(statement).lower():
            return len(self.documents)
        return self.documents[0] if self.documents else None

    def scalars(self, _statement):
        return FakeResult(sorted(self.documents, key=lambda item: item.created_at, reverse=True))

    def get(self, _model, document_id):
        return next((item for item in self.documents if item.id == document_id), None)

    def delete(self, document):
        self.documents.remove(document)

    def close(self):
        return None


def make_admin() -> User:
    now = datetime.now(timezone.utc)
    return User(
        id=uuid4(),
        name="Admin",
        email="admin@example.com",
        password_hash="not-used-in-document-tests",
        role=UserRole.ADMIN,
        is_active=True,
        created_at=now,
        updated_at=now,
    )


@pytest.fixture
def document_environment(tmp_path):
    db = FakeDocumentSession()
    storage = FileStorageService(tmp_path)
    app.dependency_overrides[get_db] = lambda: db
    app.dependency_overrides[require_admin] = lambda: make_admin()
    app.dependency_overrides[get_storage_service] = lambda: storage
    yield db, storage
    app.dependency_overrides.clear()


def test_valid_pdf_upload_creates_record_and_file(document_environment) -> None:
    db, storage = document_environment
    response = TestClient(app).post(
        "/documents",
        files={"file": ("Employee-Handbook.pdf", b"%PDF-test", "application/pdf")},
        data={"title": "Employee Handbook"},
    )

    assert response.status_code == 201
    body = response.json()
    assert body["title"] == "Employee Handbook"
    assert body["file_type"] == "pdf"
    assert body["status"] == "uploaded"
    assert body["page_count"] is None
    assert body["chunk_count"] == 0
    assert len(db.documents) == 1
    assert storage.file_exists(db.documents[0].file_path)


def test_valid_docx_upload_derives_title(document_environment) -> None:
    db, _storage = document_environment
    response = TestClient(app).post(
        "/documents",
        files={
            "file": (
                "Project_Notes.docx",
                b"PK-docx-test",
                "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            )
        },
    )

    assert response.status_code == 201
    assert response.json()["title"] == "Project Notes"
    assert db.documents[0].file_type == "docx"


def test_invalid_and_empty_uploads_are_rejected(document_environment) -> None:
    response = TestClient(app).post(
        "/documents",
        files={"file": ("notes.txt", b"text", "text/plain")},
    )
    assert response.status_code == 400


def test_oversized_upload_returns_413(document_environment, monkeypatch) -> None:
    monkeypatch.setattr(documents_api, "get_settings", lambda: Settings(max_upload_size_mb=0))

    response = TestClient(app).post(
        "/documents",
        files={"file": ("large.pdf", b"%PDF-test", "application/pdf")},
    )

    assert response.status_code == 413

    response = TestClient(app).post(
        "/documents",
        files={"file": ("empty.pdf", b"", "application/pdf")},
    )
    assert response.status_code == 400


def test_list_details_download_and_delete(document_environment) -> None:
    db, storage = document_environment
    upload = TestClient(app).post(
        "/documents",
        files={"file": ("Handbook.pdf", b"%PDF-test", "application/pdf")},
    )
    document_id = upload.json()["id"]

    listed = TestClient(app).get("/documents?page=1&page_size=20")
    assert listed.status_code == 200
    assert listed.json()["total"] == 1
    assert listed.json()["items"][0]["id"] == document_id

    details = TestClient(app).get(f"/documents/{document_id}")
    assert details.status_code == 200
    assert details.json()["file_name"] == "Handbook.pdf"

    downloaded = TestClient(app).get(f"/documents/{document_id}/file")
    assert downloaded.status_code == 200
    assert downloaded.content == b"%PDF-test"
    assert "Handbook.pdf" in downloaded.headers["content-disposition"]

    stored_path = db.documents[0].file_path
    deleted = TestClient(app).delete(f"/documents/{document_id}")
    assert deleted.status_code == 204
    assert not storage.file_exists(stored_path)
    assert db.documents == []


def test_document_management_requires_admin() -> None:
    app.dependency_overrides[get_db] = lambda: FakeDocumentSession()
    try:
        response = TestClient(app).get("/documents")
        assert response.status_code == 401
    finally:
        app.dependency_overrides.clear()


def test_missing_document_returns_404(document_environment) -> None:
    response = TestClient(app).get(f"/documents/{uuid4()}")
    assert response.status_code == 404
