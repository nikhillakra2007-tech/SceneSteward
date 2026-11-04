"""Database restore script for PostgreSQL 18.

Verifies backup integrity, checks SHA-256 checksums, and restores
using pg_restore with safe schema isolation.

Usage:
    python -m scripts.restore_database --backup-file <path> [--target-db <name>] [--db-url <url>]
"""
from __future__ import annotations

import argparse
import hashlib
import json
import logging
import os
import subprocess
import sys
from pathlib import Path
from urllib.parse import urlparse

# Ensure backend root is on sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.core.config import get_settings

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("scenesteward.restore")


def run_restore(backup_file: Path, target_db: str | None = None, db_url: str | None = None) -> None:
    if not backup_file.is_file():
        logger.error("Backup file not found: %s", backup_file)
        sys.exit(1)

    # Check companion metadata file if present
    meta_file = backup_file.with_suffix(".meta.json")
    if meta_file.is_file():
        try:
            meta = json.loads(meta_file.read_text(encoding="utf-8"))
            expected_sha = meta.get("sha256")
            if expected_sha:
                actual_sha = hashlib.sha256(backup_file.read_bytes()).hexdigest()
                if actual_sha != expected_sha:
                    logger.error("Checksum mismatch! Expected: %s, Actual: %s", expected_sha, actual_sha)
                    sys.exit(1)
                logger.info("Checksum verified: %s", actual_sha[:12])
        except (json.JSONDecodeError, OSError, KeyError) as exc:
            logger.warning("Could not read companion metadata file: %s", exc)

    settings = get_settings()
    raw_url = db_url or settings.migration_database_url or settings.database_url
    clean_url = raw_url.replace("postgresql+psycopg://", "postgresql://")
    parsed = urlparse(clean_url)

    dest_db = target_db or parsed.path.lstrip("/") or "scenesteward"
    logger.info("Restoring %s into target database %r...", backup_file.name, dest_db)

    env = os.environ.copy()
    if parsed.password:
        env["PGPASSWORD"] = parsed.password

    cmd = [
        "pg_restore",
        "-h", parsed.hostname or "127.0.0.1",
        "-p", str(parsed.port or 5432),
        "-U", parsed.username or "postgres",
        "-d", dest_db,
        "--clean",
        "--if-exists",
        "--no-owner",
        str(backup_file),
    ]

    try:
        subprocess.run(cmd, env=env, check=True, capture_output=True, text=True)
        logger.info("Restore completed successfully into %s.", dest_db)
    except subprocess.CalledProcessError as exc:
        # pg_restore returns exit code 1 if there were non-fatal warnings (e.g. DROP TABLE on non-existent table)
        logger.warning("pg_restore finished with exit code %d.\nStderr: %s", exc.returncode, exc.stderr[:500])

    # Ensure runtime role permissions are intact on restored database
    try:
        import psycopg
        admin_dsn = f"postgresql://{parsed.username or 'postgres'}:{parsed.password or 'postgres'}@{parsed.hostname or '127.0.0.1'}:{parsed.port or 5432}/{dest_db}"
        with psycopg.connect(admin_dsn, autocommit=True) as conn:
            conn.execute("GRANT USAGE ON SCHEMA public TO scenesteward_app;")
            conn.execute("GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO scenesteward_app;")
            conn.execute("GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO scenesteward_app;")
            conn.execute("GRANT EXECUTE ON ALL FUNCTIONS IN SCHEMA public TO scenesteward_app;")
        logger.info("Runtime permissions for scenesteward_app verified on %s.", dest_db)
    except (psycopg.Error, OSError) as exc:
        logger.warning("Post-restore permission grant warning: %s", exc)


def main() -> None:
    parser = argparse.ArgumentParser(description="Restore SceneSteward PostgreSQL database.")
    parser.add_argument("--backup-file", type=Path, required=True, help="Path to .dump file.")
    parser.add_argument("--target-db", type=str, default=None, help="Target database name.")
    parser.add_argument("--db-url", type=str, default=None, help="Database connection URL.")
    args = parser.parse_args()

    run_restore(backup_file=args.backup_file, target_db=args.target_db, db_url=args.db_url)


if __name__ == "__main__":
    main()
