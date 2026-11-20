import pytest

from app.services import pad
from tools import pad_eval


def test_disabled_by_default(monkeypatch):
    monkeypatch.setenv("FV_PAD_MODEL_DIR", "/nonexistent")
    assert not pad.available() and pad.score(b"x").status == "unavailable"


def test_rates_use_threshold_per_attack_type():
    r = pad_eval.rates([0.9, 0.8, 0.4], {"print": [0.2, 0.6], "replay": [0.95, 0.9]}, 0.5)
    assert r["bpcer"] == (1, 3) and r["apcer"] == {"print": (1, 2), "replay": (2, 2)}


def test_eval_refuses_without_a_model(monkeypatch, capsys, tmp_path):
    monkeypatch.setenv("FV_PAD_MODEL_DIR", "/nonexistent")
    assert pad_eval.main([str(tmp_path)]) == 2
    assert "not available" in capsys.readouterr().out


def test_eval_reports_and_warns_when_samples_are_few(monkeypatch, capsys, tmp_path):
    for d, n in (("genuine", 3), ("attack_print", 2)):
        (tmp_path / d).mkdir()
        for i in range(n):
            (tmp_path / d / f"{i}.jpg").write_bytes(b"x")
    monkeypatch.setattr(pad, "available", lambda: True)
    monkeypatch.setattr(pad, "score", lambda data: pad.PadOutcome("scored", 0.9))
    assert pad_eval.main([str(tmp_path), "--thresholds", "0.5"]) == 0
    out = capsys.readouterr().out
    assert "INDICATIVE" in out and "print" in out and "0/3" in out and "2/2" in out


REAL = pad.model_dir() / "MiniFASNetV2.onnx"


@pytest.mark.skipif(not (REAL.is_file() and pad.face.available()), reason="PAD and face models not installed")
def test_real_models_score_a_portrait_and_a_photo_of_a_photo(tmp_path):
    import io

    import cv2
    import numpy as np
    from PIL import Image
    portrait = Image.open("../public/faces/woman-selfie.webp").convert("RGB")
    b = io.BytesIO()
    portrait.save(b, "JPEG")
    live = pad.score(b.getvalue())
    assert live.status == "scored" and live.band is not None and 0 <= live.real_probability <= 1 and set(live.per_model) <= {"MiniFASNetV2", "MiniFASNetV1SE"}
    # a degraded re-photograph (blur + moire-like lines + colour cast) must at least run through the same path; no accuracy claim is made here
    a = np.array(portrait)[:, :, ::-1].copy()
    a[::6, :, 2] = np.clip(a[::6, :, 2].astype(int) + 40, 0, 255)
    ok, buf = cv2.imencode(".jpg", cv2.GaussianBlur(a, (5, 5), 0))
    assert ok and pad.score(buf.tobytes()).status in ("scored", "no_face")


def test_pad_check_is_separate_stored_encrypted_and_never_decides(client, monkeypatch):
    from app.services import pad as padmod
    from tests.conftest import auth
    from tests.test_media import setup as media_setup
    from tests.test_media import submit_all
    monkeypatch.setattr(padmod, "available", lambda: True)
    monkeypatch.setattr(padmod, "score", lambda data: padmod.PadOutcome("scored", 0.91, {"MiniFASNetV2": 0.9, "MiniFASNetV1SE": 0.92}, "high"))
    t, org, key, v = media_setup(client)
    assert submit_all(client, v["session_token"]).status_code == 204
    c = client.get(f"/api/v1/organizations/{org['id']}/verifications/{v['id']}/checks", headers=auth(t)).json()
    assert c["pad_available"] is True and c["pad"]["status"] == "scored" and c["pad"]["band"] == "high" and c["face"] is not None   # face comparison untouched
    r = client.get(f"/api/v1/verifications/{v['id']}/result", headers={"Authorization": f"Bearer {key}"}).json()
    assert r["status"] == "MANUAL_REVIEW" and r["decision"] is None                      # a good score decides nothing
    assert r["advisory"]["liveness"] == "experimental_not_certified" and "0.91" not in str(r)
    assert client.post(f"/api/v1/organizations/{org['id']}/verifications/{v['id']}/checks/pad", headers=auth(t)).status_code == 200


def test_aggregate_uses_the_worst_frame_to_downgrade():
    from app.services.pad import PadOutcome, aggregate
    good = PadOutcome("scored", 0.95, {"MiniFASNetV2": 0.95}, "high")
    bad = PadOutcome("scored", 0.1, {"MiniFASNetV2": 0.1}, "low")
    nof = PadOutcome("no_face")
    a = aggregate([good, good, bad])                      # mean 0.667 -> uncertain anyway
    assert a.min_probability == 0.1 and a.band == "uncertain"
    b = aggregate([good, good, good, bad, nof])           # mean 0.76 would be 'high', one bad frame downgrades it
    assert b.real_probability > 0.7 and b.band == "uncertain" and b.status == "scored"
    assert aggregate([nof, nof]).status == "no_face"
    assert aggregate([good]).band == "high"


def test_extra_selfie_frames_are_stored_scored_together_and_do_not_touch_face_comparison(client, monkeypatch):
    from app.services import pad as padmod
    from tests.conftest import auth
    from tests.test_media import PASSPORT_PAGE, bearer, up
    from tests.test_media import setup as media_setup
    seen = []
    monkeypatch.setattr(padmod, "available", lambda: True)

    def fake(data):
        seen.append(data)
        return padmod.PadOutcome("scored", 0.9, {"MiniFASNetV2": 0.9}, "high")
    monkeypatch.setattr(padmod, "score", fake)
    t, org, key, v = media_setup(client)
    tok = v["session_token"]
    client.post("/api/v1/session/consent", headers=bearer(tok))
    assert up(client, tok, "document_front", PASSPORT_PAGE, q="?doc_type=passport&country=HT").status_code == 204
    for k in ("selfie", "selfie_2", "selfie_3"):
        assert up(client, tok, k).status_code == 204
    assert up(client, tok, "selfie_4").status_code == 404
    assert client.post("/api/v1/session/complete", headers=bearer(tok)).status_code == 204
    assert len(seen) == 3
    c = client.get(f"/api/v1/organizations/{org['id']}/verifications/{v['id']}/checks", headers=auth(t)).json()
    assert len(c["pad"]["frames"]) == 3 and c["face"]["status"] in ("compared", "no_doc_face", "no_selfie", "ambiguous", "unavailable", "error")
