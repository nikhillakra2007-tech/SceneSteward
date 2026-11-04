"""Unit tests for encryption at rest, key ring rotation, and signed URLs."""
from __future__ import annotations

import json

import pytest
from cryptography.fernet import Fernet

from app.core.config import Settings
from app.core.exceptions import PreconditionFailed, Unauthenticated
from app.core.security import decrypt_secret, encrypt_secret
from app.integrations.storage import signed
from app.models.participants import Participant, ParticipantContactRecord
from scripts.rotate_encryption_keys import rotate_keys
from tests.conftest import make_project, make_user


@pytest.fixture()
def key_ring():
    key1 = Fernet.generate_key().decode()
    key2 = Fernet.generate_key().decode()
    return {"key1": key1, "key2": key2}


def test_encrypt_decrypt_versioned(key_ring):
    settings = Settings(
        app_env="test",
        database_url="postgresql+psycopg://u:p@127.0.0.1:5432/db",
        app_encryption_current_kid="key1",
        app_encryption_keys=json.dumps(key_ring),
    )
    secret = "+1-555-0199"
    ciphertext = encrypt_secret(secret, settings=settings)
    assert ciphertext.startswith("v2.key1.")
    assert decrypt_secret(ciphertext, settings=settings) == secret


def test_decrypt_legacy_unversioned(key_ring):
    # Old records stored plain Fernet token without v2 prefix
    f = Fernet(key_ring["key1"].encode())
    legacy_ciphertext = f.encrypt(b"secret-contact@example.com").decode("ascii")
    assert not legacy_ciphertext.startswith("v2.")

    settings = Settings(
        app_env="test",
        database_url="postgresql+psycopg://u:p@127.0.0.1:5432/db",
        app_encryption_current_kid="key2",
        app_encryption_keys=json.dumps(key_ring),
    )
    # Even when current_kid is key2, the key ring retains key1, so legacy decryption succeeds
    decrypted = decrypt_secret(legacy_ciphertext, settings=settings)
    assert decrypted == "secret-contact@example.com"


def test_multi_key_decryption(key_ring):
    settings = Settings(
        app_env="test",
        database_url="postgresql+psycopg://u:p@127.0.0.1:5432/db",
        app_encryption_current_kid="key1",
        app_encryption_keys=json.dumps(key_ring),
    )
    c1 = encrypt_secret("data-1", settings=settings, kid="key1")
    c2 = encrypt_secret("data-2", settings=settings, kid="key2")

    assert c1.startswith("v2.key1.")
    assert c2.startswith("v2.key2.")

    assert decrypt_secret(c1, settings=settings) == "data-1"
    assert decrypt_secret(c2, settings=settings) == "data-2"


def test_tampered_ciphertext_fails_closed(key_ring):
    settings = Settings(
        app_env="test",
        database_url="postgresql+psycopg://u:p@127.0.0.1:5432/db",
        app_encryption_current_kid="key1",
        app_encryption_keys=json.dumps(key_ring),
    )
    c = encrypt_secret("sensitive data", settings=settings)
    tampered = c[:-4] + "xxxx"
    with pytest.raises(Unauthenticated) as exc:
        decrypt_secret(tampered, settings=settings)
    assert exc.value.code == "encryption_failed"


def test_unknown_kid_fails_closed(key_ring):
    settings = Settings(
        app_env="test",
        database_url="postgresql+psycopg://u:p@127.0.0.1:5432/db",
        app_encryption_current_kid="key1",
        app_encryption_keys=json.dumps({"key1": key_ring["key1"]}),
    )
    # v2 ciphertext signed with an unknown kid
    with pytest.raises(Unauthenticated) as exc:
        decrypt_secret("v2.unknown_kid.gAAAAAB...", settings=settings)
    assert exc.value.code == "encryption_failed"


def test_signed_storage_tokens(monkeypatch, key_ring):
    settings = Settings(
        app_env="test",
        database_url="postgresql+psycopg://u:p@127.0.0.1:5432/db",
        app_encryption_current_kid="key1",
        app_encryption_keys=json.dumps(key_ring),
    )
    monkeypatch.setattr("app.integrations.storage.signed.get_settings", lambda: settings)

    token = signed.issue_token(
        storage_key="proj/part/doc.pdf",
        purpose="download",
        ttl_seconds=300,
        extra={"project_id": "p1"},
    )
    payload = signed.verify_token(token, purpose="download")
    assert payload["key"] == "proj/part/doc.pdf"
    assert payload["project_id"] == "p1"
    assert payload["kid"] == "key1"

    # Purpose mismatch
    with pytest.raises(PreconditionFailed):
        signed.verify_token(token, purpose="upload")

    # Tampered signature
    body, sig = token.split(".", 1)
    bad_sig = "a" * len(sig)
    with pytest.raises(PreconditionFailed):
        signed.verify_token(f"{body}.{bad_sig}", purpose="download")

    # Expired token
    expired_token = signed.issue_token(
        storage_key="proj/part/doc.pdf",
        purpose="download",
        ttl_seconds=-10,
    )
    with pytest.raises(PreconditionFailed):
        signed.verify_token(expired_token, purpose="download")


def test_rotate_encryption_keys_script(db, monkeypatch, key_ring):
    owner = make_user(db, "owner_rot@example.com")
    project = make_project(db, owner)

    part = Participant(project_id=project.id, display_name="Participant Key Rot")
    db.add(part)
    db.flush()

    # Create record with key1
    settings = Settings(
        app_env="test",
        database_url=str(db.bind.url),
        app_encryption_current_kid="key1",
        app_encryption_keys=json.dumps(key_ring),
    )
    monkeypatch.setattr("scripts.rotate_encryption_keys.get_settings", lambda: settings)
    monkeypatch.setattr("app.core.security.get_settings", lambda: settings)

    ct1 = encrypt_secret("123-456-7890", settings=settings, kid="key1")
    rec = ParticipantContactRecord(
        participant_id=part.id,
        contact_type="phone",
        encrypted_contact_data=ct1,
    )
    db.add(rec)
    db.commit()

    assert ct1.startswith("v2.key1.")

    # Now rotate to key2
    settings2 = Settings(
        app_env="test",
        database_url=str(db.bind.url),
        app_encryption_current_kid="key2",
        app_encryption_keys=json.dumps(key_ring),
    )
    monkeypatch.setattr("scripts.rotate_encryption_keys.get_settings", lambda: settings2)
    monkeypatch.setattr("app.core.security.get_settings", lambda: settings2)

    # Dry run
    dry_count = rotate_keys(target_kid="key2", dry_run=True, session=db)
    assert dry_count == 1
    db.refresh(rec)
    assert rec.encrypted_contact_data == ct1  # unchanged

    # Real rotation
    count = rotate_keys(target_kid="key2", dry_run=False, session=db)
    assert count == 1

    db.refresh(rec)
    assert rec.encrypted_contact_data.startswith("v2.key2.")
    assert decrypt_secret(rec.encrypted_contact_data, settings=settings2) == "123-456-7890"
