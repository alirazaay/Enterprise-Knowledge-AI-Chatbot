"""Parser registry selected by stored document file type."""

from pathlib import Path

from app.services.docx_parser import DocxParser
from app.services.document_parser import DocumentParser, ParserError
from app.services.pdf_parser import PdfParser


class ParserRegistry:
    def __init__(self) -> None:
        self._parsers: dict[str, DocumentParser] = {
            "pdf": PdfParser(),
            "docx": DocxParser(),
        }

    def parse(self, file_type: str, file_path: Path):
        parser = self._parsers.get(file_type.lower().removeprefix("."))
        if parser is None:
            raise ParserError("No parser is available for this document type.")
        return parser.parse(file_path)
