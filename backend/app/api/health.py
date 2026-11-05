"""Root liveness and readiness probes.

Strictly excludes secrets, credentials, internal file paths, or sensitive connection parameters.
Returns HTTP 200 for healthy/degraded (non-fatal) and HTTP 503 for critical failures.
"""
from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from fastapi import APIRouter, Response, status

from app.core.config import get_settings
from app.core.database import check_database
from app.services.malware_scanner import ping_clamav

router = APIRouter(tags=["health"])


@router.get("/health")
@router.get("/health/live")
def liveness() -> dict[str, Any]:
    """Lightweight probe verifying that the HTTP server process is running."""
    settings = get_settings()
    return {
        "status": "ok",
        "app": settings.app_name,
        "version": settings.api_version,
    }


@router.get("/health/ready")
def readiness(response: Response) -> dict[str, Any]:
    """Comprehensive readiness probe verifying all critical platform dependencies."""
    settings = get_settings()
    checks: dict[str, Any] = {}
    is_healthy = True
    is_degraded = False

    # 1. Database Check (Critical)
    db_result = check_database()
    if db_result.get("status") == "ok":
        migration_head = db_result.get("migration_head")
        if settings.app_env == "production" and not migration_head:
            is_healthy = False
            checks["database"] = {
                "status": "unmigrated",
                "error": "database missing migration version",
            }
        else:
            checks["database"] = {
                "status": "ok",
                "migration_head": migration_head,
                "current_user": db_result.get("current_user"),
            }
    else:
        is_healthy = False
        checks["database"] = {
            "status": "error",
            "category": db_result.get("error_category", "UnknownError"),
        }

    # 2. Redis Check (Configured in staging/prod)
    if settings.redis_url:
        try:
            from app.core.rate_limiter import get_rate_limiter
            limiter = get_rate_limiter(settings.redis_url)
            if limiter._redis_available and limiter.redis_client is not None:
                limiter.redis_client.ping()
                checks["redis"] = {"status": "ok"}
            else:
                checks["redis"] = {"status": "error", "fallback": "in_memory"}
                if settings.app_env == "production":
                    is_healthy = False
                else:
                    is_degraded = True
        except Exception:  # noqa: BLE001
            checks["redis"] = {"status": "error", "fallback": "in_memory"}
            if settings.app_env == "production":
                is_healthy = False
            else:
                is_degraded = True
    else:
        checks["redis"] = {"status": "disabled"}

    # 3. Antivirus Daemon Check (ClamAV)
    if settings.antivirus_provider == "clamav":
        clamav_ok = ping_clamav(settings.clamav_host, settings.clamav_port, timeout=2.0)
        if clamav_ok:
            checks["clamav"] = {"status": "ok"}
        else:
            checks["clamav"] = {"status": "error"}
            if settings.antivirus_fail_closed:
                # In fail-closed mode, ClamAV failure blocks uploads -> critical
                is_healthy = False
            else:
                is_degraded = True
    else:
        checks["clamav"] = {"status": "disabled"}

    # 4. Storage Subsystem Check
    if settings.storage_provider == "local":
        try:
            storage_dir = Path(settings.storage_local_path)
            storage_dir.mkdir(parents=True, exist_ok=True)
            probe_file = storage_dir / ".health_probe"
            probe_file.touch(exist_ok=True)
            probe_file.unlink(missing_ok=True)
            checks["storage"] = {"status": "ok", "provider": "local"}
        except Exception:  # noqa: BLE001
            is_healthy = False
            checks["storage"] = {"status": "error", "provider": "local"}
    elif settings.storage_provider == "supabase":
        configured = bool(settings.supabase_url and settings.supabase_service_role_key)
        checks["storage"] = {
            "status": "ok" if configured else "error",
            "provider": "supabase",
        }
        if not configured:
            is_healthy = False
    else:
        checks["storage"] = {"status": "ok", "provider": settings.storage_provider}

    # Determine overall status and HTTP response code
    if not is_healthy:
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
        overall_status = "unhealthy"
    elif is_degraded:
        response.status_code = status.HTTP_200_OK
        overall_status = "degraded"
    else:
        response.status_code = status.HTTP_200_OK
        overall_status = "ok"

    return {
        "status": overall_status,
        "app": settings.app_name,
        "version": settings.api_version,
        "timestamp": datetime.now(UTC).isoformat(),
        "checks": checks,
    }
