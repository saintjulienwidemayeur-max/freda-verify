from datetime import date

from app.services import idtext

TODAY = date(2026, 11, 20)
CIN = """REPIBLIK AYITI  REPUBLIQUE D'HAITI
CARTE D'IDENTIFICATION NATIONALE
NOM / SIYATI: WIDEMAYEUR
PRENOM(S): SAINT JULIEN
DATE DE NAISSANCE / DAT NESANS: 01/11/2003   SEXE: M
NIF: 00-89-06-2024-5
DATE D'EXPIRATION: 15/03/2033
"""


def test_extracts_name_birth_number_and_expiry_from_labelled_text():
    f = idtext.extract(CIN, TODAY)
    assert f["name"] == "SAINT JULIEN WIDEMAYEUR" and f["birth_date"] == "2003-11-01" and f["document_number"] == "0089062024" + "5" and f["expiry_date"] == "2033-03-15"
    assert idtext.plausible(f, TODAY) == {"name": True, "birth_date": True, "document_number": True, "expired": False}


def test_month_name_dates_and_missing_labels():
    f = idtext.extract("DUPONT MARIE CLAIRE\nNEE LE 05 MARS 1990\nNO 1234567890", TODAY)
    assert f["birth_date"] == "1990-03-05" and f["document_number"] == "1234567890" and "DUPONT" in f["name"]


def test_implausible_or_empty_readings_are_flagged():
    assert idtext.extract("", TODAY) == {}
    p = idtext.plausible(idtext.extract("NOM: DUPONT\nNAISSANCE 01/01/2015\nNUMERO 12", TODAY), TODAY)
    assert p["birth_date"] is False and p["document_number"] is False and p["name"] is False         # a child, a short number, a one-word name
    old = idtext.plausible({"name": "A B", "birth_date": "1980-01-01", "document_number": "12345678", "expiry_date": "2020-01-01"}, TODAY)
    assert old["expired"] is True


def test_random_ocr_garbage_does_not_look_like_an_identity():
    f = idtext.extract("lorem ipsum dolor sit\n%%% ??? 12 34\n.", TODAY)
    assert not idtext.plausible(f, TODAY)["birth_date"] and not idtext.plausible(f, TODAY)["document_number"]


def test_merge_trusted_uses_mrz_dates_with_valid_check_digits():
    from app.services.idtext import merge_trusted
    mrz = {"checks": {"birth_date": True, "expiry_date": True, "document_number": False, "composite": True},
           "birth_date": "2003-11-01", "expiry_date": "2033-01-15", "document_number": "0D2FTC562"}
    f, src = merge_trusted({"name": "JEAN PIERRE", "birth_date": "1999-01-01"}, "Date de naissance 05/06/1990", mrz)
    assert f["birth_date"] == "2003-11-01" and src["birth_date"] == "mrz"
    assert f["expiry_date"] == "2033-01-15" and f["document_number"] == "0D2FTC562"   # composite covers the number
    assert f["name"] == "JEAN PIERRE"


def test_merge_trusted_ignores_mrz_dates_when_digit_fails_and_fills_from_back():
    from app.services.idtext import merge_trusted
    mrz = {"checks": {"birth_date": False, "expiry_date": False, "document_number": False, "composite": False}, "birth_date": "2003-11-01"}
    f, src = merge_trusted({"name": "A B"}, "Date de naissance 05/06/1990", mrz)
    assert f["birth_date"] == "1990-06-05" and src["birth_date"] == "back_text"


def test_mrz_name_digits_dropped_and_not_used_as_fallback():
    from app.services.mrz import parse_mrz
    r = parse_mrz(["IDHTI0D2FTC5620".ljust(30, "<"), "0311015M3301156HTI".ljust(29, "<") + "0", "3SAINT<4ULIEN<<WIDEMYEUR".ljust(30, "<")]).to_dict()
    assert not any(c.isdigit() for c in r["surname"] + r["given_names"])
    assert any("digits" in w for w in r["warnings"])
    from app.services.idtext import merge_trusted
    f, _ = merge_trusted({}, None, {**r, "checks": {"birth_date": True}})
    assert "name" not in f


def test_mrz_clean_name_is_fallback_when_front_has_none():
    from app.services.idtext import merge_trusted
    f, src = merge_trusted({}, None, {"checks": {}, "surname": "SAINT JULIEN", "given_names": "WIDEMYEUR", "warnings": []})
    assert f["name"] == "WIDEMYEUR SAINT JULIEN" and src["name"] == "mrz_unchecked"
