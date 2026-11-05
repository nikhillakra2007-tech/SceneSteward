"""Automated tests for lifecycle guards against destructive operations.

Proves:
- Production reset is rejected.
- Staging reset is rejected.
- Unknown environment reset is rejected.
- Missing environment reset is rejected.
- Non-test database reset is rejected.
- Safe test database is permitted.
- Safe local development database is permitted.
- Deliberate operational overrides with exact token are accepted.
"""
from __future__ import annotations

import pytest

from app.core.config import Settings
from app.core.lifecycle_guards import (
    ensure_safe_destructive_environment,
    validate_test_database_url,
)


def test_production_destructive_operation_rejected():
    s = Settings(
        app_env="production",
        auth_provider="supabase",
        supabase_url="https://test.supabase.co",
        supabase_anon_key="anon_key_12345",
        database_url="postgresql://user:valid_strong_pass_12345@127.0.0.1/scenesteward_test",
        database_identity_secret="a" * 32,
    )
    with pytest.raises(RuntimeError) as exc_info:
        ensure_safe_destructive_environment(settings=s, operation_name="database truncation")
    assert "PRODUCTION environment" in str(exc_info.value)
    assert "strictly prohibited" in str(exc_info.value)


def test_staging_destructive_operation_rejected():
    s = Settings(
        app_env="staging",
        auth_provider="supabase",
        supabase_url="https://test.supabase.co",
        supabase_anon_key="anon_key_12345",
        database_url="postgresql://user:valid_strong_pass_12345@127.0.0.1/scenesteward_test",
        database_identity_secret="a" * 32,
    )
    with pytest.raises(RuntimeError) as exc_info:
        ensure_safe_destructive_environment(settings=s, operation_name="database drop")
    assert "STAGING environment" in str(exc_info.value)
    assert "strictly prohibited" in str(exc_info.value)


def test_unknown_environment_destructive_operation_rejected(monkeypatch):
    monkeypatch.setenv("APP_ENV", "qa_sandbox")
    with pytest.raises(RuntimeError) as exc_info:
        ensure_safe_destructive_environment(operation_name="database drop")
    assert "Unrecognized or ambiguous environment" in str(exc_info.value)
    assert "qa_sandbox" in str(exc_info.value)


def test_missing_environment_destructive_operation_rejected(monkeypatch):
    monkeypatch.delenv("APP_ENV", raising=False)
    with pytest.raises(RuntimeError) as exc_info:
        ensure_safe_destructive_environment(operation_name="schema wipe")
    assert "Environment is missing or unset" in str(exc_info.value)


def test_non_test_database_target_rejected():
    s = Settings(app_env="test", database_url="postgresql://user:pass@127.0.0.1/scenesteward_test")
    with pytest.raises(RuntimeError) as exc_info:
        ensure_safe_destructive_environment(
            settings=s,
            operation_name="test truncation",
            target_database="scenesteward_production",
        )
    assert "does not end with '_test'" in str(exc_info.value)


def test_safe_test_environment_permitted():
    s = Settings(app_env="test", database_url="postgresql://user:pass@127.0.0.1/scenesteward_test")
    # Must not raise
    ensure_safe_destructive_environment(
        settings=s,
        operation_name="test fixture truncation",
        target_database="scenesteward_test",
    )


def test_safe_development_database_permitted():
    s = Settings(app_env="development", database_url="postgresql://user:pass@127.0.0.1/scenesteward")
    # Must not raise for dev
    ensure_safe_destructive_environment(
        settings=s,
        operation_name="dev seed operation",
        target_database="scenesteward",
    )


def test_deliberate_production_override_accepted():
    s = Settings(
        app_env="production",
        auth_provider="supabase",
        supabase_url="https://test.supabase.co",
        supabase_anon_key="anon_key_12345",
        database_url="postgresql://user:valid_strong_pass_12345@127.0.0.1/scenesteward_prod",
        database_identity_secret="a" * 32,
    )
    # Correct override token
    ensure_safe_destructive_environment(
        settings=s,
        operation_name="emergency disaster recovery",
        allow_explicit_override=True,
        override_token="CONFIRM_DESTRUCTIVE_OVERRIDE_PRODUCTION",
    )


def test_validate_test_database_url_cloud_hosts_rejected():
    for cloud_url in [
        "postgresql://user:pass@mydb.12345.rds.amazonaws.com:5432/db_test",
        "postgresql://user:pass@aws-0-us-west-1.pooler.supabase.co:6543/db_test",
        "postgresql://user:pass@my-sql-srv.database.windows.net:1433/db_test",
    ]:
        with pytest.raises(RuntimeError) as exc:
            validate_test_database_url(cloud_url, "TEST_DB")
        assert "cloud database host" in str(exc.value)


def test_validate_test_database_url_non_test_db_rejected():
    with pytest.raises(RuntimeError) as exc:
        validate_test_database_url("postgresql://user:pass@127.0.0.1:5432/scenesteward_production", "TEST_DB")
    assert "does not end with '_test'" in str(exc.value)
