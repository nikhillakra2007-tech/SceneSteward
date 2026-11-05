"""Centralized environment and database isolation guards.

Ensures fail-closed protection for destructive operations:
- Truncation
- Database drop / recreate / restore
- Data deletion
- Test suite execution
- Demo / synthetic data seeding
- Lifecycle acceptance verification
"""
from __future__ import annotations

import logging
import os
from typing import TYPE_CHECKING
from urllib.parse import urlparse

if TYPE_CHECKING:
    from app.core.config import Settings

logger = logging.getLogger("scenesteward.lifecycle_guards")

SAFE_DESTRUCTIVE_ENVIRONMENTS = frozenset({"test", "development", "local"})
FORBIDDEN_CLOUD_HOST_PATTERNS = frozenset({
    ".rds.amazonaws.com",
    ".supabase.co",
    ".database.windows.net",
    "cockroachlabs.cloud",
    ".cloud.google.com",
})
ALLOWED_TEST_HOSTS = frozenset({
    "127.0.0.1",
    "localhost",
    "::1",
    "postgres",
    "db",
    "test-postgres",
})


def ensure_safe_destructive_environment(
    settings: Settings | None = None,
    operation_name: str = "destructive database operation",
    target_database: str | None = None,
    allow_explicit_override: bool = False,
    override_token: str | None = None,
) -> None:
    """Enforces fail-closed protection for destructive lifecycle and maintenance operations.

    Destructive operations are strictly rejected in:
      - production
      - staging
      - unknown / unconfigured environments
      - non-test databases
    """
    if settings is not None and getattr(settings, "app_env", None):
        env = settings.app_env.lower().strip()
    else:
        env = os.environ.get("APP_ENV", "").lower().strip()

    if not env:
        raise RuntimeError(
            f"CRITICAL LIFECYCLE GUARD: Refusing {operation_name}! "
            "Environment is missing or unset. Destructive operations fail closed by default."
        )

    if env in {"production", "staging"}:
        expected_token = f"CONFIRM_DESTRUCTIVE_OVERRIDE_{env.upper()}"
        if allow_explicit_override and override_token == expected_token:
            logger.warning(
                "DESTRUCTIVE OVERRIDE AUTHORIZED: %s executing in %s with verified token.",
                operation_name,
                env.upper(),
            )
            return
        raise RuntimeError(
            f"CRITICAL LIFECYCLE GUARD: Refusing {operation_name}! "
            f"Destructive operations are strictly prohibited in {env.upper()} environment."
        )

    if env not in SAFE_DESTRUCTIVE_ENVIRONMENTS:
        raise RuntimeError(
            f"CRITICAL LIFECYCLE GUARD: Refusing {operation_name}! "
            f"Unrecognized or ambiguous environment {env!r}. "
            f"Destructive operations are only permitted in {sorted(SAFE_DESTRUCTIVE_ENVIRONMENTS)}."
        )

    if target_database is not None:
        db_clean = target_database.lower().strip()
        # In test operations, the database must strictly end with _test
        if "test" in operation_name.lower() or env == "test":
            if not db_clean.endswith("_test"):
                raise RuntimeError(
                    f"CRITICAL LIFECYCLE GUARD: Refusing {operation_name}! "
                    f"Target database {target_database!r} does not end with '_test'."
                )
        elif not (db_clean.endswith("_test") or db_clean in {"scenesteward", "scenesteward_dev"}):
            raise RuntimeError(
                f"CRITICAL LIFECYCLE GUARD: Refusing {operation_name}! "
                f"Target database {target_database!r} is not an authorized local development database."
            )


def validate_test_database_url(url: str, label: str = "DATABASE_URL") -> str:
    """Validates that a connection URL strictly targets a safe local test database."""
    if not url:
        raise RuntimeError(f"CRITICAL SECURITY GUARD: {label} is missing or empty!")

    clean_url = url.replace("postgresql+psycopg://", "postgresql://")
    parsed = urlparse(clean_url)

    # 1. Host validation
    host = (parsed.hostname or "").lower()
    for cloud_pat in FORBIDDEN_CLOUD_HOST_PATTERNS:
        if cloud_pat in host:
            raise RuntimeError(
                f"CRITICAL SECURITY GUARD: Refusing tests against cloud database host {host!r} ({label})!"
            )

    if host not in ALLOWED_TEST_HOSTS:
        raise RuntimeError(
            f"CRITICAL SECURITY GUARD: Refusing tests against non-local host {host!r} ({label})! "
            f"Tests must target local or CI container host in {sorted(ALLOWED_TEST_HOSTS)}."
        )

    # 2. Database name validation
    db_name = parsed.path.lstrip("/").split("?")[0]
    if not db_name.endswith("_test"):
        raise RuntimeError(
            f"CRITICAL SECURITY GUARD: {label} target database {db_name!r} does not end with '_test'! "
            "Tests must target a dedicated disposable test database."
        )

    if db_name in {"postgres", "template1", "scenesteward", "scenesteward_dev"}:
        raise RuntimeError(
            f"CRITICAL SECURITY GUARD: {label} target database {db_name!r} is a protected or development database!"
        )

    return db_name
