"""System and HTTP operational metrics endpoint."""
from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Header, Query, Response

from app.core.config import get_settings
from app.core.exceptions import PreconditionFailed
from app.services.metrics import get_metrics_summary, get_prometheus_metrics

router = APIRouter(tags=["metrics"])


@router.get("/metrics")
def get_metrics(
    accept: str | None = Header(default=None),
    format: str | None = Query(default=None),
) -> Any:
    settings = get_settings()
    if not getattr(settings, "metrics_enabled", True):
        raise PreconditionFailed("Metrics collection is disabled", code="metrics_disabled")

    wants_prometheus = (
        format == "prometheus"
        or (accept and "text/plain" in accept)
    )

    if wants_prometheus:
        return Response(content=get_prometheus_metrics(), media_type="text/plain; version=0.0.4")
    return get_metrics_summary()

