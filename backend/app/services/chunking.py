"""Structure-aware word-based chunking for extracted document blocks."""

from __future__ import annotations

import re
from dataclasses import dataclass

from app.models.document_page import DocumentPage


@dataclass(frozen=True)
class TextChunk:
    content: str
    page_number: int | None
    source_sequence_start: int
    source_sequence_end: int
    word_count: int


def _words(value: str) -> list[str]:
    return value.split()


def _paragraphs(value: str) -> list[str]:
    paragraphs = [part.strip() for part in re.split(r"\n\s*\n", value) if part.strip()]
    return paragraphs or [value.strip()]


class DocumentChunker:
    """Build page-aware chunks using words and configurable overlap."""

    def __init__(self, target_words: int = 600, overlap_words: int = 100) -> None:
        if target_words < 1 or overlap_words < 0 or overlap_words >= target_words:
            raise ValueError("Chunk target must be positive and overlap must be smaller than target.")
        self.target_words = target_words
        self.overlap_words = overlap_words

    def chunk_pages(self, pages: list[DocumentPage]) -> list[TextChunk]:
        chunks: list[TextChunk] = []
        for page in sorted(pages, key=lambda item: item.sequence_index):
            chunks.extend(self._chunk_source(page))
        return chunks

    def _chunk_source(self, page: DocumentPage) -> list[TextChunk]:
        result: list[TextChunk] = []
        current: list[str] = []

        def flush() -> None:
            nonlocal current
            if not current:
                return
            content = " ".join(current).strip()
            result.append(
                TextChunk(
                    content=content,
                    page_number=page.page_number,
                    source_sequence_start=page.sequence_index,
                    source_sequence_end=page.sequence_index,
                    word_count=len(current),
                )
            )
            current = current[-self.overlap_words :] if self.overlap_words else []

        for paragraph in _paragraphs(page.content):
            paragraph_words = _words(paragraph)
            while paragraph_words:
                available = self.target_words - len(current)
                if len(paragraph_words) <= available:
                    current.extend(paragraph_words)
                    paragraph_words = []
                    continue
                if available:
                    current.extend(paragraph_words[:available])
                    paragraph_words = paragraph_words[available:]
                flush()
        flush()
        return result
