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


def mint_participant_token(
    *, participant_id: uuid.UUID, project_id: uuid.UUID, settings: Settings | None = None, ttl_seconds: int = 604800
) -> str:
    """Mint a cryptographically signed participant portal token."""
    s = settings or get_settings()
    secret = s.auth_dev_secret or s.database_identity_secret
    now = int(time.time())
    claims = {
        "sub": str(participant_id),
        "project_id": str(project_id),
        "scope": "participant_portal",
        "iss": s.auth_issuer,
        "iat": now,
        "exp": now + ttl_seconds,
    }
    return jwt.encode(claims, secret, algorithm="HS256")


def decode_participant_token(token: str, settings: Settings | None = None) -> dict[str, Any]:
    """Validate and decode a participant portal token."""
    s = settings or get_settings()
    secret = s.auth_dev_secret or s.database_identity_secret
    try:
        payload = jwt.decode(token, secret, algorithms=["HS256"], issuer=s.auth_issuer)
    except jwt.ExpiredSignatureError as exc:
        raise Unauthenticated("Participant portal access token expired", code="token_expired") from exc
    except jwt.PyJWTError as exc:
        raise Unauthenticated("Invalid participant portal token", code="invalid_token") from exc
    if payload.get("scope") != "participant_portal":
        raise Unauthenticated("Invalid token scope", code="invalid_scope")
    return payload



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

def _get_fernet_ring(s: Settings | None = None) -> tuple[str, dict[str, Fernet]]:
    s = s or get_settings()
    ring = s.resolved_encryption_key_ring
    if not ring:
        raise Unauthenticated("Contact encryption is not configured", code="encryption_unavailable")
    fernet_ring: dict[str, Fernet] = {}
    for kid, key_material in ring.items():
        try:
            fernet_ring[kid] = Fernet(key_material.encode("utf-8") if isinstance(key_material, str) else key_material)
        except Exception as exc:  # bad key material: fail closed, never fall back to plaintext
            raise Unauthenticated(f"Contact encryption key {kid} is misconfigured", code="encryption_unavailable") from exc
    current_kid = s.app_encryption_current_kid or "primary"
    if current_kid not in fernet_ring:
        current_kid = next(iter(fernet_ring))
    return current_kid, fernet_ring


def encrypt_secret(plaintext: str, settings: Settings | None = None, kid: str | None = None) -> str:
    current_kid, ring = _get_fernet_ring(settings)
    active_kid = kid or current_kid
    if active_kid not in ring:
        raise Unauthenticated(f"Encryption key {active_kid} is not available", code="encryption_unavailable")
    token = ring[active_kid].encrypt(plaintext.encode("utf-8")).decode("ascii")
    return f"v2.{active_kid}.{token}"


def decrypt_secret(ciphertext: str, settings: Settings | None = None) -> str:
    current_kid, ring = _get_fernet_ring(settings)
    if ciphertext.startswith("v2."):
        parts = ciphertext.split(".", 2)
        if len(parts) == 3:
            kid, token = parts[1], parts[2]
            f = ring.get(kid)
            if not f:
                raise Unauthenticated(f"Decryption key '{kid}' is not in key ring", code="encryption_failed")
            try:
                return f.decrypt(token.encode("ascii")).decode("utf-8")
            except InvalidToken as exc:
                raise Unauthenticated("Stored contact data could not be decrypted", code="encryption_failed") from exc

    # Legacy ciphertext (without v2.<kid>. prefix): try current_kid first, then others
    keys_to_try = [ring[current_kid]] + [f for k, f in ring.items() if k != current_kid]
    for f in keys_to_try:
        try:
            return f.decrypt(ciphertext.encode("ascii")).decode("utf-8")
        except InvalidToken:
            continue
    raise Unauthenticated("Stored contact data could not be decrypted", code="encryption_failed")


def constant_time_equals(a: str, b: str) -> bool:
    return hmac.compare_digest(a.encode(), b.encode())


def new_correlation_id() -> str:
    return str(uuid.uuid4())
