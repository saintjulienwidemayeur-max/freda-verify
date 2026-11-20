import shutil
from pathlib import Path

import pytest
from PIL import Image

from app.services import face
from tools import face_eval

FACES = Path(__file__).resolve().parents[2] / "public" / "faces"
pytestmark = pytest.mark.skipif(not face.available(), reason="face models (/opt/face-models) or opencv not installed")


def test_wilson_interval_behaves():
    lo, hi = face_eval.wilson(0, 100)
    assert lo == 0 and 0.03 < hi < 0.04                      # 0 misses in 100 pairs still allows ~3.7 %
    assert face_eval.wilson(0, 0) == (0.0, 1.0)
    lo, hi = face_eval.wilson(50, 100)
    assert lo < 0.5 < hi


def test_tool_runs_on_a_tiny_folder_and_finds_genuine_above_impostor(tmp_path, capsys, monkeypatch):
    for person, doc, selfie in (("p01", "man-doc", "man-selfie"), ("p02", "woman-doc", "woman-selfie")):
        d = tmp_path / person
        d.mkdir()
        for src, name in ((doc, "doc_id.jpg"), (selfie, "selfie_1.jpg")):
            Image.open(FACES / f"{src}.webp").convert("RGB").save(d / name, "JPEG", quality=92)
    (tmp_path / "p03").mkdir()                               # a person without photos is skipped, not fatal
    people = face_eval.load(tmp_path)
    assert set(people) == {"p01", "p02"}
    monkeypatch.setattr("sys.argv", ["face_eval", str(tmp_path)])
    face_eval.main()
    out = capsys.readouterr().out
    assert "genuine pairs: 2" in out and "impostor pairs: 2" in out and "INDICATIVE" in out
    g = [face_eval.pair_score(people[p]["docs"][0][1], people[p]["selfies"][0][1]) for p in people]
    i = face_eval.pair_score(people["p01"]["docs"][0][1], people["p02"]["selfies"][0][1])
    assert min(g) > 0.6 and i < face.COSINE_THRESHOLD
    shutil.rmtree(tmp_path, ignore_errors=True)
