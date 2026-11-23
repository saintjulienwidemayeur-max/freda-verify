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


def letters_overlap(a: str, b: str) -> float:
    """Order-insensitive, K-tolerant similarity of two names: share of the letters (K excluded: OCR reads the MRZ filler '<' as K) that both contain. Used ONLY as a lenient
    second opinion for the printed-name vs MRZ-name cross-check, where OCR noise (K for '<', one wrong letter) breaks word-by-word matching. It does not see word order,
    so a swap of surname and given name is not detected: the result is advisory, a person decides."""
    from collections import Counter
    ca = Counter(c for c in _norm(a) if c.isalpha() and c != "K")
    cb = Counter(c for c in _norm(b) if c.isalpha() and c != "K")
    n = max(sum(ca.values()), sum(cb.values()))
    return sum((ca & cb).values()) / n if n else 0.0


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
                "AU", "DE", "DU", "LA", "LE", "ET", "SIGNATURE", "PERMIS", "CONDUIRE", "DRIVER", "LICENSE", "LICENCE", "NATIONALITE", "HAITIENNE", "HAITIEN", "M", "F",
                # labels of the Haitian CIN (bilingual French / Kreyòl, from the ONI specimen): 'Prénom / Non', 'Nom / Siyati', 'Dat ou fèt', 'Kote ou fèt', 'Dat kat la fini'...
                "NON", "DAT", "OU", "FET", "KOTE", "FINI", "NASYONALITE", "AYISYEN", "NIMEWO", "IDANTIFIKASYON", "INIK", "UNIQUE", "EMISSION", "TITULAIRE",
                "DAYITI", "DEPARTEMENT", "COMMUNE", "TITILE",
                # other countries (English / Spanish / Portuguese / German / Italian label words): never a person's name
                "SURNAME", "LAST", "FAMILY", "GIVEN", "FIRST", "NAMES", "NAME", "BIRTH", "BORN", "OF", "SEX", "GENDER", "NATIONALITY", "CITIZEN", "EXPIRY", "EXPIRES", "ISSUE", "ISSUED",
                "VALID", "UNTIL", "NUMBER", "NO", "DOCUMENT", "PASSPORT", "IDENTITY", "NATIONAL", "CARD", "STATE", "COUNTRY", "REPUBLIC", "KINGDOM", "UNITED", "DRIVING", "CLASS", "ADDRESS", "HOLDER", "PLACE", "AUTHORITY",
                "APELLIDOS", "NOMBRES", "NOMBRE", "FECHA", "NACIMIENTO", "SEXO", "NACIONALIDAD",
                "DOCUMENTO", "CEDULA", "IDENTIDAD", "REPUBLICA", "SOBRENOME", "NASCIMENTO", "NOME", "VALIDADE", "NACIONALIDADE", "NACHNAME", "VORNAME", "GEBURTSDATUM", "STAATSANGEHORIGKEIT",
                "PERSONALAUSWEIS", "BUNDESREPUBLIK", "DEUTSCHLAND", "COGNOME", "DATA", "NASCITA", "CITTADINANZA", "CARTA", "IDENTITA", "PATENTE", "GUIDA", "TIPO", "DNI"}
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
    last = after(r"\bNOM\b|\bSIYATI\b|\bSURNAME\b|\bLAST NAME\b|\bFAMILY NAME\b|\bAPELLIDOS?\b|\bSOBRENOME\b|\bNACHNAME\b|\bCOGNOME\b")
    first = after(r"\bPRENOMS?\b|\bPRENM\b|\bGIVEN NAMES?\b|\bFIRST NAMES?\b|\bFORENAMES?\b|\bNOMBRES?\b|\bVORNAME\b|\bNOME\b")
    if first or last:
        out["name"] = " ".join(x for x in (first, last) if x)
    else:
        cand = [" ".join(w for w in n.split() if w not in HEADER_WORDS and w.isalpha() and len(w) >= 2) for n in nlines]
        cand = [c for c in cand if len(c.split()) >= 2]
        if cand:
            out["name"] = max(cand, key=len)
    ds = _dates(text)
    birth = [d for d, ln in ds if re.search(r"NAISS|NESANS|BORN|BIRTH|DOB|NE LE|NEE|NACIMIENTO|NASCIMENTO|GEBURT|NASCITA", _norm(ln)) and 1900 <= d.year <= today.year - 14]
    if not birth:
        birth = [d for d, _ in ds if 1900 <= d.year <= today.year - 14 and d < today]
    if birth:
        out["birth_date"] = min(birth).isoformat() if len(birth) > 1 and not any(re.search(r"NAISS|NESANS", _norm(ln)) for _, ln in ds) else birth[0].isoformat()
    exp = [d for d, ln in ds if re.search(r"EXPIR|VALABLE|VALID|JUSQU|VENCE|VENCIMIENTO|VALIDADE|GULTIG|GUELTIG|SCADENZA|EXP\b", _norm(ln))] or [d for d, _ in ds if d > today]
    if exp:
        out["expiry_date"] = max(exp).isoformat()
    # labelled numbers on the Haitian CIN: 'Numéro de carte / Nimewo kat la' (alphanumeric, also the number of the MRZ on the back) and
    # 'Numéro d'identification unique / Nimewo idantifikasyon inik' (10 digits, the person's permanent number)
    def labelled(label_re: str, value_re: str) -> str | None:
        for i, ln in enumerate(lines):
            m = re.search(label_re, _norm(ln))
            if not m:
                continue
            for cand in [_norm(ln)[m.end():]] + [_norm(x) for x in lines[i + 1:i + 3]]:
                v = re.search(value_re, cand.replace(" ", "")) if cand else None
                if v:
                    return v.group(0)
        return None
    card_no = labelled(r"NIMEWO KAT|NUMERO DE CARTE", r"(?=(?:[A-Z]*\d){2})[A-Z0-9]{8,10}")
    nid = labelled(r"IDANTIFIKASYON INIK|IDENTIFICATION UNIQUE", r"\d{9,12}")
    if card_no:
        out["card_number"] = card_no
    if nid:
        out["national_id"] = nid
    nums = []
    for ln in lines:
        n = ln.upper()
        for m in _NUM.finditer(n):
            raw = re.sub(r"[ \-]", "", m.group(1))
            if len(raw) >= 8 and sum(c.isdigit() for c in raw) >= 6 and not _DATE.fullmatch(m.group(1).strip()):
                nums.append((bool(re.search(r"NIF|NUMERO|CIN|N°|NO\b|NUMBER|DOCUMENT|ID NO|DNI|LICENSE NO|LICENCE NO", n)), raw))
    if out.get("card_number"):
        out["document_number"] = out["card_number"]                      # the number that is also in the MRZ of the back
    elif nums:
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


# ───────── layout-aware extraction for the Haitian CIN (text boxes from PaddleOCR) ─────────
# Layout seen on the ONI specimen and on 20 real cards: photo on the left; a middle column 'Prénom / Non' -> first name, 'Nom / Siyati' -> surname,
# 'Lieu de naissance', 'Date d'émission', signature; a right column 'Numéro de carte' -> card number, 'Sexe', 'Nationalité', 'Date de naissance',
# 'Date d'expiration', 'Numéro d'identification unique' -> 10 digits. OCR often garbles the LABELS, so values are found by geometry + value shape.
_DATE_BOX = re.compile(r"^(\d{1,2})\s*[-/.]\s*(\d{1,2})\s*[-/.]\s*(\d{4})$")


def _near(word: str, key: str, tol: int = 1) -> bool:
    return abs(len(word) - len(key)) <= tol and _lev(word, key, tol) <= tol


def _has_label(t: str, *keys: str) -> bool:
    ws = re.findall(r"[A-Z]+", _norm(t))
    return any(_near(w, k, 1 if len(k) < 7 else 2) for w in ws for k in keys)


_LABEL_KEYS = ("PRENOM", "PRENON", "SIYATI", "NAISSANCE", "NOM", "SEXE", "SEKS", "NATIONALITE", "NASYONALITE", "EMISSION", "EXPIRATION", "SIGNATURE",
               "TITULAIRE", "NUMERO", "NIMEWO", "IDENTIFICATION", "IDANTIFIKASYON", "UNIQUE", "INIK", "CARTE", "REPUBLIQUE", "REPIBLIK", "LIEU", "KOTE", "DAT", "FINI")


_GLUED_LABEL = re.compile(r"PRENOM|[A-Z0-9]{1,6}[7TIL1|]NON\b|N[O0][MN][7TIL1|]?S[I1]YAT")   # 'Prénom / Non' or 'Nom / Siyati' with the '/' read as 7, T, I, 1...


def _is_label(t: str) -> bool:
    return "/" in t or _has_label(t, *_LABEL_KEYS) or bool(_GLUED_LABEL.search(_norm(t).replace(" ", "")))


def _name_value(t: str) -> str | None:
    words = [w for w in _norm(t).replace("-", " ").split() if w.isalpha() and len(w) >= 2 and w not in HEADER_WORDS]
    return " ".join(words) if words and not _is_label(t) else None


def extract_boxes(boxes, today: date | None = None) -> dict:
    """Fields of a Haitian CIN front from PaddleOCR boxes (x0, y0, x1, y1, text). Returns {} when the layout is not recognised (no surname label found)."""
    today = today or date.today()
    if not boxes:
        return {}
    W = max(b[2] for b in boxes) or 1.0
    out: dict = {}
    bs = sorted(boxes, key=lambda b: (b[1], b[0]))
    sur_lab = next((b for b in bs if _has_label(b[4], "SIYATI") and not _has_label(b[4], "SIGNATURE", "TITULAIRE", "TITILE")), None)
    if sur_lab is None:                                                                        # 'Siyati' garbled: a box that STARTS with the word NOM (not 'Prénom / Non', not 'Numéro')
        sur_lab = next((b for b in bs if re.match(r"\s*N[O0][MN]\b", _norm(b[4])) and not _has_label(b[4], "PRENOM", "PRENON", "NUMERO")), None)
    if sur_lab is None:
        return {}
    h = max(sur_lab[3] - sur_lab[1], 1.0)
    col = lambda b: abs(b[0] - sur_lab[0]) < 0.06 * W                                          # noqa: E731  same column as the surname label

    cy = lambda b: (b[1] + b[3]) / 2                                                           # noqa: E731  box centres: robust to a tilted photo where boxes overlap vertically
    below = [b for b in bs if col(b) and cy(b) > cy(sur_lab) + 0.3 * h and b[1] <= sur_lab[3] + 2.2 * h and b is not sur_lab]
    surname = next((v for v in (_name_value(b[4]) for b in below) if v), None)
    above = [b for b in sorted(bs, key=cy, reverse=True) if col(b) and cy(b) < cy(sur_lab) - 0.3 * h and sur_lab[1] - b[3] < 4 * h]
    firsts: list[str] = []
    for b in above:                                                                            # the value boxes stacked just above the surname label (a long first name can take 2 lines)
        v = _name_value(b[4])
        if not v:
            if firsts or _is_label(b[4]) or any(c.isdigit() for c in b[4]):
                break
            continue
        firsts.append(v)
    first = " ".join(reversed(firsts)) or None
    if first or surname:
        out["name"] = " ".join(x for x in (first, surname) if x)
        out["first_name"], out["surname"] = first, surname

    dates = []
    for b in bs:
        m = _DATE_BOX.match(re.sub(r"\s+", "", b[4]).replace("O", "0"))
        if m:
            try:
                dates.append((date(int(m.group(3)), int(m.group(2)), int(m.group(1))), b))
            except ValueError:
                pass
    births = [d for d, _ in dates if 1900 <= d.year and (today - d).days / 365.25 >= 14]
    if births:
        out["birth_date"] = min(births).isoformat()
    later = [d for d, _ in dates if d > today]
    if later:
        out["expiry_date"] = max(later).isoformat()
    for b in bs:
        raw = re.sub(r"[\s\-]", "", _norm(b[4]))
        if re.fullmatch(r"\d{10}", raw) and "national_id" not in out:
            out["national_id"] = raw
            continue
        if b[0] > sur_lab[0] + 0.15 * W and cy(b) < cy(sur_lab) and "card_number" not in out:      # right column, above the names: 'Numéro de carte' (alone or glued to its label)
            for tok in _norm(b[4]).replace("/", " ").split():
                if re.fullmatch(r"[A-Z0-9]{8,10}", tok) and sum(c.isdigit() for c in tok) >= 2 and sum(c.isalpha() for c in tok) >= 1:
                    out["card_number"] = tok
                    break
    if out.get("card_number"):
        out["document_number"] = out["card_number"]
    elif out.get("national_id"):
        out["document_number"] = out["national_id"]
    return out


# ───────── generic layout (any country): a printed LABEL (in several languages) and its VALUE, found by position ─────────
# Works for cards where the value sits to the right of its label or just below it. It only finds what has a recognisable label; anything else is left for the text rules,
# and for a person. NOT measured on real cards of other countries (only synthetic boxes in the tests).
_GENERIC_LABELS = {
    "surname": (r"SURNAME|LAST NAME|FAMILY NAME|NOM\b|APELLIDOS?|SOBRENOME|NACHNAME|NAME\b(?! OF)|COGNOME|SIYATI",),
    "given": (r"GIVEN NAMES?|FIRST NAMES?|FORENAMES?|PRENOMS?|NOMBRES?|VORNAME|PRENOM|NOME\b",),
    "birth": (r"DATE OF BIRTH|\bDOB\b|DATE DE NAISSANCE|FECHA DE NACIMIENTO|NASCIMENTO|GEBURTSDATUM|DATA DI NASCITA|NAISSANCE|BIRTH|NACIMIENTO",),
    "expiry": (r"EXPIR|DATE D EXPIRATION|VALID UNTIL|VALID THRU|VALABLE|VENCIMIENTO|VENCE|VALIDADE|GULTIG|GUELTIG|SCADENZA|\bEXP\b",),
    "number": (r"DOCUMENT N|ID N|IDENTITY N|CARD N|LICEN[SC]E N|PASSPORT N|NUMERO|NUMBER|N DOCUMENT|\bDNI\b|CEDULA|\bNIF\b|\bNO\b",),
}


def _label_kind(t: str) -> str | None:
    n = _norm(t)
    for k in ("birth", "expiry", "given", "surname", "number"):               # most specific first ('date of birth' before 'name')
        if any(re.search(rx, n) for rx in _GENERIC_LABELS[k]):
            return k
    return None


def _date_in(t: str, today: date) -> date | None:
    for d_, _ln in _dates(t):
        return d_
    return None


def extract_boxes_generic(boxes, today: date | None = None) -> dict:
    """Fields from PaddleOCR boxes (x0, y0, x1, y1, text) of ANY card: for each label box the value is the rest of the same box (after ':' or the label words), else the nearest box
    to its right on the same row, else the box right below it. Returns {} when nothing was found. Unverified reading."""
    today = today or date.today()
    if not boxes:
        return {}
    bs = sorted(boxes, key=lambda b: (b[1], b[0]))
    cy = lambda b: (b[1] + b[3]) / 2                                              # noqa: E731
    out: dict = {}
    found: dict[str, str] = {}
    for b in bs:
        kind = _label_kind(b[4])
        if kind is None or kind in found:
            continue
        txt = b[4]
        # value in the same box: text after ':' or after the label words
        after = re.split(r"[:：]", txt, maxsplit=1)[1].strip() if re.search(r"[:：]", txt) else ""
        cands = [after] if after else []
        h = max(b[3] - b[1], 1.0)
        right = sorted((o for o in bs if o is not b and o[0] >= b[2] - 0.2 * h and abs(cy(o) - cy(b)) < 0.7 * h), key=lambda o: o[0])
        below = sorted((o for o in bs if o is not b and cy(o) > cy(b) + 0.4 * h and o[1] <= b[3] + 2.0 * h and abs(o[0] - b[0]) < 3.0 * h + 0.25 * (b[2] - b[0])), key=lambda o: o[1])
        cands += [o[4] for o in right[:1]] + [o[4] for o in below[:1]]
        for c in cands:
            if not c or _label_kind(c) is not None and not after:
                continue
            if kind in ("birth", "expiry"):
                d_ = _date_in(c, today)
                if d_:
                    found[kind] = d_.isoformat()
                    break
            elif kind in ("surname", "given"):
                words = [w for w in _norm(c).split() if w.isalpha() and len(w) >= 2 and w not in HEADER_WORDS]
                if words:
                    found[kind] = " ".join(words)
                    break
            else:
                raw = re.sub(r"[\s\-]", "", _norm(c))
                if re.fullmatch(r"[A-Z0-9]{6,20}", raw) and sum(ch.isdigit() for ch in raw) >= 4:
                    found[kind] = raw
                    break
    if found.get("surname") or found.get("given"):
        out["name"] = " ".join(x for x in (found.get("given"), found.get("surname")) if x)
        out["first_name"], out["surname"] = found.get("given"), found.get("surname")
    if "birth" in found:
        d_ = date.fromisoformat(found["birth"])
        if 1900 <= d_.year and (today - d_).days / 365.25 >= 14:
            out["birth_date"] = found["birth"]
    if "expiry" in found:
        out["expiry_date"] = found["expiry"]
    if "number" in found:
        out["document_number"] = found["number"]
    return out
