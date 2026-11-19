from datetime import timedelta

import pyotp
from sqlalchemy import select

from app.core.security import sha256
from app.db.session import SessionLocal
from app.models import PasswordResetToken, User, now
from tests.conftest import PASSWORD, auth, register


def login(client, email="owner@example.com", password=PASSWORD):
    return client.post("/api/v1/auth/login", json={"email": email, "password": password})


def test_register_login_me(client):
    t = register(client)
    assert t["token_type"] == "bearer" and t["user"]["email"] == "owner@example.com"
    assert client.get("/api/v1/auth/me", headers=auth(t)).json()["full_name"] == "Test User"
    assert login(client).status_code == 200
    assert login(client, "OWNER@example.com").status_code == 200          # e-mail is case-insensitive


def test_register_creates_org_with_owner_role(client):
    t = register(client)
    orgs = client.get("/api/v1/organizations", headers=auth(t)).json()
    assert len(orgs) == 1 and orgs[0]["role"] == "owner" and orgs[0]["name"] == "Acme Bank"


def test_duplicate_email_and_weak_password(client):
    register(client)
    r = client.post("/api/v1/auth/register", json={"email": "owner@example.com", "password": PASSWORD, "full_name": "x", "organization_name": "Other"})
    assert r.status_code == 409 and r.json()["error"]["code"] == "email_taken"
    w = client.post("/api/v1/auth/register", json={"email": "new@example.com", "password": "short", "full_name": "x", "organization_name": "Other"})
    assert w.status_code == 422 and w.json()["error"]["code"] == "weak_password"
    assert "short" not in w.text.replace("must be at least", "")           # the submitted password is never echoed back


def test_password_is_stored_hashed_with_argon2(client):
    register(client)
    with SessionLocal() as db:
        u = db.scalar(select(User))
        assert u.password_hash.startswith("$argon2id$") and PASSWORD not in u.password_hash


def test_wrong_password_and_unknown_user_look_identical(client):
    register(client)
    a = login(client, password="wrong password here")
    b = login(client, email="nobody@example.com")
    assert a.status_code == b.status_code == 401
    assert a.json()["error"]["message"] == b.json()["error"]["message"]


def test_account_locks_after_repeated_failures(client):
    register(client)
    for _ in range(5):
        assert login(client, password="wrong password here").status_code == 401
    r = login(client)                                                       # even the right password is refused while locked
    assert r.status_code == 429 and "Retry-After" in r.headers


def test_credential_endpoints_are_rate_limited(client):
    codes = [client.post("/api/v1/auth/login", json={"email": f"u{i}@example.com", "password": "whatever password"}).status_code for i in range(14)]
    assert 429 in codes and codes[0] == 401


def test_refresh_rotation_and_reuse_detection(client):
    t = register(client)
    r1 = client.post("/api/v1/auth/refresh", json={"refresh_token": t["refresh_token"]})
    assert r1.status_code == 200 and r1.json()["refresh_token"] != t["refresh_token"]
    # replaying the OLD token signals theft: it is refused and every session of the user is revoked
    assert client.post("/api/v1/auth/refresh", json={"refresh_token": t["refresh_token"]}).status_code == 401
    assert client.post("/api/v1/auth/refresh", json={"refresh_token": r1.json()["refresh_token"]}).status_code == 401


def test_logout_revokes_the_refresh_token(client):
    t = register(client)
    assert client.post("/api/v1/auth/logout", json={"refresh_token": t["refresh_token"]}).status_code == 204
    assert client.post("/api/v1/auth/refresh", json={"refresh_token": t["refresh_token"]}).status_code == 401


def test_invalid_tokens_are_rejected(client):
    assert client.get("/api/v1/auth/me").status_code == 401
    assert client.get("/api/v1/auth/me", headers={"Authorization": "Bearer nonsense"}).status_code == 401
    t = register(client)
    tampered = t["access_token"][:-3] + ("AAA" if not t["access_token"].endswith("AAA") else "BBB")
    assert client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {tampered}"}).status_code == 401
    # a refresh token / mfa token is not an access token
    assert client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {t['refresh_token']}"}).status_code == 401


def test_password_reset_flow(client):
    t = register(client)
    unknown = client.post("/api/v1/auth/password/forgot", json={"email": "nobody@example.com"})
    known = client.post("/api/v1/auth/password/forgot", json={"email": "owner@example.com"})
    assert unknown.status_code == known.status_code == 202 and unknown.json() == known.json()
    with SessionLocal() as db:                                              # the token is only ever stored hashed: plant a known one
        uid = db.scalar(select(User.id))
        db.add(PasswordResetToken(user_id=uid, token_hash=sha256("known-reset-token"), expires_at=now() + timedelta(minutes=30)))
        db.commit()
    new = "a brand new passphrase"
    assert client.post("/api/v1/auth/password/reset", json={"token": "known-reset-token", "new_password": new}).status_code == 204
    assert login(client).status_code == 401 and login(client, password=new).status_code == 200
    assert client.post("/api/v1/auth/refresh", json={"refresh_token": t["refresh_token"]}).status_code == 401   # old sessions revoked
    assert client.post("/api/v1/auth/password/reset", json={"token": "known-reset-token", "new_password": "another passphrase!"}).status_code == 400   # single use


def test_expired_reset_token_is_refused(client):
    register(client)
    with SessionLocal() as db:
        db.add(PasswordResetToken(user_id=db.scalar(select(User.id)), token_hash=sha256("old"), expires_at=now() - timedelta(minutes=1)))
        db.commit()
    assert client.post("/api/v1/auth/password/reset", json={"token": "old", "new_password": "a brand new passphrase"}).status_code == 400


def test_mfa_enrolment_login_replay_and_recovery(client):
    t = register(client)
    setup = client.post("/api/v1/auth/mfa/setup", headers=auth(t)).json()
    totp = pyotp.TOTP(setup["secret"])
    with SessionLocal() as db:                                              # the TOTP secret is encrypted at rest
        assert setup["secret"] not in (db.scalar(select(User.mfa_secret_enc)) or "")
    assert client.post("/api/v1/auth/mfa/enable", json={"code": "000000"}, headers=auth(t)).status_code == 400
    enabled = client.post("/api/v1/auth/mfa/enable", json={"code": totp.now()}, headers=auth(t))
    assert enabled.status_code == 200 and len(enabled.json()["recovery_codes"]) == 8
    codes = enabled.json()["recovery_codes"]

    step = login(client)                                                    # password alone no longer gives tokens
    assert step.json().get("mfa_required") is True and "access_token" not in step.json()
    mfa_token = step.json()["mfa_token"]
    now_code = totp.at(now() + timedelta(seconds=30))                       # next step: the enrolment step is already consumed
    assert client.post("/api/v1/auth/mfa/verify", json={"mfa_token": mfa_token, "code": "123456"}).status_code == 401
    ok = client.post("/api/v1/auth/mfa/verify", json={"mfa_token": mfa_token, "code": now_code})
    assert ok.status_code == 200 and "access_token" in ok.json()
    # the same code cannot be used twice (replay)
    again = client.post("/api/v1/auth/mfa/verify", json={"mfa_token": login(client).json()["mfa_token"], "code": now_code})
    assert again.status_code == 401
    # a recovery code works once
    rc = client.post("/api/v1/auth/mfa/verify", json={"mfa_token": login(client).json()["mfa_token"], "code": codes[0]})
    assert rc.status_code == 200
    assert client.post("/api/v1/auth/mfa/verify", json={"mfa_token": login(client).json()["mfa_token"], "code": codes[0]}).status_code == 401


def test_mfa_token_cannot_be_used_as_access_token(client):
    t = register(client)
    secret = client.post("/api/v1/auth/mfa/setup", headers=auth(t)).json()["secret"]
    client.post("/api/v1/auth/mfa/enable", json={"code": pyotp.TOTP(secret).now()}, headers=auth(t))
    mfa_token = login(client).json()["mfa_token"]
    assert client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {mfa_token}"}).status_code == 401
