"""ICAO Doc 9303 machine-readable-zone parser and check-digit validator (TD1 ID cards, TD2, TD3 passports).

Deterministic and dependency-free. It validates the *internal consistency* of the MRZ text (check digits, dates,
field layout). It does NOT prove that a document is genuine, and it does not read the text from an image (OCR).
Check digits: weights 7-3-1 repeated; digits 0-9 keep their value, letters A-Z = 10..35, the filler '<' = 0.
"""
import re
from dataclasses import asdict, dataclass, field
from datetime import UTC, date, datetime

WEIGHTS = (7, 3, 1)
LAYOUTS = {(44, 2): "TD3", (36, 2): "TD2", (30, 3): "TD1"}
# characters OCR commonly confuses, applied only where the MRZ grammar requires digits / letters
TO_DIGIT = str.maketrans({"O": "0", "Q": "0", "D": "0", "I": "1", "Z": "2", "S": "5", "B": "8", "G": "6"})
TO_ALPHA = str.maketrans({"0": "O", "1": "I", "2": "Z", "5": "S", "8": "B", "6": "G"})


class MrzError(ValueError):
    """The text cannot be an MRZ (wrong number/length of lines, forbidden characters)."""


def char_value(c: str) -> int:
    if c.isdigit():
        return int(c)
    if "A" <= c <= "Z":
        return ord(c) - 55
    if c == "<":
        return 0
    raise MrzError(f"invalid MRZ character {c!r}")


def check_digit(data: str) -> int:
    return sum(char_value(c) * WEIGHTS[i % 3] for i, c in enumerate(data)) % 10


@dataclass
class MrzResult:
    format: str
    document_type: str
    issuing_country: str
    surname: str
    given_names: str
    document_number: str
    nationality: str
    birth_date: str | None
    sex: str
    expiry_date: str | None
    optional_data: str
    checks: dict[str, bool]
    all_checks_passed: bool
    expired: bool | None
    ocr_corrections: int = 0
    warnings: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return asdict(self)


def _clean(lines: list[str]) -> list[str]:
    out = [ln.strip().upper().replace(" ", "") for ln in lines if ln and ln.strip()]
    sizes = {len(ln) for ln in out}
    if len(sizes) != 1 or (next(iter(sizes)), len(out)) not in LAYOUTS:
        raise MrzError("expected 2 lines of 44 (passport), 2 lines of 36 or 3 lines of 30 (ID card) characters")
    for ln in out:
        bad = {c for c in ln if not (c.isdigit() or "A" <= c <= "Z" or c == "<")}
        if bad:
            raise MrzError(f"invalid characters in MRZ: {sorted(bad)}")
    return out


def _digits(s: str, fixes: list[int]) -> str:
    t = s.translate(TO_DIGIT)
    fixes[0] += sum(a != b for a, b in zip(s, t, strict=True))
    return t


def _alpha(s: str, fixes: list[int]) -> str:
    t = s.translate(TO_ALPHA)
    fixes[0] += sum(a != b for a, b in zip(s, t, strict=True))
    return t


def _date(yymmdd: str, birth: bool) -> date | None:
    if len(yymmdd) != 6 or not yymmdd.isdigit():
        return None
    yy, mm, dd = int(yymmdd[:2]), int(yymmdd[2:4]), int(yymmdd[4:])
    year = (1900 + yy) if (birth and 2000 + yy > datetime.now(UTC).year) else (2000 + yy)
    try:
        return date(year, mm, dd)
    except ValueError:
        return None


NAME_NOISE = "names zone contained digits (OCR noise, dropped): names are unreliable"


NAME_K_FIX = "names zone: '<' fillers read as 'K' were repaired (no check digit protects names: compare with the photo)"


def _filler_k(nm: str) -> str:
    """OCR often reads the '<' filler as 'K'. Repairs only patterns a real name cannot produce: 2+ K's touching the fillers ('KK<' or 'KK' at the end), and, when the
    surname / given-names separator '<<' is missing altogether, the first 'K<' (e.g. 'SAINT<JULIENK<WIDEMAYEUR' -> 'SAINT<JULIEN<<WIDEMAYEUR')."""
    out = re.sub(r"K{2,}(?=<|$)", lambda m: "<" * len(m.group()), nm)
    body = out.rstrip("<")
    if "<<" not in body and "K<" in body:
        out = out.replace("K<", "<<", 1)
    return out


def _names(raw: str) -> tuple[str, str]:
    surname, _, given = raw.partition("<<")
    return " ".join(surname.replace("<", " ").split()), " ".join(given.replace("<", " ").split())


def _ok(field_value: str, digit: str, optional: bool = False) -> bool:
    if optional and set(field_value) <= {"<"}:
        return digit in ("<", "0")
    return digit.isdigit() and check_digit(field_value) == int(digit)


def parse_mrz(lines: list[str], fix_ocr: bool = True) -> MrzResult:
    ls = _clean(lines)
    fmt = LAYOUTS[(len(ls[0]), len(ls))]
    fx = [0]
    d = (lambda s: _digits(s, fx)) if fix_ocr else (lambda s: s)      # digits expected
    a = (lambda s: _alpha(s, fx)) if fix_ocr else (lambda s: s)       # letters expected

    if fmt == "TD3":
        l1, l2 = ls
        names_raw, doc_no, doc_cd = l1[5:], l2[0:9], d(l2[9])
        nat, birth, birth_cd, sex = a(l2[10:13]), d(l2[13:19]), d(l2[19]), l2[20]
        exp, exp_cd, opt, opt_cd, comp_cd = d(l2[21:27]), d(l2[27]), l2[28:42], d(l2[42]), d(l2[43])
        # ICAO 9303 composite: document number + its digit, birth date + digit, expiry + digit, optional data + digit
        composite = l2[0:9] + doc_cd + birth + birth_cd + exp + exp_cd + opt + opt_cd
        checks = {"document_number": _ok(doc_no, doc_cd), "birth_date": _ok(birth, birth_cd), "expiry_date": _ok(exp, exp_cd),
                  "optional_data": _ok(opt, opt_cd, optional=True), "composite": _ok(composite, comp_cd)}
        dtype, country = l1[0:2], a(l1[2:5])
    elif fmt == "TD2":
        l1, l2 = ls
        names_raw, doc_no, doc_cd = l1[5:], l2[0:9], d(l2[9])
        nat, birth, birth_cd, sex = a(l2[10:13]), d(l2[13:19]), d(l2[19]), l2[20]
        exp, exp_cd, opt, comp_cd = d(l2[21:27]), d(l2[27]), l2[28:35], d(l2[35])
        composite = l2[0:9] + doc_cd + birth + birth_cd + exp + exp_cd + opt
        checks = {"document_number": _ok(doc_no, doc_cd), "birth_date": _ok(birth, birth_cd), "expiry_date": _ok(exp, exp_cd), "composite": _ok(composite, comp_cd)}
        dtype, country = l1[0:2], a(l1[2:5])
    else:  # TD1
        l1, l2, l3 = ls
        dtype, country, doc_no, doc_cd, opt = l1[0:2], a(l1[2:5]), l1[5:14], d(l1[14]), l1[15:30]
        birth, birth_cd, sex, exp, exp_cd = d(l2[0:6]), d(l2[6]), l2[7], d(l2[8:14]), d(l2[14])
        nat, opt2, comp_cd = a(l2[15:18]), l2[18:29], d(l2[29])
        names_raw = l3
        composite = l1[5:14] + doc_cd + opt + birth + birth_cd + exp + exp_cd + opt2
        checks = {"document_number": _ok(doc_no, doc_cd), "birth_date": _ok(birth, birth_cd), "expiry_date": _ok(exp, exp_cd), "composite": _ok(composite, comp_cd)}
        opt = (opt + opt2).strip("<")

    warnings: list[str] = []
    if dtype.startswith("P") and fmt != "TD3":
        warnings.append(f"a passport normally has 2 lines of 44 characters; this reading has {len(ls[0])}, so the end of the lines may have been cut off (photo edge or glare). "
                        "The overall check may fail for that reason even when the individual fields are right: compare with the photo")
    bd, ed = _date(birth, birth=True), _date(exp, birth=False)
    if bd is None:
        warnings.append("birth date is not a valid calendar date")
    if ed is None:
        warnings.append("expiry date is not a valid calendar date")
    if sex not in ("M", "F", "<", "X"):
        warnings.append("unexpected sex marker")
    nm = a(names_raw) if fix_ocr else names_raw
    if any(c.isdigit() for c in nm):
        warnings.append(NAME_NOISE)
        nm = "".join("<" if c.isdigit() else c for c in nm)
    if fix_ocr:
        k = _filler_k(nm)
        if k != nm:
            warnings.append(NAME_K_FIX)
            nm = k
    surname, given = _names(nm)
    return MrzResult(
        format=fmt, document_type=dtype.replace("<", ""), issuing_country=country, surname=surname, given_names=given,
        document_number=doc_no.replace("<", ""), nationality=nat, birth_date=bd.isoformat() if bd else None, sex="X" if sex == "<" else sex,
        expiry_date=ed.isoformat() if ed else None, optional_data=opt.replace("<", " ").strip() if isinstance(opt, str) else "",
        checks=checks, all_checks_passed=all(checks.values()) and bd is not None and ed is not None,
        expired=(ed < datetime.now(UTC).date()) if ed else None, ocr_corrections=fx[0], warnings=warnings,
    )
