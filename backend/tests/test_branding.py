import pytest

from tests.conftest import auth, first_org, register

GOOD = {"name": "Acme", "color": "#7A3FF2", "theme": "dark", "shape": "pill", "lang": "fr", "title": "Hi", "subtitle": "Welcome",
        "support_email": "help@acme.example", "docs": ["id", "passport"], "redirect_url": "https://acme.example/done", "domain": "verify.acme.example", "hide_powered": True}


def url(org):
    return f"/api/v1/organizations/{org['id']}/branding"


def test_defaults_then_save_and_read_back(client):
    t = register(client)
    org = first_org(client, t)
    d = client.get(url(org), headers=auth(t)).json()
    assert d["name"] == "" and d["color"] == "#1E4FE0" and d["docs"] == ["id", "passport"]
    r = client.put(url(org), json=GOOD, headers=auth(t))
    assert r.status_code == 200, r.text
    got = client.get(url(org), headers=auth(t)).json()
    assert {k: got[k] for k in GOOD} == GOOD and got["updated_at"]


@pytest.mark.parametrize("bad", [
    {"color": "red"}, {"color": "#12345"}, {"theme": "neon"}, {"lang": "es"}, {"docs": []}, {"docs": ["visa"]},
    {"redirect_url": "http://acme.example"}, {"redirect_url": "javascript:alert(1)"}, {"redirect_url": 'https://a.example/"><script>'},
    {"domain": "not a host"}, {"domain": "localhost"}, {"support_email": "nope"}, {"name": "x" * 41}, {"unknown": 1},
])
def test_invalid_input_is_rejected(client, bad):
    t = register(client)
    org = first_org(client, t)
    assert client.put(url(org), json={**GOOD, **bad}, headers=auth(t)).status_code == 422


def test_uppercase_domain_is_rejected_and_change_is_audited(client):
    t = register(client)
    org = first_org(client, t)
    assert client.put(url(org), json={**GOOD, "domain": "Verify.ACME.example"}, headers=auth(t)).status_code == 422
    assert client.put(url(org), json=GOOD, headers=auth(t)).status_code == 200
    actions = [a["action"] for a in client.get(f"/api/v1/organizations/{org['id']}/audit-logs", headers=auth(t)).json()]
    assert "branding.updated" in actions


def test_other_tenant_cannot_read_or_write(client):
    a = register(client, "a@a.example", "Org A")
    b = register(client, "b@b.example", "Org B")
    org_b = first_org(client, b)
    assert client.get(url(org_b), headers=auth(a)).status_code == 404
    assert client.put(url(org_b), json=GOOD, headers=auth(a)).status_code == 404


def test_viewer_can_read_but_not_write(client):
    owner = register(client, "o@o.example", "Org O")
    org = first_org(client, owner)
    register(client, "v@v.example", "Org V")
    assert client.post(f"/api/v1/organizations/{org['id']}/members", json={"email": "v@v.example", "role": "viewer"}, headers=auth(owner)).status_code in (200, 201)
    from tests.conftest import PASSWORD
    tok = client.post("/api/v1/auth/login", json={"email": "v@v.example", "password": PASSWORD}).json()
    assert client.get(url(org), headers=auth(tok)).status_code == 200
    assert client.put(url(org), json=GOOD, headers=auth(tok)).status_code == 403


def test_api_keys_cannot_use_dashboard_branding_route(client):
    t = register(client)
    org = first_org(client, t)
    k = client.post(f"/api/v1/organizations/{org['id']}/api-keys", json={"name": "k", "env": "test"}, headers=auth(t)).json()
    assert client.get(url(org), headers={"Authorization": f"Bearer {k['secret']}"}).status_code in (401, 403)


def test_cors_preflight_allows_put_from_the_app_origin(client):
    r = client.options("/api/v1/organizations/00000000-0000-0000-0000-000000000000/branding",
                       headers={"Origin": "https://app.example.test", "Access-Control-Request-Method": "PUT", "Access-Control-Request-Headers": "authorization,content-type"})
    assert r.status_code == 200 and "PUT" in r.headers["access-control-allow-methods"]
