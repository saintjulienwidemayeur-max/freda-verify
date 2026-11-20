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


PNG = b"\x89PNG\r\n\x1a\n" + b"\x00" * 64
WEBP = b"RIFF\x00\x00\x00\x00WEBP" + b"\x00" * 64


def logo_url(org):
    return url(org) + "/logo"


def put_logo(client, t, org, data=PNG, ctype="image/png"):
    return client.put(logo_url(org), content=data, headers={**auth(t), "Content-Type": ctype})


def test_logo_roundtrip_flag_and_delete(client):
    t = register(client)
    org = first_org(client, t)
    assert client.get(url(org), headers=auth(t)).json()["has_logo"] is False
    assert client.get(logo_url(org), headers=auth(t)).status_code == 404
    assert put_logo(client, t, org).status_code == 204
    g = client.get(logo_url(org), headers=auth(t))
    assert g.status_code == 200 and g.content == PNG and g.headers["content-type"] == "image/png" and g.headers["x-content-type-options"] == "nosniff"
    assert client.get(url(org), headers=auth(t)).json()["has_logo"] is True
    assert put_logo(client, t, org, WEBP, "image/webp").status_code == 204          # replace
    assert client.get(logo_url(org), headers=auth(t)).content == WEBP
    assert client.delete(logo_url(org), headers=auth(t)).status_code == 204
    assert client.get(url(org), headers=auth(t)).json()["has_logo"] is False
    actions = [a["action"] for a in client.get(f"/api/v1/organizations/{org['id']}/audit-logs", headers=auth(t)).json()]
    assert "branding.logo_updated" in actions and "branding.logo_deleted" in actions


@pytest.mark.parametrize("data,ctype,code", [
    (b"<svg xmlns='http://www.w3.org/2000/svg'><script>alert(1)</script></svg>", "image/svg+xml", 422),
    (b"<svg/>" + b" " * 64, "image/png", 422),                       # declared PNG, not a PNG
    (b"GIF89a" + b"\x00" * 64, "image/gif", 422),
    (PNG, "text/html", 422),
    (b"", "image/png", 422),
    (PNG + b"\x00" * (512 * 1024), "image/png", 413),
])
def test_bad_logos_are_rejected(client, data, ctype, code):
    t = register(client)
    org = first_org(client, t)
    assert put_logo(client, t, org, data, ctype).status_code == code
    assert client.get(url(org), headers=auth(t)).json()["has_logo"] is False


def test_logo_is_tenant_isolated_and_viewer_cannot_write(client):
    a = register(client, "a@a.example", "Org A")
    b = register(client, "b@b.example", "Org B")
    org_a, org_b = first_org(client, a), first_org(client, b)
    assert put_logo(client, a, org_a).status_code == 204
    assert client.get(logo_url(org_a), headers=auth(b)).status_code == 404
    assert put_logo(client, b, org_a).status_code == 404
    assert client.delete(logo_url(org_a), headers=auth(b)).status_code == 404
    assert client.get(logo_url(org_b), headers=auth(b)).status_code == 404         # B has none: A's logo never leaks
    client.post(f"/api/v1/organizations/{org_a['id']}/members", json={"email": "b@b.example", "role": "viewer"}, headers=auth(a))
    assert client.get(logo_url(org_a), headers=auth(b)).status_code == 200
    assert put_logo(client, b, org_a).status_code == 403
    assert client.delete(logo_url(org_a), headers=auth(b)).status_code == 403
