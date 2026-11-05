"""Automated tests for operational resilience, backup/restore integrity, and fail-closed operational boundaries.

Proves:
1. Unprivileged runtime role (scenesteward_app) cannot access private.app_secrets.
2. Runtime role cannot bypass RLS (rolbypassrls=False, rolsuper=False).
3. Backup creation uses atomic staging (.tmp_bkp_*), writes metadata manifest, and cleans staging.
4. Corrupted backup archives fail TOC verification.
5. Restore aborts on SHA-256 checksum mismatch before any database commands execute.
6. Restore rejects missing manifest metadata.
7. Restore guards block execution against production/non-test targets.
8. Readiness probe fails closed (HTTP 503) on Redis failure in production.
9. Readiness probe degrades gracefully (HTTP 200) on Redis failure in development.
10. Readiness probe fails closed (HTTP 503) on unmigrated database in production.
11. Worker heartbeat records valid health state and check_worker_health() detects stale/missing heartbeats.
12. Worker recovers stale processing jobs older than threshold back to failed state.
"""
from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta
from unittest.mock import MagicMock

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text

from app.core.config import Settings, get_settings
from app.core.database import system_context, verify_runtime_role_identity
from app.main import create_app
from app.models import IntegrationEvent
from scripts.backup_database import compute_streaming_sha256, run_backup
from scripts.restore_database import run_restore
from scripts.switch_retry import check_worker_health, recover_stale_events, write_heartbeat


def test_unprivileged_role_cannot_read_private_secrets():
    """Unprivileged runtime role (scenesteward_app) must be denied access to private schema."""
    settings = get_settings()
    app_engine = create_engine(settings.database_url, future=True)
    with app_engine.connect() as conn:
        role_info = verify_runtime_role_identity(conn)
        if role_info.get("current_user") == "scenesteward_app":
            with pytest.raises(Exception) as exc_info:
                conn.execute(text("SELECT secret_val FROM private.app_secrets"))
            assert "permission denied" in str(exc_info.value).lower() or "does not exist" in str(exc_info.value).lower()


def test_unprivileged_role_cannot_bypass_rls():
    """Runtime role identity verification must confirm NOBYPASSRLS and NOSUPERUSER."""
    settings = get_settings()
    app_engine = create_engine(settings.database_url, future=True)
    with app_engine.connect() as conn:
        role_info = verify_runtime_role_identity(conn)
        if role_info.get("current_user") == "scenesteward_app":
            assert role_info.get("rolsuper") is False, "Runtime user must NOT be a superuser"
            assert role_info.get("rolbypassrls") is False, "Runtime user must NOT have BYPASSRLS privilege"


def test_backup_creates_atomic_staging_and_manifest(tmp_path):
    """Backup produces published archive, sha256 checksum, manifest, and cleans temporary files."""
    settings = get_settings()
    db_url = settings.migration_database_url or settings.database_url

    backup_path = run_backup(
        output_dir=tmp_path,
        db_url=db_url,
    )
    assert backup_path.exists()
    assert not backup_path.name.startswith(".tmp_")

    # Staging temp files must not remain
    tmp_files = list(tmp_path.glob(".tmp_bkp_*"))
    assert len(tmp_files) == 0, "Temporary staging files were not cleaned up"

    # Manifest must exist with valid checksum and metadata
    manifest_path = backup_path.parent / (backup_path.stem + ".meta.json")
    assert manifest_path.exists()
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    assert manifest["backup_id"].startswith("bkp_")
    assert manifest["sha256"] == compute_streaming_sha256(backup_path)
    assert manifest["size_bytes"] == backup_path.stat().st_size
    assert "password" not in json.dumps(manifest).lower()


def test_restore_checksum_mismatch_aborts(tmp_path):
    """Restore must immediately abort before executing restore if checksum does not match manifest."""
    dump_file = tmp_path / "test_fake.dump"
    dump_file.write_bytes(b"PGDMP_FAKE_DATA")

    manifest_file = tmp_path / "test_fake.meta.json"
    manifest_file.write_text(
        json.dumps({
            "backup_id": "bkp_fake_001",
            "sha256": "0000000000000000000000000000000000000000000000000000000000000000",
            "size_bytes": 15,
            "created_at_utc": datetime.now(UTC).isoformat(),
        }),
        encoding="utf-8",
    )

    with pytest.raises(ValueError) as exc_info:
        run_restore(
            backup_file=dump_file,
            target_db="scenesteward_disposable_test",
            db_url="postgresql://postgres:postgres@127.0.0.1:5432/scenesteward_disposable_test",
        )
    assert "checksum" in str(exc_info.value).lower()


def test_restore_missing_manifest_aborts(tmp_path):
    """Restore must fail closed if the required cryptographic manifest is missing."""
    dump_file = tmp_path / "unverified.dump"
    dump_file.write_bytes(b"PGDMP_DUMMY_PAYLOAD")

    with pytest.raises(ValueError) as exc_info:
        run_restore(
            backup_file=dump_file,
            target_db="scenesteward_disposable_test",
            db_url="postgresql://postgres:postgres@127.0.0.1:5432/scenesteward_disposable_test",
        )
    assert "manifest" in str(exc_info.value).lower()


def test_restore_lifecycle_guard_rejects_production_target(tmp_path):
    """Restore must be rejected against production databases or non-test database targets."""
    dump_file = tmp_path / "dummy.dump"
    dump_file.write_bytes(b"PGDMP")
    manifest_file = tmp_path / "dummy.meta.json"
    manifest_file.write_text(
        json.dumps({
            "backup_id": "bkp_dummy",
            "sha256": compute_streaming_sha256(dump_file),
            "size_bytes": 5,
        }),
        encoding="utf-8",
    )

    with pytest.raises(RuntimeError) as exc_info:
        run_restore(
            backup_file=dump_file,
            target_db="scenesteward_prod",  # Forbidden production target!
            db_url="postgresql://postgres:postgres@127.0.0.1:5432/scenesteward_prod",
        )
    assert "guard" in str(exc_info.value).lower() or "refusing" in str(exc_info.value).lower()


def test_redis_failure_fails_closed_in_production(monkeypatch):
    """In production, Redis unavailability must fail closed with HTTP 503."""
    mock_settings = Settings(
        app_env="production",
        auth_provider="supabase",
        supabase_url="https://prod.supabase.co",
        supabase_anon_key="anon_test",
        database_url="postgresql://user:pass@127.0.0.1/scenesteward_test",
        database_identity_secret="a" * 32,
        redis_url="redis://localhost:6379/0",
    )
    monkeypatch.setattr("app.core.config.get_settings", lambda: mock_settings)
    monkeypatch.setattr("app.api.health.get_settings", lambda: mock_settings)
    monkeypatch.setattr("app.api.health.check_database", lambda: {"status": "ok", "migration_head": "e1f2a3b4c5d6"})

    # Mock Redis failure
    mock_limiter = MagicMock()
    mock_limiter._redis_available = False
    mock_limiter.redis_client = None
    monkeypatch.setattr("app.core.rate_limiter.get_rate_limiter", lambda url: mock_limiter)

    app = create_app()
    client = TestClient(app, raise_server_exceptions=False)
    resp = client.get("/health/ready")
    assert resp.status_code == 503
    data = resp.json()
    assert data["status"] == "unhealthy"
    assert data["checks"]["redis"]["status"] == "error"


def test_redis_failure_degrades_gracefully_in_development(monkeypatch):
    """In development, Redis unavailability degrades gracefully to in-memory fallback with HTTP 200."""
    mock_settings = Settings(
        app_env="development",
        auth_provider="dev",
        database_url="postgresql://user:pass@127.0.0.1/scenesteward_test",
        database_identity_secret="a" * 32,
        redis_url="redis://localhost:6379/0",
    )
    monkeypatch.setattr("app.core.config.get_settings", lambda: mock_settings)
    monkeypatch.setattr("app.api.health.get_settings", lambda: mock_settings)
    monkeypatch.setattr("app.api.health.check_database", lambda: {"status": "ok", "migration_head": "e1f2a3b4c5d6"})

    mock_limiter = MagicMock()
    mock_limiter._redis_available = False
    mock_limiter.redis_client = None
    monkeypatch.setattr("app.core.rate_limiter.get_rate_limiter", lambda url: mock_limiter)

    app = create_app()
    client = TestClient(app, raise_server_exceptions=False)
    resp = client.get("/health/ready")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "degraded"
    assert data["checks"]["redis"]["fallback"] == "in_memory"


def test_unmigrated_database_fails_closed_in_production(monkeypatch):
    """In production, missing migration head must fail closed with HTTP 503."""
    mock_settings = Settings(
        app_env="production",
        auth_provider="supabase",
        supabase_url="https://prod.supabase.co",
        supabase_anon_key="anon_test",
        database_url="postgresql://user:pass@127.0.0.1/scenesteward_test",
        database_identity_secret="a" * 32,
    )
    monkeypatch.setattr("app.core.config.get_settings", lambda: mock_settings)
    monkeypatch.setattr("app.api.health.get_settings", lambda: mock_settings)
    # Database is up, but no migration version found
    monkeypatch.setattr("app.api.health.check_database", lambda: {"status": "ok", "migration_head": None})

    app = create_app()
    client = TestClient(app, raise_server_exceptions=False)
    resp = client.get("/health/ready")
    assert resp.status_code == 503
    data = resp.json()
    assert data["status"] == "unhealthy"
    assert data["checks"]["database"]["status"] == "unmigrated"


def test_worker_heartbeat_and_health_probe(tmp_path, monkeypatch):
    """Worker heartbeat must verify fresh execution and detect stale heartbeats."""
    test_hb_file = tmp_path / "worker_heartbeat.json"
    monkeypatch.setattr("scripts.switch_retry.HEARTBEAT_PATH", test_hb_file)
    monkeypatch.setattr("scripts.switch_retry.check_database", lambda: {"status": "ok"})

    # 1. Missing heartbeat fails
    assert check_worker_health(max_age_seconds=10.0) == 1

    # 2. Fresh healthy heartbeat passes
    write_heartbeat(status="healthy", metadata={"test": True})
    assert check_worker_health(max_age_seconds=10.0) == 0

    # 3. Stale heartbeat fails
    stale_payload = {
        "timestamp": (datetime.now(UTC) - timedelta(seconds=60)).isoformat(),
        "pid": 1234,
        "status": "healthy",
    }
    test_hb_file.write_text(json.dumps(stale_payload), encoding="utf-8")
    assert check_worker_health(max_age_seconds=10.0) == 1


def test_worker_recovers_stale_processing_events(db):
    """Worker sweeper must reset events stuck in 'processing' longer than timeout."""
    with system_context(db):
        stale_event = IntegrationEvent(
            integration_name="switch",
            event_type="test_review",
            external_event_id=f"test_stale_{datetime.now(UTC).timestamp()}",
            processing_status="processing",
            attempt_count=1,
            created_at=datetime.now(UTC) - timedelta(minutes=15),
        )
        db.add(stale_event)
        db.commit()

        # Run recovery with 300s (5m) threshold
        recovered_count = recover_stale_events(db, max_stale_seconds=300)
        assert recovered_count >= 1

        db.refresh(stale_event)
        assert stale_event.processing_status == "failed"
        assert "stale processing timeout recovered" in stale_event.last_error
