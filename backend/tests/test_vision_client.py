import pytest

from app.services import vision
from tests.conftest import auth
from tests.test_media import JPG, bearer, up
from tests.test_media import setup as media_setup


def test_disabled_by_default_and_unavailable_maps_to_an_error():
    assert vision.available() is False
    with pytest.raises(vision.VisionUnavailable):
        vision.analyze(b"x", "passport")


def test_reviewer_endpoint_stores_an_advisory_vision_check(client, monkeypatch):
    t, org, key, _ = media_setup(client)
    r = client.post("/api/v1/verifications", json={}, headers={"Authorization": f"Bearer {key}"}).json()
    tok = r["session_token"]
    client.post("/api/v1/session/consent", headers=bearer(tok))
    for k, q in (("document_front", "?doc_type=id&country=HT"), ("selfie", "")):
        assert up(client, tok, k, JPG, q=q).status_code == 204
    base = f"/api/v1/organizations/{org['id']}/verifications/{r['id']}/checks/vision"
    assert client.post(base, headers=auth(t)).status_code == 503                      # not configured: honest error
    monkeypatch.setattr(vision, "available", lambda: True)
    monkeypatch.setattr(vision, "analyze", lambda img, dt, instr=None: {"status": "partial", "fields": {"surname": {"value": "X", "confidence": 0.4}}, "model": "m", "engine": "fake",
                                                                       "extracted_text": "T", "missing_information": ["expiry_date"], "image_quality": {}})
    out = client.post(base, headers=auth(t)).json()
    assert out["vision"]["status"] == "partial"
    got = client.get(f"/api/v1/organizations/{org['id']}/verifications/{r['id']}/checks", headers=auth(t)).json()
    assert got["vision"]["status"] == "partial"
    # a failing service is recorded as unavailable, never raised
    def boom(*a, **k):
        raise vision.VisionUnavailable("down")
    monkeypatch.setattr(vision, "analyze", boom)
    assert client.post(base, headers=auth(t)).json()["vision"]["status"] == "unavailable"
