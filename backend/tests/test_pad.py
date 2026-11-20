
from app.services import pad
from tools import pad_eval


def test_disabled_by_default(monkeypatch):
    monkeypatch.delenv("FV_PAD_MODEL_PATH", raising=False)
    assert not pad.available() and pad.score(b"x").status == "unavailable"


def test_rates_use_threshold_per_attack_type():
    r = pad_eval.rates([0.9, 0.8, 0.4], {"print": [0.2, 0.6], "replay": [0.95, 0.9]}, 0.5)
    assert r["bpcer"] == (1, 3) and r["apcer"] == {"print": (1, 2), "replay": (2, 2)}


def test_eval_refuses_without_a_model(monkeypatch, capsys, tmp_path):
    monkeypatch.delenv("FV_PAD_MODEL_PATH", raising=False)
    assert pad_eval.main([str(tmp_path)]) == 2
    assert "not available" in capsys.readouterr().out


def test_eval_reports_and_warns_when_samples_are_few(monkeypatch, capsys, tmp_path):
    for d, n in (("genuine", 3), ("attack_print", 2)):
        (tmp_path / d).mkdir()
        for i in range(n):
            (tmp_path / d / f"{i}.jpg").write_bytes(b"x")
    monkeypatch.setattr(pad, "available", lambda: True)
    monkeypatch.setattr(pad, "score", lambda data: pad.PadOutcome("scored", 0.9))
    assert pad_eval.main([str(tmp_path), "--thresholds", "0.5"]) == 0
    out = capsys.readouterr().out
    assert "INDICATIVE" in out and "print" in out and "0/3" in out and "2/2" in out
