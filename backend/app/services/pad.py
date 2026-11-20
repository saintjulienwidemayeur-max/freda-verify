"""Presentation-attack detection (PAD, "liveness" from a single image) as an OPTIONAL, ADVISORY, MEASURABLE plug-in. DISABLED unless FV_PAD_MODEL_PATH points to an ONNX file.

No model ships with the product, on purpose: no candidate has been licence-cleared (see CLAUDE.md, D7 / "Liveness"). This module only gives a place to plug one in, run it on
the selfie with the same self-hosted OpenCV stack, and MEASURE it with tools/pad_eval.py. Until APCER/BPCER have been measured on a genuine set AND an attack set (printed photo,
screen replay, masks) the score must not be shown as a verdict, and nothing here may approve or reject a person.

Config (environment): FV_PAD_MODEL_PATH (ONNX), FV_PAD_INPUT (square input size, default 80), FV_PAD_REAL_INDEX (index of the "real" class in the output, default 1),
FV_PAD_CROP_SCALE (square crop = face box side x this, default 2.7), FV_PAD_THRESHOLD (default 0.5, NOT calibrated). Defaults follow the common MiniFASNet convention
(3-class softmax, 80x80 BGR crop, class 1 = real); a different model needs different values, checked on its own documentation.
"""
import os
import threading
from dataclasses import dataclass
from pathlib import Path

from app.services import face


@dataclass
class PadOutcome:
    status: str                       # scored | no_face | unavailable | error
    real_probability: float | None = None


def model_path() -> Path | None:
    p = os.environ.get("FV_PAD_MODEL_PATH", "").strip()
    return Path(p) if p else None


def threshold() -> float:
    return float(os.environ.get("FV_PAD_THRESHOLD", "0.5"))


def available() -> bool:
    p = model_path()
    return bool(p and p.is_file() and face.available())


_lock = threading.Lock()
_net_cache: tuple[str, object] | None = None


def _net():
    global _net_cache
    import cv2
    p = str(model_path())
    if _net_cache is None or _net_cache[0] != p:
        _net_cache = (p, cv2.dnn.readNetFromONNX(p))
    return _net_cache[1]


def _crop(img, box, scale: float, size: int):
    import cv2
    x, y, w, h = (float(v) for v in box[:4])
    side = max(w, h) * scale
    cx, cy = x + w / 2, y + h / 2
    x0, y0 = int(round(cx - side / 2)), int(round(cy - side / 2))
    s = max(2, int(round(side)))
    pad = s
    padded = cv2.copyMakeBorder(img, pad, pad, pad, pad, cv2.BORDER_REPLICATE)
    c = padded[y0 + pad:y0 + pad + s, x0 + pad:x0 + pad + s]
    return cv2.resize(c, (size, size))


def _softmax(v):
    import numpy as np
    e = np.exp(v - v.max())
    return e / e.sum()


def score(data: bytes) -> PadOutcome:
    """Probability that the selfie is a LIVE capture according to the plug-in model (not calibrated, not a decision)."""
    if not available():
        return PadOutcome("unavailable")
    try:
        import cv2
        img = face._decode(data)
        if img is None:
            return PadOutcome("error")
        with face._lock:
            det = face._models()[0]
            faces = face._faces(det, img)
        if not faces:
            return PadOutcome("no_face")
        size = int(os.environ.get("FV_PAD_INPUT", "80"))
        crop = _crop(img, face._largest(faces), float(os.environ.get("FV_PAD_CROP_SCALE", "2.7")), size)
        blob = cv2.dnn.blobFromImage(crop, 1.0, (size, size), (0, 0, 0), swapRB=False, crop=False)
        with _lock:
            net = _net()
            net.setInput(blob)
            out = net.forward().reshape(-1)
        probs = out if abs(float(out.sum()) - 1.0) < 1e-3 and float(out.min()) >= 0 else _softmax(out)
        return PadOutcome("scored", float(probs[int(os.environ.get("FV_PAD_REAL_INDEX", "1"))]))
    except Exception:  # noqa: BLE001  a bad model file or image must not break anything else
        return PadOutcome("error")
