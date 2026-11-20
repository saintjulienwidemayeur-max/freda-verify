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
MAX_SIDE = 1280


@dataclass
class FaceOutcome:
    status: str                    # compared | no_doc_face | no_selfie | unavailable | error
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


def band(score: float) -> str:
    return "high" if score >= HIGH else "possible" if score >= COSINE_THRESHOLD else "low"


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
        return [rec.feature(rec.alignCrop(img, f)) for f in picked], len(faces)


def cosine(a, b) -> float:
    import cv2
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
        if not doc_feats:
            return FaceOutcome("no_doc_face", selfie_faces=n_self)
        if not self_feats:
            return FaceOutcome("no_selfie", doc_faces=n_doc)
        s = max(cosine(f, self_feats[0]) for f in doc_feats)
        return FaceOutcome("compared", round(s, 4), band(s), n_doc, n_self)
    except Exception:  # noqa: BLE001  an engine problem must never break a submission
        return FaceOutcome("error")
