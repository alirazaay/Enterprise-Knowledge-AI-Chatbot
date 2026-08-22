"""Transactional document chunking and local vector indexing."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from uuid import UUID

from sqlalchemy import delete, select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.models.document import Document
from app.models.document_chunk import DocumentChunk
from app.models.document_page import DocumentPage
from app.models.enums import DocumentStatus
from app.services.chunking import DocumentChunker
from app.services.embedding_service import EmbeddingError, EmbeddingService, get_embedding_service

logger = logging.getLogger(__name__)


class IndexingNotFoundError(Exception):
    """Raised when the document does not exist."""


class IndexingEligibilityError(Exception):
    """Raised when a document cannot be indexed yet."""


@dataclass(frozen=True)
class IndexingResult:
    document: Document
    chunk_count: int
    embedding_model: str
    embedding_dimension: int


class DocumentIndexingService:
    def __init__(
        self,
        db: Session,
        embeddings: EmbeddingService | None = None,
        chunker: DocumentChunker | None = None,
    ) -> None:
        settings = get_settings()
        settings.validate_embedding_configuration()
        self.db = db
        self.embeddings = embeddings or get_embedding_service()
        self.chunker = chunker or DocumentChunker(settings.chunk_size_words, settings.chunk_overlap_words)

    def index(self, document_id: UUID) -> IndexingResult:
        document = self.db.get(Document, document_id)
        if document is None:
            raise IndexingNotFoundError
        if document.status not in {DocumentStatus.PROCESSED, DocumentStatus.INDEXED, DocumentStatus.FAILED}:
            raise IndexingEligibilityError("Only processed documents can be indexed.")

        pages = self.db.scalars(
            select(DocumentPage).where(DocumentPage.document_id == document.id).order_by(DocumentPage.sequence_index)
        ).all()
        if not pages:
            raise IndexingEligibilityError("The document has no extracted content to index.")

        logger.info("document_indexing_started", extra={"document_id": str(document_id)})
        document.status = DocumentStatus.INDEXING
        document.indexing_error = None
        self.db.commit()

        try:
            chunks = self.chunker.chunk_pages(list(pages))
            if not chunks:
                raise IndexingEligibilityError("The document produced no semantic chunks.")
            logger.info("document_chunks_generated", extra={"document_id": str(document_id), "chunk_count": len(chunks)})
            vectors = self.embeddings.embed_texts([chunk.content for chunk in chunks])
            if len(vectors) != len(chunks):
                raise EmbeddingError("Embedding count does not match chunk count.")

            self.db.execute(delete(DocumentChunk).where(DocumentChunk.document_id == document.id))
            self.db.add_all(
                [
                    DocumentChunk(
                        document_id=document.id,
                        content=chunk.content,
                        page_number=chunk.page_number,
                        chunk_index=index,
                        word_count=chunk.word_count,
                        source_sequence_start=chunk.source_sequence_start,
                        source_sequence_end=chunk.source_sequence_end,
                        embedding=vector,
                    )
                    for index, (chunk, vector) in enumerate(zip(chunks, vectors, strict=True))
                ]
            )
            document.chunk_count = len(chunks)
            document.indexing_error = None
            document.status = DocumentStatus.INDEXED
            self.db.commit()
        except (EmbeddingError, IndexingEligibilityError) as exc:
            return self._failed(document, str(exc))
        except SQLAlchemyError as exc:
            return self._failed(document, "Document vectors could not be saved.", exc)
        except Exception as exc:
            return self._failed(document, "The document could not be indexed.", exc)

        logger.info("document_indexing_succeeded", extra={"document_id": str(document_id), "chunk_count": len(chunks)})
        return IndexingResult(document, len(chunks), self.embeddings.settings.embedding_model, self.embeddings.dimension)

    def _failed(self, document: Document, reason: str, error: Exception | None = None) -> IndexingResult:
        if error:
            logger.exception("document_indexing_failed", extra={"document_id": str(document.id)})
        self.db.rollback()
        current = self.db.get(Document, document.id) or document
        current.status = DocumentStatus.FAILED
        current.indexing_error = reason[:1000]
        try:
            self.db.commit()
        except SQLAlchemyError:
            self.db.rollback()
        return IndexingResult(current, 0, self.embeddings.settings.embedding_model, self.embeddings.dimension)

    def chunks(self, document_id: UUID, page: int, page_size: int) -> tuple[list[DocumentChunk], int]:
        document = self.db.get(Document, document_id)
        if document is None:
            raise IndexingNotFoundError
        from sqlalchemy import func

        total = self.db.scalar(select(func.count()).select_from(DocumentChunk).where(DocumentChunk.document_id == document_id)) or 0
        items = self.db.scalars(
            select(DocumentChunk)
            .where(DocumentChunk.document_id == document_id)
            .order_by(DocumentChunk.chunk_index)
            .offset((page - 1) * page_size)
            .limit(page_size)
        ).all()
        return items, int(total)
