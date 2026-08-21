"""python-docx extraction for paragraphs and tables in document order."""

from pathlib import Path
from zipfile import BadZipFile

from docx import Document as DocxDocument
from docx.document import Document as DocumentObject
from docx.table import Table, _Cell
from docx.text.paragraph import Paragraph

from app.services.document_parser import DocumentParser, ParsedBlock, ParsedDocument, ParserError, clean_text, require_meaningful_blocks


def _iter_blocks(parent: DocumentObject | _Cell):
    """Yield paragraphs and tables in their XML body order."""

    parent_element = parent.element.body if isinstance(parent, DocumentObject) else parent._tc
    for child in parent_element.iterchildren():
        if child.tag.endswith("}p"):
            yield Paragraph(child, parent)
        elif child.tag.endswith("}tbl"):
            yield Table(child, parent)


def _table_text(table: Table) -> str:
    rows = []
    for row in table.rows:
        cells = [clean_text(cell.text) for cell in row.cells]
        if any(cells):
            rows.append(" | ".join(cells))
    return "\n".join(rows)


class DocxParser(DocumentParser):
    supported_file_type = "docx"

    def parse(self, file_path: Path) -> ParsedDocument:
        try:
            document = DocxDocument(file_path)
            blocks: list[ParsedBlock] = []
            for block in _iter_blocks(document):
                content = clean_text(block.text if isinstance(block, Paragraph) else _table_text(block))
                if content:
                    blocks.append(ParsedBlock(page_number=None, sequence_index=len(blocks), content=content))
            blocks = require_meaningful_blocks(blocks)
            return ParsedDocument(blocks=blocks, page_count=None)
        except ParserError:
            raise
        except (BadZipFile, ValueError, OSError, KeyError, RuntimeError) as exc:
            raise ParserError("The DOCX file could not be parsed.") from exc
