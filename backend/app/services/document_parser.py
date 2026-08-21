"""Common parser contracts and normalized extracted content."""

from dataclasses import dataclass
from pathlib import Path
from typing import Protocol


class ParserError(Exception):
    """Safe, user-facing parsing failure without internal details."""


@dataclass(frozen=True)
class ParsedBlock:
    page_number: int | None
    sequence_index: int
    content: str


@dataclass(frozen=True)
class ParsedDocument:
    blocks: list[ParsedBlock]
    page_count: int | None

    @property
    def full_text(self) -> str:
        return "\n\n".join(block.content for block in self.blocks)


class DocumentParser(Protocol):
    supported_file_type: str

    def parse(self, file_path: Path) -> ParsedDocument:
        """Parse one known local file into normalized blocks."""


def clean_text(value: str) -> str:
    """Conservatively normalize text while preserving semantic content."""

    value = value.replace("\r\n", "\n").replace("\r", "\n")
    value = "".join(char for char in value if char in "\n\t" or ord(char) >= 32)
    lines = [" ".join(line.split()) for line in value.split("\n")]
    return "\n".join(lines).strip()


def require_meaningful_blocks(blocks: list[ParsedBlock]) -> list[ParsedBlock]:
    """Reject documents with no usable extracted text."""

    usable = [block for block in blocks if clean_text(block.content)]
    if not usable:
        raise ParserError("No extractable text found in document.")
    return [ParsedBlock(block.page_number, block.sequence_index, clean_text(block.content)) for block in usable]
