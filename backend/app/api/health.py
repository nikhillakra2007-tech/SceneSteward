"""Root liveness/readiness probes. No secrets, no internals beyond up/down."""
from __future__ import annotations

from fastapi import APIRouter

from app.core.config import get_settings
from app.core.database import check_database

router = APIRouter(tags=["health"])


@router.get("/health")
@router.get("/health/live")
def liveness() -> dict:
    return {"status": "ok", "app": get_settings().app_name}


@router.get("/health/ready")
def readiness() -> dict:
    db = check_database()
    return {"status": "ok" if db["status"] == "ok" else "degraded",
            "checks": {"database": db["status"]}}
