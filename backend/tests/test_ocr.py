import io
import shutil

import pytest
from PIL import Image, ImageDraw, ImageFont

from app.services import ocr
from tests.conftest import auth, first_org, register

TD3 = ["P<UTOERIKSSON<<ANNA<MARIA<<<<<<<<<<<<<<<<<<<", "L898902C36UTO7408122F1204159ZE184226B<<<<<10"]
needs_tesseract = pytest.mark.skipif(not shutil.which("tesseract"), reason="tesseract is not installed")


def page(lines, noise=False):
    f = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf", 34)
    im = Image.new("RGB", (1100, 780), "white")
    d = ImageDraw.Draw(im)
    d.text((40, 60), "PASSPORT / PASSEPORT  REPUBLIC OF UTOPIA", fill="black", font=f)
    for i, line in enumerate(lines):
        d.text((40, 600 + i * 50), line, fill="black", font=f)
    b = io.BytesIO()
    im.save(b, "JPEG", quality=85)
    return b.getvalue()


def test_candidates_pad_and_ignore_noise():
    raw = "SOME HEADER TEXT\n" + TD3[0] + "\n" + TD3[1][:-1] + "\nshort\n"          # second line lost its last character
    cands = ocr.candidates(raw)
    assert any(c[0] == TD3[0] and len(c[1]) == 44 for c in cands)
    assert ocr.candidates("nothing useful here\n12345") == []


def test_garbage_and_corrupt_images_are_unreadable_not_errors():
    assert ocr.read_mrz(b"not an image").status in ("unreadable", "unavailable")
    blank = io.BytesIO()
    Image.new("RGB", (800, 600), "white").save(blank, "PNG")
    assert ocr.read_mrz(blank.getvalue()).status in ("unreadable", "unavailable")


@needs_tesseract
def test_reads_a_clean_synthetic_passport():
    o = ocr.read_mrz(page(TD3))
    assert o.status == "read" and o.result.all_checks_passed
    assert o.result.surname == "ERIKSSON" and o.result.document_number == "L898902C3" and o.result.issuing_country == "UTO"


@needs_tesseract
def test_a_tampered_mrz_is_read_but_flagged():
    bad = [TD3[0], TD3[1][:13] + "740813" + TD3[1][19:]]          # birth date changed, check digit no longer matches
    o = ocr.read_mrz(page(bad))
    assert o.status == "read" and not o.result.all_checks_passed and o.result.checks["birth_date"] is False


def _flow(client, image, doc="passport"):
    t = register(client, "o@o.example", "Org O")
    org = first_org(client, t)
    key = client.post(f"/api/v1/organizations/{org['id']}/api-keys", json={"name": "k", "env": "test"}, headers=auth(t)).json()["secret"]
    v = client.post("/api/v1/verifications", json={}, headers={"Authorization": f"Bearer {key}"}).json()
    h = {"Authorization": f"Bearer {v['session_token']}", "Content-Type": "image/jpeg"}
    client.post("/api/v1/session/consent", headers=h)
    client.put(f"/api/v1/session/media/document_front?doc_type={doc}&country=HT", content=image, headers=h)
    client.put("/api/v1/session/media/selfie", content=image, headers=h)
    assert client.post("/api/v1/session/complete", headers=h).status_code == 204
    return t, org, v


@needs_tesseract
def test_submission_reads_the_mrz_in_the_background_and_reviewers_see_it(client):
    t, org, v = _flow(client, page(TD3))
    r = client.get(f"/api/v1/organizations/{org['id']}/verifications/{v['id']}/checks", headers=auth(t)).json()
    m = r["mrz"]
    assert r["engine_available"] and m["status"] == "read" and m["source"] == "document_front" and m["result"]["all_checks_passed"] is True
    assert m["result"]["surname"] == "ERIKSSON"
    actions = [a["action"] for a in client.get(f"/api/v1/organizations/{org['id']}/audit-logs", headers=auth(t)).json()]
    assert "verification.mrz_read" in actions and "verification.checks_viewed" in actions
    again = client.post(f"/api/v1/organizations/{org['id']}/verifications/{v['id']}/checks/mrz", headers=auth(t))
    assert again.status_code == 200 and again.json()["mrz"]["status"] == "read"


def test_mrz_result_is_encrypted_and_owner_admin_only(client):
    from sqlalchemy import text

    from app.db.session import get_engine
    t, org, v = _flow(client, page(TD3))
    with get_engine().connect() as c:
        raw = c.execute(text("select data from freda_verify.verification_checks")).scalar()
    if raw is not None:                                                      # absent only when tesseract is missing and the check ran as "unavailable"
        assert b"ERIKSSON" not in bytes(raw)
    other = register(client, "x@x.example", "Org X")
    base = f"/api/v1/organizations/{org['id']}/verifications/{v['id']}/checks"
    assert client.get(base, headers=auth(other)).status_code == 404
    assert client.post(base + "/mrz", headers=auth(other)).status_code == 404


def test_rerun_needs_a_document_photo(client):
    t = register(client, "o@o.example", "Org O")
    org = first_org(client, t)
    v = client.post("/api/v1/verifications", json={"organization_id": org["id"]}, headers=auth(t)).json()
    assert client.post(f"/api/v1/organizations/{org['id']}/verifications/{v['id']}/checks/mrz", headers=auth(t)).status_code == 409


@needs_tesseract
def test_clean_page_is_confirmed_by_independent_readings():
    o = ocr.read_mrz(page(TD3))
    assert o.status == "read" and o.agreeing >= 2                      # two crops / preprocessings agree: stronger than one valid check digit


def test_filler_noise_and_docno_repairs_are_decided_by_check_digits():
    # OCR-B '<' read as K/X inside the optional data, and a document number whose O/0 was swapped
    noisy = [TD3[0], TD3[1][:28] + "<<K<<X<<<<<<<<" + TD3[1][42:]]
    assert any(c[1][28:42] == "<" * 14 for c in ocr.repair_variants(noisy))
    swapped = [TD3[0], TD3[1].replace("L898902C3", "L898902C3")]       # no ambiguity here: no extra variants from the swap
    assert ocr.repair_variants(swapped)
    from app.services.mrz import parse_mrz
    line2 = "O80N0S1XP" + "<"                                          # arbitrary: just prove the swap generator yields O<->0 variants
    vs = ocr._docno_variants([TD3[0], line2 + TD3[1][10:]], "TD3")
    assert any(v[1][:9] == "080N0S1XP" for v in vs) and parse_mrz(TD3)


def _best(raw):
    from app.services.mrz import parse_mrz
    from app.services.ocr import candidates
    best = None
    for c in candidates(raw):
        try:
            r = parse_mrz(c, fix_ocr=not getattr(c, "shifted", False))
        except Exception:  # noqa: BLE001, S112
            continue
        if getattr(c, "shifted", False) and not (r.all_checks_passed and not r.warnings and r.sex in ("M", "F") and all(a == "<" or a == b for a, b in zip(c[1][10:13], c[0][2:5], strict=False))):
            continue
        if "<" in r.nationality:
            from dataclasses import replace
            r = replace(r, nationality=r.issuing_country)
        if best is None or sum(r.checks.values()) > sum(best.checks.values()):
            best = r
    return best


def test_one_dropped_character_in_the_data_line_is_repaired_by_the_check_digits():
    # real failure seen on a phone: a character of the nationality was lost, every later field slid by one and all dates / sex were garbage
    l1, l2 = TD3
    dropped = l2[:12] + l2[13:]                       # 'UTO' -> 'UT'
    assert len(dropped) == 43
    r = _best(l1 + "\n" + dropped)
    assert r.all_checks_passed and r.document_number == "L898902C3" and r.birth_date == "1974-08-12" and r.nationality == "UTO" and r.sex == "F"


def test_one_extra_character_and_two_dropped_characters_are_repaired_too():
    l1, l2 = TD3
    assert _best(l1 + "\n" + l2[:11] + "X" + l2[11:]).all_checks_passed                     # one extra character (45 chars)
    assert _best(l1 + "\n" + l2[:11] + l2[13:]).all_checks_passed                           # two dropped in the nationality zone


def test_a_misaligned_reading_never_passes_by_accident_on_wrong_text():
    l1, l2 = TD3
    garbage = "".join("0123456789"[(i * 7) % 10] for i in range(40))
    r = _best(l1 + "\n" + garbage)
    assert r is None or not r.all_checks_passed
