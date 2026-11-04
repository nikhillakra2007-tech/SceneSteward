"""Database backup script for PostgreSQL 18.

Generates a compressed, atomic custom-format dump with integrity verification,
checksum calculation, and metadata recording.

Usage:
    python -m scripts.backup_database [--output-dir <dir>] [--db-url <url>]
"""
from __future__ import annotations

import argparse
import hashlib
import json
import logging
import os
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path
from urllib.parse import urlparse

# Ensure backend root is on sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.core.config import get_settings

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("scenesteward.backup")


def run_backup(output_dir: Path | None = None, db_url: str | None = None) -> Path:
    settings = get_settings()
    raw_url = db_url or settings.migration_database_url or settings.database_url
    if not raw_url:
        logger.error("No database URL provided or found in environment.")
        sys.exit(1)

    # Convert sqlalchemy url format (postgresql+psycopg://...) to standard postgresql://
    clean_url = raw_url.replace("postgresql+psycopg://", "postgresql://")
    parsed = urlparse(clean_url)

    dest_dir = output_dir or (Path(__file__).resolve().parents[1] / "var" / "backups")
    dest_dir.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now(UTC).strftime("%Y%m%d_%H%M%SZ")
    dbname = parsed.path.lstrip("/") or "scenesteward"
    backup_file = dest_dir / f"{dbname}_{timestamp}.dump"
    meta_file = dest_dir / f"{dbname}_{timestamp}.meta.json"

    logger.info("Starting atomic pg_dump for %s -> %s", dbname, backup_file)

    env = os.environ.copy()
    if parsed.password:
        env["PGPASSWORD"] = parsed.password

    cmd = [
        "pg_dump",
        "-h", parsed.hostname or "127.0.0.1",
        "-p", str(parsed.port or 5432),
        "-U", parsed.username or "postgres",
        "-d", dbname,
        "--format=custom",
        "--compress=9",
        "--no-owner",
        "--no-privileges",
        "--file", str(backup_file),
    ]

    try:
        subprocess.run(cmd, env=env, check=True, capture_output=True, text=True)
    except subprocess.CalledProcessError as exc:
        logger.error("pg_dump failed: %s\nStderr: %s", exc, exc.stderr)
        backup_file.unlink(missing_ok=True)
        sys.exit(1)

    # Verify backup archive listing with pg_restore -l
    logger.info("Verifying backup integrity with pg_restore --list...")
    verify_cmd = ["pg_restore", "--list", str(backup_file)]
    try:
        proc = subprocess.run(verify_cmd, check=True, capture_output=True, text=True)
        toc_lines = len(proc.stdout.splitlines())
        logger.info("Integrity check passed. Archive TOC contains %d items.", toc_lines)
    except subprocess.CalledProcessError as exc:
        logger.error("Backup verification failed: %s\nStderr: %s", exc, exc.stderr)
        backup_file.unlink(missing_ok=True)
        sys.exit(1)

    # Compute SHA-256
    sha256 = hashlib.sha256(backup_file.read_bytes()).hexdigest()
    file_size = backup_file.stat().st_size

    metadata = {
        "timestamp": datetime.now(UTC).isoformat(),
        "database": dbname,
        "backup_file": backup_file.name,
        "size_bytes": file_size,
        "sha256": sha256,
        "toc_entries": toc_lines,
        "pg_dump_format": "custom",
    }
    meta_file.write_text(json.dumps(metadata, indent=2), encoding="utf-8")
    logger.info("Backup complete: %s (%.2f KB, sha256: %s)", backup_file.name, file_size / 1024, sha256[:12])
    return backup_file


def main() -> None:
    parser = argparse.ArgumentParser(description="Backup SceneSteward PostgreSQL database.")
    parser.add_argument("--output-dir", type=Path, default=None, help="Directory to store backup dumps.")
    parser.add_argument("--db-url", type=str, default=None, help="Database connection URL.")
    args = parser.parse_args()

    run_backup(output_dir=args.output_dir, db_url=args.db_url)


if __name__ == "__main__":
    main()

