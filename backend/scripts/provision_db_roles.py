"""Deterministic database role provisioning and privilege enforcement.

Configures:
- Schema owner (migration role): owns DDL, Alembic version, and schema objects.
- Runtime application role (scenesteward_app): unprivileged, NOBYPASSRLS, NOSUPERUSER, DML only.
- Analytical role (scenesteward_readonly): unprivileged, NOBYPASSRLS, SELECT only.

Never prints passwords or secrets to logs or standard output.
"""
from __future__ import annotations

import argparse
import logging
import os
import sys
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

# Ensure backend root is on sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.core.config import get_settings

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("scenesteward.provision_roles")


def provision_roles(
    admin_url: str | None = None,
    app_password: str | None = None,
    readonly_password: str | None = None,
) -> dict[str, Any]:
    """Deterministically provision and harden database roles and privileges."""
    settings = get_settings()
    raw_admin_url = (
        admin_url
        or settings.migration_database_url
        or os.environ.get("DATABASE_URL_ADMIN")
        or settings.database_url
    )
    if not raw_admin_url:
        raise ValueError("No admin/migration database URL available for role provisioning")

    clean_admin_url = raw_admin_url.replace("postgresql+psycopg://", "postgresql://")
    parsed = urlparse(clean_admin_url)
    dbname = parsed.path.lstrip("/") or "scenesteward"

    app_pw = app_password or os.environ.get("APP_PASSWORD") or os.environ.get("POSTGRES_APP_PASSWORD")
    ro_pw = readonly_password or os.environ.get("READONLY_PASSWORD") or os.environ.get("POSTGRES_READONLY_PASSWORD")

    import psycopg

    logger.info("Connecting as schema owner/admin to %s at %s:%s", dbname, parsed.hostname, parsed.port or 5432)
    with psycopg.connect(clean_admin_url, autocommit=True) as conn, conn.cursor() as cur:
        # 1. Provision scenesteward_app role
            cur.execute("SELECT 1 FROM pg_roles WHERE rolname = 'scenesteward_app'")
            app_exists = cur.fetchone() is not None

            if not app_exists:
                logger.info("Creating role 'scenesteward_app' (unprivileged, NOBYPASSRLS)...")
                if app_pw:
                    cur.execute(
                        psycopg.sql.SQL(
                            "CREATE ROLE scenesteward_app WITH LOGIN PASSWORD %s "
                            "NOSUPERUSER NOCREATEDB NOCREATEROLE NOINHERIT NOBYPASSRLS;"
                        ),
                        [app_pw],
                    )
                else:
                    cur.execute("CREATE ROLE scenesteward_app NOLOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE NOINHERIT NOBYPASSRLS;")
            else:
                logger.info("Hardening existing role 'scenesteward_app' attributes...")
                if app_pw:
                    cur.execute(
                        psycopg.sql.SQL(
                            "ALTER ROLE scenesteward_app WITH LOGIN PASSWORD %s "
                            "NOSUPERUSER NOCREATEDB NOCREATEROLE NOINHERIT NOBYPASSRLS;"
                        ),
                        [app_pw],
                    )
                else:
                    cur.execute("ALTER ROLE scenesteward_app WITH NOSUPERUSER NOCREATEDB NOCREATEROLE NOINHERIT NOBYPASSRLS;")

            # 2. Provision scenesteward_readonly role
            cur.execute("SELECT 1 FROM pg_roles WHERE rolname = 'scenesteward_readonly'")
            ro_exists = cur.fetchone() is not None

            if not ro_exists:
                logger.info("Creating role 'scenesteward_readonly' (unprivileged, NOBYPASSRLS)...")
                if ro_pw:
                    cur.execute(
                        psycopg.sql.SQL(
                            "CREATE ROLE scenesteward_readonly WITH LOGIN PASSWORD %s "
                            "NOSUPERUSER NOCREATEDB NOCREATEROLE NOINHERIT NOBYPASSRLS;"
                        ),
                        [ro_pw],
                    )
                else:
                    cur.execute("CREATE ROLE scenesteward_readonly NOLOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE NOINHERIT NOBYPASSRLS;")
            else:
                logger.info("Hardening existing role 'scenesteward_readonly' attributes...")
                if ro_pw:
                    cur.execute(
                        psycopg.sql.SQL(
                            "ALTER ROLE scenesteward_readonly WITH LOGIN PASSWORD %s "
                            "NOSUPERUSER NOCREATEDB NOCREATEROLE NOINHERIT NOBYPASSRLS;"
                        ),
                        [ro_pw],
                    )
                else:
                    cur.execute("ALTER ROLE scenesteward_readonly WITH NOSUPERUSER NOCREATEDB NOCREATEROLE NOINHERIT NOBYPASSRLS;")

            # 3. Grant database connection privileges
            cur.execute(
                psycopg.sql.SQL("GRANT CONNECT ON DATABASE {} TO scenesteward_app, scenesteward_readonly;").format(
                    psycopg.sql.Identifier(dbname)
                )
            )

            # 4. Schema usage and isolation
            cur.execute("GRANT USAGE ON SCHEMA public TO scenesteward_app, scenesteward_readonly;")
            cur.execute("REVOKE ALL ON SCHEMA public FROM PUBLIC;")

            # Strict protection of private trust boundary schema
            cur.execute("""
                DO $$
                BEGIN
                    IF EXISTS (SELECT 1 FROM information_schema.schemata WHERE schema_name = 'private') THEN
                        REVOKE ALL ON SCHEMA private FROM PUBLIC, scenesteward_app, scenesteward_readonly;
                        REVOKE ALL ON ALL TABLES IN SCHEMA private FROM PUBLIC, scenesteward_app, scenesteward_readonly;
                    END IF;
                END $$;
            """)

            # 5. Table and sequence permissions for scenesteward_app (DML only, non-owner)
            cur.execute("GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO scenesteward_app;")
            cur.execute("GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO scenesteward_app;")
            cur.execute("GRANT EXECUTE ON ALL FUNCTIONS IN SCHEMA public TO scenesteward_app;")

            # Read-only permissions for scenesteward_readonly
            cur.execute("GRANT SELECT ON ALL TABLES IN SCHEMA public TO scenesteward_readonly;")

            # Deny alembic_version modification to runtime roles
            cur.execute("""
                DO $$
                BEGIN
                    IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_schema = 'public' AND table_name = 'alembic_version') THEN
                        REVOKE ALL ON TABLE alembic_version FROM scenesteward_app, scenesteward_readonly;
                    END IF;
                END $$;
            """)

            # 6. Default privileges for future schema objects created by schema owner
            cur.execute("ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO scenesteward_app;")
            cur.execute("ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT USAGE, SELECT ON SEQUENCES TO scenesteward_app;")
            cur.execute("ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT EXECUTE ON FUNCTIONS TO scenesteward_app;")
            cur.execute("ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT SELECT ON TABLES TO scenesteward_readonly;")

            # 7. Audit and verify final attributes
            cur.execute("""
                SELECT rolname, rolcanlogin, rolsuper, rolbypassrls, rolcreatedb, rolcreaterole
                FROM pg_roles
                WHERE rolname IN ('scenesteward_app', 'scenesteward_readonly', 'scenesteward', 'postgres')
                ORDER BY rolname;
            """)
            roles_audit = [
                {
                    "role": r[0],
                    "can_login": r[1],
                    "superuser": r[2],
                    "bypassrls": r[3],
                    "createdb": r[4],
                    "createrole": r[5],
                }
                for r in cur.fetchall()
            ]

            # Verify no tables are owned by runtime role
            cur.execute("""
                SELECT tablename
                FROM pg_tables
                WHERE schemaname = 'public' AND tableowner = 'scenesteward_app';
            """)
            owned_tables = [row[0] for row in cur.fetchall()]
            if owned_tables:
                raise RuntimeError(f"CRITICAL SECURITY DEFECT: Runtime role 'scenesteward_app' owns tables: {owned_tables}")

    logger.info("Database roles successfully provisioned and verified.")
    return {
        "status": "ok",
        "database": dbname,
        "roles": roles_audit,
        "owned_tables_by_runtime_role": owned_tables,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Provision SceneSteward database roles with strict least privilege.")
    parser.add_argument("--admin-url", type=str, default=None, help="Admin/Schema owner database URL.")
    parser.add_argument("--app-password", type=str, default=None, help="Password for scenesteward_app.")
    parser.add_argument("--readonly-password", type=str, default=None, help="Password for scenesteward_readonly.")
    args = parser.parse_args()

    res = provision_roles(
        admin_url=args.admin_url,
        app_password=args.app_password,
        readonly_password=args.readonly_password,
    )
    for role in res.get("roles", []):
        logger.info(
            "Role Verified: %s | Login=%s | Superuser=%s | BypassRLS=%s",
            role["role"],
            role["can_login"],
            role["superuser"],
            role["bypassrls"],
        )


if __name__ == "__main__":
    main()
