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
