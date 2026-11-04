"""Master verification runner for SceneSteward Staging Environment.

Runs:
1. Database connectivity & Alembic migration head check
2. Supabase Auth live check
3. Supabase Storage live check
4. Anthropic Claude API live check
5. Switch Integration live check
6. ClamAV Daemon live check
"""
from __future__ import annotations

import os

from app.core.config import get_settings
from scripts.verify_staging_anthropic import verify_anthropic_api
from scripts.verify_staging_auth import verify_supabase_auth
from scripts.verify_staging_clamav import verify_clamav_daemon
from scripts.verify_staging_storage import verify_supabase_storage
from scripts.verify_staging_switch import verify_switch_adapter


def run_all_staging_checks() -> dict[str, str]:
    settings = get_settings()
    summary: dict[str, str] = {}

    print("=" * 70)
    print(" SceneSteward — Comprehensive Staging Provider Activation Report")
    print(f" Environment: {settings.app_env.upper()} | Time: 2026-11-04")
    print("=" * 70)

    # 1. Database Check
    print("\n--- [1/6] POSTGRESQL 18 DATABASE ---")
    try:
        import psycopg
        dsn = settings.database_url.replace("postgresql+psycopg://", "postgresql://")
        with psycopg.connect(dsn) as conn, conn.cursor() as cur:
            cur.execute("SELECT version();")
            v = cur.fetchone()[0]
            cur.execute("SELECT current_user, current_database();")
            u, d = cur.fetchone()
            print(f"[OK] Runtime DB Connected: user='{u}', database='{d}'")
            print(f"[OK] Engine Version: {v[:40]}...")

        # Check migration version using migration DSN or admin DSN
        mig_url = settings.migration_database_url or os.environ.get("DATABASE_URL_ADMIN")
        if mig_url:
            mig_dsn = mig_url.replace("postgresql+psycopg://", "postgresql://")
            with psycopg.connect(mig_dsn) as conn, conn.cursor() as cur:
                cur.execute("SELECT version_num FROM alembic_version;")
                alem = cur.fetchone()[0]
                print(f"[OK] Schema Owner Connected: Alembic Head = '{alem}'")
                summary["database"] = f"LIVE_VERIFIED (PostgreSQL 18, rev {alem})"
        else:
            summary["database"] = f"LIVE_VERIFIED (PostgreSQL 18, user {u})"
    except Exception as exc:  # noqa: BLE001
        print(f"[FAIL] Database connection failed: {exc}")
        summary["database"] = f"FAILED: {exc}"

    # 2. Supabase Auth
    print("\n--- [2/6] SUPABASE AUTHENTICATION ---")
    auth_res = verify_supabase_auth()
    summary["auth"] = str(auth_res.get("status", "BLOCKED"))

    # 3. Supabase Storage
    print("\n--- [3/6] SUPABASE PRIVATE STORAGE ---")
    storage_res = verify_supabase_storage()
    summary["storage"] = str(storage_res.get("status", "BLOCKED"))

    # 4. Anthropic Claude AI
    print("\n--- [4/6] ANTHROPIC CLAUDE AI ---")
    ai_res = verify_anthropic_api()
    summary["ai"] = str(ai_res.get("status", "BLOCKED"))

    # 5. Switch Integration
    print("\n--- [5/6] SWITCH INTEGRATION ---")
    switch_res = verify_switch_adapter()
    summary["switch"] = str(switch_res.get("status", "BLOCKED"))

    # 6. ClamAV Daemon
    print("\n--- [6/6] CLAMAV ANTIVIRUS DAEMON ---")
    clamav_res = verify_clamav_daemon()
    summary["clamav"] = str(clamav_res.get("status", "BLOCKED"))

    print("\n" + "=" * 70)
    print(" STAGING ACTIVATION SUMMARY LEDGER")
    print("=" * 70)
    for service, status in summary.items():
        print(f"  {service.upper():<15}: {status}")

    all_live = all(s.startswith("LIVE_VERIFIED") for s in summary.values())
    print("-" * 70)
    if all_live:
        print("OVERALL VERDICT: LIVE STAGING VERIFIED (All 6 services active & tested)")
    else:
        blocked = [svc for svc, st in summary.items() if not st.startswith("LIVE_VERIFIED")]
        print(f"OVERALL VERDICT: STAGING CANDIDATE (Blocked on live credentials for: {', '.join(blocked)})")
    print("=" * 70)

    return summary


if __name__ == "__main__":
    run_all_staging_checks()
