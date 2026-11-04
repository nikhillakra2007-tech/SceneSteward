"""Integration tests for the operational metrics endpoint."""
from __future__ import annotations


def test_metrics_json_endpoint(client):
    # Make a couple requests first
    client.get("/health")
    client.get("/health/ready")

    res = client.get("/api/v1/metrics")
    assert res.status_code == 200
    data = res.json()
    assert "uptime_seconds" in data
    assert "total_requests" in data
    assert data["total_requests"] >= 2
    assert "requests_by_status" in data
    assert "db_pool" in data
    assert "checked_in" in data["db_pool"]


def test_metrics_prometheus_endpoint(client):
    res = client.get("/api/v1/metrics?format=prometheus")
    assert res.status_code == 200
    assert "text/plain" in res.headers.get("content-type", "")
    content = res.text
    assert "scenesteward_http_requests_total" in content
    assert "scenesteward_db_pool_connections" in content

