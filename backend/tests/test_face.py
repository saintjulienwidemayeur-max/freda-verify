import io
from pathlib import Path

import pytest
from PIL import Image

from app.services import face
from tests.conftest import auth, first_org, register
from tests.test_media import bearer

FACES = Path(__file__).resolve().parents[2] / "public" / "faces"
pytestmark = pytest.mark.skipif(not face.available(), reason="face models (/opt/face-models) or opencv not installed")


def jpg(name):
    b = io.BytesIO()
    Image.open(FACES / f"{name}.webp").convert("RGB").save(b, "JPEG", quality=92)
    return b.getvalue()


def test_same_person_scores_high_and_different_people_low():
    same = face.compare(jpg("man-doc"), jpg("man-selfie"))
    other = face.compare(jpg("man-doc"), jpg("woman-selfie"))
    assert same.status == "compared" and same.band == "high" and same.score > 0.6
    assert other.status == "compared" and other.band == "low" and other.score < face.COSINE_THRESHOLD
    assert face.band(0.40) == "possible"


def test_no_face_and_garbage_are_reported_not_raised():
    blank = io.BytesIO()
    Image.new("RGB", (400, 300), "white").save(blank, "JPEG")
    assert face.compare(jpg("man-doc"), blank.getvalue()).status == "no_selfie"
    assert face.compare(blank.getvalue(), jpg("man-selfie")).status == "no_doc_face"
    assert face.compare(b"not an image", jpg("man-selfie")).status == "error"


def _submit(client, selfie):
    t = register(client, "owner@o.example", "Org O")
    org = first_org(client, t)
    key = client.post(f"/api/v1/organizations/{org['id']}/api-keys", json={"name": "k", "env": "test"}, headers=auth(t)).json()["secret"]
    v = client.post("/api/v1/verifications", json={}, headers=bearer(key)).json()
    h = {**bearer(v["session_token"]), "Content-Type": "image/jpeg"}
    client.post("/api/v1/session/consent", headers=h)
    for kind, data in (("document_front", jpg("man-doc")), ("document_back", jpg("man-doc")), ("selfie", selfie)):
        assert client.put(f"/api/v1/session/media/{kind}?doc_type=id&country=HT", content=data, headers=h).status_code == 204
    assert client.post("/api/v1/session/complete", headers=h).status_code == 204
    return t, org, v


def test_submission_runs_the_comparison_and_reviewers_see_an_advisory_score(client):
    t, org, v = _submit(client, jpg("man-selfie"))
    r = client.get(f"/api/v1/organizations/{org['id']}/verifications/{v['id']}/checks", headers=auth(t)).json()
    assert r["face_available"] and r["face"]["status"] == "compared" and r["face"]["band"] == "high"
    assert "embedding" not in str(r["face"]).lower()                                   # no biometric template is stored or returned
    again = client.post(f"/api/v1/organizations/{org['id']}/verifications/{v['id']}/checks/face", headers=auth(t))
    assert again.status_code == 200 and again.json()["face"]["status"] == "compared"
    actions = [a["action"] for a in client.get(f"/api/v1/organizations/{org['id']}/audit-logs", headers=auth(t)).json()]
    assert "verification.face_compared" in actions


def test_a_different_person_is_flagged_low_and_nothing_is_decided_automatically(client):
    t, org, v = _submit(client, jpg("woman-selfie"))
    r = client.get(f"/api/v1/organizations/{org['id']}/verifications/{v['id']}/checks", headers=auth(t)).json()
    assert r["face"]["band"] == "low"
    assert client.get(f"/api/v1/verifications/{v['id']}?organization_id={org['id']}", headers=auth(t)).json()["status"] == "MANUAL_REVIEW"   # still waiting for a human


def test_other_tenants_cannot_read_or_rerun(client):
    t, org, v = _submit(client, jpg("man-selfie"))
    other = register(client, "x@x.example", "Org X")
    base = f"/api/v1/organizations/{org['id']}/verifications/{v['id']}/checks"
    assert client.get(base, headers=auth(other)).status_code == 404
    assert client.post(base + "/face", headers=auth(other)).status_code == 404


def test_selfie_with_two_equal_faces_is_not_scored():
    a = Image.open(FACES / "man-selfie.webp").convert("RGB")
    two = Image.new("RGB", (a.width * 2, a.height), "white")
    two.paste(a, (0, 0))
    two.paste(a, (a.width, 0))                      # two faces of the same size: which one is the person?
    b = io.BytesIO()
    two.save(b, "JPEG", quality=92)
    r = face.compare(jpg("man-doc"), b.getvalue())
    assert r.status == "ambiguous" and r.score is None and r.selfie_faces == 2
    big_and_small = Image.new("RGB", (a.width * 2, a.height * 2), "white")      # person large, ID portrait small (typical selfie-with-ID): scored
    big_and_small.paste(a.resize((a.width * 2, a.height * 2)), (0, 0))
    big_and_small.paste(a.resize((a.width // 4, a.height // 4)), (20, 20))
    b2 = io.BytesIO()
    big_and_small.save(b2, "JPEG", quality=92)
    assert face.compare(jpg("man-doc"), b2.getvalue()).status in ("compared", "ambiguous")


def test_extra_selfie_frames_are_averaged(client):
    t, org, v = _submit(client, jpg("man-selfie"))
    h = {**bearer(v["session_token"]), "Content-Type": "image/jpeg"}
    from app.api.v1.verifications import run_face_check
    from app.core.security import encrypt_bytes
    from app.db.session import SessionLocal
    from app.models import Verification, VerificationMedia
    with SessionLocal() as db:                                           # two more frames: the same person and a different person
        vv = db.get(Verification, v["id"])
        for kind, name in (("selfie_2", "man-selfie"), ("selfie_3", "woman-selfie")):
            db.add(VerificationMedia(verification_id=vv.id, organization_id=vv.organization_id, kind=kind, doc_type=None, country=None, content_type="image/jpeg",
                                     size=1, sha256="x", data=encrypt_bytes(jpg(name))))
        db.commit()
        run_face_check(vv.id, db)
    r = client.get(f"/api/v1/organizations/{org['id']}/verifications/{v['id']}/checks", headers=auth(t)).json()["face"]
    assert r["aggregate"] == "mean" and len(r["frames"]) == 3
    assert min(r["frames"]) <= r["score"] <= max(r["frames"]) and abs(r["score"] - sum(r["frames"]) / 3) < 1e-3
    assert h  # silence unused
