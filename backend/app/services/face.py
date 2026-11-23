"""Face comparison between the photo on the document and the selfie, fully self-hosted (OpenCV): YuNet face detector (MIT) + SFace recognizer (Apache-2.0).

ADVISORY ONLY. The score helps a human reviewer; it never approves or rejects anything. No embedding is stored: only the similarity number.
Known limits (not hidden): SFace was published with the OpenCV Zoo; its training data is a public face dataset whose licence/consent status is not
established (open question D7); accuracy differs across skin tones, ages and image quality, and has NOT been measured on our target population (Haiti / diaspora).
A photo printed on a passport (small, compressed, with a security overlay) is much harder than two selfies.
"""
import os
import threading
from dataclasses import dataclass
from pathlib import Path

DET = "face_detection_yunet_2023mar.onnx"
REC = "face_recognition_sface_2021dec.onnx"
COSINE_THRESHOLD = 0.363          # value recommended with the model by OpenCV (cosine similarity); NOT calibrated on our population
HIGH = 0.50
DOMINANCE = 4.0                   # in a selfie the person's face must be at least this many times larger (by area) than any other face
MAX_SIDE = 1280


@dataclass
class FaceOutcome:
    status: str                    # compared | no_doc_face | no_selfie | ambiguous | unavailable | error
    score: float | None = None
    band: str | None = None        # low | possible | high
    doc_faces: int = 0
    selfie_faces: int = 0


def model_dir() -> Path:
    return Path(os.environ.get("FV_FACE_MODEL_DIR", "/opt/face-models"))


def available() -> bool:
    try:
        import cv2  # noqa: F401
    except Exception:  # noqa: BLE001
        return False
    d = model_dir()
    return (d / DET).is_file() and (d / REC).is_file()


def _decode(data: bytes):
    import cv2
    import numpy as np
    img = cv2.imdecode(np.frombuffer(data, np.uint8), cv2.IMREAD_COLOR)
    if img is None:
        return None
    h, w = img.shape[:2]
    k = min(1.0, MAX_SIDE / max(h, w))
    return cv2.resize(img, (int(w * k), int(h * k))) if k < 1 else img


def _faces(det, img):
    h, w = img.shape[:2]
    det.setInputSize((w, h))
    _, f = det.detect(img)
    return [] if f is None else list(f)


def _largest(faces):
    return max(faces, key=lambda r: float(r[2]) * float(r[3]))        # x, y, w, h, landmarks..., score


# ───────── optional ArcFace recognizer (pluggable; OFF unless a model file AND its threshold are configured) ─────────
# ArcFace-type models (e.g. InsightFace 'buffalo_l' / w600k_r50.onnx, 112x112 input, 512-d output) are generally more accurate than SFace, BUT the pretrained InsightFace models are published
# for NON-COMMERCIAL RESEARCH ONLY (their README, read 2026-11-23): using them in Freda Verify for customers needs a commercial licence from the authors or another model with a licence that allows it.
# No weights are shipped or downloaded by this repository. Set FV_FACE_ARCFACE_PATH to a model file you are LICENSED to use, and FV_FACE_ARCFACE_THRESHOLD to a cosine threshold you MEASURED on your own
# lawful pairs (`python -m tools.face_eval`): SFace's 0.363 does not apply to other models. Without both, SFace stays in use.
_ARC_DST = [[38.2946, 51.6963], [73.5318, 51.5014], [56.0252, 71.7366], [41.5493, 92.3655], [70.7299, 92.2041]]     # standard 112x112 five-point template (right eye, left eye, nose, mouth corners)


def _arc_path() -> Path | None:
    p = os.environ.get("FV_FACE_ARCFACE_PATH", "").strip()
    return Path(p) if p and Path(p).is_file() else None


def arcface_active() -> bool:
    try:
        return _arc_path() is not None and float(os.environ.get("FV_FACE_ARCFACE_THRESHOLD", "")) > 0
    except ValueError:
        return False


def active_threshold() -> float:
    return float(os.environ["FV_FACE_ARCFACE_THRESHOLD"]) if arcface_active() else COSINE_THRESHOLD


def model_name() -> str:
    return f"ArcFace ({_arc_path().name}) + YuNet 2023mar" if arcface_active() else "SFace 2021dec + YuNet 2023mar"


def _arc_align(img, face_row):
    """112x112 aligned crop from the five YuNet landmarks (similarity transform to the standard template)."""
    import cv2
    import numpy as np
    pts = np.array([[float(face_row[i]), float(face_row[i + 1])] for i in range(4, 14, 2)], dtype=np.float32)
    m, _ = cv2.estimateAffinePartial2D(pts, np.array(_ARC_DST, dtype=np.float32), method=cv2.LMEDS)
    if m is None:
        raise ValueError("alignment failed")
    return cv2.warpAffine(img, m, (112, 112), borderValue=0)


_arc_net = None


def _arc_embed(img, face_row):
    import cv2
    import numpy as np
    global _arc_net
    if _arc_net is None:
        _arc_net = cv2.dnn.readNetFromONNX(str(_arc_path()))
    blob = cv2.dnn.blobFromImage(_arc_align(img, face_row), 1 / 127.5, (112, 112), (127.5, 127.5, 127.5), swapRB=True)
    _arc_net.setInput(blob)
    v = _arc_net.forward().astype(np.float32).ravel()
    return v / (np.linalg.norm(v) + 1e-12)


def band(score: float) -> str:
    thr = active_threshold()
    high = thr + (HIGH - COSINE_THRESHOLD)                 # same distance above the threshold as SFace's 'strong' band (uncalibrated for other models)
    return "high" if score >= high else "possible" if score >= thr else "low"


_lock = threading.Lock()          # OpenCV's detector keeps per-call state (input size): one comparison at a time per process
_models_cache: tuple | None = None


def _models():
    global _models_cache
    if _models_cache is None:
        import cv2
        d = model_dir()
        _models_cache = (cv2.FaceDetectorYN.create(str(d / DET), "", (320, 320), 0.6, 0.3, 5000), cv2.FaceRecognizerSF.create(str(d / REC), ""))
    return _models_cache


def embed(image: bytes, all_faces: bool = False) -> tuple[list, int]:
    """Face feature vector(s) of an image: the LARGEST face (or every face with all_faces=True). Returns (features, number_of_faces_found).
    Features are used in memory only (comparison, evaluation) and are never stored by the application."""
    img = _decode(image)
    if img is None:
        raise ValueError("undecodable image")
    with _lock:
        det, rec = _models()
        faces = _faces(det, img)
        picked = faces if all_faces else ([_largest(faces)] if faces else [])
        if arcface_active():
            return [_arc_embed(img, f) for f in picked], len(faces)
        return [rec.feature(rec.alignCrop(img, f)) for f in picked], len(faces)


def _dominant(image: bytes) -> bool:
    img = _decode(image)
    if img is None:
        return False
    with _lock:
        areas = sorted((float(f[2]) * float(f[3]) for f in _faces(_models()[0], img)), reverse=True)
    return len(areas) < 2 or areas[0] >= DOMINANCE * areas[1]


def cosine(a, b) -> float:
    import cv2
    if arcface_active():
        import numpy as np
        return float(np.dot(np.asarray(a).ravel(), np.asarray(b).ravel()))          # both are L2-normalised
    with _lock:
        return float(_models()[1].match(a, b, cv2.FaceRecognizerSF_FR_COSINE))


def compare(document_image: bytes, selfie_image: bytes) -> FaceOutcome:
    if not available():
        return FaceOutcome("unavailable")
    try:
        # a passport page can show the portrait twice (large + ghost image): every document face is compared and the best match is kept
        # (a stricter reading would use only the main portrait; the reviewer sees the photos anyway)
        doc_feats, n_doc = embed(document_image, all_faces=True)
        self_feats, n_self = embed(selfie_image)
        if n_self >= 2 and not _dominant(selfie_image):
            # 'selfie holding the ID' photos contain two faces: the person and the ID portrait. The ID portrait matches the document trivially (same card),
            # so if the person's face is not clearly the main one the score would be meaningless (or a spoof): refuse to score, let the reviewer look.
            return FaceOutcome("ambiguous", doc_faces=n_doc, selfie_faces=n_self)
        if not doc_feats:
            return FaceOutcome("no_doc_face", selfie_faces=n_self)
        if not self_feats:
            return FaceOutcome("no_selfie", doc_faces=n_doc)
        s = max(cosine(f, self_feats[0]) for f in doc_feats)
        return FaceOutcome("compared", round(s, 4), band(s), n_doc, n_self)
    except Exception:  # noqa: BLE001  an engine problem must never break a submission
        return FaceOutcome("error")
