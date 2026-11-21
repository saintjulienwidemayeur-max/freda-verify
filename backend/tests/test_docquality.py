
import cv2
import numpy as np
import pytest

from app.services import docquality
from tests.test_media import JPG, bearer, up
from tests.test_media import setup as media_setup

pytestmark = pytest.mark.docquality_real


def jpg(img) -> bytes:
    ok, buf = cv2.imencode(".jpg", img)
    assert ok
    return buf.tobytes()


def test_dark_and_blurry_photos_are_refused_and_a_sharp_one_passes(monkeypatch):
    monkeypatch.setattr(docquality.paddle, "available", lambda: False)
    dark = np.full((600, 900, 3), 10, np.uint8)
    flat = np.full((600, 900, 3), 140, np.uint8)
    rng = np.random.default_rng(1)
    sharp = rng.integers(0, 255, (600, 900, 3), dtype=np.uint8)
    assert docquality.check(jpg(dark)) == "dark"
    assert docquality.check(jpg(flat)) == "blurry"
    assert docquality.check(jpg(sharp)) is None
    assert docquality.check(b"not an image") is None            # never blocks on its own failure


def test_no_text_is_refused_when_the_ocr_finds_nothing(monkeypatch):
    monkeypatch.setattr(docquality.paddle, "available", lambda: True)
    monkeypatch.setattr(docquality.paddle, "read_text", lambda image: "a b")
    rng = np.random.default_rng(2)
    assert docquality.check(jpg(rng.integers(0, 255, (600, 900, 3), dtype=np.uint8))) == "no_text"
    monkeypatch.setattr(docquality.paddle, "read_text", lambda image: "NOM DUPONT NAISSANCE 1990")
    assert docquality.check(jpg(rng.integers(0, 255, (600, 900, 3), dtype=np.uint8))) is None


def test_upload_of_an_unreadable_card_returns_a_retake_error(client, monkeypatch):
    monkeypatch.setattr(docquality, "check", lambda image, need_text=True: "dark")
    t, org, key, _ = media_setup(client)
    r = client.post("/api/v1/verifications", json={}, headers={"Authorization": f"Bearer {key}"}).json()
    client.post("/api/v1/session/consent", headers=bearer(r["session_token"]))
    res = up(client, r["session_token"], "document_front", JPG, q="?doc_type=id&country=HT")
    assert res.status_code == 422 and res.json()["error"]["code"] == "unreadable_document"
    assert res.json()["error"]["details"] == [{"reason": "dark"}]
