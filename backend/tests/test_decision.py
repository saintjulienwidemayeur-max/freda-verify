
from app.api.v1 import verifications as V
from app.services.decision import Verdict, decide
from tests.conftest import auth
from tests.test_media import bearer, submit_all
from tests.test_media import setup as _setup


def media_setup(client, email="o@o.example", name="Org O"):
    return _setup(client, email, name, manual=False)         # these tests exercise the platform default (automatic) and explicit policies

GOOD_MRZ = {"all_checks_passed": True, "expired": False, "checks": {"document_number": True, "birth_date": True, "expiry_date": True, "composite": True}}
FACE_OK = {"status": "compared", "score": 0.55, "band": "high"}
KW = dict(face_min=0.363, require_pad=False, uncertain="review", agreeing=2, doc_type="passport", pad=None)


def d(**over):
    return decide(**{**KW, "mrz": GOOD_MRZ, "face": FACE_OK, **over})


def test_approves_only_when_every_check_is_strong():
    assert d().decision == "APPROVED"
    assert d(agreeing=1).decision is None and d(agreeing=1).codes == ["single_reading"]
    assert d(face={"status": "compared", "score": 0.30, "band": "low"}).codes == ["face_low"]
    assert d(face={"status": "ambiguous", "score": None}).codes == ["face_ambiguous"]
    assert d(face=None).codes == ["face_missing"]
    assert d(mrz=None).codes == ["mrz_unreadable"] and d(mrz=None, doc_type="id").codes == ["no_mrz_for_id"]
    assert d(mrz={**GOOD_MRZ, "all_checks_passed": False, "checks": {"document_number": True, "birth_date": True, "expiry_date": True, "composite": False}}).codes == ["mrz_partial"]
    assert d(mrz={**GOOD_MRZ, "all_checks_passed": False, "checks": {"document_number": False, "birth_date": True, "expiry_date": True}}).codes == ["mrz_invalid"]


def test_rejects_automatically_only_for_an_objective_failure():
    assert d(mrz={**GOOD_MRZ, "expired": True}).decision == "REJECTED" and d(mrz={**GOOD_MRZ, "expired": True}).codes == ["document_expired"]
    unreliable = {**GOOD_MRZ, "expired": True, "all_checks_passed": False, "checks": {"expiry_date": False, "document_number": True, "birth_date": True}}
    assert d(mrz=unreliable).decision is None                                       # the expiry digit failed: the date may be a misreading, so no automatic rejection
    assert d(face={"status": "compared", "score": 0.1, "band": "low"}).decision is None


def test_uncertain_policy_and_pad_requirement():
    assert d(agreeing=1, uncertain="reject").decision == "REJECTED"
    assert d(require_pad=True).decision is None and d(require_pad=True).codes == ["pad_missing"]
    assert d(require_pad=True, pad={"status": "scored", "real_probability": 0.9, "band": "high"}).decision == "APPROVED"
    assert d(require_pad=True, pad={"status": "scored", "real_probability": 0.2, "band": "low"}).codes == ["pad_low"]


def put_policy(client, t, org, **kw):
    body = {"mode": "auto", "uncertain": "review", "face_min": 0.363, "require_pad": False, **kw}
    return client.put(f"/api/v1/organizations/{org['id']}/decision-policy", json=body, headers=auth(t))


def test_default_is_automatic_and_only_admins_change_the_policy(client):
    t, org, key, v = media_setup(client)
    assert client.get(f"/api/v1/organizations/{org['id']}/decision-policy", headers=auth(t)).json() == {"mode": "auto", "uncertain": "review", "face_min": 0.363, "require_pad": False, "id_cards": "face_and_data"}
    assert submit_all(client, v["session_token"]).status_code == 204
    assert client.get("/api/v1/session", headers=bearer(v["session_token"])).json()["status"] == "REJECTED"            # default is automatic: the ICAO specimen passport used here expired in 2012 (expiry digit valid), an objective failure
    assert put_policy(client, t, org, face_min=0.95).status_code == 422 and put_policy(client, t, org, mode="x").status_code == 422
    assert put_policy(client, t, org).status_code == 200


def test_auto_mode_decides_notifies_audits_and_a_person_can_override(client, monkeypatch):
    t, org, key, v = media_setup(client)
    assert put_policy(client, t, org).status_code == 200
    monkeypatch.setattr(V.decision, "decide", lambda **kw: Verdict("APPROVED", ["all_checks_passed"]))
    assert submit_all(client, v["session_token"]).status_code == 204
    r = client.get(f"/api/v1/verifications/{v['id']}/result", headers={"Authorization": f"Bearer {key}"}).json()
    assert r["status"] == "APPROVED" and r["decision"] == "APPROVED" and r["decision_source"] == "automatic" and r["reason_codes"] == ["all_checks_passed"]
    assert client.get("/api/v1/session", headers=bearer(v["session_token"])).json()["status"] == "APPROVED"                  # the customer sees it
    logs = client.get(f"/api/v1/organizations/{org['id']}/audit-logs", headers=auth(t)).json()
    assert any(x["action"] == "verification.auto_decided" for x in logs)
    o = client.post(f"/api/v1/organizations/{org['id']}/verifications/{v['id']}/decision", json={"decision": "REJECTED", "reason": "photo mismatch"}, headers=auth(t))
    assert o.status_code == 200
    r = client.get(f"/api/v1/verifications/{v['id']}/result", headers={"Authorization": f"Bearer {key}"}).json()
    assert r["decision"] == "REJECTED" and r["decision_source"] == "human"
    assert client.post(f"/api/v1/organizations/{org['id']}/verifications/{v['id']}/decision", json={"decision": "APPROVED"}, headers=auth(t)).status_code == 409   # a human decision is final


def test_auto_mode_leaves_unclear_cases_to_a_person_and_never_breaks_submission(client, monkeypatch):
    t, org, key, v = media_setup(client)
    put_policy(client, t, org)
    monkeypatch.setattr(V.decision, "decide", lambda **kw: Verdict(None, ["face_low"]))
    assert submit_all(client, v["session_token"]).status_code == 204
    r = client.get(f"/api/v1/verifications/{v['id']}/result", headers={"Authorization": f"Bearer {key}"}).json()
    assert r["status"] == "MANUAL_REVIEW" and r["decision"] is None
    def boom(**kw):
        raise RuntimeError("engine failure")
    t2, org2, key2, v2 = media_setup(client, "z@z.example", "Org Z")
    put_policy(client, t2, org2)
    monkeypatch.setattr(V.decision, "decide", boom)
    assert submit_all(client, v2["session_token"]).status_code == 204
    assert client.get("/api/v1/session", headers=bearer(v2["session_token"])).json()["status"] == "MANUAL_REVIEW"             # a failure leaves it in manual review


def card(**over):
    return decide(**{**KW, "mrz": None, "doc_type": "id", "face": FACE_OK, **over})


def test_id_cards_follow_the_organizations_rule():
    assert card().decision is None and card().codes == ["no_mrz_for_id"]                                     # default: a person
    assert card(id_cards="face_only").decision == "APPROVED"                                                  # explicit risk choice: no document check
    assert card(id_cards="face_only", face={"status": "compared", "score": 0.2, "band": "low"}).decision is None
    good = {"status": "compared", "fields": 3, "matched": 3, "name": 1.0, "number": True, "birth": True}
    assert card(id_cards="face_and_data", idtext=good).decision == "APPROVED"
    assert card(id_cards="face_and_data", idtext={**good, "matched": 1, "name": 1.0}).codes == ["id_data_mismatch"]
    assert card(id_cards="face_and_data", idtext={**good, "name": 0.4, "matched": 2}).codes == ["id_data_mismatch"]
    assert card(id_cards="face_and_data", idtext={"status": "no_expected"}).codes == ["id_data_no_expected"]
    assert card(id_cards="face_and_data", idtext=None).codes == ["id_data_missing"]
    assert card(id_cards="face_and_data", idtext={**good, "fields": 1, "matched": 1}).decision is None        # one declared field is not enough


def test_declared_data_is_encrypted_never_returned_and_checked_on_the_card(client, monkeypatch):
    from sqlalchemy import text

    from app.db.session import get_engine
    from app.services import idtext as it
    t, org, key, _ = media_setup(client)
    r = client.post("/api/v1/verifications", json={"reference": "c9", "expected": {"name": "Saint Julien Widemayeur", "birth_date": "2003-11-01", "document_number": "0089062024-5"}},
                    headers={"Authorization": f"Bearer {key}"})
    assert r.status_code == 201 and "expected" not in r.json() and "Widemayeur" not in r.text
    with get_engine().connect() as c:
        assert "Widemayeur" not in str(c.execute(text("select expected_enc from freda_verify.verifications")).all())
    assert client.post("/api/v1/verifications", json={"expected": {"birth_date": "not-a-date"}}, headers={"Authorization": f"Bearer {key}"}).status_code == 422
    monkeypatch.setattr(it, "read_text", lambda image: "NOM WIDEMAYEUR PRENOM SAINT JULIEN NAISSANCE 01/11/2003 NIF 00-89-06-2024-5")
    tok = r.json()["session_token"]
    from tests.test_media import JPG, up
    client.post("/api/v1/session/consent", headers=bearer(tok))
    assert up(client, tok, "document_front", JPG, q="?doc_type=id&country=HT").status_code == 204
    assert up(client, tok, "document_back", JPG, q="?doc_type=id&country=HT").status_code == 204
    assert up(client, tok, "selfie").status_code == 204
    assert client.post("/api/v1/session/complete", headers=bearer(tok)).status_code == 204
    c = client.get(f"/api/v1/organizations/{org['id']}/verifications/{r.json()['id']}/checks", headers=auth(t)).json()
    assert c["idtext"]["status"] == "compared" and c["idtext"]["matched"] == 3 and "WIDEMAYEUR" not in str(c["idtext"])


def test_recheck_runs_the_pipeline_again_and_decides_when_auto(client, monkeypatch):
    t, org, key, v = _setup(client, manual=True)
    assert submit_all(client, v["session_token"]).status_code == 204                                  # manual mode: stays in review
    put_policy(client, t, org)
    monkeypatch.setattr(V.decision, "decide", lambda **kw: Verdict("APPROVED", ["all_checks_passed"]))
    assert client.post(f"/api/v1/organizations/{org['id']}/verifications/{v['id']}/recheck", headers=auth(t)).status_code == 202
    assert client.get("/api/v1/session", headers=bearer(v["session_token"])).json()["status"] == "APPROVED"
    assert client.post(f"/api/v1/organizations/{org['id']}/verifications/{v['id']}/recheck", headers=auth(t)).status_code == 409   # already decided


def test_platform_default_applies_without_a_saved_policy_and_can_be_overridden_by_env(client, monkeypatch):
    t, org, key, v = media_setup(client)
    monkeypatch.setattr(V.decision, "decide", lambda **kw: Verdict("APPROVED", ["all_checks_passed"]))
    assert submit_all(client, v["session_token"]).status_code == 204                     # no policy was ever saved: the automatic default decides
    assert client.get("/api/v1/session", headers=bearer(v["session_token"])).json()["status"] == "APPROVED"
    from app.core.config import get_settings
    monkeypatch.setenv("FV_DECISION_DEFAULT_MODE", "manual")
    get_settings.cache_clear()
    try:
        t2, org2, key2, v2 = media_setup(client, "m@m.example", "Org M")
        assert submit_all(client, v2["session_token"]).status_code == 204
        assert client.get("/api/v1/session", headers=bearer(v2["session_token"])).json()["status"] == "MANUAL_REVIEW"
        assert client.get(f"/api/v1/organizations/{org2['id']}/decision-policy", headers=auth(t2)).json()["mode"] == "manual"
    finally:
        monkeypatch.delenv("FV_DECISION_DEFAULT_MODE")
        get_settings.cache_clear()
