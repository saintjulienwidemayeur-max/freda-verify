# ruff: noqa: E501
"""Measures a presentation-attack-detection plug-in (app.services.pad) the way ISO/IEC 30107-3 asks: BPCER on genuine captures, APCER per attack type.

Folder layout (photos you lawfully collected, with consent; never commit them):

    pad_set/
      genuine/            *.jpg   live selfies of real people (vary phones, light, skin tones)
      attack_print/       *.jpg   photos of a PRINTED photo of a person
      attack_replay/      *.jpg   photos of a phone/laptop SCREEN showing the person (photo or video frame)
      attack_mask/        *.jpg   3D / silicone / paper mask ...  (any folder starting with "attack_" is one attack type)

Run (needs FV_PAD_MODEL_PATH and the face models):  python -m tools.pad_eval pad_set [--thresholds 0.3,0.5,0.7,0.9]

BPCER = genuine captures classified as attacks (real probability < threshold).  APCER(type) = attacks of that type accepted as live (>= threshold).
The headline APCER is the WORST attack type (APCER_PAIS). Captures where no face is found are counted separately, not hidden. 95 % Wilson intervals are shown;
with few samples they are wide and the tool says the result is only indicative. This does NOT replace an independent test lab, and a passing number on your own set
says nothing about attack types you did not include (injection of a virtual camera and deepfakes cannot be tested by photos at all).
"""
import argparse
import sys
from pathlib import Path

from app.services import pad
from tools.face_eval import IMG, wilson


def _scores(folder: Path) -> tuple[list[float], int]:
    got, none = [], 0
    for f in sorted(folder.iterdir()):
        if f.suffix.lower() not in IMG:
            continue
        o = pad.score(f.read_bytes())
        if o.status == "scored" and o.real_probability is not None:
            got.append(o.real_probability)
        else:
            none += 1
    return got, none


def rates(genuine: list[float], attacks: dict[str, list[float]], thr: float) -> dict:
    bp = sum(1 for s in genuine if s < thr)
    ap = {k: sum(1 for s in v if s >= thr) for k, v in attacks.items()}
    return {"bpcer": (bp, len(genuine)), "apcer": {k: (ap[k], len(attacks[k])) for k in attacks}}


def fmt(k: int, n: int) -> str:
    lo, hi = wilson(k, n)
    return f"{k}/{n} = {100 * k / n:5.1f} % [{100 * lo:4.1f}-{100 * hi:5.1f}]" if n else "n/a"


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("root")
    ap.add_argument("--thresholds", default="0.3,0.5,0.7,0.9")
    a = ap.parse_args(argv)
    if not pad.available():
        print("PAD is not available: set FV_PAD_MODEL_PATH to an ONNX model and install the face models (FV_FACE_MODEL_DIR).")
        return 2
    root = Path(a.root)
    genuine, g_none = _scores(root / "genuine")
    attacks, a_none = {}, {}
    for d in sorted(root.iterdir()):
        if d.is_dir() and d.name.startswith("attack_"):
            attacks[d.name[7:]], a_none[d.name[7:]] = _scores(d)
    print(f"genuine: {len(genuine)} scored, {g_none} without a usable face")
    for k, v in attacks.items():
        print(f"attack {k}: {len(v)} scored, {a_none[k]} without a usable face")
    if len(genuine) < 100 or any(len(v) < 50 for v in attacks.values()) or not attacks:
        print("WARNING: fewer than ~100 genuine / 50 per attack type (or no attack set): these numbers are INDICATIVE only; they do not support any claim.")
    print(f"\n{'threshold':>9}  {'BPCER (genuine refused)':<34}{'APCER worst type':<34}per type")
    for t in (float(x) for x in a.thresholds.split(",")):
        r = rates(genuine, attacks, t)
        worst = max(r["apcer"].items(), key=lambda kv: (kv[1][0] / kv[1][1]) if kv[1][1] else 0, default=None)
        per = "  ".join(f"{k}: {fmt(*v)}" for k, v in r["apcer"].items())
        print(f"{t:>9.2f}  {fmt(*r['bpcer']):<34}{(worst[0] + ' ' + fmt(*worst[1])) if worst else 'n/a':<34}{per}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
