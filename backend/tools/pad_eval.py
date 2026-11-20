# ruff: noqa: E501
"""Measures a presentation-attack-detection plug-in (app.services.pad) the way ISO/IEC 30107-3 asks: BPCER on genuine captures, APCER per attack type.

Folder layout (photos you lawfully collected, with consent; never commit them):

    pad_set/
      genuine/            *.jpg   live selfies of real people (vary phones, light, skin tones)
      attack_print/       *.jpg   photos of a PRINTED photo of a person
      attack_replay/      *.jpg   photos of a phone/laptop SCREEN showing the person (photo or video frame)
      attack_mask/        *.jpg   3D / silicone / paper mask ...  (any folder starting with "attack_" is one attack type)

PROTOCOL mode (`--protocol`, the OULU-NPU way): file names must start with the PERSON code and a separator (`p017_phoneA_dark_1.jpg`). People are split into a DEVELOPMENT half and a TEST half
deterministically (never the same person in both). The threshold is chosen on the development half where BPCER = pooled APCER (EER); the numbers that matter are then reported ONCE on
the test half: BPCER, APCER per attack type, worst-type APCER and ACER = (worst APCER + BPCER) / 2. Splitting people, not images, is what makes the result mean something.

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
import hashlib
import re
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


PERSON = re.compile(r"^([A-Za-z0-9]+)[_-]")


def person_of(f: Path) -> str | None:
    m = PERSON.match(f.name)
    return m.group(1) if m else None


def scores_by_person(folder: Path) -> tuple[list[tuple[str, float]], int, int]:
    """[(person, real_probability)], files without a usable face, files without a person code. Looks in sub-folders too."""
    out, none, noperson = [], 0, 0
    for f in sorted(x for x in folder.rglob("*") if x.is_file() and x.suffix.lower() in IMG):
        who = person_of(f)
        if who is None:
            noperson += 1
            continue
        sc = _score_file(f)
        if sc is None:
            none += 1
        else:
            out.append((who, sc))
    return out, none, noperson


def side(person: str) -> str:
    """Deterministic dev/test side of a person (stable across runs and machines)."""
    return "dev" if int(hashlib.sha256(person.encode()).hexdigest(), 16) % 2 == 0 else "test"


def eer_threshold(genuine: list[float], attacks: list[float]) -> tuple[float, float]:
    """Threshold where BPCER (genuine below it) and APCER (attacks at/above it) are closest; returns (threshold, EER estimate)."""
    cand = sorted({0.0, 1.0, *genuine, *attacks})
    best = (0.5, 1.0, 1.0)
    for t in cand:
        bp = sum(1 for x in genuine if x < t) / max(1, len(genuine))
        ap = sum(1 for x in attacks if x >= t) / max(1, len(attacks))
        gap = abs(bp - ap)
        if gap < best[2] or (gap == best[2] and (bp + ap) / 2 < best[1]):
            best = (t, (bp + ap) / 2, gap)
    return best[0], best[1]


def protocol(genuine: list[tuple[str, float]], attacks: dict[str, list[tuple[str, float]]]) -> dict:
    """Dev/test split by person, EER threshold on dev, report on test. Pure function (testable)."""
    g_dev = [s for p, s in genuine if side(p) == "dev"]
    g_test = [s for p, s in genuine if side(p) == "test"]
    a_dev = {k: [s for p, s in v if side(p) == "dev"] for k, v in attacks.items()}
    a_test = {k: [s for p, s in v if side(p) == "test"] for k, v in attacks.items()}
    pooled = [s for v in a_dev.values() for s in v]
    t, eer = eer_threshold(g_dev, pooled)
    bp = (sum(1 for x in g_test if x < t), len(g_test))
    ap = {k: (sum(1 for x in v if x >= t), len(v)) for k, v in a_test.items()}
    worst = max(ap.items(), key=lambda kv: kv[1][0] / kv[1][1] if kv[1][1] else 0, default=None)
    rate = lambda c: c[0] / c[1] if c[1] else None  # noqa: E731
    acer = None if (worst is None or rate(worst[1]) is None or rate(bp) is None) else (rate(worst[1]) + rate(bp)) / 2
    persons = {side(p) for p, _ in genuine}
    return {"threshold": t, "dev_eer": eer, "bpcer": bp, "apcer": ap, "worst": worst, "acer": acer,
            "people": {"dev": len({p for p, _ in genuine if side(p) == "dev"}), "test": len({p for p, _ in genuine if side(p) == "test"})},
            "both_sides": persons == {"dev", "test"}}


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("root")
    ap.add_argument("--protocol", action="store_true", help="OULU-NPU style: split people into dev/test, pick the EER threshold on dev, report ACER on test (file names start with the person code)")
    ap.add_argument("--thresholds", default="0.3,0.5,0.7,0.9")
    ap.add_argument("--stress", action="store_true", help="also re-score the genuine images after synthetic darkening / noise / blur / compression")
    a = ap.parse_args(argv)
    if not pad.available():
        print("PAD is not available: put MiniFASNetV2.onnx and/or MiniFASNetV1SE.onnx in FV_PAD_MODEL_DIR (default /opt/pad-models) and install the face models (FV_FACE_MODEL_DIR).")
        return 2
    root = Path(a.root)
    if a.protocol:
        return _run_protocol(root)
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


def _run_protocol(root: Path) -> int:
    genuine, g_none, g_np = scores_by_person(root / "genuine")
    attacks, none_total, np_total = {}, g_none, g_np
    for d in sorted(root.iterdir()):
        if d.is_dir() and d.name.startswith("attack_"):
            attacks[d.name[7:]], n1, n2 = scores_by_person(d)
            none_total, np_total = none_total + n1, np_total + n2
    if np_total:
        print(f"WARNING: {np_total} files ignored because their name does not start with a person code (e.g. p017_...).")
    if none_total:
        print(f"{none_total} files without a usable face were left out (counted, not hidden).")
    r = protocol(genuine, attacks)
    print(f"people: development {r['people']['dev']}, test {r['people']['test']} (genuine set); threshold chosen on DEVELOPMENT only")
    if not r["both_sides"] or r["people"]["dev"] < 2 or r["people"]["test"] < 2:
        print("NOT ENOUGH PEOPLE: need several people on each side; the result below is meaningless.")
    print(f"threshold {r['threshold']:.3f}  (development EER about {100 * r['dev_eer']:.1f} %)\n")
    print(f"TEST  BPCER {fmt(*r['bpcer'])}")
    for k, v in r["apcer"].items():
        print(f"TEST  APCER {k:<14} {fmt(*v)}")
    if r["worst"]:
        print(f"TEST  worst attack type: {r['worst'][0]}")
    if r["acer"] is not None:
        print(f"TEST  ACER = (worst APCER + BPCER) / 2 = {100 * r['acer']:.1f} %")
    n_g = r["bpcer"][1]
    if n_g < 100 or any(v[1] < 50 for v in r["apcer"].values()):
        print("WARNING: fewer than ~100 genuine / 50 per attack type on the TEST half: INDICATIVE only, no claim can rest on it.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
