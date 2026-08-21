"""Local filesystem storage with a future-friendly service boundary."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from uuid import uuid4

from fastapi import UploadFile


class StorageError(Exception):
    """Raised when a file cannot be safely stored or removed."""


class UploadSizeExceededError(StorageError):
    """Raised when an upload exceeds the configured byte limit."""


@dataclass(frozen=True)
class StoredFile:
    """Safe metadata returned after a file is stored."""

    relative_path: str
    size: int


class FileStorageService:
    """Store files beneath one configured root using generated names."""

    def __init__(self, root: str | Path) -> None:
        self.root = Path(root).expanduser().resolve()
        self.root.mkdir(parents=True, exist_ok=True)

    def _resolve_relative(self, relative_path: str) -> Path:
        """Resolve a stored relative path and reject traversal."""

        candidate = (self.root / relative_path).resolve()
        try:
            candidate.relative_to(self.root)
        except ValueError as exc:
            raise StorageError("Invalid storage path.") from exc
        return candidate

    async def save_file(self, upload: UploadFile, extension: str, max_bytes: int) -> StoredFile:
        """Stream an upload to a collision-resistant UUID filename."""

        normalized_extension = extension.lower()
        if normalized_extension not in {".pdf", ".docx"}:
            raise StorageError("Unsupported file extension.")

        relative_path = f"{uuid4()}{normalized_extension}"
        destination = self._resolve_relative(relative_path)
        bytes_written = 0
        try:
            with destination.open("xb") as output:
                while chunk := await upload.read(1024 * 1024):
                    bytes_written += len(chunk)
                    if bytes_written > max_bytes:
                        raise UploadSizeExceededError("File exceeds the configured upload limit.")
                    output.write(chunk)
        except StorageError:
            destination.unlink(missing_ok=True)
            raise
        except OSError as exc:
            destination.unlink(missing_ok=True)
            raise StorageError("Unable to write uploaded file.") from exc
        finally:
            await upload.close()

        if bytes_written == 0:
            destination.unlink(missing_ok=True)
            raise StorageError("Uploaded file is empty.")
        return StoredFile(relative_path=relative_path, size=bytes_written)

    def resolve_file(self, relative_path: str) -> Path:
        """Resolve a stored path without accepting arbitrary client paths."""

        return self._resolve_relative(relative_path)

    def file_exists(self, relative_path: str) -> bool:
        """Return whether a stored regular file exists."""

        path = self.resolve_file(relative_path)
        return path.is_file()

    def delete_file(self, relative_path: str) -> None:
        """Delete a stored file, treating an already-missing file as clean."""

        try:
            self.resolve_file(relative_path).unlink(missing_ok=True)
        except OSError as exc:
            raise StorageError("Unable to delete stored file.") from exc
