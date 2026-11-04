"""Token validation: valid/invalid/expired/wrong issuer/audience/membership/account."""
from __future__ import annotations

import time
import uuid

import jwt

from app.core.config import get_settings
from app.core.security import mint_dev_token
from tests.conftest import auth_headers, make_project, make_user


def test_missing_token(client):
    assert client.get("/api/v1/auth/me").status_code == 401


def test_garbage_token(client):
    r = client.get("/api/v1/auth/me", headers={"Authorization": "Bearer not-a-jwt"})
    assert r.status_code == 401
    assert r.json()["error"]["code"] == "invalid_token"


def test_valid_token_and_memberships(client, db):
    owner = make_user(db, "me@example.com", "Me Owner")
    project = make_project(db, owner)
    r = client.get("/api/v1/auth/me", headers=auth_headers(owner))
    assert r.status_code == 200
    body = r.json()
    assert body["email"] == "me@example.com"
    assert body["memberships"][0]["project_id"] == str(project.id)
    assert body["memberships"][0]["role"] == "project_owner"


def test_expired_token(client, db):
    owner = make_user(db, "exp@example.com")
    token = mint_dev_token(user_id=owner.provider_user_id, email=owner.email,
                           full_name=owner.full_name, ttl_seconds=-10)
    r = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 401
    assert r.json()["error"]["code"] == "token_expired"


def test_wrong_audience(client, db):
    owner = make_user(db, "aud@example.com")
    s = get_settings()
    now = int(time.time())
    token = jwt.encode({"sub": owner.provider_user_id, "email": owner.email, "name": "A",
                        "iss": s.auth_issuer, "aud": "somebody-else", "iat": now, "exp": now + 600},
                       s.auth_dev_secret, algorithm="HS256")
    r = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 401


def test_wrong_issuer(client, db):
    owner = make_user(db, "iss@example.com")
    s = get_settings()
    now = int(time.time())
    token = jwt.encode({"sub": owner.provider_user_id, "email": owner.email, "name": "A",
                        "iss": "not-us", "aud": s.auth_audience, "iat": now, "exp": now + 600},
                       s.auth_dev_secret, algorithm="HS256")
    r = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 401


def test_tampered_signature(client, db):
    owner = make_user(db, "sig@example.com")
    token = mint_dev_token(user_id=owner.provider_user_id, email=owner.email,
                           full_name=owner.full_name)
    head, payload, _sig = token.split(".")
    forged = f"{head}.{payload}.{'A' * 43}"
    r = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {forged}"})
    assert r.status_code == 401


def test_suspended_account_rejected(client, db):
    owner = make_user(db, "susp@example.com")
    owner.account_status = "suspended"
    db.commit()
    r = client.get("/api/v1/auth/me", headers=auth_headers(owner))
    assert r.status_code == 403
    assert r.json()["error"]["code"] == "account_inactive"


def test_unknown_user_rejected(client):
    s = get_settings()
    now = int(time.time())
    token = jwt.encode({"sub": str(uuid.uuid4()), "email": "ghost@example.com", "name": "Ghost",
                        "iss": s.auth_issuer, "aud": s.auth_audience, "iat": now, "exp": now + 600},
                       s.auth_dev_secret, algorithm="HS256")
    r = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 401
    assert r.json()["error"]["code"] == "user_not_provisioned"


def test_production_rejects_dev_tokens():
    """R-006: In APP_ENV=production, AUTH_PROVIDER=dev must fail boot unconditionally."""
    import pytest

    from app.core.config import Settings
    with pytest.raises(ValueError) as exc:
        Settings(
            app_env="production",
            auth_provider="dev",
            database_url="postgresql+psycopg://u:p@127.0.0.1:5432/db",
            app_encryption_key="T_kDLwS1SAGcgyw6ZCdioTJFcVd9ysp9_Lvobogn8nI=",
        )
    assert "AUTH_PROVIDER=dev is not permitted in APP_ENV=production" in str(exc.value)


def test_supabase_jwks_offline_verification(monkeypatch):
    """R-007: Supabase token verification using PyJWKClient and RSA256 signature."""

    from cryptography.hazmat.primitives import serialization
    from cryptography.hazmat.primitives.asymmetric import rsa

    from app.core.config import Settings
    from app.core.security import _decode_supabase

    private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    public_pem = private_key.public_key().public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo,
    ).decode("ascii")

    class MockSigningKey:
        key = public_pem

    class MockJWKClient:
        def __init__(self, *args, **kwargs):
            pass
        def get_signing_key_from_jwt(self, token):
            return MockSigningKey()

    import app.core.security as sec_mod
    monkeypatch.setattr(sec_mod.jwt, "PyJWKClient", MockJWKClient)
    sec_mod._jwks_clients.clear()

    settings = Settings(
        app_env="staging",
        auth_provider="supabase",
        supabase_url="https://xyzcompany.supabase.co",
        supabase_anon_key="anon-key",
        auth_audience="authenticated",
        database_url="postgresql+psycopg://u:p@127.0.0.1:5432/db",
        app_encryption_key="T_kDLwS1SAGcgyw6ZCdioTJFcVd9ysp9_Lvobogn8nI=",
    )

    now = int(time.time())
    claims = {
        "sub": "b2c019d4-6df5-40ea-92b8-932d8816b8b9",
        "email": "user@supabase.test",
        "iss": "https://xyzcompany.supabase.co/auth/v1",
        "aud": "authenticated",
        "iat": now,
        "exp": now + 3600,
        "user_metadata": {"full_name": "Supabase User"},
    }
    private_pem = private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    )
    token = jwt.encode(claims, private_pem, algorithm="RS256", headers={"kid": "mock-key-1"})

    token_claims = _decode_supabase(token, settings)
    assert token_claims.provider == "supabase"
    assert token_claims.subject == "b2c019d4-6df5-40ea-92b8-932d8816b8b9"
    assert token_claims.email == "user@supabase.test"
    assert token_claims.full_name == "Supabase User"


def test_membership_revocation_effective_immediately(client, db):
    # 1. Setup owner and editor
    owner = make_user(db, "owner_revoc@example.com", "Project Owner")
    editor = make_user(db, "editor_revoc@example.com", "Project Editor")
    project = make_project(db, owner, title="Revocation Test Project")

    # 2. Owner adds editor via API
    res = client.post(
        f"/api/v1/projects/{project.id}/members",
        json={"email": editor.email, "role": "editor"},
        headers=auth_headers(owner),
    )
    assert res.status_code == 201
    membership_id = res.json()["id"]

    # 3. Editor can access project
    res = client.get(f"/api/v1/projects/{project.id}", headers=auth_headers(editor))
    assert res.status_code == 200

    # 4. Owner revokes membership
    del_res = client.delete(
        f"/api/v1/projects/{project.id}/members/{membership_id}",
        headers=auth_headers(owner),
    )
    assert del_res.status_code == 204

    # 5. Editor is immediately blocked (404 Not Found to prevent oracle leak)
    res = client.get(f"/api/v1/projects/{project.id}", headers=auth_headers(editor))
    assert res.status_code == 404



