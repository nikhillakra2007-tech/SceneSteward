"""Local storage transfer endpoints — authorisation is the HMAC token itself.

Tokens are short-lived, purpose-bound (upload|download), and size-capped.
These routes never accept bearer-only access and never log file contents.
"""
from __future__ import annotations

import mimetypes

from fastapi import APIRouter, Request
from fastapi.responses import FileResponse, JSONResponse, Response

from app.core.config import get_settings
from app.integrations.storage import local as local_storage
from app.integrations.storage import signed

router = APIRouter(prefix="/storage/local", tags=["storage-local"])
settings = get_settings()

_MAX_BODY_SLACK = 1024 * 1024  # 1 MiB over the advertised cap is still rejected


@router.put("/upload/{token}")
async def local_upload(token: str, request: Request) -> Response:
    payload = signed.verify_token(token, purpose="upload")
    max_bytes = int(payload.get("max_bytes", settings.max_upload_bytes))
    content_length = request.headers.get("content-length")
    if content_length and int(content_length) > max_bytes + _MAX_BODY_SLACK:
        return JSONResponse(status_code=413, content={"error": {"code": "file_too_large",
                                                                "message": "Upload exceeds the allowed size"}})
    body = await request.body()
    if len(body) > max_bytes:
        return JSONResponse(status_code=413, content={"error": {"code": "file_too_large",
                                                                "message": "Upload exceeds the allowed size"}})
    provider = local_storage.get_local_provider()
    size = provider.store_bytes(payload["key"], body)
    return JSONResponse(status_code=201, content={"stored_bytes": size})


@router.get("/download/{token}")
def local_download(token: str) -> FileResponse:
    payload = signed.verify_token(token, purpose="download")
    provider = local_storage.get_local_provider()
    path = provider.open_download(payload["key"])
    media_type = mimetypes.guess_type(path.name)[0] or "application/octet-stream"
    return FileResponse(
        path,
        media_type=media_type,
        filename=path.name.split("_", 1)[-1] if "_" in path.name else path.name,
        headers={"X-Content-Type-Options": "nosniff", "Cache-Control": "no-store"},
    )
