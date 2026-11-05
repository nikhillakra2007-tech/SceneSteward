"""Unit tests for Health, Liveness, and Readiness probes.

Verifies:
- Liveness contract
- Readiness multi-subsystem contract
- Critical failure handling (HTTP 503)
- Degraded mode handling (HTTP 200)
- Absolute secret exclusion from probe responses
"""
from __future__ import annotations

from unittest.mock import MagicMock, patch

from app.core.config import get_settings


def test_health_liveness(client):
    res = client.get("/health")
    assert res.status_code == 200
    assert res.json()["status"] == "ok"
    assert "version" in res.json()

    res_live = client.get("/health/live")
    assert res_live.status_code == 200
    assert res_live.json()["status"] == "ok"


def test_health_readiness(client):
    res = client.get("/health/ready")
    assert res.status_code == 200
    data = res.json()
    assert data["status"] in ("ok", "degraded")
    assert "checks" in data
    assert "database" in data["checks"]
    assert "storage" in data["checks"]
    assert "timestamp" in data
    assert "version" in data


def test_health_readiness_database_failure_returns_503(client):
    with patch("app.api.health.check_database", return_value={"status": "unavailable", "error_category": "OperationalError"}):
        res = client.get("/health/ready")
        assert res.status_code == 503
        data = res.json()
        assert data["status"] == "unhealthy"
        assert data["checks"]["database"]["status"] == "error"


def test_health_readiness_clamav_fail_closed_returns_503(client, monkeypatch):
    current = get_settings()
    mock_settings = MagicMock(wraps=current)
    mock_settings.antivirus_provider = "clamav"
    mock_settings.antivirus_fail_closed = True
    mock_settings.clamav_host = "127.0.0.1"
    mock_settings.clamav_port = 3310
    mock_settings.storage_provider = "local"
    mock_settings.storage_local_path = current.storage_local_path
    mock_settings.redis_url = None

    with patch("app.api.health.get_settings", return_value=mock_settings), \
         patch("app.api.health.ping_clamav", return_value=False):
        res = client.get("/health/ready")
        assert res.status_code == 503
        data = res.json()
        assert data["status"] == "unhealthy"
        assert data["checks"]["clamav"]["status"] == "error"


def test_health_readiness_clamav_non_fail_closed_returns_200_degraded(client):
    current = get_settings()
    mock_settings = MagicMock(wraps=current)
    mock_settings.antivirus_provider = "clamav"
    mock_settings.antivirus_fail_closed = False
    mock_settings.clamav_host = "127.0.0.1"
    mock_settings.clamav_port = 3310
    mock_settings.storage_provider = "local"
    mock_settings.storage_local_path = current.storage_local_path
    mock_settings.redis_url = None

    with patch("app.api.health.get_settings", return_value=mock_settings), \
         patch("app.api.health.ping_clamav", return_value=False):
        res = client.get("/health/ready")
        assert res.status_code == 200
        data = res.json()
        assert data["status"] == "degraded"
        assert data["checks"]["clamav"]["status"] == "error"


def test_health_readiness_redis_failure_returns_200_degraded(client):
    current = get_settings()
    mock_settings = MagicMock(wraps=current)
    mock_settings.redis_url = "redis://:secret_pass@redis:6379/0"
    mock_settings.antivirus_provider = "none"
    mock_settings.storage_provider = "local"
    mock_settings.storage_local_path = current.storage_local_path

    with patch("app.api.health.get_settings", return_value=mock_settings), \
         patch("app.core.rate_limiter.get_rate_limiter") as mock_limiter:
        mock_instance = mock_limiter.return_value
        mock_instance._redis_available = False
        res = client.get("/health/ready")
        assert res.status_code == 200
        data = res.json()
        assert data["status"] == "degraded"
        assert data["checks"]["redis"]["status"] == "error"
        assert data["checks"]["redis"]["fallback"] == "in_memory"


def test_health_readiness_secret_exclusion(client):
    res = client.get("/health/ready")
    text = res.text
    forbidden_tokens = [
        "secret", "password", "postgresql://", "redis://",
        "Bearer", "Fernet", "key", "token", "DATABASE_URL"
    ]
    for token in forbidden_tokens:
        assert token not in text, f"Found secret/credential token '{token}' in health readiness response: {text}"
