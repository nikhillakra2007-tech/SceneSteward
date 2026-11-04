"""Key rotation management script for participant contact records.

Scans all stored participant contact records and re-encrypts any record
encrypted with a legacy key or older KID to the current primary KID.
Performs decryption-re-encryption without downtime.

Usage:
    python -m scripts.rotate_encryption_keys [--target-kid <kid>] [--dry-run] [--batch-size 100]
"""
from __future__ import annotations

import argparse
import logging
import sys

from sqlalchemy import select

from app.core.config import get_settings
from app.core.database import get_session_factory, system_context
from app.core.security import decrypt_secret, encrypt_secret
from app.models.participants import ParticipantContactRecord

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("scenesteward.key_rotation")


def rotate_keys(
    target_kid: str | None = None,
    dry_run: bool = False,
    batch_size: int = 100,
    session=None,
) -> int:
    settings = get_settings()
    ring = settings.resolved_encryption_key_ring
    if not ring:
        logger.error("No encryption keys found in configuration. Set APP_ENCRYPTION_KEY or APP_ENCRYPTION_KEYS.")
        sys.exit(1)

    active_kid = target_kid or settings.app_encryption_current_kid or "primary"
    if active_kid not in ring:
        logger.error("Target KID %r not found in configured key ring: %s", active_kid, list(ring.keys()))
        sys.exit(1)

    prefix = f"v2.{active_kid}."
    logger.info("Starting encryption key rotation. Target KID: %s, Dry Run: %s", active_kid, dry_run)

    rotated_count = 0
    skipped_count = 0

    def _process_records(s) -> int:
        nonlocal rotated_count, skipped_count
        records = s.execute(select(ParticipantContactRecord)).scalars().all()
        total_records = len(records)
        logger.info("Found %d total contact records to inspect.", total_records)

        to_rotate = []
        for record in records:
            if record.encrypted_contact_data.startswith(prefix):
                skipped_count += 1
            else:
                to_rotate.append(record)

        logger.info("%d already up-to-date with KID %s; %d need re-encryption.", skipped_count, active_kid, len(to_rotate))

        if dry_run:
            logger.info("[Dry Run] Would rotate %d records. Exiting without modifying database.", len(to_rotate))
            return len(to_rotate)

        batch: list[ParticipantContactRecord] = []
        for record in to_rotate:
            try:
                plaintext = decrypt_secret(record.encrypted_contact_data, settings=settings)
                new_ciphertext = encrypt_secret(plaintext, settings=settings, kid=active_kid)
                record.encrypted_contact_data = new_ciphertext
                batch.append(record)
                rotated_count += 1

                if len(batch) >= batch_size:
                    s.commit()
                    logger.info("Committed batch of %d rotated records.", len(batch))
                    batch.clear()
            except Exception as exc:
                logger.error("Failed to re-encrypt contact record %s: %s", record.id, exc)
                s.rollback()
                raise

        if batch:
            s.commit()
            logger.info("Committed final batch of %d rotated records.", len(batch))
        return rotated_count

    if session is not None:
        with system_context(session):
            return _process_records(session)

    session_factory = get_session_factory()
    with session_factory() as sess, system_context(sess):
        return _process_records(sess)


def main() -> None:
    parser = argparse.ArgumentParser(description="Rotate participant contact data encryption keys.")
    parser.add_argument("--target-kid", type=str, default=None, help="Target key ID to re-encrypt records to.")
    parser.add_argument("--dry-run", action="store_true", help="Inspect and report without modifying database.")
    parser.add_argument("--batch-size", type=int, default=100, help="Number of records per commit batch.")
    args = parser.parse_args()

    rotate_keys(target_kid=args.target_kid, dry_run=args.dry_run, batch_size=args.batch_size)


if __name__ == "__main__":
    main()
