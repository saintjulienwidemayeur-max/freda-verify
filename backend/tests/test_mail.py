import httpx
import pytest

from app.api.v1.verifications import notify_submission
from app.core.config import get_settings
from app.services import mailer
from tests.conftest import PASSWORD, auth, first_org, register


class Capture:
    """Replaces the network: records every request the mailer would send to Brevo."""
    def __init__(self, status=201):
        self.calls, self.status = [], status

    def handler(self, request: httpx.Request) -> httpx.Response:
        import json
        self.calls.append({"url": str(request.url), "headers": dict(request.headers), "json": json.loads(request.content)})
        return httpx.Response(self.status, json={"messageId": "x"})

    def client(self):
        return httpx.Client(transport=httpx.MockTransport(self.handler))


@pytest.fixture()
def brevo(monkeypatch):
    cap = Capture()
    monkeypatch.setattr(get_settings(), "brevo_api_key", "xkeysib-test-not-real")
    real = mailer.httpx.Client
    monkeypatch.setattr(mailer.httpx, "Client", lambda *a, **k: real(transport=httpx.MockTransport(cap.handler)))
    return cap


def test_disabled_without_key_sends_nothing(client, monkeypatch):
    monkeypatch.setattr(get_settings(), "brevo_api_key", None)
    assert mailer.send_email(["a@a.example"], "s", "t") is False and not mailer.enabled()


def test_payload_shape_key_in_header_and_html_escaped(brevo):
    ok = mailer.send_email(["a@a.example", "a@a.example", "not-an-email"], "Hello <b>", "line <script>", ("Open", "https://fredaverify.com/x?a=1&b=2"))
    c = brevo.calls[0]
    assert ok and c["url"] == "https://api.brevo.com/v3/smtp/email" and c["headers"]["api-key"] == "xkeysib-test-not-real"
    assert c["json"]["to"] == [{"email": "a@a.example"}]                              # de-duplicated, invalid address dropped
    assert "<script>" not in c["json"]["htmlContent"] and "&lt;script&gt;" in c["json"]["htmlContent"]
    assert "https://fredaverify.com/x?a=1&b=2" in c["json"]["textContent"]
    assert "xkeysib" not in str(c["json"])                                           # the key never goes in the body


def test_provider_error_or_network_failure_never_raises(monkeypatch):
    monkeypatch.setattr(get_settings(), "brevo_api_key", "k")
    real = mailer.httpx.Client

    def boom(request):
        raise httpx.ConnectError("down")
    monkeypatch.setattr(mailer.httpx, "Client", lambda *a, **k: real(transport=httpx.MockTransport(boom)))
    assert mailer.send_email(["a@a.example"], "s", "t") is False
    monkeypatch.setattr(mailer.httpx, "Client", lambda *a, **k: real(transport=httpx.MockTransport(lambda r: httpx.Response(401, json={}))))
    assert mailer.send_email(["a@a.example"], "s", "t") is False


def test_password_reset_mail_is_sent_for_known_accounts_only_and_the_answer_is_identical(client, brevo):
    register(client, "owner@o.example", "Org O")
    r1 = client.post("/api/v1/auth/password/forgot", json={"email": "owner@o.example"})
    r2 = client.post("/api/v1/auth/password/forgot", json={"email": "ghost@nowhere.example"})
    assert r1.status_code == r2.status_code == 202 and r1.json() == r2.json()
    assert len(brevo.calls) == 1 and brevo.calls[0]["json"]["to"] == [{"email": "owner@o.example"}]
    assert "reset-password?token=" in brevo.calls[0]["json"]["textContent"]


def test_submission_notifies_owners_and_admins_without_personal_data(client, brevo):
    from tests.test_media import PASSPORT_PAGE, bearer
    t = register(client, "owner@o.example", "Org O")
    org = first_org(client, t)
    register(client, "viewer@v.example", "Org V")
    client.post(f"/api/v1/organizations/{org['id']}/members", json={"email": "viewer@v.example", "role": "viewer"}, headers=auth(t))
    key = client.post(f"/api/v1/organizations/{org['id']}/api-keys", json={"name": "k", "env": "test"}, headers=auth(t)).json()["secret"]
    v = client.post("/api/v1/verifications", json={"reference": "cust-42"}, headers=bearer(key)).json()
    h = {**bearer(v["session_token"]), "Content-Type": "image/jpeg"}
    client.post("/api/v1/session/consent", headers=h)
    client.put("/api/v1/session/media/document_front?doc_type=passport&country=HT", content=PASSPORT_PAGE, headers=h)
    client.put("/api/v1/session/media/selfie", content=PASSPORT_PAGE, headers=h)
    assert client.post("/api/v1/session/complete", headers=h).status_code == 204
    sent = [c for c in brevo.calls if "review" in c["json"]["subject"]]
    assert len(sent) == 1
    body = sent[0]["json"]
    assert body["to"] == [{"email": "owner@o.example"}]                                # the viewer is not notified
    assert "cust-42" in body["textContent"] and "/dashboard/verifications" in body["textContent"]
    assert "ERIKSSON" not in str(body) and "L898902C3" not in str(body)               # no identity data in the e-mail
    actions = [a["action"] for a in client.get(f"/api/v1/organizations/{org['id']}/audit-logs", headers=auth(t)).json()]
    assert "verification.notified" in actions


def test_notification_can_be_switched_off(client, brevo, monkeypatch):
    monkeypatch.setattr(get_settings(), "notify_on_submit", False)
    assert notify_submission(__import__("uuid").uuid4()) == 0 and not brevo.calls


def test_login_password_still_works_after_reset_flow_changes(client):
    register(client, "owner@o.example", "Org O")
    assert client.post("/api/v1/auth/login", json={"email": "owner@o.example", "password": PASSWORD}).status_code == 200
