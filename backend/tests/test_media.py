
import pytest
from sqlalchemy import text

from app.api.v1.verifications import purge_expired_media
from app.db.session import SessionLocal, get_engine
from tests.conftest import PASSWORD, auth, first_org, register
from tests.test_ocr import TD3, page  # noqa: E402

JPG = b"\xff\xd8\xff\xe0" + b"SECRETPHOTOBYTES" * 8
PASSPORT_PAGE = page(TD3)                 # a passport front must contain readable MRZ text (server gate)
PNG = b"\x89PNG\r\n\x1a\n" + b"\x00" * 64


def bearer(tok):
    return {"Authorization": f"Bearer {tok}"}


def setup(client, email="o@o.example", name="Org O", manual=True):
    t = register(client, email, name)
    org = first_org(client, t)
    key = client.post(f"/api/v1/organizations/{org['id']}/api-keys", json={"name": "k", "env": "test"}, headers=auth(t)).json()["secret"]
    if manual:       # the platform default is AUTOMATIC; most tests exercise the human review flow
        client.put(f"/api/v1/organizations/{org['id']}/decision-policy", json={"mode": "manual", "uncertain": "review", "face_min": 0.363, "require_pad": False, "id_cards": "review"}, headers=auth(t))
    v = client.post("/api/v1/verifications", json={"reference": "c1"}, headers=bearer(key)).json()
    return t, org, key, v


def up(client, tok, kind, data=JPG, ctype="image/jpeg", q=""):
    return client.put(f"/api/v1/session/media/{kind}{q}", content=data, headers={**bearer(tok), "Content-Type": ctype})


def submit_all(client, tok, doc="passport"):
    client.post("/api/v1/session/consent", headers=bearer(tok))
    assert up(client, tok, "document_front", PASSPORT_PAGE if doc == "passport" else JPG, q=f"?doc_type={doc}&country=HT").status_code == 204
    if doc != "passport":
        assert up(client, tok, "document_back", q=f"?doc_type={doc}&country=HT").status_code == 204
    assert up(client, tok, "selfie").status_code == 204
    return client.post("/api/v1/session/complete", headers=bearer(tok))


def test_upload_requires_consent_and_valid_input(client):
    _, _, _, v = setup(client)
    tok = v["session_token"]
    assert up(client, tok, "selfie").status_code == 409                                  # no consent yet
    client.post("/api/v1/session/consent", headers=bearer(tok))
    assert up(client, tok, "selfie").status_code == 204
    assert up(client, tok, "face").status_code == 404                                    # unknown kind
    assert up(client, tok, "document_front", q="").status_code == 422                    # doc_type missing
    assert up(client, tok, "document_back", q="?doc_type=passport").status_code == 422
    assert up(client, tok, "document_front", q="?doc_type=id&country=ht").status_code == 422
    assert up(client, tok, "selfie", b"<svg/>" + b" " * 64, "image/svg+xml").status_code == 422
    assert up(client, tok, "selfie", b"<svg/>" + b" " * 64, "image/jpeg").status_code == 422   # lies about its type
    assert up(client, tok, "selfie", JPG + b"\x00" * (2 * 1024 * 1024), "image/jpeg").status_code == 413


def test_photos_are_encrypted_at_rest_and_roundtrip_for_admins(client):
    t, org, _, v = setup(client)
    assert submit_all(client, v["session_token"]).status_code == 204
    with get_engine().connect() as c:
        raw = bytes(c.execute(text("select data from freda_verify.verification_media where kind = 'selfie'")).scalar())
    assert b"SECRETPHOTOBYTES" not in raw and raw != JPG
    base = f"/api/v1/organizations/{org['id']}/verifications/{v['id']}/media"
    assert {m["kind"] for m in client.get(base, headers=auth(t)).json()} == {"document_front", "selfie"}
    g = client.get(base + "/selfie", headers=auth(t))
    assert g.status_code == 200 and g.content == JPG and g.headers["cache-control"] == "private, no-store" and g.headers["x-content-type-options"] == "nosniff"
    actions = [a["action"] for a in client.get(f"/api/v1/organizations/{org['id']}/audit-logs", headers=auth(t)).json()]
    assert "verification.media_viewed" in actions and "verification.media_uploaded" in actions and "verification.submitted" in actions


def test_complete_needs_everything_and_then_locks(client):
    _, _, _, v = setup(client)
    tok = v["session_token"]
    client.post("/api/v1/session/consent", headers=bearer(tok))
    assert client.post("/api/v1/session/complete", headers=bearer(tok)).status_code == 422
    up(client, tok, "document_front", q="?doc_type=id&country=HT")
    up(client, tok, "selfie")
    r = client.post("/api/v1/session/complete", headers=bearer(tok))
    assert r.status_code == 422 and "document_back" in r.text                           # an ID card needs its back
    up(client, tok, "document_back", q="?doc_type=id&country=HT")
    assert client.post("/api/v1/session/complete", headers=bearer(tok)).status_code == 204
    assert client.get("/api/v1/session", headers=bearer(tok)).json()["status"] == "MANUAL_REVIEW"
    assert up(client, tok, "selfie").status_code == 409                                  # closed
    assert client.post("/api/v1/session/complete", headers=bearer(tok)).status_code == 409


def test_manual_decision_flow_and_permissions(client):
    t, org, key, v = setup(client)
    dec = f"/api/v1/organizations/{org['id']}/verifications/{v['id']}/decision"
    assert client.post(dec, json={"decision": "APPROVED"}, headers=auth(t)).status_code == 409   # not submitted yet
    assert submit_all(client, v["session_token"]).status_code == 204
    assert client.get(f"/api/v1/verifications/{v['id']}", headers=bearer(key)).json()["status"] == "MANUAL_REVIEW"
    register(client, "m@m.example", "Org M")
    client.post(f"/api/v1/organizations/{org['id']}/members", json={"email": "m@m.example", "role": "member"}, headers=auth(t))
    mt = client.post("/api/v1/auth/login", json={"email": "m@m.example", "password": PASSWORD}).json()
    assert client.post(dec, json={"decision": "APPROVED"}, headers=auth(mt)).status_code == 403
    assert client.get(f"/api/v1/organizations/{org['id']}/verifications/{v['id']}/media/selfie", headers=auth(mt)).status_code == 403   # photos: owner/admin only
    assert client.post(dec, json={"decision": "MAYBE"}, headers=auth(t)).status_code == 422
    r = client.post(dec, json={"decision": "REJECTED", "reason": "blurry"}, headers=auth(t))
    assert r.status_code == 200 and r.json()["status"] == "REJECTED" and r.json()["decision_reason"] == "blurry" and r.json()["media_count"] == 2
    assert client.post(dec, json={"decision": "APPROVED"}, headers=auth(t)).status_code == 409   # decided once


def test_other_tenants_cannot_see_or_decide(client):
    t, org, _, v = setup(client)
    submit_all(client, v["session_token"])
    other = register(client, "x@x.example", "Org X")
    base = f"/api/v1/organizations/{org['id']}/verifications/{v['id']}"
    for method, path, kw in [("get", "/media", {}), ("get", "/media/selfie", {}), ("delete", "/media", {}), ("post", "/decision", {"json": {"decision": "APPROVED"}})]:
        assert getattr(client, method)(base + path, headers=auth(other), **kw).status_code == 404
    oorg = first_org(client, other)
    wrong = f"/api/v1/organizations/{oorg['id']}/verifications/{v['id']}/media/selfie"      # own org path, foreign verification id
    assert client.get(wrong, headers=auth(other)).status_code == 404


def test_delete_media_and_retention_purge(client):
    t, org, _, v = setup(client)
    submit_all(client, v["session_token"])
    base = f"/api/v1/organizations/{org['id']}/verifications/{v['id']}"
    with get_engine().begin() as c:
        c.execute(text("update freda_verify.verification_media set purge_after = now() - interval '1 minute' where kind = 'selfie'"))
    with SessionLocal() as db:
        assert purge_expired_media(db) == 1
    assert client.get(base + "/media/selfie", headers=auth(t)).status_code == 404
    assert client.get(base + "/media/document_front", headers=auth(t)).status_code == 200
    assert client.delete(base + "/media", headers=auth(t)).status_code == 204
    assert client.get(base + "/media", headers=auth(t)).json() == []
    assert client.get(f"/api/v1/organizations/{org['id']}/audit-logs", headers=auth(t)).json()[0]["action"] == "verification.media_deleted"
    assert client.get(f"/api/v1/verifications?organization_id={org['id']}", headers=auth(t)).json()[0]["status"] == "MANUAL_REVIEW"   # record stays


def test_expired_session_cannot_upload(client):
    _, _, _, v = setup(client)
    client.post("/api/v1/session/consent", headers=bearer(v["session_token"]))
    with get_engine().begin() as c:
        c.execute(text("update freda_verify.verifications set expires_at = now() - interval '1 minute'"))
    assert up(client, v["session_token"], "selfie").status_code == 410


@pytest.mark.parametrize("path", ["/session/media/selfie"])
def test_api_keys_and_jwts_cannot_upload_as_a_session(client, path):
    t, _, key, _ = setup(client)
    assert client.put("/api/v1" + path, content=JPG, headers={**bearer(key), "Content-Type": "image/jpeg"}).status_code == 401
    assert client.put("/api/v1" + path, content=JPG, headers={**auth(t), "Content-Type": "image/jpeg"}).status_code == 401


def test_photos_are_kept_by_default_and_only_purged_when_retention_is_enabled(client):
    t, org, _, v = setup(client)
    submit_all(client, v["session_token"])
    with get_engine().connect() as c:
        assert c.execute(text("select count(*) from freda_verify.verification_media where purge_after is not null")).scalar() == 0
    with SessionLocal() as db:
        assert purge_expired_media(db) == 0
    base = f"/api/v1/organizations/{org['id']}/verifications/{v['id']}/media"
    assert all(m["purge_after"] is None for m in client.get(base, headers=auth(t)).json())


def test_passport_front_without_mrz_text_is_refused_by_the_server(client):
    import shutil

    import pytest
    if not shutil.which("tesseract"):
        pytest.skip("tesseract is not installed")
    from PIL import Image
    t, org, _, v = setup(client)
    tok = v["session_token"]
    client.post("/api/v1/session/consent", headers=bearer(tok))
    import io
    blank = io.BytesIO()
    Image.new("RGB", (900, 640), "white").save(blank, "JPEG")
    r = up(client, tok, "document_front", blank.getvalue(), q="?doc_type=passport&country=HT")
    assert r.status_code == 422 and "mrz_not_found" in r.text                 # e.g. a national ID card held as a passport
    assert up(client, tok, "document_front", PASSPORT_PAGE, q="?doc_type=passport&country=HT").status_code == 204
    assert up(client, tok, "document_front", blank.getvalue(), q="?doc_type=id&country=HT").status_code == 204   # ID cards are not gated (no MRZ on the front)


WEBM = b"\x1a\x45\xdf\xa3" + b"\x00" * 2048
MP4 = b"\x00\x00\x00\x18ftypmp42" + b"\x00" * 2048


def test_challenge_video_is_optional_validated_encrypted_and_viewable_by_the_reviewer(client):
    t, org, _, v = setup(client)
    tok = v["session_token"]
    client.post("/api/v1/session/consent", headers=bearer(tok))
    assert up(client, tok, "selfie_video", WEBM, "video/webm").status_code == 204
    assert up(client, tok, "selfie_video", MP4, "video/mp4").status_code == 204                    # replaces the previous clip
    assert up(client, tok, "selfie_video", b"not a video" * 200, "video/webm").status_code == 422   # type must match the bytes
    assert up(client, tok, "selfie_video", JPG, "image/jpeg").status_code == 422
    assert up(client, tok, "selfie_video", b"\x1a\x45\xdf\xa3" + b"\x00" * (9 * 1024 * 1024), "video/webm").status_code == 413
    with get_engine().connect() as c:
        assert b"ftypmp42" not in b"".join(r[0] for r in c.execute(text("select data from freda_verify.verification_media")).all())
    # the clip does not replace or count as a required photo
    assert up(client, tok, "document_front", PASSPORT_PAGE, q="?doc_type=passport&country=HT").status_code == 204
    assert client.post("/api/v1/session/complete", headers=bearer(tok)).status_code == 422          # selfie still required
    assert up(client, tok, "selfie").status_code == 204
    assert client.post("/api/v1/session/complete", headers=bearer(tok)).status_code == 204
    r = client.get(f"/api/v1/organizations/{org['id']}/verifications/{v['id']}/media/selfie_video", headers=auth(t))
    assert r.status_code == 200 and r.headers["content-type"] == "video/mp4" and r.content == MP4 and r.headers["cache-control"] == "private, no-store"


def test_customer_can_read_the_outcome_with_the_session_link_even_after_expiry(client):
    t, org, _, v = setup(client)
    tok = v["session_token"]
    assert submit_all(client, tok).status_code == 204
    assert client.get("/api/v1/session", headers=bearer(tok)).json()["status"] == "MANUAL_REVIEW"
    client.post(f"/api/v1/organizations/{org['id']}/verifications/{v['id']}/decision", json={"decision": "REJECTED", "reason": "private reviewer note"}, headers=auth(t))
    with get_engine().begin() as c:
        c.execute(text("update freda_verify.verifications set expires_at = now() - interval '1 day'"))
    r = client.get("/api/v1/session", headers=bearer(tok))
    assert r.status_code == 200 and r.json()["status"] == "REJECTED" and "private reviewer note" not in r.text      # outcome yes, reviewer note never
    assert up(client, tok, "selfie").status_code == 409                                                               # but nothing can be uploaded any more
