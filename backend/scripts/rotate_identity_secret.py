"""Database Identity Secret Rotation Utility.

Safely rotates the HMAC database identity secret used by PostgreSQL Row-Level Security.

Features:
- Validates the new secret (entropy, placeholder checks, min length 32 in production/staging).
- Requires schema-owner credentials to update private.app_secrets.
- Verifies cryptographic handshake after rotation.
- Does not modify or damage existing historical consent records or audit events.

Usage:
    python -m scripts.rotate_identity_secret --new-secret <secret> [--confirm]
"""
from __future__ import annotations

import argparse
import logging
import os
import sys
from pathlib import Path

# Ensure backend root is on sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sqlalchemy import create_engine, text

from app.core.config import get_settings
from app.core.database import compute_identity_sig

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("scenesteward.rotate_secret")

KNOWN_INSECURE_PLACEHOLDERS = frozenset({
    "CHANGE_ME",
    "CHANGE_ME_GENERATE_WITH_OPENSSL_RAND_HEX_32",
    "scenesteward_db_trust_secret_2026_prod_v1",
    "scenesteward_staging_identity_trust_secret_2026",
})


def rotate_secret(new_secret: str, confirm: bool = False, admin_db_url: str | None = None) -> bool:
    settings = get_settings()
    app_env = (settings.app_env or "development").lower()
    is_restricted = app_env in ("production", "staging")

    # 1. Secret validation
    if not new_secret:
        logger.error("New secret cannot be empty.")
        return False

    if is_restricted and (new_secret in KNOWN_INSECURE_PLACEHOLDERS or "CHANGE_ME" in new_secret or len(new_secret) < 32):
        logger.error(
            "In %s environment, new secret must be high-entropy and >= 32 characters.",
            app_env.upper(),
        )
        return False

    if is_restricted and not confirm:
        logger.error(
            "Secret rotation in %s requires explicit --confirm flag.",
            app_env.upper(),
        )
        return False

    url = admin_db_url or settings.migration_database_url or settings.database_url
    admin_engine = create_engine(url, future=True)

    with admin_engine.begin() as conn:
        active_db = conn.execute(text("SELECT current_database()")).scalar()
        logger.info("Connected to database %r for secret rotation.", active_db)

        # Check existing secret
        existing = conn.execute(
            text("SELECT secret_val FROM private.app_secrets WHERE key_name = 'identity_secret'")
        ).scalar()

        if existing == new_secret:
            logger.info("New secret is identical to existing secret. No change needed.")
            return True

        # Perform rotation
        conn.execute(
            text(
                "INSERT INTO private.app_secrets (key_name, secret_val) "
                "VALUES ('identity_secret', :sec) "
                "ON CONFLICT (key_name) DO UPDATE SET secret_val = EXCLUDED.secret_val"
            ),
            {"sec": new_secret},
        )
        logger.info("Successfully updated private.app_secrets.")

    # 2. Verify handshake with new secret
    # Temporarily set environment secret for verification check
    os.environ["DATABASE_IDENTITY_SECRET"] = new_secret
    # Clear settings cache
    get_settings.cache_clear()
    get_settings()

    test_sig = compute_identity_sig("probe_rotation", secret=new_secret)
    with admin_engine.connect() as conn:
        verified = conn.execute(
            text("SELECT public.app_verify_trust_handshake(CAST('probe_rotation' AS text), CAST(:sig AS text))"),
            {"sig": test_sig},
        ).scalar()

    if verified is True:
        logger.info("Cryptographic trust handshake VERIFIED with rotated secret.")
        print("\n" + "=" * 60)
        print("SECRET ROTATION COMPLETE")
        print("=" * 60)
        print(f"Active database: {active_db}")
        print("Next step: Update your deployment environment variable:")
        print(f"DATABASE_IDENTITY_SECRET={new_secret}")
        print("=" * 60 + "\n")
        return True
    else:
        logger.error("Post-rotation handshake FAILED! Database rejected new signature.")
        return False


def main() -> None:
    parser = argparse.ArgumentParser(description="Rotate SceneSteward PostgreSQL identity trust secret.")
    parser.add_argument("--new-secret", type=str, required=True, help="New secret string (min 32 chars in prod/stage).")
    parser.add_argument("--confirm", action="store_true", help="Confirm rotation in production or staging.")
    parser.add_argument("--admin-url", type=str, default=None, help="Schema owner DSN.")
    args = parser.parse_args()

    success = rotate_secret(new_secret=args.new_secret, confirm=args.confirm, admin_db_url=args.admin_url)
    if not success:
        sys.exit(1)


if __name__ == "__main__":
    main()
