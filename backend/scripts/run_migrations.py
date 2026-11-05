"""One-shot migration runner and permission synchronizer.

Used by the 'migrate' container during deployment orchestration:
1. Provisions/hardens least-privilege roles (scenesteward_app, scenesteward_readonly)
2. Executes Alembic schema migrations to head
3. Enforces least-privilege table, sequence, and function grants
4. Verifies cryptographic database trust handshake
"""
from __future__ import annotations

import logging
import os
import subprocess
import sys
from pathlib import Path

# Ensure backend root is on sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.core.config import get_settings
from scripts.provision_db_roles import provision_roles

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("scenesteward.migrate_runner")


def main() -> None:
    settings = get_settings()
    admin_url = (
        settings.migration_database_url
        or os.environ.get("MIGRATION_DATABASE_URL")
        or os.environ.get("DATABASE_URL_ADMIN")
        or settings.database_url
    )
    if not admin_url:
        logger.error("No database URL provided for migration runner.")
        sys.exit(1)

    # 1. Pre-migration role provisioning & hardening
    logger.info("Phase 1: Deterministic database role provisioning...")
    try:
        role_status = provision_roles(admin_url=admin_url)
        logger.info("Roles provisioned successfully for database: %s", role_status.get("database"))
    except Exception as exc:  # noqa: BLE001
        logger.warning("Pre-migration role provisioning warning (continuing to Alembic): %s", exc)

    # 2. Alembic migration execution
    logger.info("Phase 2: Executing Alembic migrations to head...")
    alembic_ini = Path(__file__).resolve().parent.parent / "alembic.ini"
    env = os.environ.copy()
    env["ALEMBIC_DATABASE_URL"] = admin_url.replace("postgresql+psycopg://", "postgresql://")

    cmd = ["alembic", "-c", str(alembic_ini), "upgrade", "head"]
    try:
        proc = subprocess.run(cmd, env=env, check=True, capture_output=True, text=True)
        logger.info("Alembic upgrade output:\n%s", proc.stdout.strip())
    except subprocess.CalledProcessError as exc:
        logger.error("Alembic migration failed with code %d:\n%s", exc.returncode, exc.stderr.strip())
        sys.exit(exc.returncode)

    # 3. Post-migration permission grant re-enforcement
    logger.info("Phase 3: Re-enforcing least-privilege grants on migrated schema...")
    try:
        provision_roles(admin_url=admin_url)
    except Exception as exc:  # noqa: BLE001
        logger.error("Post-migration grant enforcement failed: %s", exc)
        sys.exit(1)

    # 4. Database trust handshake verification
    logger.info("Phase 4: Verifying cryptographic database trust handshake...")
    from app.core.database import verify_database_trust
    trust = verify_database_trust()
    if not trust.get("ok"):
        logger.error("Database trust verification failed: %s", trust.get("detail"))
        if settings.is_production or settings.is_staging:
            sys.exit(1)

    logger.info("Migration runner completed successfully. Database is at head and roles are hardened.")


if __name__ == "__main__":
    main()
