"""Supabase Storage adapter (private bucket) — implemented, NOT live-verified here.

Uses the Storage REST API with the service-role key (server-side only).
"""
from __future__ import annotations

import logging
from typing import BinaryIO

import httpx

from app.core.config import get_settings
from app.core.exceptions import NotFoundError, PreconditionFailed, UpstreamUnavailable

logger = logging.getLogger("scenesteward.storage.supabase")


class SupabaseStorageProvider:
    def __init__(self) -> None:
        s = get_settings()
        if not (s.supabase_url and s.supabase_service_role_key and s.storage_bucket):
            raise PreconditionFailed("Supabase storage is not configured (SUPABASE_URL / SUPABASE_SERVICE_ROLE_KEY / STORAGE_BUCKET)")
        self.base = s.supabase_url.rstrip("/") + "/storage/v1"
        self.bucket = s.storage_bucket
        self._headers = {"Authorization": f"Bearer {s.supabase_service_role_key}", "apikey": s.supabase_service_role_key}
        self._client = httpx.Client(timeout=httpx.Timeout(20.0))

    def create_upload_target(self, storage_key: str, *, max_bytes: int, ttl_seconds: int) -> str:
        resp = self._client.post(
            f"{self.base}/object/upload/sign/{self.bucket}/{storage_key}",
            headers=self._headers,
        )
        if resp.status_code >= 400:
            logger.warning("supabase sign-upload failed status=%s", resp.status_code)
            raise UpstreamUnavailable("Could not create a signed upload URL")
        data = resp.json()
        signed_path = data.get("url") or data.get("signedUrl") or ""
        return self.base + signed_path if signed_path.startswith("/") else signed_path

    def create_download_url(self, storage_key: str, *, ttl_seconds: int) -> str:
        resp = self._client.post(
            f"{self.base}/object/sign/{self.bucket}/{storage_key}",
            headers=self._headers,
            json={"expiresIn": ttl_seconds},
        )
        if resp.status_code >= 400:
            logger.warning("supabase sign-download failed status=%s", resp.status_code)
            raise UpstreamUnavailable("Could not create a signed download URL")
        data = resp.json()
        signed_path = data.get("signedURL") or data.get("signedUrl") or data.get("url") or ""
        return (self.base + signed_path) if signed_path.startswith("/") else signed_path

    def read_bytes(self, storage_key: str) -> bytes:
        resp = self._client.get(f"{self.base}/object/{self.bucket}/{storage_key}", headers=self._headers)
        if resp.status_code == 404:
            raise NotFoundError("File not found")
        if resp.status_code >= 400:
            raise UpstreamUnavailable("Could not read the stored file")
        return resp.content

    def store_stream(self, storage_key: str, stream: BinaryIO, *, max_bytes: int) -> int:
        data = stream.read(max_bytes + 1)
        if len(data) > max_bytes:
            raise PreconditionFailed("Upload exceeds the maximum allowed size")
        resp = self._client.put(
            f"{self.base}/object/{self.bucket}/{storage_key}",
            headers={**self._headers, "Content-Type": "application/octet-stream", "x-upsert": "false"},
            content=data,
        )
        if resp.status_code >= 400:
            logger.warning("supabase object put failed status=%s", resp.status_code)
            raise UpstreamUnavailable("Could not store the file")
        return len(data)

    def open_download(self, storage_key: str):
        raise NotImplementedError("Supabase mode: clients use create_download_url directly")

    def exists(self, storage_key: str) -> bool:
        resp = self._client.post(f"{self.base}/object/info/{self.bucket}/{storage_key}", headers=self._headers)
        return resp.status_code == 200

    def size(self, storage_key: str) -> int:
        resp = self._client.post(f"{self.base}/object/info/{self.bucket}/{storage_key}", headers=self._headers)
        if resp.status_code != 200:
            raise NotFoundError("File not found")
        return int(resp.json().get("size") or 0)

    def delete(self, storage_key: str) -> None:
        resp = self._client.delete(f"{self.base}/object/{self.bucket}/{storage_key}", headers=self._headers)
        if resp.status_code >= 400:
            logger.warning("supabase delete failed status=%s", resp.status_code)

    def check(self) -> dict[str, str]:
        try:
            resp = self._client.get(f"{self.base}/bucket/{self.bucket}", headers=self._headers)
            return {"status": "ok"} if resp.status_code == 200 else {"status": "unavailable"}
        except httpx.TimeoutException:
            return {"status": "timeout"}
        except httpx.HTTPError:
            return {"status": "unavailable"}


def get_supabase_provider() -> SupabaseStorageProvider:
    return SupabaseStorageProvider()
