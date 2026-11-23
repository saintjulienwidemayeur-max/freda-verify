from app.services import idtext, provenance

B = lambda x0, y0, x1, y1, t: (x0, y0, x1, y1, t)  # noqa: E731


def test_generic_layout_english_card_label_above_value():
    boxes = [B(10, 10, 120, 24, "SURNAME"), B(10, 28, 120, 44, "MARTINEZ"), B(10, 52, 140, 66, "GIVEN NAMES"), B(10, 70, 140, 86, "CARLOS ANDRES"),
             B(200, 10, 330, 24, "DATE OF BIRTH"), B(200, 28, 330, 44, "14 03 1990"), B(200, 52, 330, 66, "EXPIRY DATE"), B(200, 70, 330, 86, "01 06 2099"),
             B(10, 100, 140, 114, "DOCUMENT NO"), B(10, 118, 140, 134, "X1234567")]
    r = idtext.extract_boxes_generic(boxes)
    assert r["name"] == "CARLOS ANDRES MARTINEZ"
    assert r["birth_date"] == "1990-03-14" and r["expiry_date"] == "2099-06-01" and r["document_number"] == "X1234567"


def test_generic_layout_value_in_same_box_spanish():
    boxes = [B(0, 0, 200, 14, "APELLIDOS: GOMEZ RUIZ"), B(0, 20, 200, 34, "NOMBRES: LUIS"), B(0, 40, 260, 54, "FECHA DE NACIMIENTO: 02/11/1985")]
    r = idtext.extract_boxes_generic(boxes)
    assert r["surname"] == "GOMEZ RUIZ" and r["first_name"] == "LUIS" and r["birth_date"] == "1985-11-02"


def test_generic_layout_returns_empty_without_labels():
    assert idtext.extract_boxes_generic([B(0, 0, 50, 10, "HELLO"), B(0, 20, 50, 30, "WORLD")]) == {}


def test_text_rules_understand_english_labels():
    r = idtext.extract("Surname DUPONT\nGiven names MARIE CLAIRE\nDate of birth 05 07 1992\nExpiry 01 01 2099\nDocument No AB123456")
    assert r["name"] == "MARIE CLAIRE DUPONT" and r["birth_date"] == "1992-07-05"


def test_provenance_refuses_png_and_editor_tags():
    assert provenance.check(b"\x89PNG....", "image/png") == "not_camera_photo"
    seg = b"Exif\x00\x00Software Adobe Photoshop 25.0"
    jpeg = b"\xff\xd8" + b"\xff\xe1" + (len(seg) + 2).to_bytes(2, "big") + seg + b"\xff\xda\x00\x02"
    assert provenance.check(jpeg, "image/jpeg") == "edited_image"
    adobe14 = b"\xff\xd8\xff\xee\x00\x0eAdobe\x00\x64\x00\x00\x00\x00\x01\xff\xda\x00\x02"      # APP14 'Adobe' marker from an ordinary encoder
    assert provenance.check(adobe14, "image/jpeg") is None
    assert provenance.check(b"\xff\xd8\xff\xe0 plain camera jpeg", "image/jpeg") is None


def test_mrz_filler_read_as_k_is_repaired_without_touching_real_names():
    from app.services.mrz import _filler_k, _names
    assert _names(_filler_k("SAINT<JULIENK<WIAEMAYEURKK<<<")) == ("SAINT JULIEN", "WIAEMAYEUR")
    assert _names(_filler_k("DUPONT<<ERIK<<<<<")) == ("DUPONT", "ERIK")
    assert _names(_filler_k("ERIK<<JOHN<<<<")) == ("ERIK", "JOHN")
