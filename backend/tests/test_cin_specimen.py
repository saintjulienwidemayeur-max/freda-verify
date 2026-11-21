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
