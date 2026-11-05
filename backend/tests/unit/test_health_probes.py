"""Unit tests for Health and Liveness/Readiness probes."""
from __future__ import annotations


def test_health_liveness(client):
    res = client.get("/health")
    assert res.status_code == 200
    assert res.json()["status"] == "ok"

    res_live = client.get("/health/live")
    assert res_live.status_code == 200
    assert res_live.json()["status"] == "ok"


def test_health_readiness(client):
    res = client.get("/health/ready")
    assert res.status_code == 200
    assert res.json()["status"] in ("ok", "degraded")
    assert "checks" in res.json()
    assert "database" in res.json()["checks"]
