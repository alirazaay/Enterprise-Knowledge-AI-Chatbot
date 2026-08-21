"""PyMuPDF PDF text extraction."""

from pathlib import Path

import pymupdf as fitz

from app.services.document_parser import DocumentParser, ParsedBlock, ParsedDocument, ParserError, clean_text, require_meaningful_blocks


class PdfParser(DocumentParser):
    supported_file_type = "pdf"

    def parse(self, file_path: Path) -> ParsedDocument:
        try:
            with fitz.open(file_path) as document:
                if document.is_encrypted:
                    raise ParserError("The PDF is encrypted and cannot be processed.")
                blocks = []
                for index, page in enumerate(document, start=1):
                    text = clean_text(page.get_text("text"))
                    if text:
                        blocks.append(ParsedBlock(page_number=index, sequence_index=index - 1, content=text))
                blocks = require_meaningful_blocks(blocks)
                return ParsedDocument(blocks=blocks, page_count=document.page_count)
        except ParserError:
            raise
        except (fitz.FileDataError, RuntimeError, OSError) as exc:
            raise ParserError("The PDF could not be parsed.") from exc
