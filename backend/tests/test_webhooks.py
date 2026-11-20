import hashlib
import hmac
import json

import pytest
from sqlalchemy import text

from app.db.session import get_engine
from app.services import webhooks
from tests.conftest import PASSWORD, auth, first_org, register
from tests.test_media import setup as media_setup
from tests.test_media import submit_all


class FakeResp:
    def __init__(self, code):
        self.status_code = code


class FakeClient:
    calls: list = []
    code = 200

    def __init__(self, *a, **k):
        pass

    def post(self, url, content=None, headers=None):
        FakeClient.calls.append({"url": url, "body": content, "headers": headers})
        return FakeResp(FakeClient.code)


@pytest.fixture(autouse=True)
def fake_network(monkeypatch):
    FakeClient.calls, FakeClient.code = [], 200
    monkeypatch.setattr(webhooks.httpx, "Client", FakeClient)
    monkeypatch.setattr(webhooks, "check_url", lambda url: None)
    monkeypatch.setattr(webhooks.time, "sleep", lambda s: None)
    import app.api.v1.webhooks as api
    monkeypatch.setattr(api.webhooks, "check_url", lambda url: None)


def add_hook(client, t, org, url="https://example.org/hook"):
    r = client.post(f"/api/v1/organizations/{org['id']}/webhooks", json={"url": url}, headers=auth(t))
    assert r.status_code == 201, r.text
    return r.json()


def test_url_rules_are_enforced_by_the_real_check():
    import importlib
    real = importlib.reload(webhooks)
    for bad in ("http://example.org/x", "https://127.0.0.1/x", "https://10.0.0.5/x", "https://169.254.169.254/latest", "https://[::1]/x", "https://user:pw@8.8.8.8/x", "ftp://8.8.8.8/x"):
        with pytest.raises(real.UnsafeUrl):
            real.check_url(bad)
    real.check_url("https://8.8.8.8/hook")                                       # public literal address: no DNS needed


def test_secret_is_shown_once_and_stored_encrypted(client):
    t, org, _, _ = media_setup(client)
    h = add_hook(client, t, org)
    assert h["secret"].startswith("whsec_")
    listed = client.get(f"/api/v1/organizations/{org['id']}/webhooks", headers=auth(t)).json()
    assert len(listed) == 1 and "secret" not in listed[0]
    with get_engine().connect() as c:
        assert h["secret"] not in str(c.execute(text("select * from freda_verify.webhook_endpoints")).all())


def test_submit_and_decision_are_delivered_signed_without_personal_data(client):
    t, org, key, v = media_setup(client)
    h = add_hook(client, t, org)
    assert submit_all(client, v["session_token"]).status_code == 204
    assert [json.loads(c["body"])["type"] for c in FakeClient.calls] == ["verification.submitted"]
    c = FakeClient.calls[0]
    ts, sig = (p.split("=", 1)[1] for p in c["headers"]["Freda-Signature"].split(","))
    assert hmac.compare_digest(sig, hmac.new(h["secret"].encode(), f"{ts}.".encode() + c["body"], hashlib.sha256).hexdigest())
    body = json.loads(c["body"])["data"]
    assert body["verification_id"] == v["id"] and body["reference"] == "c1" and body["status"] == "MANUAL_REVIEW"
    r = client.post(f"/api/v1/organizations/{org['id']}/verifications/{v['id']}/decision", json={"decision": "APPROVED", "reason": "private note"}, headers=auth(t))
    assert r.status_code == 200
    types = [json.loads(x["body"])["type"] for x in FakeClient.calls]
    assert types == ["verification.submitted", "verification.approved"]
    assert "private note" not in b"".join(x["body"] for x in FakeClient.calls).decode()      # reviewer notes never leave
    dl = client.get(f"/api/v1/organizations/{org['id']}/webhooks/{h['id']}/deliveries", headers=auth(t)).json()
    assert {d["status"] for d in dl} == {"delivered"}


def test_result_endpoint_for_api_keys(client):
    t, org, key, v = media_setup(client)
    bearer = {"Authorization": f"Bearer {key}"}
    r = client.get(f"/api/v1/verifications/{v['id']}/result", headers=bearer).json()
    assert r["status"] == "PENDING" and r["decision"] is None and r["advisory"] is None
    submit_all(client, v["session_token"])
    r = client.get(f"/api/v1/verifications/{v['id']}/result", headers=bearer).json()
    assert r["status"] == "MANUAL_REVIEW" and r["decision"] is None
    assert r["advisory"]["liveness"] == "not_performed" and r["advisory"]["aml"] == "not_performed"
    client.post(f"/api/v1/organizations/{org['id']}/verifications/{v['id']}/decision", json={"decision": "REJECTED"}, headers=auth(t))
    r = client.get(f"/api/v1/verifications/{v['id']}/result", headers=bearer).json()
    assert r["decision"] == "REJECTED" and r["decided_at"]
    text_ = json.dumps(r)
    assert "ERIKSSON" not in text_ and "L898902C3" not in text_                  # no identity data in the result
    _, _, other_key, _ = media_setup(client, "z@z.example", "Org Z")
    assert client.get(f"/api/v1/verifications/{v['id']}/result", headers={"Authorization": f"Bearer {other_key}"}).status_code == 404


def test_failed_delivery_is_recorded_and_can_be_resent(client):
    t, org, _, v = media_setup(client)
    h = add_hook(client, t, org)
    FakeClient.code = 500
    submit_all(client, v["session_token"])
    dl = client.get(f"/api/v1/organizations/{org['id']}/webhooks/{h['id']}/deliveries", headers=auth(t)).json()
    assert dl[0]["status"] == "failed" and dl[0]["attempts"] == 3 and dl[0]["last_error"] == "HTTP 500"
    FakeClient.code = 200
    assert client.post(f"/api/v1/organizations/{org['id']}/webhooks/{h['id']}/deliveries/{dl[0]['id']}/resend", headers=auth(t)).status_code == 202
    dl = client.get(f"/api/v1/organizations/{org['id']}/webhooks/{h['id']}/deliveries", headers=auth(t)).json()
    assert dl[0]["status"] == "delivered"


def test_unsafe_address_at_delivery_time_is_refused_without_a_request(client, monkeypatch):
    t, org, _, _ = media_setup(client)
    h = add_hook(client, t, org)
    with get_engine().begin() as c:                                              # the address becomes private after it was saved (DNS change)
        c.execute(text("update freda_verify.webhook_endpoints set url = 'https://127.0.0.1/hook'"))
    import importlib
    real = importlib.reload(webhooks)
    monkeypatch.setattr(real.httpx, "Client", FakeClient)
    d = client.post(f"/api/v1/organizations/{org['id']}/webhooks/{h['id']}/test", headers=auth(t)).json()
    assert FakeClient.calls == []
    rows = client.get(f"/api/v1/organizations/{org['id']}/webhooks/{h['id']}/deliveries", headers=auth(t)).json()
    assert rows[0]["id"] == d["id"]


def test_permissions_and_isolation(client):
    t, org, _, _ = media_setup(client)
    h = add_hook(client, t, org)
    register(client, "m@m.example", "Org M")
    client.post(f"/api/v1/organizations/{org['id']}/members", json={"email": "m@m.example", "role": "member"}, headers=auth(t))
    mt = client.post("/api/v1/auth/login", json={"email": "m@m.example", "password": PASSWORD}).json()
    assert client.get(f"/api/v1/organizations/{org['id']}/webhooks", headers=auth(mt)).status_code == 403
    assert client.post(f"/api/v1/organizations/{org['id']}/webhooks", json={"url": "https://example.org/x"}, headers=auth(mt)).status_code == 403
    other = register(client, "q@q.example", "Org Q")
    assert client.get(f"/api/v1/organizations/{org['id']}/webhooks", headers=auth(other)).status_code == 404
    other_org = first_org(client, other)
    assert client.delete(f"/api/v1/organizations/{other_org['id']}/webhooks/{h['id']}", headers=auth(other)).status_code == 404
    assert client.delete(f"/api/v1/organizations/{org['id']}/webhooks/{h['id']}", headers=auth(t)).status_code == 204
