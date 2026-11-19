import uuid

import pytest
from sqlalchemy import text

from app.db.session import SessionLocal, get_engine
from tests.conftest import auth, first_org, register


def two_tenants(client):
    a = register(client, "alice@a.example", "Org A")
    b = register(client, "bob@b.example", "Org B")
    return a, b, first_org(client, a), first_org(client, b)


def test_a_user_only_lists_their_own_organizations(client):
    a, b, org_a, org_b = two_tenants(client)
    assert [o["id"] for o in client.get("/api/v1/organizations", headers=auth(a)).json()] == [org_a["id"]]
    assert [o["id"] for o in client.get("/api/v1/organizations", headers=auth(b)).json()] == [org_b["id"]]


@pytest.mark.parametrize("method,path", [
    ("get", "/api/v1/organizations/{o}"), ("get", "/api/v1/organizations/{o}/members"), ("get", "/api/v1/organizations/{o}/api-keys"),
    ("get", "/api/v1/organizations/{o}/audit-logs"), ("get", "/api/v1/usage?organization_id={o}"),
])
def test_other_tenants_data_is_invisible(client, method, path):
    a, b, org_a, org_b = two_tenants(client)
    r = getattr(client, method)(path.format(o=org_b["id"]), headers=auth(a))
    assert r.status_code == 404                                             # not 403: the organization's existence is not revealed
    assert r.status_code == getattr(client, method)(path.format(o=uuid.uuid4()), headers=auth(a)).status_code


def test_cannot_write_to_another_tenant(client):
    a, b, org_a, org_b = two_tenants(client)
    assert client.post(f"/api/v1/organizations/{org_b['id']}/api-keys", json={"name": "x", "env": "test"}, headers=auth(a)).status_code == 404
    assert client.patch(f"/api/v1/organizations/{org_b['id']}", json={"name": "pwned"}, headers=auth(a)).status_code == 404
    assert client.post(f"/api/v1/organizations/{org_b['id']}/members", json={"email": "alice@a.example", "role": "admin"}, headers=auth(a)).status_code == 404


def test_key_ids_cannot_be_crossed_between_tenants(client):
    a, b, org_a, org_b = two_tenants(client)
    key_b = client.post(f"/api/v1/organizations/{org_b['id']}/api-keys", json={"name": "b key", "env": "test"}, headers=auth(b)).json()
    # A is a legitimate owner of org A, but the key belongs to org B: revoking it through A's own org path must fail
    assert client.delete(f"/api/v1/organizations/{org_a['id']}/api-keys/{key_b['id']}", headers=auth(a)).status_code == 404
    still = client.get("/api/v1/organizations", headers={"Authorization": f"Bearer {key_b['secret']}"})
    assert still.status_code == 200                                         # B's key still works: nothing was revoked


def test_api_key_only_sees_its_own_organization(client):
    a, b, org_a, org_b = two_tenants(client)
    key = client.post(f"/api/v1/organizations/{org_a['id']}/api-keys", json={"name": "k", "env": "test"}, headers=auth(a)).json()
    h = {"Authorization": f"Bearer {key['secret']}"}
    assert [o["id"] for o in client.get("/api/v1/organizations", headers=h).json()] == [org_a["id"]]
    assert client.get("/api/v1/usage", headers=h).json()["organization_id"] == org_a["id"]
    assert client.get(f"/api/v1/organizations/{org_a['id']}", headers=h).status_code == 401   # dashboard routes need a user session, not an API key


def add_member(client, owner, org, email, role):
    return client.post(f"/api/v1/organizations/{org['id']}/members", json={"email": email, "role": role}, headers=auth(owner))


def test_roles_and_permissions(client):
    owner = register(client, "owner@o.example", "Org")
    org = first_org(client, owner)
    people = {role: register(client, f"{role}@x.example", f"{role} own org") for role in ("admin", "member", "viewer")}
    for role in people:
        assert add_member(client, owner, org, f"{role}@x.example", role).status_code == 201
    base = f"/api/v1/organizations/{org['id']}"
    def mk(tok):
        return client.post(f"{base}/api-keys", json={"name": "k", "env": "test"}, headers=auth(tok))

    assert mk(people["admin"]).status_code == 201                           # admin: manage keys
    assert mk(people["member"]).status_code == 403                          # member: can read keys, cannot create
    assert client.get(f"{base}/api-keys", headers=auth(people["member"])).status_code == 200
    assert client.get(f"{base}/api-keys", headers=auth(people["viewer"])).status_code == 403
    assert client.get(f"{base}", headers=auth(people["viewer"])).status_code == 200
    assert client.get(f"{base}/audit-logs", headers=auth(people["member"])).status_code == 403
    assert client.get(f"{base}/audit-logs", headers=auth(people["admin"])).status_code == 200
    assert add_member(client, people["member"], org, "viewer@x.example", "admin").status_code == 403


def test_owner_protections(client):
    owner = register(client, "owner@o.example", "Org")
    org = first_org(client, owner)
    admin = register(client, "admin@x.example", "Admin org")
    add_member(client, owner, org, "admin@x.example", "admin")
    base = f"/api/v1/organizations/{org['id']}"
    me = client.get("/api/v1/auth/me", headers=auth(owner)).json()["id"]
    adm = client.get("/api/v1/auth/me", headers=auth(admin)).json()["id"]
    assert client.patch(f"{base}/members/{adm}", json={"role": "owner"}, headers=auth(admin)).status_code == 403          # admin cannot mint owners
    assert client.patch(f"{base}/members/{me}", json={"role": "member"}, headers=auth(owner)).status_code == 409         # last owner
    assert client.delete(f"{base}/members/{me}", headers=auth(admin)).status_code == 403                                  # admin cannot remove an owner
    assert client.delete(f"{base}/members/{me}", headers=auth(owner)).status_code == 409                                  # last owner cannot leave
    assert client.patch(f"{base}/members/{adm}", json={"role": "owner"}, headers=auth(owner)).status_code == 200
    assert client.patch(f"{base}/members/{me}", json={"role": "admin"}, headers=auth(owner)).status_code == 200           # now allowed: two owners existed


def test_database_refuses_to_modify_the_audit_log(client):
    register(client)
    with get_engine().connect() as c:
        for stmt in ("UPDATE freda_verify.audit_logs SET action = 'tampered'", "DELETE FROM freda_verify.audit_logs"):
            with pytest.raises(Exception, match="append-only"):
                c.execute(text(stmt))
            c.rollback()


def test_audit_trail_records_security_events_without_secrets(client):
    t = register(client)
    org = first_org(client, t)
    key = client.post(f"/api/v1/organizations/{org['id']}/api-keys", json={"name": "k", "env": "live"}, headers=auth(t)).json()
    client.delete(f"/api/v1/organizations/{org['id']}/api-keys/{key['id']}", headers=auth(t))
    rows = client.get(f"/api/v1/organizations/{org['id']}/audit-logs", headers=auth(t)).json()
    actions = [r["action"] for r in rows]
    assert {"org.created", "api_key.created", "api_key.revoked"} <= set(actions)
    assert key["secret"] not in client.get(f"/api/v1/organizations/{org['id']}/audit-logs", headers=auth(t)).text
    with SessionLocal() as db:
        assert db.execute(text("select count(*) from freda_verify.audit_logs where meta::text like :s"), {"s": f"%{key['secret']}%"}).scalar() == 0
