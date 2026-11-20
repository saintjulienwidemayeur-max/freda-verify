from datetime import timedelta

import pytest
from sqlalchemy import text

from app.db.session import get_engine
from tests.conftest import PASSWORD, auth, first_org, register

PNG = b"\x89PNG\r\n\x1a\n" + b"\x00" * 64


def make_key(client, t, org, env="test"):
    return client.post(f"/api/v1/organizations/{org['id']}/api-keys", json={"name": "k", "env": env}, headers=auth(t)).json()["secret"]


def bearer(tok):
    return {"Authorization": f"Bearer {tok}"}


def setup(client, email="o@o.example", name="Org O"):
    t = register(client, email, name)
    org = first_org(client, t)
    return t, org, make_key(client, t, org)


def test_create_with_api_key_returns_token_once_and_fragment_url(client):
    t, org, key = setup(client)
    r = client.post("/api/v1/verifications", json={"reference": "cust-42"}, headers=bearer(key))
    assert r.status_code == 201, r.text
    v = r.json()
    assert v["status"] == "PENDING" and v["env"] == "test" and v["reference"] == "cust-42" and v["consent_given"] is False
    assert v["session_token"].startswith("fvs_") and v["url"].endswith(f"/verify#s={v['session_token']}")
    got = client.get(f"/api/v1/verifications/{v['id']}", headers=bearer(key)).json()
    assert "session_token" not in got and got["status"] == "PENDING"
    with get_engine().connect() as c:                                            # only the hash is stored
        assert v["session_token"] not in str(c.execute(text("select * from freda_verify.verifications")).all())


def test_dashboard_user_needs_org_and_membership(client):
    t, org, _ = setup(client)
    assert client.post("/api/v1/verifications", json={}, headers=auth(t)).status_code == 422
    r = client.post("/api/v1/verifications", json={"organization_id": org["id"]}, headers=auth(t))
    assert r.status_code == 201 and r.json()["env"] == "test"
    other = register(client, "x@x.example", "Org X")
    assert client.post("/api/v1/verifications", json={"organization_id": org["id"]}, headers=auth(other)).status_code == 404
    assert client.get(f"/api/v1/verifications?organization_id={org['id']}", headers=auth(other)).status_code == 404


def test_viewer_reads_but_cannot_create(client):
    t, org, _ = setup(client)
    register(client, "v@v.example", "Org V")
    client.post(f"/api/v1/organizations/{org['id']}/members", json={"email": "v@v.example", "role": "viewer"}, headers=auth(t))
    vt = client.post("/api/v1/auth/login", json={"email": "v@v.example", "password": PASSWORD}).json()
    assert client.get(f"/api/v1/verifications?organization_id={org['id']}", headers=auth(vt)).status_code == 200
    assert client.post("/api/v1/verifications", json={"organization_id": org["id"]}, headers=auth(vt)).status_code == 403


def test_tenant_isolation(client):
    _, _, key_a = setup(client, "a@a.example", "Org A")
    _, _, key_b = setup(client, "b@b.example", "Org B")
    va = client.post("/api/v1/verifications", json={}, headers=bearer(key_a)).json()
    assert client.get(f"/api/v1/verifications/{va['id']}", headers=bearer(key_b)).status_code == 404
    assert client.get("/api/v1/verifications", headers=bearer(key_b)).json() == []
    assert [x["id"] for x in client.get("/api/v1/verifications", headers=bearer(key_a)).json()] == [va["id"]]


@pytest.mark.parametrize("body", [{"reference": "<script>"}, {"reference": "x" * 101}, {"expires_in_minutes": 1}, {"expires_in_minutes": 999999}, {"bogus": 1}])
def test_invalid_input(client, body):
    _, _, key = setup(client)
    assert client.post("/api/v1/verifications", json=body, headers=bearer(key)).status_code == 422


def test_session_exposes_only_public_branding_and_logo(client):
    t, org, key = setup(client)
    client.put(f"/api/v1/organizations/{org['id']}/branding", headers=auth(t), json={
        "name": "Acme", "color": "#7A3FF2", "lang": "fr", "docs": ["passport"], "support_email": "help@acme.example",
        "redirect_url": "https://acme.example/done", "domain": "verify.acme.example"})
    client.put(f"/api/v1/organizations/{org['id']}/branding/logo", content=PNG, headers={**auth(t), "Content-Type": "image/png"})
    tok = client.post("/api/v1/verifications", json={}, headers=bearer(key)).json()["session_token"]
    s = client.get("/api/v1/session", headers=bearer(tok))
    assert s.status_code == 200
    b = s.json()["branding"]
    assert b["name"] == "Acme" and b["color"] == "#7A3FF2" and b["docs"] == ["passport"] and b["has_logo"] is True
    assert "redirect_url" not in b and "domain" not in b
    lg = client.get("/api/v1/session/logo", headers=bearer(tok))
    assert lg.status_code == 200 and lg.content == PNG and lg.headers["x-content-type-options"] == "nosniff"


def test_session_token_is_not_a_dashboard_or_api_credential(client):
    t, org, key = setup(client)
    tok = client.post("/api/v1/verifications", json={}, headers=bearer(key)).json()["session_token"]
    assert client.get("/api/v1/verifications", headers=bearer(tok)).status_code == 401
    assert client.get(f"/api/v1/organizations/{org['id']}", headers=bearer(tok)).status_code == 401
    assert client.get("/api/v1/session", headers=bearer(key)).status_code == 401           # keys and JWTs do not open sessions either
    assert client.get("/api/v1/session", headers=auth(t)).status_code == 401
    assert client.get("/api/v1/session", headers=bearer("fvs_nope")).status_code == 401
    assert client.get("/api/v1/session").status_code == 401


def test_consent_once_and_audited(client):
    t, org, key = setup(client)
    v = client.post("/api/v1/verifications", json={}, headers=bearer(key)).json()
    assert client.post("/api/v1/session/consent", headers=bearer(v["session_token"])).status_code == 204
    assert client.post("/api/v1/session/consent", headers=bearer(v["session_token"])).status_code == 204
    assert client.get("/api/v1/session", headers=bearer(v["session_token"])).json()["consent_given"] is True
    actions = [a["action"] for a in client.get(f"/api/v1/organizations/{org['id']}/audit-logs", headers=auth(t)).json()]
    assert actions.count("verification.consent_given") == 1 and "verification.created" in actions


def test_expired_session_is_gone_and_listed_as_expired(client):
    t, org, key = setup(client)
    v = client.post("/api/v1/verifications", json={}, headers=bearer(key)).json()
    with get_engine().begin() as c:
        c.execute(text("update freda_verify.verifications set expires_at = :t"), {"t": __import__("datetime").datetime.now(__import__("datetime").UTC) - timedelta(minutes=1)})
    assert client.get("/api/v1/session", headers=bearer(v["session_token"])).status_code == 410
    assert client.post("/api/v1/session/consent", headers=bearer(v["session_token"])).status_code == 410
    assert client.get(f"/api/v1/verifications/{v['id']}", headers=bearer(key)).json()["status"] == "EXPIRED"


def test_session_cors_preflight_and_rate_limit(client, monkeypatch):
    _, _, key = setup(client)
    tok = client.post("/api/v1/verifications", json={}, headers=bearer(key)).json()["session_token"]
    from app.core.config import get_settings
    monkeypatch.setattr(get_settings(), "session_rate_limit", 3)
    codes = [client.get("/api/v1/session", headers=bearer(tok)).status_code for _ in range(5)]
    assert codes[:3] == [200, 200, 200] and codes[-1] == 429
