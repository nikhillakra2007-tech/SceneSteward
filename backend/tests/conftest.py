"""Test harness — runs against a dedicated PostgreSQL database (scenesteward_test).

Hard safety rule: this module REQUIRES DATABASE_URL (env or .env) to point at a
database whose name ends with '_test'; otherwise the whole suite aborts.
"""
from __future__ import annotations

import os
import sys
import uuid
from pathlib import Path

import pytest

BACKEND_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND_ROOT))

# Force APP_ENV to 'test' if unset in test harness
os.environ.setdefault("APP_ENV", "test")

# Force the test databases BEFORE any app import; pydantic-settings prefers env vars over .env.
from app.core.lifecycle_guards import (
    ensure_safe_destructive_environment,
    validate_test_database_url,
)

ensure_safe_destructive_environment(operation_name="test suite initialization")

_test_url = os.environ.get("DATABASE_URL_TEST")
_admin_url = os.environ.get("DATABASE_URL_ADMIN")
_backend_env = BACKEND_ROOT / ".env"
if (_test_url is None or _admin_url is None) and _backend_env.exists():
    for _line in _backend_env.read_text(encoding="utf-8").splitlines():
        _line = _line.strip()
        if not _line or _line.startswith("#") or "=" not in _line:
            continue
        _k, _v = _line.split("=", 1)
        _v = _v.strip().strip('"').strip("'")
        _k = _k.strip()
        if _k == "DATABASE_URL_TEST" and _test_url is None:
            _test_url = _v
        elif _k == "DATABASE_URL_ADMIN" and _admin_url is None:
            _admin_url = _v
if _test_url is None or _admin_url is None:
    raise RuntimeError(
        "Tests require DATABASE_URL_TEST (runtime role, RLS enforced) and "
        "DATABASE_URL_ADMIN (schema owner). Set them or provide backend/.env."
    )

# Strict URL & Target Environment Guards
validate_test_database_url(_test_url, "DATABASE_URL_TEST")
validate_test_database_url(_admin_url, "DATABASE_URL_ADMIN")

os.environ["DATABASE_URL"] = _test_url
os.environ["MIGRATION_DATABASE_URL"] = _admin_url
os.environ["APP_ENV"] = "test"
os.environ["AI_PROVIDER"] = "offline"
os.environ["SWITCH_ADAPTER"] = "test"
os.environ["STORAGE_PROVIDER"] = "local"
os.environ["STORAGE_LOCAL_PATH"] = str(BACKEND_ROOT / "var" / "storage-test")
# Deterministic TEST-ONLY secrets (never used outside pytest):
os.environ.setdefault("AUTH_DEV_SECRET", "test-only-dev-secret-not-for-production-0123456789abcdef0123456789abcdef")
os.environ.setdefault("APP_ENCRYPTION_KEY", "67yRWp6G4NQfdYCVyaajG5JspDXj6h8qHmly0wKpDkM=")

_url = os.environ["DATABASE_URL"]
if not _url.rsplit("/", 1)[-1].endswith("_test"):
    raise RuntimeError(f"Refusing to run tests against non-test database: {_url!r}")

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

from app.core.security import mint_dev_token
from app.main import create_app
from app.models import Base, Project, ProjectMembership, User

TABLE_NAMES = sorted(Base.metadata.tables)
_admin_engine = create_engine(
    _admin_url,
    pool_size=2,
    future=True,
    connect_args={"options": "-c idle_in_transaction_session_timeout=10000"},
)
_AdminSession = sessionmaker(bind=_admin_engine, autoflush=False, expire_on_commit=False, future=True)

_test_engine = create_engine(
    _test_url,
    pool_size=2,
    future=True,
    connect_args={"options": "-c idle_in_transaction_session_timeout=10000"},
)


@pytest.fixture(scope="session", autouse=True)
def _verify_schema():
    expected = ("e1f2a3b4c5d6",)
    with _admin_engine.connect() as conn:
        active_db = conn.execute(text("SELECT current_database()")).scalar()
        if not active_db or not str(active_db).endswith("_test"):
            raise RuntimeError(
                f"CRITICAL DATABASE TRUST VIOLATION: Connected database {active_db!r} is not a test database! "
                "Refusing to inspect schema or modify trust configuration."
            )
        try:
            row = conn.execute(text("select version_num from alembic_version")).scalar()
        except Exception as exc:
            raise RuntimeError(
                "Test database is not migrated. Run: "
                "ALEMBIC_DATABASE_URL=$DATABASE_URL_ADMIN alembic -c alembic.ini upgrade head"
            ) from exc
    if row not in expected:
        raise RuntimeError(f"test database is not at head (found {row!r}); run alembic upgrade head")

    from app.core.config import get_settings
    settings = get_settings()
    if settings.app_env != "test":
        raise RuntimeError(f"CRITICAL GUARD: Cannot synchronize test secret in environment {settings.app_env!r}")

    with _admin_engine.begin() as conn:
        conn.execute(
            text(
                "INSERT INTO private.app_secrets (key_name, secret_val) "
                "VALUES ('identity_secret', :sec) "
                "ON CONFLICT (key_name) DO UPDATE SET secret_val = EXCLUDED.secret_val"
            ),
            {"sec": settings.database_identity_secret},
        )

    # Independently verify runtime engine (scenesteward_app) boundaries and handshake
    with _test_engine.connect() as test_conn:
        test_db = test_conn.execute(text("SELECT current_database()")).scalar()
        if str(test_db) != str(active_db):
            raise RuntimeError(f"Database mismatch between admin ({active_db}) and runtime ({test_db}) engines!")
        user_role = test_conn.execute(text("SELECT current_user")).scalar()
        if user_role != "scenesteward_app":
            raise RuntimeError(f"DATABASE_URL_TEST must connect as scenesteward_app (found {user_role!r})")
        try:
            has_sel = test_conn.execute(
                text("SELECT has_table_privilege('scenesteward_app', 'private.app_secrets', 'select')")
            ).scalar()
            if has_sel:
                raise RuntimeError("CRITICAL PRIVILEGE LEAK: scenesteward_app has SELECT on private.app_secrets!")
        except Exception as exc:
            if "permission denied" not in str(exc).lower():
                raise

    from app.core.database import verify_database_trust
    trust = verify_database_trust(_test_engine)
    if not trust.get("ok"):
        raise RuntimeError(f"Test database trust handshake failed: {trust.get('detail')}")


@pytest.fixture()
def db():
    with _admin_engine.begin() as conn:  # truncate everything for isolation (owner bypasses RLS)
        conn.execute(text("TRUNCATE " + ", ".join(TABLE_NAMES) + " RESTART IDENTITY CASCADE"))
    session = _AdminSession()
    try:
        yield session
    finally:
        session.rollback()
        session.close()


@pytest.fixture()
def client(db):
    from fastapi.testclient import TestClient
    app = create_app()
    with TestClient(app, raise_server_exceptions=False) as c:
        yield c


# --- factories ---------------------------------------------------------------

def make_user(db, email: str, full_name: str = "Test User") -> User:
    user = User(email=email.lower(), full_name=full_name, auth_provider="dev",
                provider_user_id=str(uuid.uuid4()), account_status="active")
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def auth_headers(user: User) -> dict:
    token = mint_dev_token(user_id=user.provider_user_id, email=user.email,
                           full_name=user.full_name)
    return {"Authorization": f"Bearer {token}"}


def make_project(db, owner: User, title: str = "Beyond the Silence") -> Project:
    project = Project(title=title, created_by=owner.id, status="active")
    db.add(project)
    db.flush()
    db.add(ProjectMembership(project_id=project.id, user_id=owner.id,
                             role="project_owner", membership_status="active",
                             invited_by=owner.id))
    db.commit()
    db.refresh(project)
    return project


def add_member(db, project: Project, user: User, role: str) -> ProjectMembership:
    m = ProjectMembership(project_id=project.id, user_id=user.id, role=role,
                          membership_status="active", invited_by=project.created_by)
    db.add(m)
    db.commit()
    return m
