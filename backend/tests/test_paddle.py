import pytest

from app.services import idtext, paddle


def box(x, y, w=100, h=20):
    return [[x, y], [x + w, y], [x + w, y + h], [x, y + h]]


def test_lines_group_boxes_by_height_and_sort_left_to_right():
    res = [(box(300, 11), "1990", 0.9), (box(10, 10), "Naissance", 0.9), (box(10, 60), "Nom", 0.9), (box(150, 62), "JEAN", 0.9)]
    assert paddle._lines(res).split("\n") == ["Naissance 1990", "Nom JEAN"]


def test_read_text_is_none_when_disabled(monkeypatch):
    monkeypatch.setattr(paddle, "available", lambda: False)
    assert paddle.read_text(b"x") is None


def test_combine_prefers_paddle_when_plausible_else_tesseract():
    paddle_text = "Nom DUPONT\nPrénom MARIE LOUISE\nDate de naissance 05/06/1990\nNIF 000-111-222-3"
    tess_text = "Nom DUPONT\nPrénom MARIE LOUISE\nDate de naissance 05/08/1990\nNIF 000-111-222-3"
    f, src, agree = idtext.combine_engines(paddle_text, tess_text)
    assert f["birth_date"] == "1990-06-05" and src["birth_date"] == "paddle" and agree["birth_date"] is False
    assert agree["document_number"] is True and agree["name"] is True
    f2, src2, _ = idtext.combine_engines("garbage", tess_text)
    assert src2["birth_date"] == "tesseract" and f2["birth_date"] == "1990-08-05"


def test_combine_with_one_engine_only():
    f, src, agree = idtext.combine_engines(None, "Nom DUPONT\nPrénom MARIE\nDate de naissance 05/06/1990")
    assert f["birth_date"] == "1990-06-05" and set(src.values()) == {"tesseract"} and agree == {}


@pytest.mark.skipif(not paddle.available(), reason="rapidocr-onnxruntime not installed")
def test_reads_printed_text_from_an_image():
    import io

    from PIL import Image, ImageDraw, ImageFont
    img = Image.new("RGB", (900, 300), "white")
    d = ImageDraw.Draw(img)
    f = ImageFont.load_default(size=40)
    d.text((20, 30), "Nom DUPONT", fill="black", font=f)
    d.text((20, 120), "Date de naissance 05/06/1990", fill="black", font=f)
    buf = io.BytesIO()
    img.save(buf, "PNG")
    out = paddle.read_text(buf.getvalue()) or ""
    assert "DUPONT" in out.upper() and "1990" in out
