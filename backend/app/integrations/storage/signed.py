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


def _signing_material(kid: str | None = None) -> tuple[str, bytes]:
    s = get_settings()
    ring = s.resolved_encryption_key_ring
    active_kid = kid or s.app_encryption_current_kid or "primary"
    if ring and active_kid in ring:
        return active_kid, hashlib.sha256(ring[active_kid].encode("utf-8")).digest()
    material = s.app_encryption_key or s.auth_dev_secret
    if not material:
        raise PreconditionFailed("Storage signing is not configured (APP_ENCRYPTION_KEY missing)")
    return "primary", hashlib.sha256(material.encode("utf-8")).digest()


def _b64u(raw: bytes) -> str:
    return base64.urlsafe_b64encode(raw).decode("ascii").rstrip("=")


def _unb64u(data: str) -> bytes:
    pad = "=" * (-len(data) % 4)
    return base64.urlsafe_b64decode(data + pad)


def issue_token(*, storage_key: str, purpose: str, ttl_seconds: int, extra: dict[str, Any] | None = None,
                kid: str | None = None) -> str:
    if purpose not in _PURPOSES:
        raise ValueError(f"purpose must be one of {_PURPOSES}")
    active_kid, material = _signing_material(kid)
    payload = {"key": storage_key, "purpose": purpose, "exp": int(time.time()) + ttl_seconds, "kid": active_kid}
    if extra:
        payload.update(extra)
    body = _b64u(json.dumps(payload, separators=(",", ":")).encode())
    sig = hmac.new(material, body.encode(), hashlib.sha256).hexdigest()
    return f"{body}.{sig}"


def verify_token(token: str, *, purpose: str) -> dict[str, Any]:
    try:
        body, sig = token.split(".", 1)
    except ValueError as exc:
        raise PreconditionFailed("Malformed storage token") from exc
    try:
        payload = json.loads(_unb64u(body))
    except Exception as exc:
        raise PreconditionFailed("Malformed storage token payload") from exc
    kid = payload.get("kid")
    _, material = _signing_material(kid)
    expected = hmac.new(material, body.encode(), hashlib.sha256).hexdigest()
    if not hmac.compare_digest(expected, sig):
        raise PreconditionFailed("Invalid storage token signature")
    if payload.get("purpose") != purpose:
        raise PreconditionFailed("Storage token purpose mismatch")
    if int(payload.get("exp", 0)) < int(time.time()):
        raise PreconditionFailed("Storage token expired")
    return payload
