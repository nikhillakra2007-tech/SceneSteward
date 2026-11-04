"""Live integration status. 'configured' is NEVER reported as 'connected'."""
from __future__ import annotations

import logging

from fastapi import APIRouter

from app.core.config import get_settings
from app.core.database import check_database
from app.schemas.timeline import IntegrationHealthResponse, IntegrationStatus

logger = logging.getLogger("scenesteward.integrations.status")
router = APIRouter(tags=["integrations"])


@router.get("/integrations/status", response_model=IntegrationHealthResponse)
def integrations_status() -> IntegrationHealthResponse:
    s = get_settings()
    items: list[IntegrationStatus] = []

    db = check_database()
    items.append(IntegrationStatus(name="postgresql", status="configured_verified" if db["status"] == "ok" else "unavailable"))

    # Storage: local check is a real filesystem probe; supabase does a real GET.
    try:
        from app.integrations.storage import get_storage_provider
        probe = get_storage_provider().check()
        items.append(IntegrationStatus(name="storage", status="configured_verified" if probe.get("status") == "ok" else "unavailable"))
    except Exception as exc:  # noqa: BLE001 — health must never leak internals or raise
        items.append(IntegrationStatus(name="storage", status="missing_credentials" if "not configured" in str(exc) else "unavailable"))

    # AI provider: configured-ness only; a live probe would spend tokens.
    if s.ai_provider == "offline":
        items.append(IntegrationStatus(name="ai_provider", status="configured_verified", detail="offline deterministic provider"))
    elif s.anthropic_api_key:
        items.append(IntegrationStatus(name="ai_provider", status="configured_unverified", detail="ANTHROPIC_API_KEY set; live call not performed"))
    else:
        items.append(IntegrationStatus(name="ai_provider", status="missing_credentials"))

    # Switch: performs a real health+auth probe when http mode is selected.
    from app.integrations.switch import switch_status
    sw = switch_status()
    items.append(IntegrationStatus(name="switch", status=sw.status, detail=sw.detail))

    # Auth provider
    if s.auth_provider == "dev":
        items.append(IntegrationStatus(name="auth", status="configured_verified" if s.auth_dev_secret else "missing_credentials", detail="dev issuer (not for production)"))
    else:
        items.append(IntegrationStatus(
            name="auth",
            status="configured_unverified" if s.resolved_jwks_url else "missing_credentials",
            detail="supabase JWKS" + (" (jwks url derived)" if not s.auth_jwks_url else ""),
        ))

    # Redis is optional and only used if REDIS_URL is set (not part of required env).
    items.append(IntegrationStatus(name="redis", status="not_configured", detail="optional; rate limiting runs in-process"))
    return IntegrationHealthResponse(integrations=items)
