"""Filesystem-backed private storage (development/demo).

- Keys are sanitised; path traversal is rejected.
- Upload size is capped; MIME is verified from magic bytes after transfer.
- Downloads are served only through HMAC-signed URLs validated by the API.
"""
from __future__ import annotations

import logging
import os
import re
from pathlib import Path
from typing import BinaryIO

from app.core.config import get_settings
from app.core.exceptions import NotFoundError, PreconditionFailed
from app.integrations.storage import signed

logger = logging.getLogger("scenesteward.storage.local")

_CHUNK = 1024 * 1024
_SAFE_KEY = re.compile(r"^(?!/)(?!.*\.\.)[A-Za-z0-9][A-Za-z0-9._/-]*$")

_MAGIC = [
    (b"%PDF-", "application/pdf"),
    (b"PK\x03\x04", "application/vnd.openxmlformats-officedocument.wordprocessingml.document"),
]


class LocalStorageProvider:
    def __init__(self, root: str) -> None:
        self.root = Path(root).resolve()

    # -- helpers -----------------------------------------------------------
    def _path(self, storage_key: str) -> Path:
        if not _SAFE_KEY.match(storage_key):
            raise PreconditionFailed("Invalid storage key")
        path = (self.root / storage_key).resolve()
        if self.root not in path.parents and path != self.root:
            raise PreconditionFailed("Storage key escapes the storage root")
        return path

    # -- interface ---------------------------------------------------------
    def create_upload_target(self, storage_key: str, *, max_bytes: int, ttl_seconds: int) -> str:
        token = signed.issue_token(storage_key=storage_key, purpose="upload", ttl_seconds=ttl_seconds,
                                   extra={"max_bytes": max_bytes})
        return f"/api/v1/storage/local/upload/{token}"

    def create_download_url(self, storage_key: str, *, ttl_seconds: int) -> str:
        token = signed.issue_token(storage_key=storage_key, purpose="download", ttl_seconds=ttl_seconds)
        return f"/api/v1/storage/local/download/{token}"

    def store_bytes(self, storage_key: str, data: bytes) -> int:
        path = self._path(storage_key)
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "wb") as fh:
            fh.write(data)
        return len(data)

    def store_stream(self, storage_key: str, stream: BinaryIO, *, max_bytes: int) -> int:
        path = self._path(storage_key)
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp = path.with_suffix(path.suffix + ".part")
        size = 0
        with open(tmp, "wb") as fh:
            while True:
                chunk = stream.read(_CHUNK)
                if not chunk:
                    break
                size += len(chunk)
                if size > max_bytes:
                    fh.close()
                    tmp.unlink(missing_ok=True)
                    raise PreconditionFailed("Upload exceeds the maximum allowed size")
                fh.write(chunk)
        os.replace(tmp, path)
        return size

    def sniff_mime(self, storage_key: str) -> str | None:
        path = self._path(storage_key)
        with open(path, "rb") as fh:
            head = fh.read(8)
        for magic, mime in _MAGIC:
            if head.startswith(magic):
                return mime
        try:
            with open(path, "rb") as fh:
                fh.read(8192).decode("utf-8")
            ext = path.suffix.lower()
            return "text/markdown" if ext == ".md" else "text/plain"
        except UnicodeDecodeError:
            return None

    def read_bytes(self, storage_key: str) -> bytes:
        path = self._path(storage_key)
        if not path.is_file():
            raise NotFoundError("File not found")
        return path.read_bytes()

    def exists(self, storage_key: str) -> bool:
        return self._path(storage_key).is_file()

    def size(self, storage_key: str) -> int:
        return self._path(storage_key).stat().st_size

    def open_download(self, storage_key: str) -> Path:
        path = self._path(storage_key)
        if not path.is_file():
            raise NotFoundError("File not found")
        return path

    def delete(self, storage_key: str) -> None:
        self._path(storage_key).unlink(missing_ok=True)

    def check(self) -> dict[str, str]:
        try:
            self.root.mkdir(parents=True, exist_ok=True)
            probe = self.root / ".healthcheck"
            probe.write_text("ok", encoding="utf-8")
            probe.unlink()
            return {"status": "ok"}
        except OSError as exc:
            logger.warning("local storage check failed: %s", type(exc).__name__)
            return {"status": "unavailable"}


_provider: LocalStorageProvider | None = None


def get_local_provider() -> LocalStorageProvider:
    global _provider
    if _provider is None:
        _provider = LocalStorageProvider(get_settings().storage_local_path)
    return _provider
