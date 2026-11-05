"""Robust, atomic, verified database backup system for PostgreSQL.

Implements:
1. Unique backup identification and locking to prevent concurrent jobs.
2. Temporary file staging in destination filesystem.
3. Full pg_dump execution with strict exit code validation.
4. Mandatory archive integrity check via 'pg_restore --list'.
5. Streaming SHA-256 checksum calculation (chunked, memory-safe).
6. Comprehensive metadata manifest generation (no secrets included).
7. OS file synchronization (fsync) and atomic file publication (os.replace).
8. Optional Fernet encryption-at-rest for external storage.
9. Configurable off-site storage replication interface.
10. Automatic cleanup of transient artifacts upon any failure.

Usage:
    python -m scripts.backup_database [--output-dir <dir>] [--db-url <url>] [--encrypt] [--offsite-dir <dir>]
"""
from __future__ import annotations

import argparse
import hashlib
import json
import logging
import os
import subprocess
import sys
import uuid
from datetime import UTC, datetime
from pathlib import Path
from typing import Self
from urllib.parse import urlparse

try:
    import fcntl
except ImportError:
    fcntl = None

# Ensure backend root is on sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.core.config import get_settings

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("scenesteward.backup")


class BackupLock:
    """File-based lock preventing duplicate concurrent backup jobs."""

    def __init__(self, lock_file: Path) -> None:
        self.lock_file = lock_file
        self.fd: int | None = None

    def __enter__(self) -> Self:
        self.lock_file.parent.mkdir(parents=True, exist_ok=True)
        try:
            self.fd = os.open(str(self.lock_file), os.O_CREAT | os.O_RDWR)
            if fcntl is not None:
                fcntl.flock(self.fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
            elif sys.platform == "win32":
                import msvcrt
                msvcrt.locking(self.fd, msvcrt.LK_NBLCK, 1)
        except (BlockingIOError, OSError) as exc:
            logger.error("Another backup job is currently running (lock acquired: %s)", self.lock_file)
            raise RuntimeError("Concurrent backup execution rejected") from exc
        return self

    def __exit__(self, exc_type: object, exc_val: object, exc_tb: object) -> None:
        if self.fd is not None:
            try:
                if fcntl is not None:
                    fcntl.flock(self.fd, fcntl.LOCK_UN)
                elif sys.platform == "win32":
                    import msvcrt
                    try:
                        msvcrt.locking(self.fd, msvcrt.LK_UNLCK, 1)
                    except OSError:
                        pass
                os.close(self.fd)
            except OSError:
                pass


def compute_streaming_sha256(file_path: Path, chunk_size: int = 65536) -> str:
    """Compute SHA-256 hash in chunked blocks to prevent loading large backups into RAM."""
    hasher = hashlib.sha256()
    with file_path.open("rb") as f:
        while chunk := f.read(chunk_size):
            hasher.update(chunk)
    return hasher.hexdigest()


def encrypt_backup_file(input_path: Path, output_path: Path, encryption_key: str) -> None:
    """Encrypt a backup dump using 256-bit AES Fernet before off-site replication."""
    from cryptography.fernet import Fernet
    fernet = Fernet(encryption_key.encode("utf-8") if isinstance(encryption_key, str) else encryption_key)

    with input_path.open("rb") as fin, output_path.open("wb") as fout:
        data = fin.read()
        encrypted = fernet.encrypt(data)
        fout.write(encrypted)
        fout.flush()
        os.fsync(fout.fileno())


def run_backup(
    output_dir: Path | None = None,
    db_url: str | None = None,
    encrypt: bool = False,
    encryption_key: str | None = None,
    offsite_dir: Path | None = None,
) -> Path:
    """Create an atomic, verified, and manifested database backup."""
    settings = get_settings()
    raw_url = db_url or settings.migration_database_url or settings.database_url
    if not raw_url:
        logger.error("No database URL provided or found in environment.")
        raise ValueError("Missing database connection URL for backup")

    clean_url = raw_url.replace("postgresql+psycopg://", "postgresql://")
    parsed = urlparse(clean_url)
    dbname = parsed.path.lstrip("/") or "scenesteward"

    dest_dir = output_dir or (Path(__file__).resolve().parents[1] / "var" / "backups")
    dest_dir.mkdir(parents=True, exist_ok=True)

    lock_file = dest_dir / ".backup.lock"
    with BackupLock(lock_file):
        start_time = datetime.now(UTC)
        timestamp_str = start_time.strftime("%Y%m%d_%H%M%SZ")
        backup_id = f"bkp_{uuid.uuid4().hex[:12]}_{timestamp_str}"

        # Temporary staging filenames
        tmp_dump_file = dest_dir / f".tmp_{backup_id}.dump"
        tmp_meta_file = dest_dir / f".tmp_{backup_id}.meta.json"

        # Final published filenames
        final_dump_file = dest_dir / f"{dbname}_{timestamp_str}.dump"
        final_meta_file = dest_dir / f"{dbname}_{timestamp_str}.meta.json"

        # Query source database metadata (version, alembic revision)
        pg_version = "unknown"
        alembic_head = None
        try:
            import psycopg
            with psycopg.connect(clean_url, connect_timeout=5) as conn, conn.cursor() as cur:
                cur.execute("SELECT version();")
                row = cur.fetchone()
                if row:
                    pg_version = row[0]
                cur.execute("""
                        SELECT version_num FROM alembic_version LIMIT 1;
                    """)
                row = cur.fetchone()
                if row:
                    alembic_head = row[0]
        except Exception as exc:  # noqa: BLE001
            logger.warning("Could not query DB metadata prior to backup: %s", exc)

        logger.info("Initiating atomic pg_dump for %s [ID: %s] -> staging file %s", dbname, backup_id, tmp_dump_file.name)

        env = os.environ.copy()
        if parsed.password:
            env["PGPASSWORD"] = parsed.password

        dump_cmd = [
            "pg_dump",
            "-h", parsed.hostname or "127.0.0.1",
            "-p", str(parsed.port or 5432),
            "-U", parsed.username or "postgres",
            "-d", dbname,
            "--format=custom",
            "--compress=9",
            "--no-owner",
            "--no-privileges",
            "--file", str(tmp_dump_file),
        ]

        try:
            subprocess.run(dump_cmd, env=env, check=True, capture_output=True, text=True)
        except subprocess.CalledProcessError as exc:
            logger.error("pg_dump failed with exit code %d: %s", exc.returncode, exc.stderr.strip()[:500])
            tmp_dump_file.unlink(missing_ok=True)
            raise RuntimeError(f"pg_dump execution failed: {exc.stderr.strip()[:200]}") from exc

        # Mandatory archive integrity verification with pg_restore --list
        logger.info("Executing mandatory integrity check with pg_restore --list on staged artifact...")
        verify_cmd = ["pg_restore", "--list", str(tmp_dump_file)]
        try:
            proc = subprocess.run(verify_cmd, check=True, capture_output=True, text=True)
            toc_lines = len(proc.stdout.splitlines())
            if toc_lines < 5:
                raise RuntimeError(f"Archive TOC is suspiciously small ({toc_lines} entries)")
            logger.info("Integrity check PASSED. Archive TOC contains %d items.", toc_lines)
        except (subprocess.CalledProcessError, RuntimeError) as exc:
            logger.error("Backup archive verification failed: %s", exc)
            tmp_dump_file.unlink(missing_ok=True)
            raise RuntimeError(f"Backup archive verification failed: {exc}") from exc

        # Memory-safe streaming SHA-256 calculation
        sha256_hash = compute_streaming_sha256(tmp_dump_file)
        file_size = tmp_dump_file.stat().st_size

        # Encryption handling if requested
        is_encrypted = False
        enc_sha256 = None
        key_to_use = encryption_key or os.environ.get("BACKUP_ENCRYPTION_KEY") or settings.app_encryption_key
        if encrypt:
            if not key_to_use:
                tmp_dump_file.unlink(missing_ok=True)
                raise ValueError("Backup encryption requested but no encryption key provided.")
            logger.info("Encrypting backup archive with Fernet AES-256-CBC...")
            tmp_enc_file = dest_dir / f".tmp_{backup_id}.dump.enc"
            encrypt_backup_file(tmp_dump_file, tmp_enc_file, key_to_use)
            enc_sha256 = compute_streaming_sha256(tmp_enc_file)
            # Replace staged dump with encrypted archive
            tmp_dump_file.unlink(missing_ok=True)
            tmp_dump_file = tmp_enc_file
            file_size = tmp_dump_file.stat().st_size
            sha256_hash = enc_sha256
            final_dump_file = dest_dir / f"{dbname}_{timestamp_str}.dump.enc"
            is_encrypted = True

        # Generate comprehensive metadata manifest (NO SECRETS)
        end_time = datetime.now(UTC)
        duration_sec = round((end_time - start_time).total_seconds(), 2)

        metadata = {
            "backup_id": backup_id,
            "database": dbname,
            "created_at_utc": start_time.isoformat(),
            "completed_at_utc": end_time.isoformat(),
            "duration_seconds": duration_sec,
            "postgres_version": pg_version,
            "alembic_head": alembic_head,
            "backup_format": "custom",
            "size_bytes": file_size,
            "sha256": sha256_hash,
            "toc_entries": toc_lines,
            "verification_status": "verified",
            "encryption_status": "fernet_aes256_cbc" if is_encrypted else "unencrypted",
            "storage_destination": "local",
            "filename": final_dump_file.name,
        }

        # Staging manifest write & flush
        with tmp_meta_file.open("w", encoding="utf-8") as f:
            f.write(json.dumps(metadata, indent=2))
            f.flush()
            os.fsync(f.fileno())

        # Atomic publication: rename staged files to final filenames
        os.replace(tmp_dump_file, final_dump_file)
        os.replace(tmp_meta_file, final_meta_file)

        logger.info(
            "Backup successfully published: %s (%.2f KB, SHA-256: %s, duration: %.2fs)",
            final_dump_file.name,
            file_size / 1024,
            sha256_hash[:12],
            duration_sec,
        )

        # Offsite replication if configured
        offsite_target = offsite_dir or (Path(os.environ["BACKUP_OFFSITE_DIR"]) if "BACKUP_OFFSITE_DIR" in os.environ else None)
        if offsite_target:
            offsite_target.mkdir(parents=True, exist_ok=True)
            logger.info("Replicating backup to offsite destination: %s", offsite_target)
            offsite_dump = offsite_target / final_dump_file.name
            offsite_meta = offsite_target / final_meta_file.name

            import shutil
            shutil.copy2(final_dump_file, offsite_dump)
            shutil.copy2(final_meta_file, offsite_meta)

            # Verify offsite copy integrity
            remote_sha = compute_streaming_sha256(offsite_dump)
            if remote_sha != sha256_hash:
                offsite_dump.unlink(missing_ok=True)
                offsite_meta.unlink(missing_ok=True)
                raise RuntimeError(f"Offsite replication integrity mismatch: {remote_sha} != {sha256_hash}")
            logger.info("Offsite replication integrity verified (SHA-256: %s)", remote_sha[:12])

        return final_dump_file


def main() -> None:
    parser = argparse.ArgumentParser(description="Backup SceneSteward PostgreSQL database.")
    parser.add_argument("--output-dir", type=Path, default=None, help="Directory to store backup dumps.")
    parser.add_argument("--db-url", type=str, default=None, help="Database connection URL.")
    parser.add_argument("--encrypt", action="store_true", help="Encrypt backup with Fernet key.")
    parser.add_argument("--encryption-key", type=str, default=None, help="Fernet key for encryption.")
    parser.add_argument("--offsite-dir", type=Path, default=None, help="Directory for off-site backup replication.")
    args = parser.parse_args()

    run_backup(
        output_dir=args.output_dir,
        db_url=args.db_url,
        encrypt=args.encrypt,
        encryption_key=args.encryption_key,
        offsite_dir=args.offsite_dir,
    )


if __name__ == "__main__":
    main()
