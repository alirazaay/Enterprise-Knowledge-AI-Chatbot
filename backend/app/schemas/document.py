"""Safe document API schemas."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.models.enums import DocumentStatus


class DocumentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    title: str
    file_name: str
    file_type: str
    file_size: int
    page_count: int | None
    chunk_count: int
    status: DocumentStatus
    processing_error: str | None
    indexing_error: str | None
    uploaded_by: UUID
    created_at: datetime
    updated_at: datetime


class UploaderResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    email: str
    role: str


class DocumentDetailsResponse(DocumentResponse):
    uploader: UploaderResponse | None = None
    extracted_block_count: int = 0
    embedding_model: str | None = None
    embedding_dimension: int | None = None
    chunk_size_words: int | None = None
    chunk_overlap_words: int | None = None


class DocumentListResponse(BaseModel):
    items: list[DocumentResponse]
    page: int = Field(ge=1)
    page_size: int = Field(ge=1)
    total: int = Field(ge=0)
    total_pages: int = Field(ge=0)


class ProcessingResponse(BaseModel):
    document_id: UUID
    status: DocumentStatus
    page_count: int | None
    extracted_block_count: int
    processing_error: str | None


class IndexingResponse(BaseModel):
    document_id: UUID
    status: DocumentStatus
    chunk_count: int
    embedding_model: str
    embedding_dimension: int
    indexing_error: str | None


class DocumentChunkResponse(BaseModel):
    id: UUID
    chunk_index: int
    page_number: int | None
    content: str
    word_count: int
    source_sequence_start: int
    source_sequence_end: int
    embedding_dimension: int | None
    embedding_exists: bool


class DocumentChunkListResponse(BaseModel):
    document_id: UUID
    items: list[DocumentChunkResponse]
    page: int = Field(ge=1)
    page_size: int = Field(ge=1)
    total: int = Field(ge=0)
    total_pages: int = Field(ge=0)


class DocumentContentItem(BaseModel):
    page_number: int | None
    sequence_index: int
    content: str


class DocumentContentResponse(BaseModel):
    document_id: UUID
    items: list[DocumentContentItem]
    page: int = Field(ge=1)
    page_size: int = Field(ge=1)
    total: int = Field(ge=0)
    total_pages: int = Field(ge=0)
