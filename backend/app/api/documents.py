"""Admin-only document upload and file management endpoints."""

from math import ceil
from pathlib import Path
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile, status
from fastapi.responses import FileResponse
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import select

from app.api.dependencies import require_admin
from app.core.config import get_settings
from app.core.database import get_db
from app.core.storage import FileStorageService, StorageError, UploadSizeExceededError
from app.core.storage_dependencies import get_storage_service
from app.models.document import Document
from app.models.enums import DocumentStatus
from app.models.user import User
from app.schemas.document import DocumentDetailsResponse, DocumentListResponse, DocumentResponse
from app.services.documents import DocumentService, DocumentServiceError, max_upload_bytes, validate_upload_metadata

router = APIRouter(prefix="/documents", tags=["documents"])


def _service(db: Session, storage: FileStorageService) -> DocumentService:
    return DocumentService(db, storage, max_upload_bytes(get_settings().max_upload_size_mb))


def _not_found() -> HTTPException:
    return HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found.")


@router.post("", response_model=DocumentResponse, status_code=status.HTTP_201_CREATED)
async def upload_document(
    file: Annotated[UploadFile, File(description="PDF or DOCX document")],
    title: Annotated[str | None, Form()] = None,
    db: Annotated[Session, Depends(get_db)] = None,
    admin: Annotated[User, Depends(require_admin)] = None,
    storage: Annotated[FileStorageService, Depends(get_storage_service)] = None,
) -> Document:
    """Upload one PDF or DOCX document for later processing."""

    try:
        validate_upload_metadata(file)
        return await _service(db, storage).upload(file, title, admin.id)
    except UploadSizeExceededError as exc:
        raise HTTPException(status_code=status.HTTP_413_CONTENT_TOO_LARGE, detail=str(exc)) from exc
    except (DocumentServiceError, StorageError) as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    except SQLAlchemyError as exc:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Document service unavailable.") from exc


@router.get("", response_model=DocumentListResponse)
def list_documents(
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 20,
    status_filter: Annotated[DocumentStatus | None, Query(alias="status")] = None,
    file_type: Annotated[str | None, Query()] = None,
    search: Annotated[str | None, Query()] = None,
    db: Annotated[Session, Depends(get_db)] = None,
    _: Annotated[User, Depends(require_admin)] = None,
) -> DocumentListResponse:
    """List document metadata newest-first with basic pagination."""

    try:
        documents, total = _service(db, get_storage_service()).list(page, page_size, status_filter, file_type, search)
    except SQLAlchemyError as exc:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Document service unavailable.") from exc
    return DocumentListResponse(
        items=[DocumentResponse.model_validate(document) for document in documents],
        page=page,
        page_size=page_size,
        total=total,
        total_pages=ceil(total / page_size) if total else 0,
    )


@router.get("/{document_id}", response_model=DocumentDetailsResponse)
def get_document(
    document_id: UUID,
    db: Annotated[Session, Depends(get_db)] = None,
    _: Annotated[User, Depends(require_admin)] = None,
) -> Document:
    """Return safe metadata for one document."""

    try:
        document = db.scalar(select(Document).options(joinedload(Document.uploader)).where(Document.id == document_id))
    except SQLAlchemyError as exc:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Document service unavailable.") from exc
    if document is None:
        raise _not_found()
    return document


@router.get("/{document_id}/file")
def download_document(
    document_id: UUID,
    db: Annotated[Session, Depends(get_db)] = None,
    _: Annotated[User, Depends(require_admin)] = None,
    storage: Annotated[FileStorageService, Depends(get_storage_service)] = None,
) -> FileResponse:
    """Download a document through its stored safe relative path."""

    try:
        document = db.get(Document, document_id)
    except SQLAlchemyError as exc:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Document service unavailable.") from exc
    if document is None:
        raise _not_found()
    try:
        path = storage.resolve_file(document.file_path)
    except StorageError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document file is unavailable.") from exc
    if not path.is_file():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document file is unavailable.")

    media_types = {"pdf": "application/pdf", "docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document"}
    return FileResponse(path, media_type=media_types.get(document.file_type, "application/octet-stream"), filename=Path(document.file_name).name)


@router.delete("/{document_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_document(
    document_id: UUID,
    db: Annotated[Session, Depends(get_db)] = None,
    _: Annotated[User, Depends(require_admin)] = None,
    storage: Annotated[FileStorageService, Depends(get_storage_service)] = None,
) -> None:
    """Delete document metadata and its physical file."""

    try:
        document = db.get(Document, document_id)
        if document is None:
            raise _not_found()
        _service(db, storage).delete(document)
    except HTTPException:
        raise
    except DocumentServiceError as exc:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc)) from exc
    except SQLAlchemyError as exc:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Document service unavailable.") from exc
