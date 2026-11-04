"""Token validation (Google/Supabase/dev), password-free users, encryption at rest.

AUTH_PROVIDER=dev     -> HS256 tokens minted by scripts/dev_token.py (local only)
AUTH_PROVIDER=supabase -> validates Supabase-issued JWTs against the project's JWKS
                          (signature, exp, issuer, audience, subject). Never trusts a
                          user id sent by the frontend.
"""
from __future__ import annotations

import hmac
import logging
import time
import uuid
from dataclasses import dataclass
from typing import Any

import jwt
from cryptography.fernet import Fernet, InvalidToken

from app.core.config import Settings, get_settings
from app.core.exceptions import Unauthenticated

logger = logging.getLogger("scenesteward.security")


@dataclass(frozen=True)
class TokenClaims:
    provider: str
    subject: str          # provider's stable user id (never a client-supplied value)
    email: str | None
    full_name: str | None
    issued_at: int
    expires_at: int
    raw: dict[str, Any]


def mint_dev_token(*, user_id: str, email: str, full_name: str, settings: Settings | None = None,
                   ttl_seconds: int = 3600) -> str:
    """Mint a local dev HS256 token. Disabled outside the dev provider."""
    s = settings or get_settings()
    if s.auth_provider != "dev":
        raise RuntimeError("dev tokens can only be minted when AUTH_PROVIDER=dev")
    if not s.auth_dev_secret:
        raise RuntimeError("AUTH_DEV_SECRET is not configured")
    now = int(time.time())
    claims = {
        "sub": user_id,
        "email": email,
        "name": full_name,
        "iss": s.auth_issuer,
        "aud": s.auth_audience,
        "iat": now,
        "exp": now + ttl_seconds,
    }
    return jwt.encode(claims, s.auth_dev_secret, algorithm="HS256")


def _decode_dev(token: str, s: Settings) -> TokenClaims:
    if not s.auth_dev_secret:
        raise Unauthenticated("Dev auth is not configured")
    try:
        payload = jwt.decode(token, s.auth_dev_secret, algorithms=["HS256"],
                             issuer=s.auth_issuer, audience=s.auth_audience)
    except jwt.ExpiredSignatureError as exc:
        raise Unauthenticated("Token expired", code="token_expired") from exc
    except jwt.PyJWTError as exc:
        raise Unauthenticated("Invalid token", code="invalid_token") from exc
    return TokenClaims("dev", payload["sub"], payload.get("email"), payload.get("name"),
                       int(payload.get("iat", 0)), int(payload["exp"]), payload)


_jwks_clients: dict[str, jwt.PyJWKClient] = {}


def _decode_supabase(token: str, s: Settings) -> TokenClaims:
    jwks_url = s.resolved_jwks_url
    issuer = s.resolved_supabase_issuer
    if not jwks_url or not issuer:
        raise Unauthenticated("Supabase auth is not configured")
    client = _jwks_clients.get(jwks_url)
    if client is None:
        client = jwt.PyJWKClient(jwks_url, cache_jwk_set=True, lifespan=3600)
        _jwks_clients[jwks_url] = client
    try:
        signing_key = client.get_signing_key_from_jwt(token)
        payload = jwt.decode(
            token,
            signing_key.key,
            algorithms=["RS256", "ES256"],
            issuer=issuer,
            audience=s.auth_audience or "authenticated",
        )
    except jwt.ExpiredSignatureError as exc:
        raise Unauthenticated("Token expired", code="token_expired") from exc
    except jwt.InvalidAudienceError as exc:
        raise Unauthenticated("Wrong token audience", code="invalid_audience") from exc
    except jwt.InvalidIssuerError as exc:
        raise Unauthenticated("Wrong token issuer", code="invalid_issuer") from exc
    except jwt.PyJWTError as exc:
        raise Unauthenticated("Invalid token", code="invalid_token") from exc
    meta = payload.get("user_metadata") or {}
    return TokenClaims(
        "supabase",
        payload["sub"],
        payload.get("email"),
        meta.get("full_name") or meta.get("name"),
        int(payload.get("iat", 0)),
        int(payload["exp"]),
        payload,
    )


def decode_token(token: str, settings: Settings | None = None) -> TokenClaims:
    s = settings or get_settings()
    if s.auth_provider == "dev":
        return _decode_dev(token, s)
    if s.auth_provider == "supabase":
        return _decode_supabase(token, s)
    raise Unauthenticated("Unsupported auth provider")


# --- Encryption at rest for participant contact details -------------------

def _fernet(s: Settings | None = None) -> Fernet:
    s = s or get_settings()
    if not s.app_encryption_key:
        raise Unauthenticated("Contact encryption is not configured", code="encryption_unavailable")
    try:
        return Fernet(s.app_encryption_key.encode())
    except Exception as exc:  # bad key material: fail closed, never fall back to plaintext
        raise Unauthenticated("Contact encryption is misconfigured", code="encryption_unavailable") from exc


def encrypt_secret(plaintext: str, settings: Settings | None = None) -> str:
    return _fernet(settings).encrypt(plaintext.encode("utf-8")).decode("ascii")


def decrypt_secret(ciphertext: str, settings: Settings | None = None) -> str:
    try:
        return _fernet(settings).decrypt(ciphertext.encode("ascii")).decode("utf-8")
    except InvalidToken as exc:
        raise Unauthenticated("Stored contact data could not be decrypted", code="encryption_failed") from exc


def constant_time_equals(a: str, b: str) -> bool:
    return hmac.compare_digest(a.encode(), b.encode())


def new_correlation_id() -> str:
    return str(uuid.uuid4())
