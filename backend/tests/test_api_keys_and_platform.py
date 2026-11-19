import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError
from sqlalchemy import select, text

from app.core.config import Settings
from app.db.session import SessionLocal
from app.main import app
from app.models import ApiKey, RequestLog
from tests.conftest import auth, first_org, register


def mkkey(client, t, env="test", name="backend"):
    org = first_org(client, t)
    return org, client.post(f"/api/v1/organizations/{org['id']}/api-keys", json={"name": name, "env": env}, headers=auth(t)).json()


def test_key_secret_is_shown_once_and_only_its_hash_is_stored(client):
    t = register(client)
    org, key = mkkey(client, t, "live")
    assert key["secret"].startswith("fv_live_") and key["prefix"] == key["secret"][:12] and key["last4"] == key["secret"][-4:]
    listed = client.get(f"/api/v1/organizations/{org['id']}/api-keys", headers=auth(t))
    assert key["secret"] not in listed.text and "secret" not in listed.json()[0]
    with SessionLocal() as db:
        row = db.scalar(select(ApiKey))
        assert len(row.key_hash) == 64 and row.key_hash != key["secret"]
        assert db.execute(text("select count(*) from freda_verify.api_keys where key_hash = :s or name = :s or prefix = :s"), {"s": key["secret"]}).scalar() == 0


def test_key_authentication_revocation_and_last_used(client):
    t = register(client)
    org, key = mkkey(client, t)
    h = {"Authorization": f"Bearer {key['secret']}"}
    assert client.get("/api/v1/organizations", headers=h).status_code == 200
    with SessionLocal() as db:
        assert db.scalar(select(ApiKey.last_used_at)) is not None
    assert client.get("/api/v1/organizations", headers={"Authorization": "Bearer fv_test_doesnotexist"}).status_code == 401
    assert client.delete(f"/api/v1/organizations/{org['id']}/api-keys/{key['id']}", headers=auth(t)).status_code == 204
    assert client.get("/api/v1/organizations", headers=h).status_code == 401
    assert client.delete(f"/api/v1/organizations/{org['id']}/api-keys/{key['id']}", headers=auth(t)).status_code == 204   # idempotent


def test_api_keys_are_rate_limited(client, monkeypatch):
    from app.core.config import get_settings
    monkeypatch.setattr(get_settings(), "api_rate_limit", 5)
    t = register(client)
    _, key = mkkey(client, t)
    codes = [client.get("/api/v1/organizations", headers={"Authorization": f"Bearer {key['secret']}"}).status_code for _ in range(8)]
    assert codes[:5] == [200] * 5 and 429 in codes[5:]


def test_requests_are_logged_without_bodies_or_secrets(client):
    t = register(client)
    org, key = mkkey(client, t)
    client.get("/api/v1/usage", headers={"Authorization": f"Bearer {key['secret']}"})
    with SessionLocal() as db:
        rows = db.scalars(select(RequestLog).where(RequestLog.organization_id == org["id"])).all()
        assert any(r.path == "/api/v1/usage" and r.api_key_id is not None and r.status == 200 for r in rows)
        dump = " ".join(f"{r.path} {r.request_id}" for r in db.scalars(select(RequestLog)).all())
        assert key["secret"] not in dump and "correct horse" not in dump
    usage = client.get("/api/v1/usage", headers={"Authorization": f"Bearer {key['secret']}"}).json()
    assert usage["requests"] >= 1 and usage["period_days"] == 30


def test_errors_are_structured_and_carry_a_request_id(client):
    r = client.get("/api/v1/does-not-exist")
    body = r.json()["error"]
    assert r.status_code == 404 and body["code"] == "not_found" and body["request_id"] == r.headers["X-Request-ID"]
    v = client.post("/api/v1/auth/login", json={"email": "not-an-email", "password": "secret-password-value", "extra": 1})
    assert v.status_code == 422 and v.json()["error"]["code"] == "validation_error"
    assert "secret-password-value" not in v.text                            # submitted values are never echoed
    assert client.get("/api/v1/auth/me", headers={"X-Request-ID": "trace-abc-12345"}).headers["X-Request-ID"] == "trace-abc-12345"
    assert client.get("/api/v1/auth/me", headers={"X-Request-ID": "bad id with spaces!"}).headers["X-Request-ID"] != "bad id with spaces!"


def test_unhandled_errors_do_not_leak_details():
    @app.get("/__boom")
    def boom():
        raise RuntimeError("secret internals")
    with TestClient(app, raise_server_exceptions=False) as c:
        r = c.get("/__boom")
    assert r.status_code == 500 and r.json()["error"]["code"] == "internal_error" and "secret internals" not in r.text


def test_security_headers_health_and_cors(client):
    r = client.get("/health")
    assert r.json() == {"status": "ok"} and r.headers["X-Content-Type-Options"] == "nosniff" and r.headers["X-Frame-Options"] == "DENY"
    assert client.get("/health/ready").json() == {"status": "ready"}
    ok = client.options("/api/v1/auth/login", headers={"Origin": "https://app.example.test", "Access-Control-Request-Method": "POST"})
    bad = client.options("/api/v1/auth/login", headers={"Origin": "https://evil.example", "Access-Control-Request-Method": "POST"})
    assert ok.headers.get("access-control-allow-origin") == "https://app.example.test"
    assert "access-control-allow-origin" not in bad.headers


def test_prod_refuses_to_start_without_real_secrets():
    base = {"app_env": "prod", "database_url": "postgresql+psycopg://x@y/z"}
    with pytest.raises(ValidationError):
        Settings(**base)
    with pytest.raises(ValidationError):
        Settings(**base, secret_key="short", encryption_key="k")
    with pytest.raises(ValidationError):
        Settings(**base, secret_key="x" * 40, encryption_key="y" * 32, cors_origins=["*"])
    assert Settings(**base, secret_key="x" * 40, encryption_key="y" * 32).app_env == "prod"
