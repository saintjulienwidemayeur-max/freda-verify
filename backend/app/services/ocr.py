"""Server-side reading of the machine-readable zone (MRZ) from an uploaded document photo.

Pipeline: bottom part of the image → grayscale, upscale, contrast → Tesseract (restricted to MRZ characters) → candidate lines →
ICAO 9303 parser/check-digit validator (app.services.mrz). The BEST candidate (most check digits passed) wins.

Honest limits: Tesseract is a general OCR engine, not trained on OCR-B; accuracy on real passports (curved pages, guilloche background, glare,
low-resolution phone photos) has NOT been measured. Passing check digits proves the TEXT is internally consistent, not that the document is genuine.
Output is advice for a human reviewer, never an automatic decision.
"""
import io
import shutil
import threading
from dataclasses import dataclass

from app.services.mrz import LAYOUTS, MrzError, MrzResult, parse_mrz

MAX_PIXELS = 40_000_000
_ALLOWED = set("ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789<")
_CONFIG = "--psm 6 -c tessedit_char_whitelist=ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789< -c load_system_dawg=0 -c load_freq_dawg=0"
_one_at_a_time = threading.Semaphore(1)        # Tesseract is CPU/RAM hungry: never run two readings at once on a small instance


@dataclass
class OcrOutcome:
    status: str                     # read | unreadable | unavailable
    result: MrzResult | None = None
    lines: list[str] | None = None


def available() -> bool:
    return shutil.which("tesseract") is not None


def _normalise(line: str) -> str:
    s = line.upper().replace(" ", "").replace("«", "<").replace("‹", "<").replace("〈", "<")
    return "".join(ch for ch in s if ch in _ALLOWED)


def _fit(line: str, size: int) -> str | None:
    """OCR often drops or adds a filler at the end of a line: accept ±3 characters by padding / trimming with '<' only."""
    if abs(len(line) - size) > 3:
        return None
    return line[:size] if len(line) >= size else line + "<" * (size - len(line))


def candidates(raw: str) -> list[list[str]]:
    lines = [_normalise(x) for x in raw.splitlines()]
    lines = [x for x in lines if len(x) >= 25]
    out: list[list[str]] = []
    for (size, count) in LAYOUTS:
        for i in range(0, len(lines) - count + 1):
            fitted = [_fit(x, size) for x in lines[i:i + count]]
            if all(fitted):
                out.append([x for x in fitted if x])
    return out


def _score(res: MrzResult) -> int:
    return sum(res.checks.values())


def read_mrz(image: bytes) -> OcrOutcome:
    if not available():
        return OcrOutcome("unavailable")
    try:
        import pytesseract
        from PIL import Image, ImageOps
        Image.MAX_IMAGE_PIXELS = MAX_PIXELS
        img = Image.open(io.BytesIO(image))
        img.load()
    except Exception:  # noqa: BLE001  corrupt image, decompression bomb, missing library
        return OcrOutcome("unreadable")
    w, h = img.size
    best: tuple[int, MrzResult, list[str]] | None = None
    with _one_at_a_time:
        for top in (0.60, 0.45):                                        # MRZ sits in the bottom ~30 % of a passport page / ID back
            crop = img.convert("L").crop((0, int(h * top), w, h))
            k = 1800 / max(1, crop.width)
            crop = crop.resize((1800, max(1, int(crop.height * k))))
            for variant in (ImageOps.autocontrast(crop, cutoff=2), ImageOps.autocontrast(crop, cutoff=2).point(lambda p: 255 if p > 140 else 0)):
                try:
                    text = pytesseract.image_to_string(variant, lang="eng", config=_CONFIG, timeout=25)
                except Exception:  # noqa: BLE001, S112  timeout or engine failure: try the next variant
                    continue
                for cand in candidates(text):
                    try:
                        res = parse_mrz(cand, fix_ocr=True)
                    except (MrzError, KeyError, IndexError, ValueError):
                        continue
                    sc = _score(res)
                    if best is None or sc > best[0]:
                        best = (sc, res, cand)
                if best and best[1].all_checks_passed:
                    return OcrOutcome("read", best[1], best[2])
    if best is None:
        return OcrOutcome("unreadable")
    return OcrOutcome("read", best[1], best[2])
