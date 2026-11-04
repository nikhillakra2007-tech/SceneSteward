"""Mint a local dev token (AUTH_PROVIDER=dev only) and optionally provision the user.

Usage:
  python scripts/dev_token.py --email owner@example.com --name "Olivia Owner"
Prints a bearer token to stdout (1h TTL). Never use against a real deployment.
"""
from __future__ import annotations

import argparse
import sys
import uuid
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.core.config import get_settings
from app.core.database import get_session_factory
from app.core.security import mint_dev_token
from app.models import User


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--email", required=True)
    parser.add_argument("--name", required=True)
    parser.add_argument("--ttl-seconds", type=int, default=3600)
    args = parser.parse_args()

    settings = get_settings()
    if settings.auth_provider != "dev":
        print("Refusing: AUTH_PROVIDER is not 'dev'.", file=sys.stderr)
        return 2

    email = args.email.strip().lower()
    session = get_session_factory()()
    try:
        user = session.query(User).filter(User.email == email, User.auth_provider == "dev").first()
        if user is None:
            user = User(email=email, full_name=args.name, auth_provider="dev",
                        provider_user_id=str(uuid.uuid4()), account_status="active")
            session.add(user)
            session.commit()
            session.refresh(user)
            print(f"provisioned dev user id={user.id}", file=sys.stderr)
        print(mint_dev_token(user_id=user.provider_user_id, email=user.email,
                             full_name=user.full_name, settings=settings,
                             ttl_seconds=args.ttl_seconds))
        return 0
    finally:
        session.close()


if __name__ == "__main__":
    raise SystemExit(main())
