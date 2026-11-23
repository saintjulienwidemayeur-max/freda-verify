import asyncio
import io
import json

import httpx
import numpy as np
import pytest
from PIL import Image

from app.config import Settings
from app.engine import FakeEngine, ModelError, OpenAICompatEngine, parse_answer
from app.main import create_app

TOKEN = "t" * 40
H = {"Authorization": f"Bearer {TOKEN}"}


def settings(**kw):
    base = dict(token=TOKEN, env="dev", engine="fake", llm_url="http://x", llm_model="m", max_upload_bytes=2_000_000, max_pixels=20_000_000, max_side=1344,
                timeout_s=5, max_concurrent=2, max_queued=3, rate_per_minute=1000)
    base.update(kw)
    return Settings(**base)


def jpeg(w=900, h=600, noise=True, level=128):
    a = (np.random.default_rng(1).integers(0, 255, (h, w, 3), dtype=np.uint8) if noise else np.full((h, w, 3), level, np.uint8))
    b = io.BytesIO()
    Image.fromarray(a).save(b, "JPEG")
    return b.getvalue()


async def call(app, data, doc="passport", headers=H, **form):
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://t") as c:
        return await c.post("/api/v1/vision/analyze", files={"image": ("a.jpg", data, "image/jpeg")}, data={"document_type": doc, **form}, headers=headers)


def run(coro):
    return asyncio.run(coro)


def test_valid_passport_returns_structured_json_without_any_decision():
    r = run(call(create_app(settings(), FakeEngine()), jpeg()))
    assert r.status_code == 200
    j = r.json()
    assert j["document_type"] == "passport" and j["fields"]["surname"]["value"] == "EXAMPLE" and j["engine"] == "fake"
    assert "verified" not in j and "decision" not in j and "NOT proof" in j["disclaimer"]
    assert j["status"] == "partial" and j["missing_information"] == ["expiry_date"]


def test_blurry_document_is_reported_by_local_measurement():
    r = run(call(create_app(settings(), FakeEngine()), jpeg(noise=False)))
    q = r.json()["image_quality"]
    assert q["usable"] is False and "blurry" in q["issues"] and r.json()["status"] == "partial"


def test_invalid_and_unsupported_images_are_refused():
    app = create_app(settings(), FakeEngine())
    assert run(call(app, b"not an image at all" * 20)).json()["error"]["code"] == "unsupported_image"
    assert run(call(app, b"\xff\xd8\xff" + b"broken" * 50)).json()["error"]["code"] == "invalid_image"
    assert run(call(app, jpeg(40, 40))).json()["error"]["code"] == "bad_image_size"
    big = run(call(create_app(settings(max_upload_bytes=1000), FakeEngine()), jpeg()))
    assert big.status_code == 413
    assert run(call(app, jpeg(), doc="visa")).status_code == 422                          # unsupported document type


def test_token_is_required():
    app = create_app(settings(), FakeEngine())
    assert run(call(app, jpeg(), headers={})).status_code == 401
    assert run(call(app, jpeg(), headers={"Authorization": "Bearer wrong"})).status_code == 401


def test_prod_requires_a_long_token_and_refuses_the_fake_engine():
    with pytest.raises(RuntimeError):
        create_app(settings(env="prod", token="short"), FakeEngine())
    with pytest.raises(RuntimeError):
        create_app(settings(env="prod", engine="fake"))


def test_missing_fields_and_empty_answers():
    raw = json.dumps({"document_type": "id_card", "extracted_text": "", "fields": {}, "missing_information": ["name"], "suspicious_visual_anomalies": []})
    r = run(call(create_app(settings(), FakeEngine(raw=raw)), jpeg(), doc="id_card"))
    assert r.json()["status"] == "failed"


@pytest.mark.parametrize("bad", ["not json", "{}", '{"document_type": "passport", "verified": true}', '{"document_type": "passport", "fields": {"a b": {"value": "x"}}}',
                                 '{"document_type": "visa"}', '{"document_type": "passport", "overall_confidence": 7}'])
def test_malformed_or_hostile_model_output_is_rejected_and_not_echoed(bad):
    r = run(call(create_app(settings(), FakeEngine(raw=bad)), jpeg()))
    assert r.status_code == 502 and r.json()["error"]["code"] == "model_error" and bad not in r.text
    with pytest.raises(ModelError):
        parse_answer(bad)


def test_markdown_fenced_json_is_accepted():
    a = parse_answer('```json\n{"document_type": "passport", "extracted_text": "x"}\n```')
    assert a.document_type.value == "passport"


def test_model_unavailable_gives_503_and_ready_reports_it():
    app = create_app(settings(), FakeEngine(fail="unavailable"))
    assert run(call(app, jpeg())).status_code == 503

    async def ready():
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://t") as c:
            return await c.get("/health/ready"), await c.get("/health")
    r, h = run(ready())
    assert r.status_code == 503 and r.json()["status"] == "model_unavailable" and h.status_code == 200


def test_openai_engine_maps_connection_errors_and_bad_answers(monkeypatch):
    eng = OpenAICompatEngine("http://127.0.0.1:9", "m", 1)           # nothing listens there: GPU / model server down
    r = run(call(create_app(settings(), eng), jpeg()))
    assert r.status_code == 503 and r.json()["error"]["code"] == "model_unavailable"


def test_openai_engine_parses_a_real_shaped_response():
    content = json.dumps({"document_type": "passport", "extracted_text": "P<HTI", "fields": {"surname": {"value": "X", "confidence": 0.9}}})
    handler = httpx.MockTransport(lambda req: httpx.Response(200, json={"choices": [{"message": {"content": content}}]}))
    real = httpx.AsyncClient

    class Patched(real):
        def __init__(self, *a, **k):
            super().__init__(*a, transport=handler, **{x: y for x, y in k.items() if x != "transport"})
    import app.engine as e
    e.httpx.AsyncClient = Patched
    try:
        a = run(OpenAICompatEngine("http://llm", "m", 5).analyze(jpeg(), "passport", None))
    finally:
        e.httpx.AsyncClient = real
    assert a.fields["surname"].value == "X"


def test_concurrent_requests_respect_the_queue_limit():
    app = create_app(settings(max_concurrent=1, max_queued=1), FakeEngine(delay=0.3))

    async def many():
        return await asyncio.gather(*[call(app, jpeg()) for _ in range(5)])
    codes = sorted(r.status_code for r in run(many()))
    assert codes.count(200) >= 1 and 429 in codes and all(c in (200, 429) for c in codes)


def test_logs_never_contain_document_content(caplog):
    import logging
    caplog.set_level(logging.INFO, logger="vision")
    run(call(create_app(settings(), FakeEngine()), jpeg()))
    text = " ".join(r.getMessage() for r in caplog.records)
    assert "EXAMPLE" not in text and "FAKE ENGINE TEXT" not in text and "analyze vis_" in text
