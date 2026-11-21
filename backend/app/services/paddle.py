"""PaddleOCR text reader (PP-OCR detection + recognition models) run locally through `rapidocr-onnxruntime` (Apache-2.0 code and bundled ONNX models, no PaddlePaddle, no network, no
third-party API: decision D11 stays respected). Used for the PRINTED text of ID cards, next to Tesseract; MRZ reading stays with Tesseract + the ICAO check digits.
Measured 2026-11-20 on 45 real merchant documents (see CLAUDE.md): better than Tesseract on card dates and numbers, worse on passport names/dates, hence both are used.
The bundled recognition model is PP-OCRv3 (Chinese + Latin): accents and Haitian layouts have not been measured separately."""
import threading

from app.core.config import get_settings

_engine = None
_failed = False
_lock = threading.Lock()          # one reading at a time per process (RAM on small instances)
MAX_SIDE = 1600


def available() -> bool:
    if not get_settings().paddle_ocr_enabled or _failed:
        return False
    try:
        import rapidocr_onnxruntime  # noqa: F401
    except Exception:  # noqa: BLE001
        return False
    return True


def _get():
    global _engine, _failed
    if _engine is None:
        try:
            from rapidocr_onnxruntime import RapidOCR
            _engine = RapidOCR()
        except Exception:  # noqa: BLE001
            _failed = True
            return None
    return _engine


def _lines(result) -> str:
    """Boxes -> text lines: boxes whose vertical centres are within 60 % of a line height share a line, left to right."""
    boxes = []
    for box, text, _score in result:
        ys = [p[1] for p in box]
        xs = [p[0] for p in box]
        boxes.append((sum(ys) / 4, max(ys) - min(ys), min(xs), text))
    boxes.sort()
    lines: list[list[tuple[float, float, float, str]]] = []
    cy = None
    for b in boxes:
        if cy is None or abs(b[0] - cy) >= b[1] * 0.6:
            lines.append([])
        lines[-1].append(b)
        cy = b[0]
    return "\n".join(" ".join(t for _, _, _, t in sorted(ln, key=lambda b: b[2])) for ln in lines)


def read_text(image: bytes) -> str | None:
    """Printed text of a whole document photo; None when the engine, the image or the reading is unavailable. Never raises."""
    if not available():
        return None
    try:
        import cv2
        import numpy as np
        a = cv2.imdecode(np.frombuffer(image, np.uint8), cv2.IMREAD_COLOR)
        if a is None:
            return None
        k = MAX_SIDE / max(a.shape[:2])
        if k < 1:
            a = cv2.resize(a, None, fx=k, fy=k, interpolation=cv2.INTER_AREA)
        with _lock:
            eng = _get()
            if eng is None:
                return None
            res, _ = eng(a)
        return _lines(res) if res else ""
    except Exception:  # noqa: BLE001
        return None
