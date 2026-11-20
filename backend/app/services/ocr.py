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
_LANG: str | None = None


def reading_lang() -> str:
    """`ocrb` (Tesseract model trained on OCR-B, Apache-2.0, installed in the Docker image) when present, otherwise the generic `eng` model (much less accurate)."""
    global _LANG
    if _LANG is None:
        try:
            import pytesseract
            _LANG = "ocrb" if "ocrb" in pytesseract.get_languages(config="") else "eng"
        except Exception:  # noqa: BLE001
            _LANG = "eng"
    return _LANG


_one_at_a_time = threading.Semaphore(1)        # Tesseract is CPU/RAM hungry: never run two readings at once on a small instance


@dataclass
class OcrOutcome:
    status: str                     # read | unreadable | unavailable
    result: MrzResult | None = None
    lines: list[str] | None = None
    agreeing: int = 0              # independent readings (different crop / preprocessing) with every check digit valid AND the same fields


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


_FILLER_NOISE = set("KXCSEL")              # OCR-B "<" is often read as one of these (measured: K and X most often)
# (line index, start, end) of the optional-data fields whose check digit lets us decide whether a region is really all filler
_OPTIONAL = {"TD3": [(1, 28, 42)], "TD2": [(1, 28, 35)], "TD1": [(0, 15, 30), (1, 18, 29)]}
_NAMES_LINE = {"TD3": 0, "TD2": 0, "TD1": 2}


def _fix_names_tail(line: str) -> str:
    """A name never ends in a long run of K/X/C/S… after its first '<': that run is the filler '<<<<' misread. Keeps the last real letter."""
    i = line.find("<")
    while i != -1:
        tail = line[i:]
        if len(tail) >= 6 and all(c == "<" or c in _FILLER_NOISE for c in tail) and tail.count("<") >= len(tail) // 2:
            return line[:i] + "<" * len(tail)
        i = line.find("<", i + 1)
    return line


_DOCNO = {"TD3": (1, 0, 9, 9), "TD2": (1, 0, 9, 9), "TD1": (0, 5, 14, 14)}        # line, start, end, check-digit index
_SWAP = {"O": "0", "0": "O"}


def _docno_variants(cand: list[str], fmt: str) -> list[list[str]]:
    """The document number is alphanumeric, so the parser cannot know whether OCR-B 'O' / '0' was read right; its check digit can. Variants with
    O<->0 swapped (at most 4 ambiguous characters) are generated; the scoring step keeps the one whose check digit is valid."""
    li, a, b, _ = _DOCNO[fmt]
    field = cand[li][a:b]
    pos = [i for i, c in enumerate(field) if c in _SWAP][:4]
    out = []
    for mask in range(1, 1 << len(pos)):
        f = list(field)
        for bit, i in enumerate(pos):
            if mask >> bit & 1:
                f[i] = _SWAP[f[i]]
        v = list(cand)
        v[li] = cand[li][:a] + "".join(f) + cand[li][b:]
        out.append(v)
    return out


def repair_variants(cand: list[str]) -> list[list[str]]:
    """OCR-B reading errors on the filler character. Variants are scored later by the ICAO check digits, which decide which one is right
    (a region is only forced to '<' when that makes its check digit valid, because the optional data of a real document may contain letters)."""
    fmt = LAYOUTS.get((len(cand[0]), len(cand)))
    if not fmt:
        return [cand]
    out = [cand]
    regions = _OPTIONAL[f"TD{3 if fmt == 'TD3' else 2 if fmt == 'TD2' else 1}"]
    v = list(cand)
    for li, a, b in regions:
        v[li] = v[li][:a] + "".join("<" if c in _FILLER_NOISE or c == "<" else c for c in v[li][a:b]) + v[li][b:]
    out.append(v)
    w = list(v)
    for li, a, b in regions:
        w[li] = w[li][:a] + "<" * (b - a) + w[li][b:]
    out.append(w)
    ni = _NAMES_LINE[f"TD{3 if fmt == 'TD3' else 2 if fmt == 'TD2' else 1}"]
    fixed = []
    for var in out:
        nv = list(var)
        nv[ni] = _fix_names_tail(nv[ni])
        fixed.append(nv)
    allv = fixed + out
    extra = [w for v in out[:1] for w in _docno_variants(v, f"TD{3 if fmt == 'TD3' else 2 if fmt == 'TD2' else 1}")]
    return allv + extra                                     # repaired names first: on equal check-digit scores the first variant wins


def candidates(raw: str) -> list[list[str]]:
    lines = [_normalise(x) for x in raw.splitlines()]
    lines = [x for x in lines if len(x) >= 25]
    out: list[list[str]] = []
    for (size, count) in LAYOUTS:
        for i in range(0, len(lines) - count + 1):
            fitted = [_fit(x, size) for x in lines[i:i + count]]
            if all(fitted):
                out.extend(repair_variants([x for x in fitted if x]))
    return out


def _score(res: MrzResult) -> int:
    return sum(res.checks.values())


def _key(res: MrzResult) -> tuple:
    return (res.document_number, res.birth_date, res.expiry_date, res.nationality, res.issuing_country, res.sex)


def read_mrz(image: bytes, quick: bool = False) -> OcrOutcome:
    """Several independent readings (two crops × two preprocessings, then small rotations). A reading counts as a VOTE only when every ICAO check
    digit passes; the outcome carries how many independent readings agree (`agreeing`). One check digit is just one digit (a wrong text passes it
    about 1 time in 10), so a single valid reading is not proof; two agreeing readings are much stronger evidence.
    quick=True (used as an upload gate): one crop, two preprocessings, no rotations; the outcome says whether an MRZ-shaped text was found at all."""
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
    votes: dict[tuple, int] = {}
    kept: dict[tuple, tuple[MrzResult, list[str]]] = {}

    def run(variant) -> bool:
        """One Tesseract pass. Returns True once two independent readings agree."""
        nonlocal best
        try:
            text = pytesseract.image_to_string(variant, lang=reading_lang(), config=_CONFIG, timeout=25)
        except Exception:  # noqa: BLE001  timeout or engine failure: the other variants may still work
            return False
        seen: set[tuple] = set()
        for cand in candidates(text):
            try:
                res = parse_mrz(cand, fix_ocr=True)
            except (MrzError, KeyError, IndexError, ValueError):
                continue
            sc = _score(res)
            if best is None or sc > best[0]:
                best = (sc, res, cand)
            if res.all_checks_passed and _key(res) not in seen:
                seen.add(_key(res))
                votes[_key(res)] = votes.get(_key(res), 0) + 1
                kept.setdefault(_key(res), (res, cand))
        return any(v >= 2 for v in votes.values())

    def prep(top: float):
        crop = img.convert("L").crop((0, int(h * top), w, h))
        crop = crop.resize((1800, max(1, int(crop.height * 1800 / max(1, crop.width)))))
        crop = ImageOps.autocontrast(crop, cutoff=2)
        # Tesseract drops characters that touch the image border (a hand-held photo often ends right at the last '<'): a white margin keeps them
        return ImageOps.expand(crop, border=(90, 40), fill=255)

    done = False
    with _one_at_a_time:
        for top in ((0.60,) if quick else (0.60, 0.45)):                # MRZ sits in the bottom ~30 % of a passport page / ID back
            base = prep(top)
            for variant in (base, base.point(lambda p: 255 if p > 140 else 0)):
                if run(variant):
                    done = True
                    break
            if done:
                break
        if not done and not quick:                                      # tilted upload (the in-browser crop is upright): small rotations
            wide = prep(0.45)
            for angle in (-2, 2, -4, 4, -6, 6):
                if run(wide.rotate(angle, resample=Image.BICUBIC, expand=True, fillcolor=255)):
                    break
    if votes:
        k = max(votes, key=lambda x: votes[x])
        res, cand = kept[k]
        return OcrOutcome("read", res, cand, agreeing=votes[k])
    if best is None:
        return OcrOutcome("unreadable")
    return OcrOutcome("read", best[1], best[2], agreeing=0)
