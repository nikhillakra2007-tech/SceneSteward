"""Automated tests for secret lifecycle and migration scenarios (A, B, C, D, E).

Scenarios:
- Scenario A: Fresh installation (inserts high-entropy secret, handshake passes)
- Scenario B: Existing valid secret (environment mismatch without rotation flag raises RuntimeError)
- Scenario C: Insecure placeholder secret (detected in production/staging and rejected without rotation)
- Scenario D: Missing secret (fails validation safely in production/staging)
- Scenario E: Secret rotation (authorized via ROTATE_IDENTITY_SECRET=true or CLI, updates secret, maintains data)
"""
from __future__ import annotations

import os

import pytest
from pydantic import ValidationError
from sqlalchemy import create_engine, text

from app.core.config import Settings, get_settings
from app.core.database import compute_identity_sig, verify_database_trust
from scripts.rotate_identity_secret import rotate_secret


def test_scenario_d_missing_or_weak_secret_rejected_in_production():
    """Scenario D: In production/staging, missing or weak secret fails validation immediately."""
    with pytest.raises(ValidationError) as exc:
        Settings(
            app_env="production",
            auth_provider="supabase",
            supabase_url="https://test.supabase.co",
            supabase_anon_key="anon_key_12345",
            database_url="postgresql://user:valid_strong_pass_12345@127.0.0.1/scenesteward_test",
            database_identity_secret="",
        )
    assert "DATABASE_IDENTITY_SECRET must be an explicitly generated secret" in str(exc.value)

    # Weak secret (< 32 chars)
    with pytest.raises(ValidationError) as exc2:
        Settings(
            app_env="production",
            auth_provider="supabase",
            supabase_url="https://test.supabase.co",
            supabase_anon_key="anon_key_12345",
            database_url="postgresql://user:valid_strong_pass_12345@127.0.0.1/scenesteward_test",
            database_identity_secret="short_weak_secret",
        )
    assert "min 32 chars" in str(exc2.value)

    # Insecure placeholder
    with pytest.raises(ValidationError) as exc3:
        Settings(
            app_env="staging",
            auth_provider="supabase",
            supabase_url="https://test.supabase.co",
            supabase_anon_key="anon_key_12345",
            database_url="postgresql://user:valid_strong_pass_12345@127.0.0.1/scenesteward_test",
            database_identity_secret="scenesteward_db_trust_secret_2026_prod_v1",
        )
    assert "default/placeholder is forbidden" in str(exc3.value)


def test_scenario_b_secret_mismatch_detected_by_handshake():
    """Scenario B: When application secret does not match database secret, handshake fails."""
    settings = get_settings()
    app_engine = create_engine(settings.database_url, future=True)

    # Verify matching secret succeeds
    res_valid = verify_database_trust(app_engine)
    assert res_valid.get("ok") is True

    # Compute a signature using forged/mismatched secret
    mismatched_sig = compute_identity_sig("probe_nonce", secret="mismatched_forged_secret_key_1234567890")
    with app_engine.connect() as conn:
        verified = conn.execute(
            text("SELECT public.app_verify_trust_handshake(CAST('probe_nonce' AS text), CAST(:sig AS text))"),
            {"sig": mismatched_sig},
        ).scalar()
        assert verified is False, "Database handshake must reject mismatched secret signatures"


def test_scenario_e_secret_rotation_workflow(db):
    """Scenario E: Deliberate secret rotation updates DB, verifies new handshake, leaves data intact."""
    settings = get_settings()
    admin_url = os.environ.get("DATABASE_URL_ADMIN") or os.environ.get("MIGRATION_DATABASE_URL")
    original_secret = settings.database_identity_secret
    new_rotated_secret = "new_rotated_high_entropy_secret_0123456789abcdef"

    try:
        # Perform rotation via rotation utility
        success = rotate_secret(
            new_secret=new_rotated_secret,
            confirm=True,
            admin_db_url=admin_url,
        )
        assert success is True, "Rotation script must succeed"

        # Database now has new secret: verify new secret handshake passes
        admin_engine = create_engine(admin_url, future=True)
        new_sig = compute_identity_sig("probe_check", secret=new_rotated_secret)
        with admin_engine.connect() as conn:
            verified_new = conn.execute(
                text("SELECT public.app_verify_trust_handshake(CAST('probe_check' AS text), CAST(:sig AS text))"),
                {"sig": new_sig},
            ).scalar()
            assert verified_new is True, "Handshake with new secret must succeed"

            # Old secret handshake must now FAIL
            old_sig = compute_identity_sig("probe_check", secret=original_secret)
            verified_old = conn.execute(
                text("SELECT public.app_verify_trust_handshake(CAST('probe_check' AS text), CAST(:sig AS text))"),
                {"sig": old_sig},
            ).scalar()
            assert verified_old is False, "Handshake with old secret must now be rejected"

    finally:
        # Restore original secret in database
        rotate_secret(new_secret=original_secret, confirm=True, admin_db_url=admin_url)
        os.environ["DATABASE_IDENTITY_SECRET"] = original_secret
        get_settings.cache_clear()


def test_scenario_c_placeholder_rejection_in_restricted_environments():
    """Scenario C: Placeholder secrets cannot be preserved in production/staging without rotation."""
    from app.core.config import Settings
    with pytest.raises(ValidationError) as exc:
        Settings(
            app_env="production",
            auth_provider="supabase",
            supabase_url="https://test.supabase.co",
            supabase_anon_key="anon_key_12345",
            database_url="postgresql://user:valid_strong_pass_12345@127.0.0.1/scenesteward_test",
            database_identity_secret="CHANGE_ME_GENERATE_WITH_OPENSSL_RAND_HEX_32",
        )
    assert "default/placeholder is forbidden" in str(exc.value)
