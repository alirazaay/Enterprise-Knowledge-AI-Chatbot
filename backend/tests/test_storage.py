from io import BytesIO

import pytest
from fastapi import UploadFile

from app.core.storage import FileStorageService, StorageError


@pytest.mark.anyio
async def test_storage_uses_safe_unique_names_and_streams_file(tmp_path) -> None:
    service = FileStorageService(tmp_path)
    upload = UploadFile(filename="../../Employee Handbook.pdf", file=BytesIO(b"%PDF-test"), headers={"content-type": "application/pdf"})

    stored = await service.save_file(upload, ".pdf", max_bytes=100)

    assert stored.relative_path.endswith(".pdf")
    assert ".." not in stored.relative_path
    assert (tmp_path / stored.relative_path).is_file()
    assert stored.size == len(b"%PDF-test")


@pytest.mark.anyio
async def test_storage_rejects_empty_and_oversized_files(tmp_path) -> None:
    service = FileStorageService(tmp_path)
    empty = UploadFile(filename="empty.pdf", file=BytesIO(b""), headers={"content-type": "application/pdf"})
    with pytest.raises(StorageError, match="empty"):
        await service.save_file(empty, ".pdf", max_bytes=100)

    oversized = UploadFile(filename="large.pdf", file=BytesIO(b"12345"), headers={"content-type": "application/pdf"})
    with pytest.raises(StorageError, match="exceeds"):
        await service.save_file(oversized, ".pdf", max_bytes=4)


def test_storage_rejects_path_traversal(tmp_path) -> None:
    service = FileStorageService(tmp_path)
    with pytest.raises(StorageError):
        service.resolve_file("../outside.pdf")
