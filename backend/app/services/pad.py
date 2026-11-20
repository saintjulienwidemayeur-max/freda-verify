"""Presentation-attack detection (PAD) on the SELFIE, from a single image: Minivision MiniFASNetV2 + MiniFASNetV1SE (ONNX), run with OpenCV DNN, fully self-hosted.

ADVISORY and EXPERIMENTAL. Separate from face comparison (app.services.face) on purpose: liveness says "is this a live capture?", comparison says "is it the same person?". It never decides.
What it is: a passive, single-frame 2D-attack detector (printed photo / screen replay). What it is NOT: certified (no iBeta/ISO 30107-3 result), tested against masks, deepfakes or camera
injection, or measured on our users (skin tones, phones, lighting: APCER/BPCER unknown, measure with tools/pad_eval.py). Training-data origin and licence of the WEIGHTS are not stated by the
publishers (the code is Apache-2.0): open question D7. Do not describe this as 'liveness detection' to customers.

Models live in FV_PAD_MODEL_DIR (default /opt/pad-models): MiniFASNetV2.onnx (crop scale 2.7) and MiniFASNetV1SE.onnx (crop scale 4.0), 80x80 BGR, 3-class softmax with class 1 = real
(the convention of the Minivision repo). Disabled (status `unavailable`) when no model file is present. The result is the mean real-probability of the available models, with each model's value.
"""
import os
import threading
from dataclasses import dataclass, field
from pathlib import Path

from app.services import face

MODELS = (("MiniFASNetV2.onnx", 2.7), ("MiniFASNetV1SE.onnx", 4.0))      # (file, crop scale = square side / face box side)
SIZE = 80
REAL_INDEX = 1
HIGH, LOW = 0.7, 0.3                                                      # bands on the mean real probability: NOT calibrated


@dataclass
class PadOutcome:
    status: str                       # scored | no_face | unavailable | error
    real_probability: float | None = None
    per_model: dict[str, float] = field(default_factory=dict)
    band: str | None = None           # high | uncertain | low (probability of a live capture)
    min_probability: float | None = None     # worst frame when several frames were scored


def model_dir() -> Path:
    return Path(os.environ.get("FV_PAD_MODEL_DIR", "/opt/pad-models"))


def _present() -> list[tuple[Path, float]]:
    return [(model_dir() / f, sc) for f, sc in MODELS if (model_dir() / f).is_file()]


def available() -> bool:
    return bool(_present()) and face.available()


def band(p: float) -> str:
    return "high" if p >= HIGH else "low" if p < LOW else "uncertain"


_lock = threading.Lock()
_nets: dict[str, object] = {}


def _net(path: Path):
    import cv2
    k = str(path)
    if k not in _nets:
        _nets[k] = cv2.dnn.readNetFromONNX(k)
    return _nets[k]


def _crop(img, box, scale: float, size: int):
    import cv2
    x, y, w, h = (float(v) for v in box[:4])
    side = max(w, h) * scale
    cx, cy = x + w / 2, y + h / 2
    x0, y0 = int(round(cx - side / 2)), int(round(cy - side / 2))
    s = max(2, int(round(side)))
    padded = cv2.copyMakeBorder(img, s, s, s, s, cv2.BORDER_REPLICATE)
    return cv2.resize(padded[y0 + s:y0 + s + s, x0 + s:x0 + s + s], (size, size))


def _softmax(v):
    import numpy as np
    e = np.exp(v - v.max())
    return e / e.sum()


def score(data: bytes) -> PadOutcome:
    """Probability that the selfie is a LIVE capture according to the models (not calibrated, not a decision)."""
    present = _present()
    if not present or not face.available():
        return PadOutcome("unavailable")
    try:
        import cv2
        img = face._decode(data)
        if img is None:
            return PadOutcome("error")
        with face._lock:
            faces = face._faces(face._models()[0], img)
        if not faces:
            return PadOutcome("no_face")
        box = face._largest(faces)
        per: dict[str, float] = {}
        for path, scale in present:
            blob = cv2.dnn.blobFromImage(_crop(img, box, scale, SIZE), 1.0, (SIZE, SIZE), (0, 0, 0), swapRB=False, crop=False)
            with _lock:
                net = _net(path)
                net.setInput(blob)
                out = net.forward().reshape(-1)
            probs = out if abs(float(out.sum()) - 1.0) < 1e-3 and float(out.min()) >= 0 else _softmax(out)
            per[path.stem] = float(probs[REAL_INDEX])
        mean = sum(per.values()) / len(per)
        return PadOutcome("scored", mean, per, band(mean))
    except Exception:  # noqa: BLE001  a bad model file or image must not break anything else
        return PadOutcome("error")


def aggregate(outs: list["PadOutcome"]) -> "PadOutcome":
    """Several frontal frames of the same capture (taken at different moments). Score = mean over the frames that were scored; the WORST frame is kept too and
    a good mean with one bad frame is downgraded to 'uncertain' (a replayed screen often flickers between frames). Frames without a face are ignored; none scored -> first status."""
    ok = [o for o in outs if o.status == "scored" and o.real_probability is not None]
    if not ok:
        return outs[0] if outs else PadOutcome("unavailable")
    mean = sum(o.real_probability for o in ok) / len(ok)
    low = min(o.real_probability for o in ok)
    names = {k for o in ok for k in o.per_model}
    per = {k: sum(o.per_model[k] for o in ok if k in o.per_model) / sum(1 for o in ok if k in o.per_model) for k in names}
    b = band(mean)
    if b == "high" and low < LOW:
        b = "uncertain"
    return PadOutcome("scored", mean, per, b, low)
