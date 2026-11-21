from app.services import idtext

# text laid out like the public ONI specimen of the new Haitian CIN (oni.gouv.ht, 'carte-5.jpg'; fictitious data on the specimen)
SPECIMEN = """RÉPUBLIQUE D'HAITI
REPIBLIK DAYITI
CARTE D'IDENTIFICATION NATIONALE
KAT IDANTIFIKASYON NASYONAL
Numéro de carte / Nimewo kat la
T1K2N89G7
Prénom / Non
PATRICIA
Sexe / Sèks
F
Nom / Siyati
DELAIRE
Nationalité / Nasyonalite
Haïtien / Ayisyen
Date de Naissance / Dat ou fèt
01-01-1987
Lieu de Naissance / Kote ou fèt
Département Ouest, Commune Port-au-Prince
Date d'émission /
Dat kat la fèt
07-02-2018
Date d'expiration /
Dat kat la fini
06-02-2028
Signature du titulaire /
Numéro d'identification unique /
Nimewo idantifikasyon inik
0123456789"""


def test_specimen_gives_both_names_and_both_numbers():
    f = idtext.extract(SPECIMEN)
    assert f["name"] == "PATRICIA DELAIRE"
    assert f["birth_date"] == "1987-01-01" and f["expiry_date"] == "2028-02-06"
    assert f["card_number"] == "T1K2N89G7" and f["document_number"] == "T1K2N89G7"
    assert f["national_id"] == "0123456789"
    assert all(v for k, v in idtext.plausible(f).items() if k != "expired")


def test_specimen_with_values_on_the_same_line():
    t = SPECIMEN.replace("Prénom / Non\nPATRICIA", "Prénom / Non PATRICIA").replace("Nom / Siyati\nDELAIRE", "Nom / Siyati DELAIRE")
    assert idtext.extract(t)["name"] == "PATRICIA DELAIRE"


def _boxes():
    # boxes laid out like the ONI specimen / real cards (x0, y0, x1, y1, text); the '/' of a label is often read as 7 or T
    return [(170, 40, 580, 80, "RÉPUBLIQUE D'HAITI"), (700, 50, 1000, 80, "Numéro de carte / Nimewo kat la"), (700, 85, 870, 120, "T1K2N89G7"),
            (400, 170, 530, 200, "PRENOM7NON"), (400, 205, 520, 240, "PATRICIA"), (700, 175, 820, 200, "SEXE / SEKS"), (700, 205, 720, 230, "F"),
            (400, 270, 510, 300, "NOM / SIYATI"), (400, 305, 520, 340, "DELAIRE"), (700, 330, 990, 360, "DATE DE NAISSANCE / DAT OU FET"),
            (700, 365, 860, 395, "01 - 01 - 1987"), (400, 420, 680, 450, "LIEU DE NAISSANCE / KOTE OU FET"), (400, 455, 600, 485, "OUEST - PORT - AU - PRINCE"),
            (400, 520, 550, 550, "07 - 02 - 2018"), (700, 520, 860, 550, "06 - 02 - 2028"), (700, 600, 990, 630, "NUMERO D'IDENTIFICATION UNIQUE /"),
            (700, 640, 880, 670, "0123456789")]


def test_layout_extraction_from_boxes():
    f = idtext.extract_boxes(_boxes())
    assert f["name"] == "PATRICIA DELAIRE" and f["first_name"] == "PATRICIA" and f["surname"] == "DELAIRE"
    assert f["birth_date"] == "1987-01-01" and f["expiry_date"] == "2028-02-06"
    assert f["card_number"] == "T1K2N89G7" and f["national_id"] == "0123456789" and f["document_number"] == "T1K2N89G7"


def test_layout_extraction_with_garbled_surname_label_and_two_line_first_name():
    b = [x for x in _boxes() if x[4] != "PATRICIA"] + [(400, 205, 520, 235, "MARIE"), (400, 238, 540, 266, "PATRICIA")]
    b = [(x[0], x[1], x[2], x[3], "NOM / S1YAT" if x[4] == "NOM / SIYATI" else x[4]) for x in b]
    assert idtext.extract_boxes(b)["name"] == "MARIE PATRICIA DELAIRE"


def test_layout_extraction_returns_nothing_for_other_documents():
    assert idtext.extract_boxes([(0, 0, 100, 20, "PASSEPORT"), (0, 30, 100, 50, "P<HTI")]) == {}
