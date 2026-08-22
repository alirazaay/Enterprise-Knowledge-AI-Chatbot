from datetime import datetime, timezone
from uuid import uuid4

from app.models.document_page import DocumentPage
from app.services.chunking import DocumentChunker


def make_page(content: str, sequence: int, page_number: int | None) -> DocumentPage:
    return DocumentPage(
        id=uuid4(), document_id=uuid4(), content=content, sequence_index=sequence, page_number=page_number,
        created_at=datetime.now(timezone.utc),
    )


def test_short_source_stays_one_chunk_and_preserves_page() -> None:
    chunks = DocumentChunker(10, 2).chunk_pages([make_page("Heading\n\nPolicy content remains readable.", 0, 3)])

    assert len(chunks) == 1
    assert chunks[0].page_number == 3
    assert "Heading" in chunks[0].content
    assert chunks[0].word_count == 5


def test_long_page_chunks_with_word_overlap() -> None:
    content = " ".join(f"word{i}" for i in range(25))
    chunks = DocumentChunker(10, 2).chunk_pages([make_page(content, 0, 1)])

    assert len(chunks) == 3
    assert chunks[0].page_number == chunks[1].page_number == 1
    assert chunks[1].content.split()[:2] == chunks[0].content.split()[-2:]
    assert [chunk.word_count for chunk in chunks] == [10, 10, 9]


def test_chunks_do_not_merge_source_pages_and_docx_page_number_stays_null() -> None:
    pages = [make_page("first page", 0, 1), make_page("logical section", 1, None)]
    chunks = DocumentChunker(20, 2).chunk_pages(pages)

    assert [chunk.page_number for chunk in chunks] == [1, None]
    assert [chunk.source_sequence_start for chunk in chunks] == [0, 1]
