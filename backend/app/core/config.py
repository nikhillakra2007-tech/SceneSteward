"""Application configuration.

Environment-based, validated at startup. Secret values are never logged;
the startup check reports only whether each value is present/valid.
"""
from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from pydantic import field_validator
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

    app_encryption_key: str | None = None

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

    def switch_configured(self) -> bool:
        return self.switch_adapter == "http" and bool(self.switch_base_url) and bool(self.switch_api_key) and bool(self.switch_agent_id)


def startup_checks(s: Settings) -> list[dict[str, str]]:
    """Report configuration health by NAME only (never values)."""
    checks: list[dict[str, str]] = []

    def add(name: str, ok: bool, detail_missing: str = "missing", detail_ok: str = "configured") -> None:
        checks.append({"check": name, "status": detail_ok if ok else detail_missing})

    add("DATABASE_URL", bool(s.database_url))
    if s.is_production:
        add("AUTH_PROVIDER!=dev", s.auth_provider != "dev", "dev provider not allowed in production")
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
    return Settings()
