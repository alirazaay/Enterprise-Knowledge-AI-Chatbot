"""Explicit, transactional document parsing lifecycle."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path
from uuid import UUID

from sqlalchemy import delete, func, select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.core.storage import FileStorageService, StorageError
from app.models.document import Document
from app.models.document_page import DocumentPage
from app.models.enums import DocumentStatus
from app.services.document_parser import ParsedDocument, ParserError
from app.services.parsers import ParserRegistry

logger = logging.getLogger(__name__)


class ProcessingNotFoundError(Exception):
    """Raised when a document does not exist."""


@dataclass(frozen=True)
class ProcessingResult:
    document: Document
    block_count: int


class DocumentProcessingService:
    def __init__(self, db: Session, storage: FileStorageService, parsers: ParserRegistry | None = None) -> None:
        self.db = db
        self.storage = storage
        self.parsers = parsers or ParserRegistry()

    def process(self, document_id: UUID) -> ProcessingResult:
        document = self.db.get(Document, document_id)
        if document is None:
            raise ProcessingNotFoundError

        logger.info("document_processing_started", extra={"document_id": str(document_id), "file_type": document.file_type})
        try:
            file_path = self.storage.resolve_file(document.file_path)
            if not file_path.is_file():
                raise ParserError("Source file is missing from storage.")
        except StorageError as exc:
            return self._failed(document, "Source file is unavailable.", exc)

        document.status = DocumentStatus.PROCESSING
        document.processing_error = None
        self.db.commit()

        try:
            parsed: ParsedDocument = self.parsers.parse(document.file_type, file_path)
            logger.info("document_parser_extracted", extra={"document_id": str(document_id), "block_count": len(parsed.blocks)})
        except ParserError as exc:
            return self._failed(document, str(exc))
        except Exception as exc:
            logger.exception("document_processing_failed", extra={"document_id": str(document_id)})
            return self._failed(document, "The document could not be processed.", exc)

        try:
            self.db.execute(delete(DocumentPage).where(DocumentPage.document_id == document.id))
            self.db.add_all(
                [
                    DocumentPage(
                        document_id=document.id,
                        page_number=block.page_number,
                        sequence_index=block.sequence_index,
                        content=block.content,
                    )
                    for block in parsed.blocks
                ]
            )
            document.page_count = parsed.page_count
            document.processing_error = None
            document.status = DocumentStatus.PROCESSED
            self.db.commit()
        except SQLAlchemyError as exc:
            self.db.rollback()
            return self._failed(document, "Extracted content could not be saved.", exc)

        logger.info("document_processing_succeeded", extra={"document_id": str(document_id), "block_count": len(parsed.blocks)})
        return ProcessingResult(document=document, block_count=len(parsed.blocks))

    def _failed(self, document: Document, reason: str, error: Exception | None = None) -> ProcessingResult:
        if error:
            logger.exception("document_processing_failed", extra={"document_id": str(document.id)})
        self.db.rollback()
        current = self.db.get(Document, document.id) or document
        current.status = DocumentStatus.FAILED
        current.processing_error = reason[:1000]
        try:
            self.db.commit()
        except SQLAlchemyError:
            self.db.rollback()
        return ProcessingResult(document=current, block_count=0)

    def content(self, document_id: UUID, page: int, page_size: int) -> tuple[list[DocumentPage], int]:
        document = self.db.get(Document, document_id)
        if document is None:
            raise ProcessingNotFoundError
        total = self.db.scalar(select(func.count()).select_from(DocumentPage).where(DocumentPage.document_id == document_id)) or 0
        items = self.db.scalars(
            select(DocumentPage)
            .where(DocumentPage.document_id == document_id)
            .order_by(DocumentPage.sequence_index)
            .offset((page - 1) * page_size)
            .limit(page_size)
        ).all()
        return items, int(total)
