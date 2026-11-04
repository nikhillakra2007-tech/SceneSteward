"""HMAC-signed, purpose-bound, short-lived tokens for local storage URLs.

Token format: base64url(json{key, purpose, exp}) + "." + hex(hmac_sha256).
The signing key is derived from server-side secrets only; nothing here is
client-computable. Tokens are single-purpose and expire.
"""
from __future__ import annotations

import base64
import hashlib
import hmac
import json
import time
from typing import Any

from app.core.config import get_settings
from app.core.exceptions import PreconditionFailed

_PURPOSES = ("upload", "download")


def _signing_material() -> bytes:
    s = get_settings()
    material = s.app_encryption_key or s.auth_dev_secret
    if not material:
        raise PreconditionFailed("Storage signing is not configured (APP_ENCRYPTION_KEY missing)")
    return hashlib.sha256(material.encode("utf-8")).digest()


def _b64u(raw: bytes) -> str:
    return base64.urlsafe_b64encode(raw).decode("ascii").rstrip("=")


def _unb64u(data: str) -> bytes:
    pad = "=" * (-len(data) % 4)
    return base64.urlsafe_b64decode(data + pad)


def issue_token(*, storage_key: str, purpose: str, ttl_seconds: int, extra: dict[str, Any] | None = None) -> str:
    if purpose not in _PURPOSES:
        raise ValueError(f"purpose must be one of {_PURPOSES}")
    payload = {"key": storage_key, "purpose": purpose, "exp": int(time.time()) + ttl_seconds}
    if extra:
        payload.update(extra)
    body = _b64u(json.dumps(payload, separators=(",", ":")).encode())
    sig = hmac.new(_signing_material(), body.encode(), hashlib.sha256).hexdigest()
    return f"{body}.{sig}"


def verify_token(token: str, *, purpose: str) -> dict[str, Any]:
    try:
        body, sig = token.split(".", 1)
    except ValueError as exc:
        raise PreconditionFailed("Malformed storage token") from exc
    expected = hmac.new(_signing_material(), body.encode(), hashlib.sha256).hexdigest()
    if not hmac.compare_digest(expected, sig):
        raise PreconditionFailed("Invalid storage token signature")
    try:
        payload = json.loads(_unb64u(body))
    except Exception as exc:
        raise PreconditionFailed("Malformed storage token payload") from exc
    if payload.get("purpose") != purpose:
        raise PreconditionFailed("Storage token purpose mismatch")
    if int(payload.get("exp", 0)) < int(time.time()):
        raise PreconditionFailed("Storage token expired")
    return payload
