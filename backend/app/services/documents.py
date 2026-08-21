"""Document metadata and file lifecycle services."""

from __future__ import annotations

import math
import re
from pathlib import Path
from uuid import UUID

from fastapi import UploadFile
from sqlalchemy import func, or_, select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.core.storage import FileStorageService, StorageError
from app.models.document import Document
from app.models.enums import DocumentStatus


class DocumentServiceError(Exception):
    """Raised for controlled document lifecycle failures."""


def derive_title(filename: str) -> str:
    """Create a readable title without trusting the filename as a path."""

    stem = Path(filename).stem
    title = re.sub(r"[-_]+", " ", stem).strip()
    return re.sub(r"\s+", " ", title) or "Untitled document"


def validate_upload_metadata(upload: UploadFile) -> str:
    """Validate supported extension and practical MIME metadata."""

    if not upload.filename:
        raise DocumentServiceError("A filename is required.")
    extension = Path(upload.filename).suffix.lower()
    allowed_types = {
        ".pdf": {"application/pdf", "application/octet-stream"},
        ".docx": {
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            "application/octet-stream",
        },
    }
    if extension not in allowed_types:
        raise DocumentServiceError("Only PDF and DOCX files are supported.")
    if upload.content_type and upload.content_type.lower() not in allowed_types[extension]:
        raise DocumentServiceError("The uploaded file type does not match its extension.")
    return extension


class DocumentService:
    """Coordinate database metadata with the storage service."""

    def __init__(self, db: Session, storage: FileStorageService, max_upload_bytes: int) -> None:
        self.db = db
        self.storage = storage
        self.max_upload_bytes = max_upload_bytes

    async def upload(
        self, upload: UploadFile, title: str | None, uploaded_by: UUID
    ) -> Document:
        extension = validate_upload_metadata(upload)
        stored = await self.storage.save_file(upload, extension, self.max_upload_bytes)
        document = Document(
            title=title.strip() if title and title.strip() else derive_title(upload.filename or "document"),
            file_name=Path(upload.filename or "document").name,
            file_type=extension.removeprefix("."),
            file_path=stored.relative_path,
            file_size=stored.size,
            page_count=None,
            chunk_count=0,
            status=DocumentStatus.UPLOADED,
            uploaded_by=uploaded_by,
        )
        self.db.add(document)
        try:
            self.db.commit()
            self.db.refresh(document)
        except SQLAlchemyError as exc:
            self.db.rollback()
            try:
                self.storage.delete_file(stored.relative_path)
            except StorageError:
                pass
            raise DocumentServiceError("Unable to create document record.") from exc
        return document

    def list(
        self,
        page: int,
        page_size: int,
        status: DocumentStatus | None = None,
        file_type: str | None = None,
        search: str | None = None,
    ) -> tuple[list[Document], int]:
        """Return newest documents first with basic filters and pagination."""

        filters = []
        if status:
            filters.append(Document.status == status)
        if file_type:
            filters.append(Document.file_type == file_type.lower().removeprefix("."))
        if search and search.strip():
            term = f"%{search.strip()}%"
            filters.append(or_(Document.title.ilike(term), Document.file_name.ilike(term)))

        total = self.db.scalar(select(func.count()).select_from(Document).where(*filters)) or 0
        documents = self.db.scalars(
            select(Document)
            .where(*filters)
            .order_by(Document.created_at.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        ).all()
        return documents, int(total)

    def get(self, document_id: UUID) -> Document | None:
        return self.db.get(Document, document_id)

    def delete(self, document: Document) -> None:
        """Delete storage and metadata, tolerating an already-missing file."""

        try:
            self.storage.delete_file(document.file_path)
            self.db.delete(document)
            self.db.commit()
        except SQLAlchemyError as exc:
            self.db.rollback()
            raise DocumentServiceError("Unable to delete document.") from exc
        except StorageError as exc:
            raise DocumentServiceError("Unable to delete document file.") from exc


def max_upload_bytes(max_upload_size_mb: int) -> int:
    return max_upload_size_mb * 1024 * 1024
