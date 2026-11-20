from datetime import UTC, datetime

import pytest

from app.services.mrz import MrzError, check_digit, parse_mrz

# ICAO Doc 9303 specimen data (Anna Maria Eriksson, "Utopia")
TD3 = ["P<UTOERIKSSON<<ANNA<MARIA<<<<<<<<<<<<<<<<<<<", "L898902C36UTO7408122F1204159ZE184226B<<<<<10"]
TD1 = ["I<UTOD231458907<<<<<<<<<<<<<<<", "7408122F1204159UTO<<<<<<<<<<<6", "ERIKSSON<<ANNA<MARIA<<<<<<<<<<"]


def td2(expiry="320415"):
    names = "I<UTOERIKSSON<<ANNA<MARIA".ljust(36, "<")
    doc, birth = "D23145890", "740812"
    body = doc + str(check_digit(doc)) + "UTO" + birth + str(check_digit(birth)) + "F" + expiry + str(check_digit(expiry)) + "<<<<<<<"
    comp = doc + str(check_digit(doc)) + birth + str(check_digit(birth)) + expiry + str(check_digit(expiry)) + "<<<<<<<"
    return [names, body + str(check_digit(comp))]


def test_check_digit_known_values():
    assert check_digit("520727") == 3          # example in ICAO 9303 part 3
    assert check_digit("L898902C3") == 6
    assert check_digit("740812") == 2


def test_td3_passport_specimen_is_fully_valid():
    r = parse_mrz(TD3)
    assert r.format == "TD3" and r.all_checks_passed and all(r.checks.values())
    assert (r.surname, r.given_names, r.document_number) == ("ERIKSSON", "ANNA MARIA", "L898902C3")
    assert (r.issuing_country, r.nationality, r.sex, r.document_type) == ("UTO", "UTO", "F", "P")
    assert (r.birth_date, r.expiry_date) == ("1974-08-12", "2012-04-15")
    assert r.expired is True and r.ocr_corrections == 0


def test_td1_id_card_specimen():
    r = parse_mrz(TD1)
    assert r.format == "TD1" and r.all_checks_passed and r.document_number == "D23145890" and r.surname == "ERIKSSON"


def test_td2_generated_with_correct_digits():
    r = parse_mrz(td2())
    assert r.format == "TD2" and r.all_checks_passed and r.expired is False


@pytest.mark.parametrize("line,idx,char,failed", [
    (1, 9, "7", "document_number"),    # wrong check digit of the document number
    (1, 19, "3", "birth_date"),
    (1, 27, "0", "expiry_date"),
    (1, 43, "1", "composite"),
])
def test_tampered_digit_is_detected(line, idx, char, failed):
    l2 = TD3[1][:idx] + char + TD3[1][idx + 1:]
    r = parse_mrz([TD3[0], l2])
    assert r.checks[failed] is False and r.all_checks_passed is False


def test_changed_data_without_updating_the_digit_fails():
    r = parse_mrz([TD3[0], TD3[1].replace("L898902C3", "L898902C4")])       # document number altered
    assert r.checks["document_number"] is False and r.checks["composite"] is False


def test_ocr_confusions_are_corrected_only_where_digits_are_required():
    noisy = TD3[1][:13] + "74O812" + TD3[1][19:]                           # birth date with a letter O instead of 0
    r = parse_mrz([TD3[0], noisy])
    assert r.all_checks_passed and r.ocr_corrections == 1
    assert parse_mrz([TD3[0], noisy], fix_ocr=False).checks["birth_date"] is False


def test_spaces_and_case_are_normalised():
    assert parse_mrz([TD3[0].lower() + " ", " " + TD3[1].lower()]).all_checks_passed


@pytest.mark.parametrize("lines", [["P<UTO"], [TD3[0]], [TD3[0], TD3[1][:-1]], ["A" * 44, "B" * 43]])
def test_wrong_layout_is_rejected(lines):
    with pytest.raises(MrzError):
        parse_mrz(lines)


def test_forbidden_characters_are_rejected():
    with pytest.raises(MrzError):
        parse_mrz([TD3[0], TD3[1].replace("L898902C3", "L898-02C3")])


def test_impossible_dates_are_reported():
    l2 = TD3[1][:13] + "741342" + TD3[1][19:]                              # month 13
    r = parse_mrz([TD3[0], l2])
    assert r.birth_date is None and "birth date" in " ".join(r.warnings) and r.all_checks_passed is False


def test_future_expiry_is_not_expired():
    year = datetime.now(UTC).year + 5
    assert parse_mrz(td2(expiry=f"{year % 100:02d}0415")).expired is False


def test_mrz_endpoint_requires_authentication_and_validates(client):
    assert client.post("/api/v1/tools/mrz/check", json={"lines": TD3}).status_code == 401
    from tests.conftest import auth, register
    t = register(client)
    ok = client.post("/api/v1/tools/mrz/check", json={"lines": TD3}, headers=auth(t))
    assert ok.status_code == 200 and ok.json()["all_checks_passed"] is True
    bad = client.post("/api/v1/tools/mrz/check", json={"lines": ["too", "short"]}, headers=auth(t))
    assert bad.status_code == 422 and bad.json()["error"]["code"] == "invalid_mrz"


def test_passport_read_as_36_character_layout_warns_about_cut_lines():
    # ICAO 9303 specimen (public, invented person); the second line is cut to 36 characters like a photo that lost the end of the line
    l1 = ("P<UTOERIKSSON<<ANNA<MARIA" + "<" * 19)
    l2 = "L898902C36UTO7408122F1204159ZE184226B<<<<<10"
    short = parse_mrz([l1[:36], l2[:36]])
    assert short.format == "TD2" and short.checks["document_number"] and short.checks["birth_date"] and short.checks["expiry_date"]
    assert not short.checks["composite"]
    assert any("cut off" in w for w in short.warnings)
    full = parse_mrz([l1, l2])
    assert full.format == "TD3" and full.all_checks_passed and not full.warnings
