# ruff: noqa: E501
"""Measures a presentation-attack-detection plug-in (app.services.pad) the way ISO/IEC 30107-3 asks: BPCER on genuine captures, APCER per attack type.

Folder layout (photos you lawfully collected, with consent; never commit them):

    pad_set/
      genuine/            *.jpg   live selfies of real people (vary phones, light, skin tones)
      attack_print/       *.jpg   photos of a PRINTED photo of a person
      attack_replay/      *.jpg   photos of a phone/laptop SCREEN showing the person (photo or video frame)
      attack_mask/        *.jpg   3D / silicone / paper mask ...  (any folder starting with "attack_" is one attack type)

Optional sub-folders give GROUP results (skin tone, lighting, phone, ... labels YOU assign with the person's consent), e.g. genuine/dark_skin/, genuine/low_light/,
attack_print/low_light/. Files directly in a folder form the group "(all other)". Use `--stress` to also see how the genuine scores react to synthetic darkening / noise / blur
(a quick sensitivity probe ONLY: it does not replace real low-light and dark-skin captures, which this protocol asks you to collect: docs/pad-collection-protocol.md).

Run (needs the PAD models in FV_PAD_MODEL_DIR and the face models):  python -m tools.pad_eval pad_set [--thresholds 0.3,0.5,0.7,0.9]

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


def _score_file(f: Path, transform=None) -> float | None:
    data = f.read_bytes()
    if transform:
        import cv2
        import numpy as np
        img = cv2.imdecode(np.frombuffer(data, np.uint8), cv2.IMREAD_COLOR)
        if img is None:
            return None
        data = cv2.imencode(".jpg", transform(img))[1].tobytes()
    o = pad.score(data)
    return o.real_probability if o.status == "scored" and o.real_probability is not None else None


def _scores(folder: Path, transform=None) -> tuple[list[float], int, dict[str, list[float]]]:
    """Scores of the images directly in `folder` plus, per immediate sub-folder, the group's scores. Returns (all scores, files without a usable face, groups)."""
    got, none, groups = [], 0, {}
    files = [(f, "(all other)") for f in sorted(folder.iterdir()) if f.is_file()]
    for d in sorted(x for x in folder.iterdir() if x.is_dir()):
        files += [(f, d.name) for f in sorted(d.iterdir()) if f.is_file()]
    for f, grp in files:
        if f.suffix.lower() not in IMG:
            continue
        sc = _score_file(f, transform)
        if sc is None:
            none += 1
        else:
            got.append(sc)
            groups.setdefault(grp, []).append(sc)
    return got, none, groups


STRESS = {
    "darker x0.6": lambda im: (im * 0.6).clip(0, 255).astype("uint8"),
    "dark x0.35": lambda im: (im * 0.35).clip(0, 255).astype("uint8"),
    "dark x0.35 + noise": lambda im: (im * 0.35 + __import__("numpy").random.default_rng(0).normal(0, 12, im.shape)).clip(0, 255).astype("uint8"),
    "blur 5 px": lambda im: __import__("cv2").GaussianBlur(im, (11, 11), 0),
    "jpeg q25": lambda im: __import__("cv2").imdecode(__import__("cv2").imencode(".jpg", im, [1, 25])[1], 1),
}


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
    ap.add_argument("--stress", action="store_true", help="also re-score the genuine images after synthetic darkening / noise / blur / compression")
    a = ap.parse_args(argv)
    if not pad.available():
        print("PAD is not available: put MiniFASNetV2.onnx and/or MiniFASNetV1SE.onnx in FV_PAD_MODEL_DIR (default /opt/pad-models) and install the face models (FV_FACE_MODEL_DIR).")
        return 2
    root = Path(a.root)
    genuine, g_none, g_groups = _scores(root / "genuine")
    attacks, a_none, a_groups = {}, {}, {}
    for d in sorted(root.iterdir()):
        if d.is_dir() and d.name.startswith("attack_"):
            attacks[d.name[7:]], a_none[d.name[7:]], a_groups[d.name[7:]] = _scores(d)
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
    primary = float(a.thresholds.split(",")[min(1, len(a.thresholds.split(",")) - 1)])
    if len(g_groups) > 1 or any(len(g) > 1 for g in a_groups.values()):
        print(f"\nGROUPS at threshold {primary:.2f} (small groups are very noisy: look at the interval)")
        for g, v in g_groups.items():
            print(f"  genuine / {g:<18} BPCER {fmt(sum(1 for x in v if x < primary), len(v))}")
        for k, gs in a_groups.items():
            for g, v in gs.items():
                print(f"  attack {k} / {g:<14} APCER {fmt(sum(1 for x in v if x >= primary), len(v))}")
    if a.stress and genuine:
        print(f"\nSYNTHETIC STRESS on the genuine images at threshold {primary:.2f} (sensitivity probe, not a measurement of real low light or skin tones)")
        for name, fn in STRESS.items():
            sc, none, _ = _scores(root / "genuine", fn)
            print(f"  {name:<22} BPCER {fmt(sum(1 for x in sc if x < primary), len(sc))}   no usable face: {none}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
