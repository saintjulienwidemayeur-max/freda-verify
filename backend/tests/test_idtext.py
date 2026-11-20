from datetime import date

from app.services import idtext

TEXT = """REPIBLIK AYITI  CARTE D'IDENTITE NATIONALE
Nom: WIDEMAYEUR  Prenom: SAINT JULIEN
Date de naissance: 01/11/2003   Sexe: M
NIF: 00-89-06-2024-5   Lieu: Mirebalais
"""


def test_name_matches_with_one_ocr_error_and_in_any_order():
    assert idtext.name_score("Saint Julien Widemayeur", TEXT) == 1.0
    assert idtext.name_score("Julien WIDEMAYEUR", TEXT.replace("WIDEMAYEUR", "WIDEMAYEUF")) == 1.0      # one wrong letter in a long word is tolerated
    assert idtext.name_score("Marie Dupont", TEXT) == 0.0
    assert idtext.name_score("", TEXT) == 0.0


def test_document_number_ignores_separators_and_tolerates_one_character():
    assert idtext.number_match("0089062024-5", TEXT)
    assert idtext.number_match("00 89 06 2024 5", TEXT)
    assert idtext.number_match("0089062O245", TEXT)                      # O instead of 0 (one wrong character) from 8 characters up
    assert not idtext.number_match("1234567890", TEXT)
    assert not idtext.number_match("123", TEXT)


def test_birth_date_in_numeric_and_month_name_forms():
    assert idtext.birth_match(date(2003, 11, 1), TEXT)
    assert idtext.birth_match(date(2003, 11, 1), "Né le 01 Nov 2003 à Mirebalais")
    assert idtext.birth_match(date(2003, 11, 1), "naissance 01-11-03")
    assert not idtext.birth_match(date(2003, 11, 2), TEXT)
    assert not idtext.birth_match(date(1999, 11, 1), TEXT)


def test_compare_counts_only_declared_fields_and_returns_no_text():
    r = idtext.compare({"name": "Saint Julien Widemayeur", "birth_date": "2003-11-01", "document_number": None}, TEXT)
    assert r == {"fields": 2, "matched": 2, "name": 1.0, "birth": True}
    assert "REPIBLIK" not in str(r)
    assert idtext.compare({}, TEXT) == {"fields": 0, "matched": 0}
