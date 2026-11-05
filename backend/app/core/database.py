"""Database engine/session management.

Sync SQLAlchemy 2.x with psycopg v3.

Security model
--------------
The runtime role is a NON-owner role subject to ROW LEVEL SECURITY
(see migrations/versions/c7a1e52b93f0 and docs/DATABASE_SECURITY.md).
Every connection transaction carries a transaction-local identity:

    SELECT set_config('app.user_id', '<uuid>', true)     -- or app.system='on'

`set_config(..., true)` is transaction-local: it is discarded when the
transaction ends, so pooled connections can never leak identity across
requests. An Engine "begin" listener injects it automatically from the
contextvars below, so every session/transaction in the process is covered
(sessions that never set an identity see ZERO rows — deny by default).

- API layer       -> set_identity(user.id)  (per authenticated request)
- System workers  -> system_context()       (listener, retry sweeper, seeds)
- Admin/migration -> separate owner role, bypasses RLS by construction
"""
from __future__ import annotations

import contextlib
import contextvars
import logging
from collections.abc import Generator
from functools import lru_cache
from typing import Any

from sqlalchemy import create_engine, event, text
from sqlalchemy.engine import Engine
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import get_settings

logger = logging.getLogger("scenesteward.database")

_identity_var: contextvars.ContextVar[str | None] = contextvars.ContextVar("identity", default=None)
_system_var: contextvars.ContextVar[bool] = contextvars.ContextVar("system", default=False)


def compute_identity_sig(user_id: str | None, secret: str | None = None) -> str:
    if not user_id:
        return ""
    import hashlib
    sec = secret or get_settings().database_identity_secret
    return hashlib.sha256(f"{user_id}:{sec}".encode()).hexdigest()


def compute_system_sig(secret: str | None = None) -> str:
    import hashlib
    sec = secret or get_settings().database_identity_secret
    return hashlib.sha256(f"system:on:{sec}".encode()).hexdigest()


def set_identity(user_id, session: Session | None = None) -> None:
    _identity_var.set(str(user_id) if user_id else None)
    _system_var.set(False)
    if session is not None:
        session.info["user_id"] = str(user_id) if user_id else None
        session.info["system"] = False
        if user_id:
            try:
                sig = compute_identity_sig(str(user_id))
                session.execute(
                    text("SELECT set_config('app.user_id', :uid, true), set_config('app.user_sig', :sig, true)"),
                    {"uid": str(user_id), "sig": sig},
                )
            except SQLAlchemyError as exc:
                logger.debug("Failed setting transaction user context: %s", exc)


def clear_identity(session: Session | None = None) -> None:
    _identity_var.set(None)
    _system_var.set(False)
    if session is not None:
        session.info.pop("user_id", None)
        session.info.pop("system", None)


@contextlib.contextmanager
def system_context(session: Session | None = None):
    """Trusted server-side scope (listener, sweeper, seed, workflow)."""
    was_system = _system_var.get()
    token = _system_var.set(True)
    if session is not None and not was_system:
        session.info["system"] = True
        try:
            sig = compute_system_sig()
            session.execute(
                text("SELECT set_config('app.system', 'on', true), set_config('app.system_sig', :sig, true)"),
                {"sig": sig},
            )
        except SQLAlchemyError as exc:
            logger.debug("Failed setting transaction system context: %s", exc)
    try:
        yield
    finally:
        _system_var.reset(token)
        if session is not None and not was_system:
            session.info.pop("system", None)
            try:
                session.execute(
                    text("SELECT set_config('app.system', 'off', true), set_config('app.system_sig', '', true)")
                )
            except SQLAlchemyError as exc:
                logger.debug("Failed resetting transaction system context: %s", exc)


@lru_cache
def get_engine() -> Engine:
    settings = get_settings()
    engine = create_engine(
        settings.database_url,
        pool_size=10,
        max_overflow=20,
        pool_pre_ping=True,
        future=True,
    )
    _install_rls_context_hook(engine)
    return engine


def _install_rls_context_hook(engine: Engine) -> None:
    @event.listens_for(engine, "begin")
    def _inject_identity(conn) -> None:
        identity = _identity_var.get()
        system = _system_var.get()
        if system:
            sig = compute_system_sig()
            conn.exec_driver_sql(
                "SELECT set_config('app.system', 'on', true), set_config('app.system_sig', %s, true)",
                (sig,),
            )
        if identity:
            sig = compute_identity_sig(str(identity))
            conn.exec_driver_sql(
                "SELECT set_config('app.user_id', %s, true), set_config('app.user_sig', %s, true)",
                (str(identity), sig),
            )

    @event.listens_for(Session, "after_begin")
    def _inject_identity_session(session, transaction, connection) -> None:
        identity = session.info.get("user_id") or _identity_var.get()
        system = session.info.get("system") or _system_var.get()
        if system:
            sig = compute_system_sig()
            connection.exec_driver_sql(
                "SELECT set_config('app.system', 'on', true), set_config('app.system_sig', %s, true)",
                (sig,),
            )
        if identity:
            sig = compute_identity_sig(str(identity))
            connection.exec_driver_sql(
                "SELECT set_config('app.user_id', %s, true), set_config('app.user_sig', %s, true)",
                (str(identity), sig),
            )


@lru_cache
def get_session_factory() -> sessionmaker[Session]:
    return sessionmaker(bind=get_engine(), autoflush=False, expire_on_commit=False, future=True)


@lru_cache
def get_admin_engine() -> Engine:
    """Schema-owner engine. Bypasses RLS by construction. Migrations/admin only."""
    settings = get_settings()
    url = settings.migration_database_url or get_settings().database_url
    engine = create_engine(url, pool_size=2, max_overflow=0, pool_pre_ping=True, future=True)
    return engine


@lru_cache
def get_admin_session_factory() -> sessionmaker[Session]:
    return sessionmaker(bind=get_admin_engine(), autoflush=False, expire_on_commit=False, future=True)


def get_db() -> Generator[Session, None, None]:
    session = get_session_factory()()
    try:
        yield session
    except Exception:
        session.rollback()
        raise
    finally:
        clear_identity(session)
        session.close()


def check_database(engine: Engine | None = None) -> dict[str, Any]:
    eng = engine or get_engine()
    try:
        with eng.connect() as conn:
            conn.execute(text("SELECT 1"))
            migration_head = None
            try:
                res = conn.execute(text("SELECT version_num FROM alembic_version LIMIT 1")).scalar()
                migration_head = str(res) if res else None
            except Exception:  # noqa: BLE001
                migration_head = None
        return {"status": "ok", "migration_head": migration_head}
    except Exception as exc:  # noqa: BLE001 — health must never raise or leak internals
        return {"status": "unavailable", "error_category": type(exc).__name__}


def verify_database_trust(engine: Engine | None = None) -> dict[str, Any]:
    """Cryptographic handshake verifying that application secret matches PostgreSQL RLS trust boundary."""
    import uuid

    eng = engine or get_engine()
    nonce = f"probe-{uuid.uuid4()}"
    sig = compute_identity_sig(nonce)
    try:
        with eng.connect() as conn:
            try:
                verified = conn.execute(
                    text("SELECT public.app_verify_trust_handshake(CAST(:nonce AS text), CAST(:sig AS text))"),
                    {"nonce": nonce, "sig": sig},
                ).scalar()
                if verified is True:
                    return {"status": "ok", "ok": True}
                if verified is False:
                    return {
                        "status": "trust_secret_mismatch",
                        "ok": False,
                        "detail": "Application DATABASE_IDENTITY_SECRET does not match PostgreSQL private.app_secrets",
                    }
            except Exception as e:  # noqa: BLE001
                # Rollback autobegun transaction first
                conn.rollback()
                # Fallback to testing via app_current_user_id inside an explicit transaction
                test_uid = str(uuid.uuid4())
                u_sig = compute_identity_sig(test_uid)
                with conn.begin():
                    conn.execute(
                        text("SELECT set_config('app.user_id', :uid, true), set_config('app.user_sig', :sig, true)"),
                        {"uid": test_uid, "sig": u_sig},
                    )
                    res_uid = conn.execute(text("SELECT public.app_current_user_id()")).scalar()
                    if str(res_uid) == test_uid:
                        return {"status": "ok", "ok": True}
                return {
                    "status": "trust_secret_mismatch",
                    "ok": False,
                    "detail": f"Application DATABASE_IDENTITY_SECRET failed app_current_user_id verification: {e}",
                }
    except Exception as exc:  # noqa: BLE001
        return {"status": "error", "ok": False, "detail": str(exc)[:200]}
