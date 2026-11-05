"""Application configuration.

Environment-based, validated at startup. Secret values are never logged;
the startup check reports only whether each value is present/valid.
"""
from __future__ import annotations

import os
from functools import lru_cache
from pathlib import Path

from pydantic import AliasChoices, Field, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

_BACKEND_ROOT = Path(__file__).resolve().parents[2]

_VALID_ENVS = {"development", "test", "staging", "production"}
_VALID_AUTH = {"dev", "supabase"}
_VALID_STORAGE = {"local", "supabase"}
_VALID_SWITCH = {"test", "http"}
_VALID_AI = {"offline", "anthropic"}


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=str(_BACKEND_ROOT / ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_env: str = "development"
    app_name: str = "SceneSteward"
    api_version: str = "v1"
    log_level: str = "INFO"

    database_url: str
    database_url_test: str | None = None
    # Schema owner used only for migrations; never used at runtime.
    migration_database_url: str | None = None
    # Database identity secret for cryptographic HMAC trust-boundary RLS enforcement
    database_identity_secret: str = "scenesteward_db_trust_secret_2026_prod_v1"

    auth_provider: str = "dev"
    auth_dev_secret: str | None = None
    auth_issuer: str = "scenesteward-dev"
    auth_audience: str = "scenesteward-api"
    auth_jwks_url: str | None = None

    supabase_url: str | None = None
    supabase_anon_key: str | None = None
    supabase_service_role_key: str | None = None

    storage_provider: str = "local"
    storage_bucket: str = "scenesteward-private"
    storage_local_path: str = "backend/var/storage"
    signed_url_ttl_seconds: int = 600
    download_url_ttl_seconds: int = 300
    max_upload_bytes: int = 25 * 1024 * 1024
    max_uncompressed_bytes: int = 50 * 1024 * 1024

    antivirus_provider: str = "mock"
    clamav_host: str = Field(default="127.0.0.1", validation_alias=AliasChoices("clamav_host", "antivirus_clamav_host"))
    clamav_port: int = Field(default=3310, validation_alias=AliasChoices("clamav_port", "antivirus_clamav_port"))
    antivirus_fail_closed: bool = False

    app_encryption_key: str | None = None
    app_encryption_current_kid: str = "primary"
    app_encryption_keys: str = "{}"

    ai_provider: str = "offline"
    anthropic_api_key: str | None = None
    ai_model: str = "claude-sonnet-4-5"
    ai_timeout_seconds: float = 45.0
    ai_max_retries: int = 1

    switch_adapter: str = "test"
    switch_base_url: str | None = None
    switch_api_key: str | None = None
    switch_agent_id: str | None = None
    switch_registration_token: str | None = None
    switch_webhook_secret: str | None = None

    frontend_origin: str = "http://localhost:3000"
    rate_limit_per_minute: int = 120
    max_request_bytes: int = 1048576

    redis_url: str | None = None
    trusted_proxies: str = "127.0.0.1,::1,10.0.0.0/8,172.16.0.0/12,192.168.0.0/16"

    @model_validator(mode="after")
    def _production_guard(self) -> Settings:
        is_live = self.is_production or self.is_staging
        if is_live and self.auth_provider == "dev":
            raise ValueError(f"AUTH_PROVIDER=dev is not permitted in APP_ENV={self.app_env}; configure Supabase or another real IdP")
        if is_live:
            if not self.app_encryption_key:
                raise ValueError(f"APP_ENCRYPTION_KEY must be set in APP_ENV={self.app_env}")
            if "GENERATE" in self.app_encryption_key or "CHANGE_ME" in self.app_encryption_key:
                raise ValueError(f"APP_ENCRYPTION_KEY contains a placeholder in APP_ENV={self.app_env}")
            try:
                from cryptography.fernet import Fernet
                Fernet(self.app_encryption_key.encode("utf-8") if isinstance(self.app_encryption_key, str) else self.app_encryption_key)
            except Exception as e:
                raise ValueError(f"APP_ENCRYPTION_KEY is invalid for Fernet 256-bit AES-CBC: {e}") from e

            # Check database identity secret
            if self.is_production and (
                not self.database_identity_secret
                or self.database_identity_secret in (
                    "CHANGE_ME", "CHANGE_ME_GENERATE_WITH_OPENSSL_RAND_HEX_32",
                    "scenesteward_db_trust_secret_2026_prod_v1", "scenesteward_staging_identity_trust_secret_2026",
                )
                or "CHANGE_ME" in self.database_identity_secret
            ):
                raise ValueError("DATABASE_IDENTITY_SECRET must be an explicitly generated secret in production (default/placeholder is forbidden)")

            # Check database credentials
            low_db = self.database_url.lower()
            if self.is_production and any(p in low_db for p in (":app_password@", ":changeme@", ":postgres@", ":staging_db_secure_pass_2026@")):
                raise ValueError("DATABASE_URL contains a default/example password in production")

            # Check ClamAV fail-closed in production
            if self.is_production and self.antivirus_provider == "clamav" and not self.antivirus_fail_closed:
                raise ValueError("ANTIVIRUS_FAIL_CLOSED must be True in production when ANTIVIRUS_PROVIDER=clamav")

        return self

    @field_validator("app_env")
    @classmethod
    def _env_ok(cls, v: str) -> str:
        v = v.lower()
        if v not in _VALID_ENVS:
            raise ValueError(f"APP_ENV must be one of {sorted(_VALID_ENVS)}")
        return v

    @field_validator("auth_provider")
    @classmethod
    def _auth_ok(cls, v: str) -> str:
        v = v.lower()
        if v not in _VALID_AUTH:
            raise ValueError(f"AUTH_PROVIDER must be one of {sorted(_VALID_AUTH)}")
        return v

    @field_validator("storage_provider")
    @classmethod
    def _storage_ok(cls, v: str) -> str:
        v = v.lower()
        if v not in _VALID_STORAGE:
            raise ValueError(f"STORAGE_PROVIDER must be one of {sorted(_VALID_STORAGE)}")
        return v

    @field_validator("switch_adapter")
    @classmethod
    def _switch_ok(cls, v: str) -> str:
        v = v.lower()
        if v not in _VALID_SWITCH:
            raise ValueError(f"SWITCH_ADAPTER must be one of {sorted(_VALID_SWITCH)}")
        return v

    @field_validator("ai_provider")
    @classmethod
    def _ai_ok(cls, v: str) -> str:
        v = v.lower()
        if v not in _VALID_AI:
            raise ValueError(f"AI_PROVIDER must be one of {sorted(_VALID_AI)}")
        return v

    @property
    def is_production(self) -> bool:
        return self.app_env == "production"

    @property
    def is_staging(self) -> bool:
        return self.app_env == "staging"

    @property
    def resolved_jwks_url(self) -> str | None:
        if self.auth_jwks_url:
            return self.auth_jwks_url
        if self.supabase_url:
            return self.supabase_url.rstrip("/") + "/auth/v1/.well-known/jwks.json"
        return None

    @property
    def resolved_supabase_issuer(self) -> str | None:
        if self.supabase_url:
            return self.supabase_url.rstrip("/") + "/auth/v1"
        return self.auth_issuer

    @property
    def frontend_origins(self) -> list[str]:
        return [o.strip() for o in self.frontend_origin.split(",") if o.strip()]

    @property
    def resolved_trusted_proxies(self) -> list[str]:
        return [p.strip() for p in self.trusted_proxies.split(",") if p.strip()]

    @property
    def resolved_encryption_key_ring(self) -> dict[str, str]:
        ring: dict[str, str] = {}
        if self.app_encryption_keys and self.app_encryption_keys.strip() not in ("{}", ""):
            import json
            try:
                parsed = json.loads(self.app_encryption_keys)
                if isinstance(parsed, dict):
                    ring.update({str(k): str(v) for k, v in parsed.items()})
            except (json.JSONDecodeError, TypeError, ValueError):
                for pair in self.app_encryption_keys.split(","):
                    if ":" in pair:
                        k, v = pair.split(":", 1)
                        ring[k.strip()] = v.strip()
        if self.app_encryption_key:
            ring.setdefault(self.app_encryption_current_kid or "primary", self.app_encryption_key)
        return ring

    def switch_configured(self) -> bool:
        return self.switch_adapter == "http" and bool(self.switch_base_url) and bool(self.switch_api_key) and bool(self.switch_agent_id)


def startup_checks(s: Settings) -> list[dict[str, str]]:
    """Report configuration health by NAME only (never values)."""
    checks: list[dict[str, str]] = []

    def add(name: str, ok: bool, detail_missing: str = "missing", detail_ok: str = "configured") -> None:
        checks.append({"check": name, "status": detail_ok if ok else detail_missing})

    add("DATABASE_URL", bool(s.database_url))
    if s.is_production or s.is_staging:
        add("AUTH_PROVIDER!=dev", s.auth_provider != "dev", f"dev provider not allowed in {s.app_env}")
    if s.auth_provider == "dev":
        add("AUTH_DEV_SECRET", bool(s.auth_dev_secret))
    else:
        add("AUTH_JWKS_URL/SUPABASE_URL", bool(s.resolved_jwks_url))
    add("APP_ENCRYPTION_KEY", bool(s.app_encryption_key), "missing (contact endpoints will fail closed)")
    add("STORAGE_PROVIDER", s.storage_provider in _VALID_STORAGE)
    if s.storage_provider == "supabase":
        add("SUPABASE_SERVICE_ROLE_KEY", bool(s.supabase_service_role_key))
    add("AI_PROVIDER", s.ai_provider in _VALID_AI)
    if s.ai_provider == "anthropic":
        add("ANTHROPIC_API_KEY", bool(s.anthropic_api_key))
    add("SWITCH_ADAPTER", (not s.switch_configured()) or bool(s.switch_base_url and s.switch_api_key and s.switch_agent_id),
        "http adapter selected but SWITCH_BASE_URL/SWITCH_API_KEY/SWITCH_AGENT_ID missing")
    return checks


@lru_cache
def get_settings() -> Settings:
    env_file = os.environ.get("SCENESTEWARD_ENV_FILE") or os.environ.get("ENV_FILE")
    if env_file:
        return Settings(_env_file=env_file)
    return Settings()
