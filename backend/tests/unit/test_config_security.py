"""Tests for configuration security guards and startup validation."""
from __future__ import annotations

import pytest
from pydantic import ValidationError

from app.core.config import Settings


def test_production_rejects_dev_auth():
    with pytest.raises(ValidationError, match="AUTH_PROVIDER=dev is not permitted"):
        Settings(
            app_env="production",
            database_url="postgresql+psycopg://user:pass@127.0.0.1:5432/db",
            auth_provider="dev",
            app_encryption_key="rfbmYlSxk4ofQ0EM8KbeAiGRGQjEoOvbxZV2-WsRZ-k=",
            database_identity_secret="secure_hex_secret_production_2026",
        )


def test_production_rejects_missing_encryption_key():
    with pytest.raises(ValidationError, match="APP_ENCRYPTION_KEY must be set"):
        Settings(
            app_env="production",
            database_url="postgresql+psycopg://user:pass@127.0.0.1:5432/db",
            auth_provider="supabase",
            supabase_url="https://test.supabase.co",
            supabase_anon_key="anon",
            app_encryption_key=None,
            database_identity_secret="secure_hex_secret_production_2026",
        )


def test_production_rejects_placeholder_encryption_key():
    with pytest.raises(ValidationError, match="contains a placeholder"):
        Settings(
            app_env="production",
            database_url="postgresql+psycopg://user:pass@127.0.0.1:5432/db",
            auth_provider="supabase",
            supabase_url="https://test.supabase.co",
            supabase_anon_key="anon",
            app_encryption_key="GENERATE_FERNET_KEY_HERE",
            database_identity_secret="secure_hex_secret_production_2026",
        )


def test_production_rejects_default_database_identity_secret():
    with pytest.raises(ValidationError, match="DATABASE_IDENTITY_SECRET must be an explicitly generated secret"):
        Settings(
            app_env="production",
            database_url="postgresql+psycopg://user:pass@127.0.0.1:5432/db",
            auth_provider="supabase",
            supabase_url="https://test.supabase.co",
            supabase_anon_key="anon",
            app_encryption_key="rfbmYlSxk4ofQ0EM8KbeAiGRGQjEoOvbxZV2-WsRZ-k=",
            database_identity_secret="scenesteward_db_trust_secret_2026_prod_v1",
        )


def test_production_rejects_default_db_passwords():
    with pytest.raises(ValidationError, match="contains a default/example password"):
        Settings(
            app_env="production",
            database_url="postgresql+psycopg://user:changeme@127.0.0.1:5432/db",
            auth_provider="supabase",
            supabase_url="https://test.supabase.co",
            supabase_anon_key="anon",
            app_encryption_key="rfbmYlSxk4ofQ0EM8KbeAiGRGQjEoOvbxZV2-WsRZ-k=",
            database_identity_secret="secure_hex_secret_production_2026",
        )


def test_production_rejects_clamav_without_fail_closed():
    with pytest.raises(ValidationError, match="ANTIVIRUS_FAIL_CLOSED must be True in production"):
        Settings(
            app_env="production",
            database_url="postgresql+psycopg://user:secret_prod_pass@127.0.0.1:5432/db",
            auth_provider="supabase",
            supabase_url="https://test.supabase.co",
            supabase_anon_key="anon",
            app_encryption_key="rfbmYlSxk4ofQ0EM8KbeAiGRGQjEoOvbxZV2-WsRZ-k=",
            database_identity_secret="secure_hex_secret_production_2026",
            antivirus_provider="clamav",
            antivirus_fail_closed=False,
        )


def test_development_allows_defaults():
    s = Settings(
        app_env="development",
        database_url="postgresql+psycopg://scenesteward_app:changeme@127.0.0.1:5432/scenesteward",
        auth_provider="dev",
        auth_dev_secret="dev_secret_only",
    )
    assert s.app_env == "development"
    assert s.auth_provider == "dev"
