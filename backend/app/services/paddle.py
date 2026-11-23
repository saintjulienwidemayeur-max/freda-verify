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


def read_boxes(image: bytes) -> list[tuple[float, float, float, float, str]] | None:
    """Text boxes (x0, y0, x1, y1, text) in pixels of the (possibly downscaled) image, for layout-aware extraction. None when unavailable. Never raises."""
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
        def run(img):
            with _lock:
                eng = _get()
                if eng is None:
                    return None
                res, _ = eng(img)
            out = []
            for box, text, _score in res or []:
                xs, ys = [p[0] for p in box], [p[1] for p in box]
                out.append((float(min(xs)), float(min(ys)), float(max(xs)), float(max(ys)), str(text)))
            return out

        out = run(a)
        if out is None:
            return None
        tall = sum(1 for b in out if (b[3] - b[1]) > 1.5 * (b[2] - b[0]))
        if len(out) >= 4 and tall > len(out) / 2:                                     # photo taken sideways: the text lines are vertical, try both quarter turns
            def score(bx):
                return sum(len(b[4]) for b in bx if (b[2] - b[0]) > (b[3] - b[1])) + 50 * sum(1 for b in bx if "HAITI" in b[4].upper() or "IDENTIFICATION" in b[4].upper())
            cands = [out] + [r for r in (run(cv2.rotate(a, rot)) for rot in (cv2.ROTATE_90_CLOCKWISE, cv2.ROTATE_90_COUNTERCLOCKWISE)) if r]
            out = max(cands, key=score)
        return out
    except Exception:  # noqa: BLE001
        return None


def boxes_to_text(boxes) -> str:
    return _lines([([[b[0], b[1]], [b[2], b[1]], [b[2], b[3]], [b[0], b[3]]], b[4], 1.0) for b in boxes]) if boxes else ""


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


FAST_SIDE = 960


def count_text_fast(image: bytes) -> int | None:
    """Number of alphanumeric characters found on a DOWNSCALED copy (960 px, no angle classifier): a quick 'is there printed text?' test for the upload gate. None when unavailable."""
    if not available():
        return None
    try:
        import cv2
        import numpy as np
        a = cv2.imdecode(np.frombuffer(image, np.uint8), cv2.IMREAD_COLOR)
        if a is None:
            return None
        k = FAST_SIDE / max(a.shape[:2])
        if k < 1:
            a = cv2.resize(a, None, fx=k, fy=k, interpolation=cv2.INTER_AREA)
        with _lock:
            eng = _get()
            if eng is None:
                return None
            res, _ = eng(a, use_cls=False)
        return sum(c.isalnum() for _b, t, _s in (res or []) for c in str(t))
    except Exception:  # noqa: BLE001
        return None


def warm_up() -> None:
    """Loads the models once in the background at startup, so the first customer does not wait for it."""
    if available():
        try:
            import numpy as np
            with _lock:
                eng = _get()
            if eng is not None:
                with _lock:
                    eng(np.full((64, 256, 3), 255, np.uint8), use_cls=False)
        except Exception:  # noqa: BLE001  warm-up is best effort
            import logging
            logging.getLogger("freda").warning("OCR warm-up failed")
