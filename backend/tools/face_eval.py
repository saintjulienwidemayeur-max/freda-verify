# ruff: noqa: S311, E501
"""Measures the face-comparison error rates on photos YOU lawfully collected with the people's consent (never commit them).

Folder layout (one folder per person; the folder name is only a label, use codes, not names):

    photos/
      p01/doc_passport.jpg  doc_id.jpg      <- photo(s) of the document (passport data page, ID card front ...)
      p01/selfie_1.jpg  selfie_2.jpg        <- selfie(s) of the same person (any file starting with "selfie")
      p02/...
    meta.json   (optional)  {"p01": {"group": "any label you chose with the person's consent"}, ...}

Run:  python -m tools.face_eval photos [--meta photos/meta.json] [--thresholds 0.25,0.3,0.363,0.4,0.5]

Genuine pair  = a document photo and a selfie of the SAME person (should score high).
Impostor pair = a document photo of person A and a selfie of person B (should score low).
Reported: score distributions, FRR (genuine pairs below the threshold) and FAR (impostor pairs at or above it) with 95 % Wilson intervals, the
threshold that gives FAR <= 1 % and <= 0.1 % when there are enough impostor pairs, and the weakest genuine pairs so you can look at the photos.
With too few people the numbers are only indicative: the tool says so. No feature vector is written anywhere.
"""
import argparse
import json
import math
import statistics
import sys
from pathlib import Path

from app.services import face

IMG = (".jpg", ".jpeg", ".png", ".webp")


def wilson(k: int, n: int, z: float = 1.96) -> tuple[float, float]:
    if n == 0:
        return (0.0, 1.0)
    p = k / n
    d = 1 + z * z / n
    c = (p + z * z / (2 * n)) / d
    h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return (max(0.0, c - h), min(1.0, c + h))


def load(root: Path):
    people: dict[str, dict] = {}
    for d in sorted(p for p in root.iterdir() if p.is_dir()):
        docs, selfies = [], []
        for f in sorted(d.iterdir()):
            if f.suffix.lower() not in IMG:
                continue
            try:
                feats_all, nf = face.embed(f.read_bytes(), all_faces=True)
                feats_one, _ = face.embed(f.read_bytes())
            except Exception:  # noqa: BLE001
                print(f"  ! {d.name}/{f.name}: not readable")
                continue
            if f.name.lower().startswith("selfie"):
                if feats_one:
                    selfies.append((f.name, feats_one[0]))
                else:
                    print(f"  ! {d.name}/{f.name}: no face found")
            elif feats_all:
                docs.append((f.name, feats_all))
            else:
                print(f"  ! {d.name}/{f.name}: no face found on the document photo ({nf} faces)")
        if docs and selfies:
            people[d.name] = {"docs": docs, "selfies": selfies}
        else:
            print(f"  ! {d.name}: needs at least one document photo and one selfie, skipped")
    return people


def pair_score(doc_feats, selfie_feat) -> float:
    return max(face.cosine(f, selfie_feat) for f in doc_feats)       # same rule as the product: best of the document faces


def summarize(name: str, xs: list[float]) -> None:
    if not xs:
        print(f"{name}: no pairs")
        return
    print(f"{name}: n={len(xs)}  min={min(xs):.3f}  p5={sorted(xs)[max(0, int(0.05 * len(xs)) - 1)]:.3f}  median={statistics.median(xs):.3f}  mean={statistics.mean(xs):.3f}  max={max(xs):.3f}")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("root")
    ap.add_argument("--meta")
    ap.add_argument("--thresholds", default="0.25,0.30,0.363,0.40,0.45,0.50")
    a = ap.parse_args()
    if not face.available():
        sys.exit("Face models or OpenCV not available (see FV_FACE_MODEL_DIR).")
    people = load(Path(a.root))
    meta = json.loads(Path(a.meta).read_text()) if a.meta else {}
    ids = list(people)
    genuine, impostor, weakest = [], [], []
    by_group: dict[str, list[float]] = {}
    for pid in ids:
        for dn, df in people[pid]["docs"]:
            for sn, sf in people[pid]["selfies"]:
                s = pair_score(df, sf)
                genuine.append(s)
                weakest.append((s, f"{pid}: {dn} vs {sn}"))
                by_group.setdefault(meta.get(pid, {}).get("group", "(none)"), []).append(s)
    for pa in ids:
        for pb in ids:
            if pa == pb:
                continue
            for _, df in people[pa]["docs"]:
                for _, sf in people[pb]["selfies"]:
                    impostor.append(pair_score(df, sf))
    print(f"\npeople: {len(ids)}   genuine pairs: {len(genuine)}   impostor pairs: {len(impostor)}")
    if len(ids) < 30 or len(genuine) < 60:
        print("WARNING: fewer than ~30 people / 60 genuine pairs: these numbers are INDICATIVE only (wide intervals below). 100 genuine pairs with 0 misses are needed just to say FRR < 3 %.")
    print()
    summarize("genuine ", genuine)
    summarize("impostor", impostor)
    print("\nthreshold   FRR (genuine below)         FAR (impostor at/above)")
    for t in (float(x) for x in a.thresholds.split(",")):
        kf, ka = sum(1 for g in genuine if g < t), sum(1 for i in impostor if i >= t)
        lf, hf = wilson(kf, len(genuine))
        la, ha = wilson(ka, len(impostor))
        mark = "   <- current product threshold" if abs(t - face.COSINE_THRESHOLD) < 1e-9 else ""
        print(f"  {t:5.3f}    {kf:3d}/{len(genuine):<4d} = {100 * kf / max(1, len(genuine)):5.1f} %  [{100 * lf:4.1f}-{100 * hf:5.1f}]      {ka:4d}/{len(impostor):<5d} = {100 * ka / max(1, len(impostor)):5.2f} %  [{100 * la:4.2f}-{100 * ha:5.2f}]{mark}")
    for target in (0.01, 0.001):
        if len(impostor) >= 1 / target:
            t = sorted(impostor, reverse=True)[max(0, int(target * len(impostor)) - 1)]
            print(f"\nthreshold for FAR <= {100 * target:g} % (needs >= {int(1 / target)} impostor pairs): {t + 1e-4:.3f}  -> FRR there = {100 * sum(1 for g in genuine if g < t + 1e-4) / max(1, len(genuine)):.1f} %")
        else:
            print(f"\nFAR <= {100 * target:g} %: not enough impostor pairs ({len(impostor)} < {int(1 / target)}), cannot be estimated.")
    if len(by_group) > 1 or "(none)" not in by_group:
        print("\ngenuine scores by group (labels YOU assigned, with consent):")
        for g, xs in sorted(by_group.items()):
            kf = sum(1 for x in xs if x < face.COSINE_THRESHOLD)
            print(f"  {g:20s} n={len(xs):3d}  median={statistics.median(xs):.3f}  below {face.COSINE_THRESHOLD}: {kf}/{len(xs)}")
        print("  (small groups prove nothing: look at the intervals before concluding that the model is worse for a group)")
    print("\nweakest genuine pairs (look at these photos):")
    for s, label in sorted(weakest)[:8]:
        print(f"  {s:.3f}  {label}")


if __name__ == "__main__":
    main()
