"""Client of the INTERNAL Vision AI service (`/vision`, Qwen3-VL on our own GPU). Disabled unless FV_VISION_URL is set. Advisory only: its output never decides anything,
is never used by the automatic decision, and is shown to reviewers as 'read by a language model, can be wrong'. No external AI provider is ever called (decision D11)."""
import httpx

from app.core.config import get_settings


class VisionUnavailable(Exception):
    pass


def available() -> bool:
    s = get_settings()
    return bool(s.vision_url and s.vision_token)


def analyze(image: bytes, doc_type: str, instructions: str | None = None) -> dict:
    """Returns the service's JSON (status, fields, image_quality, anomalies...). Raises VisionUnavailable on any failure (the caller records 'unavailable', nothing else)."""
    s = get_settings()
    if not available():
        raise VisionUnavailable("not configured")
    data = {"document_type": doc_type}
    if instructions:
        data["instructions"] = instructions[:300]
    try:
        r = httpx.post(f"{s.vision_url.rstrip('/')}/api/v1/vision/analyze", headers={"Authorization": f"Bearer {s.vision_token}"}, data=data,
                       files={"image": ("document.jpg", image, "application/octet-stream")}, timeout=s.vision_timeout_s)
    except httpx.HTTPError as e:
        raise VisionUnavailable("service unreachable") from e
    if r.status_code != 200:
        raise VisionUnavailable(f"service answered {r.status_code}")
    try:
        return r.json()
    except ValueError as e:
        raise VisionUnavailable("bad answer") from e
