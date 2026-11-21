"""Consistency check between what the CUSTOMER DECLARED (the business passes `expected` when it creates the verification) and the text printed on an ID card / licence, read with Tesseract.

A national ID card (CIN) has no machine-readable zone and no check digits, so the only machine evidence of its content is whether the printed text agrees with the declared name, date
of birth and document number. This is a CONSISTENCY check, not proof of authenticity: a forged card can be printed with the declared data, and OCR of printed fields is unreliable
(measured on a real CIN: it misread a day and a 0/O). So it is only ever used as POSITIVE evidence together with the face comparison. The OCR text is never stored; only match results.
"""
import io
import re
import unicodedata
from datetime import date

MONTHS = {1: ("JAN", "JANV", "JANVIER", "JANUARY", "JANVYE"), 2: ("FEB", "FEV", "FEVR", "FEVRIER", "FEBRUARY", "FEVRIYE"), 3: ("MAR", "MARS", "MARCH", "MAS"),
          4: ("APR", "AVR", "AVRIL", "APRIL", "AVRIL"), 5: ("MAY", "MAI", "ME"), 6: ("JUN", "JUIN", "JUNE", "JEN"), 7: ("JUL", "JUIL", "JUILLET", "JULY", "JIYE"),
          8: ("AUG", "AOU", "AOUT", "AUGUST", "OUT"), 9: ("SEP", "SEPT", "SEPTEMBRE", "SEPTEMBER", "SEPTANM"), 10: ("OCT", "OCTOBRE", "OCTOBER", "OKTOB"),
          11: ("NOV", "NOVEMBRE", "NOVEMBER", "NOVANM"), 12: ("DEC", "DECEMBRE", "DECEMBER", "DESANM")}


def _norm(s: str) -> str:
    s = unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode().upper()
    return re.sub(r"[^A-Z0-9]+", " ", s).strip()


def _lev(a: str, b: str, cap: int = 2) -> int:
    if abs(len(a) - len(b)) > cap:
        return cap + 1
    prev = list(range(len(b) + 1))
    for i, ca in enumerate(a, 1):
        cur = [i]
        for j, cb in enumerate(b, 1):
            cur.append(min(prev[j] + 1, cur[j - 1] + 1, prev[j - 1] + (ca != cb)))
        prev = cur
    return prev[-1]


def name_score(expected: str, text: str) -> float:
    """Share of the declared name words found in the text (a word may carry one OCR error when it has >= 5 letters)."""
    words = [w for w in _norm(expected).split() if len(w) >= 2]
    if not words:
        return 0.0
    toks = _norm(text).split()
    hit = 0
    for w in words:
        tol = 1 if len(w) >= 5 else 0
        if any(_lev(w, t, tol) <= tol for t in toks if abs(len(t) - len(w)) <= tol):
            hit += 1
    return hit / len(words)


def number_match(expected: str, text: str) -> bool:
    """The declared document number appears in the text (spaces / dashes ignored, one wrong character allowed from 8 characters up)."""
    e = re.sub(r"[^A-Z0-9]", "", _norm(expected).replace(" ", ""))
    if len(e) < 5:
        return False
    hay = re.sub(r"[^A-Z0-9]", "", _norm(text).replace(" ", ""))
    tol = 1 if len(e) >= 8 else 0
    if e in hay:
        return True
    if tol:
        for ln in (len(e) - 1, len(e), len(e) + 1):
            for i in range(0, max(0, len(hay) - ln) + 1):
                if _lev(e, hay[i:i + ln], 1) <= 1:
                    return True
    return False


def birth_match(expected: date, text: str) -> bool:
    """Day, month and year of the declared birth date all appear (numeric forms such as 01/11/2003, 01-11-03, or a month name)."""
    n = _norm(text)
    d, m, y = f"{expected.day:02d}", f"{expected.month:02d}", f"{expected.year:04d}"
    compact = n.replace(" ", "")
    if any(x in compact for x in (d + m + y, d + m + y[2:], y + m + d)):
        return True
    toks = n.split()
    yy = {y, y[2:]}
    names = {x for x in MONTHS[expected.month]}
    has_d = d in toks or str(expected.day) in toks
    has_y = bool(yy & set(toks))
    has_m = m in toks or str(expected.month) in toks or any(t in names or (len(t) >= 3 and t[:3] in {x[:3] for x in names} and t[:3] != "MAR" or t in names) for t in toks)
    return has_d and has_m and has_y


def read_text(image: bytes) -> str | None:
    """Tesseract (generic model) over the whole card. None when the engine or the image is unavailable."""
    from app.services import ocr
    if not ocr.available():
        return None
    try:
        import pytesseract
        from PIL import Image, ImageOps
        img = Image.open(io.BytesIO(image))
        img.load()
        g = ImageOps.autocontrast(img.convert("L"), cutoff=1)
        k = 1800 / max(g.size)
        if k > 1:
            g = g.resize((int(g.width * k), int(g.height * k)))
        return pytesseract.image_to_string(g, lang="eng", config="--psm 6", timeout=25)
    except Exception:  # noqa: BLE001
        return None


def compare(expected: dict, text: str) -> dict:
    """Match results for the declared fields (only the ones the business supplied). No OCR text is returned."""
    out: dict = {"fields": 0, "matched": 0}
    if expected.get("name"):
        out["fields"] += 1
        sc = name_score(expected["name"], text)
        out["name"] = round(sc, 2)
        out["matched"] += 1 if sc >= 0.8 else 0
    if expected.get("document_number"):
        out["fields"] += 1
        out["number"] = number_match(expected["document_number"], text)
        out["matched"] += 1 if out["number"] else 0
    if expected.get("birth_date"):
        out["fields"] += 1
        try:
            out["birth"] = birth_match(date.fromisoformat(expected["birth_date"]), text)
        except ValueError:
            out["birth"] = False
        out["matched"] += 1 if out["birth"] else 0
    return out


# ───────── extraction of the identity data printed on an ID card / licence (no declared data needed) ─────────
HEADER_WORDS = {"REPUBLIQUE", "REPIBLIK", "AYITI", "HAITI", "CARTE", "KAT", "IDENTITE", "IDANTITE", "NATIONALE", "NASYONAL", "DIDENTIFICATION", "D", "IDENTIFICATION", "ONI",
                "NOM", "SIYATI", "PRENOM", "PRENOMS", "SEXE", "SEKS", "DATE", "NAISSANCE", "NESANS", "LIEU", "LOKAL", "NUMERO", "NIF", "CIN", "EXPIRATION", "EXPIRE", "VALABLE", "JUSQU",
                "AU", "DE", "DU", "LA", "LE", "ET", "SIGNATURE", "PERMIS", "CONDUIRE", "DRIVER", "LICENSE", "LICENCE", "NATIONALITE", "HAITIENNE", "HAITIEN", "M", "F"}
_DATE = re.compile(r"(?<!\d)(\d{1,2})\s*[/.\- ]\s*(\d{1,2})\s*[/.\- ]\s*(\d{4}|\d{2})(?!\d)")
_NUM = re.compile(r"(?<![A-Z0-9])((?:[A-Z]{0,3}\d[\dA-Z \-]{6,18}\d))(?![A-Z0-9])")


def _dates(text: str) -> list[tuple[date, str]]:
    found: list[tuple[date, str]] = []
    for ln in text.splitlines():
        n = ln.upper()
        for m in _DATE.finditer(n):
            d_, mo, y = int(m.group(1)), int(m.group(2)), int(m.group(3))
            y = y + (2000 if y < 40 else 1900) if y < 100 else y
            try:
                found.append((date(y, mo, d_), n))
            except ValueError:
                continue
        toks = _norm(ln).split()
        for i, t in enumerate(toks):
            if t.isdigit() and len(t) <= 2 and i + 2 < len(toks):
                mon = next((k for k, names in MONTHS.items() if toks[i + 1] in names), None)
                if mon and toks[i + 2].isdigit() and len(toks[i + 2]) in (2, 4):
                    y = int(toks[i + 2])
                    y = y + (2000 if y < 40 else 1900) if y < 100 else y
                    try:
                        found.append((date(y, mon, int(t)), n))
                    except ValueError:
                        pass
    return found


def extract(text: str, today: date | None = None) -> dict:
    """Best-effort identity fields from the printed text of an ID card / licence (no declared data needed). Heuristics: label-based first (Nom / Prénom / Date de naissance / numéro),
    then plausibility (dates in range, a name made of 2+ words, a number of 8+ characters). Returns only what was found; the caller must still treat it as UNVERIFIED reading."""
    today = today or date.today()
    out: dict = {}
    lines = [ln for ln in text.splitlines() if ln.strip()]
    nlines = [_norm(ln) for ln in lines]
    # name: words after the NOM / PRENOM labels, otherwise the longest all-letters lines that are not header words
    def after(label_re: str) -> str | None:
        for i, ln in enumerate(lines):
            m = re.search(label_re, _norm(ln))
            if m:
                rest = _norm(ln)[m.end():].strip()
                words = [w for w in rest.split() if w not in HEADER_WORDS and len(w) >= 2 and w.isalpha()]
                if not words and i + 1 < len(lines):
                    words = [w for w in nlines[i + 1].split() if w not in HEADER_WORDS and len(w) >= 2 and w.isalpha()]
                if words:
                    return " ".join(words)
        return None
    last = after(r"\bNOM\b|\bSIYATI\b")
    first = after(r"\bPRENOMS?\b|\bPRENM\b")
    if first or last:
        out["name"] = " ".join(x for x in (first, last) if x)
    else:
        cand = [" ".join(w for w in n.split() if w not in HEADER_WORDS and w.isalpha() and len(w) >= 2) for n in nlines]
        cand = [c for c in cand if len(c.split()) >= 2]
        if cand:
            out["name"] = max(cand, key=len)
    ds = _dates(text)
    birth = [d for d, ln in ds if re.search(r"NAISS|NESANS|BORN|BIRTH|NE LE|NEE", _norm(ln)) and 1900 <= d.year <= today.year - 14]
    if not birth:
        birth = [d for d, _ in ds if 1900 <= d.year <= today.year - 14 and d < today]
    if birth:
        out["birth_date"] = min(birth).isoformat() if len(birth) > 1 and not any(re.search(r"NAISS|NESANS", _norm(ln)) for _, ln in ds) else birth[0].isoformat()
    exp = [d for d, ln in ds if re.search(r"EXPIR|VALABLE|VALID|JUSQU", _norm(ln))] or [d for d, _ in ds if d > today]
    if exp:
        out["expiry_date"] = max(exp).isoformat()
    nums = []
    for ln in lines:
        n = ln.upper()
        for m in _NUM.finditer(n):
            raw = re.sub(r"[ \-]", "", m.group(1))
            if len(raw) >= 8 and sum(c.isdigit() for c in raw) >= 6 and not _DATE.fullmatch(m.group(1).strip()):
                nums.append((bool(re.search(r"NIF|NUMERO|CIN|N°|NO\b", n)), raw))
    if nums:
        out["document_number"] = sorted(nums, key=lambda t: (not t[0], -len(t[1])))[0][1]
    return out


def combine_engines(paddle_text: str | None, tess_text: str | None, today: date | None = None) -> tuple[dict, dict, dict]:
    """Extracts the printed fields with BOTH readers. PaddleOCR (PP-OCR) is preferred per field when it gives a plausible value, else Tesseract, else whichever exists.
    Returns (fields, sources, agree) where agree[field] is True when both engines gave the same value (more confidence, not proof)."""
    fp = extract(paddle_text, today) if paddle_text else {}
    ft = extract(tess_text, today) if tess_text else {}
    fields: dict = {}
    src: dict = {}
    agree: dict = {}
    for k in ("name", "birth_date", "document_number", "expiry_date"):
        a, b = fp.get(k), ft.get(k)
        if a is None and b is None:
            continue
        if k == "name" and a and b:
            same = name_score(a, b) >= 0.8 and name_score(b, a) >= 0.8
        elif k == "document_number" and a and b:
            same = re.sub(r"[^A-Z0-9]", "", a.upper()) == re.sub(r"[^A-Z0-9]", "", b.upper())
        else:
            same = a == b
        if a and b:
            agree[k] = same
        pk = {"name": "name", "birth_date": "birth_date", "document_number": "document_number"}.get(k)
        ok_a = a is not None and (pk is None or bool(plausible({k: a}, today)[pk]))
        use_a = a is not None and (b is None or ok_a)
        fields[k], src[k] = (a, "paddle") if use_a else (b, "tesseract")
    return fields, src, agree


def merge_trusted(fields: dict, back_text: str | None, mrz: dict | None, front_sources: dict | None = None) -> tuple[dict, dict]:
    """Completes the fields read from the card FRONT with (1) the printed text of the BACK (only fields still missing) and (2) the machine-readable zone of the back, but only the
    values whose own ICAO check digit passed (a birth date or expiry date whose digit is valid is far more reliable than printed-text OCR). The MRZ values take priority.
    The second returned dict says where each value came from. MRZ names are only a fallback when the front gave none and the reading has no digit noise."""
    out = dict(fields)
    src = {k: (front_sources or {}).get(k, "front_text") for k in out}
    if back_text:
        for k, val in extract(back_text).items():
            if k not in out:
                out[k], src[k] = val, "back_text"
    checks = (mrz or {}).get("checks") or {}
    if mrz:
        whole = bool(checks.get("composite")) and checks.get("birth_date") and checks.get("expiry_date")
        if checks.get("birth_date") and mrz.get("birth_date"):
            out["birth_date"], src["birth_date"] = mrz["birth_date"], "mrz"
        if checks.get("expiry_date") and mrz.get("expiry_date"):
            out["expiry_date"], src["expiry_date"] = mrz["expiry_date"], "mrz"
        mrz_name = " ".join(x for x in (mrz.get("given_names"), mrz.get("surname")) if x).strip()
        clean = mrz_name and not any("names zone contained digits" in w for w in mrz.get("warnings") or []) and mrz_name.replace(" ", "").isalpha()
        if clean and "name" not in out and len(mrz_name.split()) >= 2:
            out["name"], src["name"] = mrz_name, "mrz_unchecked"      # fallback only: no check digit protects names
        if (checks.get("document_number") or whole) and mrz.get("document_number"):
            out["document_number"], src["document_number"] = mrz["document_number"], "mrz"
    return out, src


def plausible(fields: dict, today: date | None = None) -> dict:
    """Checks on the extracted fields themselves (not a verification against any registry)."""
    today = today or date.today()
    name_words = [w for w in _norm(fields.get("name", "")).split() if len(w) >= 2]
    ok_name = len(name_words) >= 2
    ok_birth = False
    if fields.get("birth_date"):
        try:
            b = date.fromisoformat(fields["birth_date"])
            age = (today - b).days / 365.25
            ok_birth = 18 <= age <= 110
        except ValueError:
            pass
    ok_number = len(re.sub(r"[^A-Z0-9]", "", fields.get("document_number", "").upper())) >= 8
    expired = False
    if fields.get("expiry_date"):
        try:
            expired = date.fromisoformat(fields["expiry_date"]) < today
        except ValueError:
            pass
    return {"name": ok_name, "birth_date": ok_birth, "document_number": ok_number, "expired": expired}
