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

# Force the test database BEFORE any app import; pydantic-settings prefers env vars over .env.
os.environ["DATABASE_URL"] = os.environ.get(
    "DATABASE_URL_TEST",
    "postgresql+psycopg://scenesteward:prQb6Qa65eQ9hRwZq9aLa8jeiHbexci@127.0.0.1:5432/scenesteward_test",
)
os.environ["APP_ENV"] = "test"
os.environ["AI_PROVIDER"] = "offline"
os.environ["SWITCH_ADAPTER"] = "test"
os.environ["STORAGE_PROVIDER"] = "local"
os.environ["STORAGE_LOCAL_PATH"] = str(BACKEND_ROOT / "var" / "storage-test")

_url = os.environ["DATABASE_URL"]
if not _url.rsplit("/", 1)[-1].endswith("_test"):
    raise RuntimeError(f"Refusing to run tests against non-test database: {_url!r}")

from sqlalchemy import text

from app.core.database import get_engine, get_session_factory
from app.core.security import mint_dev_token
from app.main import create_app
from app.models import Base, Project, ProjectMembership, User

TABLE_NAMES = sorted(Base.metadata.tables)


@pytest.fixture(scope="session", autouse=True)
def _verify_schema():
    rounds = ("b3f9c21a7d44",)
    engine = get_engine()
    with engine.connect() as conn:
        try:
            row = conn.execute(text("select version_num from alembic_version")).scalar()
        except Exception as exc:
            raise RuntimeError(
                "Test database is not migrated. Run: "
                "ALEMBIC_DATABASE_URL=$DATABASE_URL_TEST alembic -c alembic.ini upgrade head"
            ) from exc
    if row not in rounds:
        raise RuntimeError(f"test database is not at head (found {row!r}); run alembic upgrade head")


@pytest.fixture()
def db():
    engine = get_engine()
    with engine.begin() as conn:  # truncate everything for isolation
        conn.execute(text("TRUNCATE " + ", ".join(TABLE_NAMES) + " RESTART IDENTITY CASCADE"))
    session = get_session_factory()()
    try:
        yield session
    finally:
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
