import cv2
import numpy as np

from app.services import decision, forensics


def _card(seed=1):
    r = np.random.default_rng(seed)
    a = np.full((640, 1000, 3), 235, np.uint8)
    cv2.rectangle(a, (30, 30), (970, 610), (200, 210, 230), -1)
    for i in range(8):
        cv2.putText(a, f"NAME SURNAME 12-03-1990 ID {i * 7919}", (200, 120 + i * 55), cv2.FONT_HERSHEY_SIMPLEX, 1, (30, 30, 30), 2)
    return (a.astype(np.float32) + r.normal(0, 3, a.shape)).clip(0, 255).astype(np.uint8)


def _enc(a, q=90):
    return cv2.imencode(".jpg", a, [cv2.IMWRITE_JPEG_QUALITY, q])[1].tobytes()


def test_clean_synthetic_card_is_not_flagged():
    assert not forensics.analyse(_enc(_card()))["flagged"]


def test_diagonal_grid_is_flagged_as_screen():
    b = _card().astype(np.float32)
    g = b * (1 + 0.12 * np.sin(2 * np.pi * (np.arange(1000)[None, :] * 0.2 + np.arange(640)[:, None] * 0.27)))[:, :, None]
    assert "possible_screen_photo" in forensics.analyse(_enc(g.clip(0, 255).astype(np.uint8)))["reasons"]


def test_pasted_patch_is_flagged_as_edit():
    b = _card()
    rng = np.random.default_rng(1)
    patch = cv2.imdecode(np.frombuffer(_enc(cv2.GaussianBlur(b[300:420, 300:700], (0, 0), 1.5), 20), np.uint8), 1)
    b[300:420, 300:700] = (patch.astype(np.float32) + rng.normal(0, 12, patch.shape)).clip(0, 255).astype(np.uint8)
    assert "possible_local_edit" in forensics.analyse(_enc(b))["reasons"]


def test_garbage_bytes_do_not_raise():
    assert forensics.analyse(b"not an image")["status"] == "unavailable"


def test_flag_or_missing_video_never_approves():
    ok = dict(face_min=0.363, require_pad=False, uncertain="review", mrz=None, agreeing=0, face={"status": "compared", "score": 0.6}, pad=None, doc_type="id",
              idfields={"status": "extracted", "plausible": {"name": True, "birth_date": True, "document_number": True}})
    assert decision.decide(**ok).decision == "APPROVED"
    assert decision.decide(**ok, forensics={"flagged": True}).decision is None
    assert decision.decide(**ok, has_video=False).decision is None
