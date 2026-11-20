# ruff: noqa: S311, E501  (test-data generator: seeded pseudo-random on purpose; wide report formatting lines)
"""Measures the accuracy of the server-side MRZ reader (app/services/ocr.py).

Two modes:
  python -m tools.ocr_eval --synthetic [--n 10] [--seed 1]
      Renders valid MRZ pages with the real OCR-B font (apt: fonts-ocr-b) on busy backgrounds and degrades them (blur, noise, JPEG, rotation,
      perspective, glare, low contrast, a "phone" combination). Ground truth is known, so wrong-but-valid readings (false accepts) are counted.
      LIMIT: still synthetic. It says nothing about real printing, holograms, laminate glare, worn pages or national layouts.
  python -m tools.ocr_eval --dir /path/to/photos [--labels labels.json]
      Runs the reader on YOUR lawful test photos (never commit them). Without labels it reports the status and the share of readings whose
      ICAO check digits ALL pass (a strong sign of a correct reading). With labels ({"file.jpg": ["line1", "line2"]}) it also reports exact-line
      matches, character error rate and false accepts (all check digits valid but text different from the label).
"""
import argparse
import io
import json
import math
import random
import string
import sys
from collections import defaultdict
from multiprocessing import Pool
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter, ImageFont

from app.services.mrz import check_digit, parse_mrz
from app.services.ocr import read_mrz

FONT = "/usr/share/fonts/opentype/ocr-b/OCRB.otf"
SURNAMES = ["ERIKSSON", "JEAN BAPTISTE", "PIERRE", "ETIENNE", "DESROSIERS", "CHARLES", "LOUIS", "MILLER", "TANAKA", "OKAFOR", "BELIZAIRE", "NOEL"]
GIVEN = ["ANNA MARIA", "MARC", "NADEGE", "JONAS", "WIDLINE", "KEVENS", "SOPHIA", "ALEXANDRE", "MARIE CLAIRE", "DAVID"]
COUNTRIES = ["HTI", "USA", "CAN", "FRA", "DOM", "UTO", "GBR", "BRA"]


def _cd(s: str) -> str:
    return str(check_digit(s))


def _fill(s: str, n: int) -> str:
    return (s + "<" * n)[:n]


def _names(rng: random.Random, n: int) -> str:
    return _fill(rng.choice(SURNAMES).replace(" ", "<") + "<<" + rng.choice(GIVEN).replace(" ", "<"), n)


def _date(rng: random.Random, y0: int, y1: int) -> str:
    return f"{rng.randint(y0, y1) % 100:02d}{rng.randint(1, 12):02d}{rng.randint(1, 28):02d}"


def make_mrz(kind: str, rng: random.Random) -> list[str]:
    docno = "".join(rng.choice(string.ascii_uppercase + string.digits) for _ in range(9))
    nat, issuer, sex = rng.choice(COUNTRIES), rng.choice(COUNTRIES), rng.choice("MF<")
    birth, exp = _date(rng, 1950, 2005), _date(rng, 2026, 2034)
    if kind == "TD3":
        l1 = _fill("P<" + issuer + _names(rng, 39)[:39], 44)
        body = docno + _cd(docno) + nat + birth + _cd(birth) + sex + exp + _cd(exp)
        opt = _fill("", 14)
        pre = body + opt + _cd(opt)
        comp = _cd(pre[0:10] + pre[13:20] + pre[21:43])
        return [l1, pre + comp]
    if kind == "TD2":
        l1 = _fill("I<" + issuer + _names(rng, 31), 36)
        pre = docno + _cd(docno) + nat + birth + _cd(birth) + sex + exp + _cd(exp) + _fill("", 7)
        return [l1, pre + _cd(pre[0:10] + pre[13:20] + pre[21:35])]
    opt1, opt2 = _fill("", 15), _fill("", 11)
    l1 = "I<" + issuer + docno + _cd(docno) + opt1
    l2 = birth + _cd(birth) + sex + exp + _cd(exp) + nat + opt2
    comp = _cd(l1[5:30] + l2[0:7] + l2[8:15] + l2[18:29])
    return [l1, l2 + comp, _names(rng, 30)]


def render(lines: list[str], rng: random.Random) -> Image.Image:
    td1 = len(lines) == 3
    w, h = (1000, 640) if td1 else (1250, 880)
    base = rng.choice([(246, 240, 226), (238, 244, 250), (250, 246, 238)])
    im = Image.new("RGB", (w, h), base)
    d = ImageDraw.Draw(im)
    for k in range(18):                                              # guilloche-like wavy lines over the whole page
        col = tuple(max(0, c - rng.randint(15, 45)) for c in base)
        ph, amp, per = rng.random() * 6, rng.randint(8, 40), rng.randint(60, 200)
        d.line([(x, h * (k + 1) / 19 + amp * math.sin(x / per + ph)) for x in range(0, w, 6)], fill=col, width=1)
    d.rectangle((40, 80, 330, 420), fill=(170, 150, 140))           # photo placeholder
    big = ImageFont.truetype(FONT, 38)
    d.text((370, 100), "PASSPORT / PASSEPORT / PASAPORTE", font=big, fill=(30, 30, 60))
    for i in range(5):
        d.text((370, 170 + i * 44), "".join(rng.choice(string.ascii_uppercase) for _ in range(rng.randint(10, 22))), font=big, fill=(60, 60, 80))
    size = len(lines[0])
    fs = 40
    fs = int(fs * (w * 0.92) / ImageFont.truetype(FONT, fs).getlength("<" * size))   # fit the real advance width of the font
    f = ImageFont.truetype(FONT, fs)
    y0 = h - len(lines) * int(fs * 1.55) - 30
    d.rectangle((0, y0 - 14, w, h), fill=tuple(min(255, c + 6) for c in base))
    for i, ln in enumerate(lines):
        d.text((w * 0.04, y0 + i * int(fs * 1.55)), ln, font=f, fill=(20, 20, 20))
    return im


def _persp(im: Image.Image, rng: random.Random, k: float) -> Image.Image:
    pad = int(im.width * 0.08)                                       # a real photo shows the table around the page: never crop the MRZ
    big = Image.new("RGB", (im.width + 2 * pad, im.height + 2 * pad), (90, 90, 90))
    big.paste(im, (pad, pad))
    im = big
    w, h = im.size
    j = lambda: rng.uniform(-k, k)  # noqa: E731
    src = [(0, 0), (w, 0), (w, h), (0, h)]
    dst = [(w * j(), h * j()), (w * (1 + j()), h * j()), (w * (1 + j()), h * (1 + j())), (w * j(), h * (1 + j()))]
    a = []
    for (x, y), (u, v) in zip(dst, src, strict=True):
        a += [[x, y, 1, 0, 0, 0, -u * x, -u * y], [0, 0, 0, x, y, 1, -v * x, -v * y]]
    b = [c for p in src for c in p]
    # solve 8x8 with Gaussian elimination (no numpy)
    m = [row + [bb] for row, bb in zip(a, b, strict=True)]
    for i in range(8):
        p = max(range(i, 8), key=lambda r: abs(m[r][i]))
        m[i], m[p] = m[p], m[i]
        for r in range(8):
            if r != i:
                f = m[r][i] / m[i][i]
                m[r] = [x - f * y for x, y in zip(m[r], m[i], strict=True)]
    coeffs = [m[i][8] / m[i][i] for i in range(8)]
    return im.transform(im.size, Image.PERSPECTIVE, coeffs, Image.BICUBIC, fillcolor=(90, 90, 90))


def _pad(im: Image.Image) -> Image.Image:
    pad = int(im.width * 0.08)
    big = Image.new("RGB", (im.width + 2 * pad, im.height + 2 * pad), (90, 90, 90))
    big.paste(im, (pad, pad))
    return big


def _noise(im: Image.Image, sigma: float) -> Image.Image:
    n = Image.effect_noise(im.size, sigma).convert("RGB")
    return Image.blend(im, n, 0.18)


def _glare(im: Image.Image, rng: random.Random) -> Image.Image:
    w, h = im.size
    g = Image.new("L", im.size, 0)
    cx, cy = rng.randint(int(w * .2), int(w * .8)), int(h * rng.uniform(.72, .95))
    ImageDraw.Draw(g).ellipse((cx - w * .18, cy - h * .09, cx + w * .18, cy + h * .09), fill=235)
    g = g.filter(ImageFilter.GaussianBlur(40))
    return Image.composite(Image.new("RGB", im.size, (255, 255, 255)), im, g)


def _jpeg(im: Image.Image, q: int) -> bytes:
    b = io.BytesIO()
    im.save(b, "JPEG", quality=q)
    return b.getvalue()


def _scale(im: Image.Image, f: float) -> Image.Image:
    return im.resize((max(1, int(im.width * f)), max(1, int(im.height * f))), Image.LANCZOS)


SCENARIOS = {
    "clean": lambda im, r: _jpeg(im, 92),
    "jpeg q35": lambda im, r: _jpeg(im, 35),
    "downscale 0.5": lambda im, r: _jpeg(_scale(im, 0.5), 80),
    "downscale 0.35": lambda im, r: _jpeg(_scale(im, 0.35), 80),
    "blur 1.5": lambda im, r: _jpeg(im.filter(ImageFilter.GaussianBlur(1.5)), 85),
    "blur 3": lambda im, r: _jpeg(im.filter(ImageFilter.GaussianBlur(3)), 85),
    "noise": lambda im, r: _jpeg(_noise(im, 60), 80),
    "rotate ±2°": lambda im, r: _jpeg(_pad(im).rotate(r.choice([-2, 2]), expand=False, fillcolor=(90, 90, 90), resample=Image.BICUBIC), 85),
    "rotate ±5°": lambda im, r: _jpeg(_pad(im).rotate(r.choice([-5, 5]), expand=False, fillcolor=(90, 90, 90), resample=Image.BICUBIC), 85),
    "perspective": lambda im, r: _jpeg(_persp(im, r, 0.04), 85),
    "low contrast": lambda im, r: _jpeg(Image.blend(im, Image.new("RGB", im.size, (170, 170, 170)), 0.55), 85),
    "glare on MRZ": lambda im, r: _jpeg(_glare(im, r), 85),
    "phone (combined)": lambda im, r: _jpeg(_noise(_persp(_scale(im, 0.7), r, 0.025).rotate(r.uniform(-2, 2), fillcolor=(90, 90, 90)).filter(ImageFilter.GaussianBlur(1.0)), 40), 60),
}


def _unused_cer(a: str, b: str) -> float:
    prev = list(range(len(b) + 1))
    for i, ca in enumerate(a, 1):
        cur = [i]
        for j, cb in enumerate(b, 1):
            cur.append(min(prev[j] + 1, cur[j - 1] + 1, prev[j - 1] + (ca != cb)))
        prev = cur
    return prev[-1] / max(1, len(b))


FIELDS = ("document_number", "birth_date", "expiry_date", "nationality", "issuing_country", "sex")


def _one(job):
    name, data, truth = job
    o = read_mrz(data)
    got = o.result.to_dict() if o.result else None
    want = parse_mrz(truth).to_dict() if truth else None
    return name, o.status, bool(o.result and o.result.all_checks_passed), got, want, o.agreeing


def summarise(rows) -> dict:
    n = len(rows)
    read = sum(1 for r in rows if r[1] == "read")
    valid = sum(1 for r in rows if r[2])
    lab = [r for r in rows if r[4]]
    fields_ok = lambda r: bool(r[3]) and all(r[3][f] == r[4][f] for f in FIELDS)  # noqa: E731
    names_ok = lambda r: bool(r[3]) and (r[3]["surname"], r[3]["given_names"]) == (r[4]["surname"], r[4]["given_names"])  # noqa: E731
    return {"n": n, "read": read / n if n else 0, "all_check_digits_valid": valid / n if n else 0,
            "fields": (sum(map(fields_ok, lab)) / len(lab)) if lab else None,
            "names": (sum(map(names_ok, lab)) / len(lab)) if lab else None,
            "false_accepts": sum(1 for r in lab if r[2] and not fields_ok(r)) if lab else None,
            "confirmed": sum(1 for r in rows if r[5] >= 2) / n if n else 0,
            "confirmed_wrong": sum(1 for r in lab if r[5] >= 2 and not fields_ok(r)) if lab else None}


def pct(v):
    return "—" if v is None else f"{v * 100:5.1f}%"


def table(title: str, groups: dict) -> None:
    print(f"\n{title}\n{'scenario':<20}{'N':>4}{'read':>9}{'all digits ✓':>14}{'fields ok':>11}{'names ok':>10}{'false acc.':>12}{'confirmed':>11}{'conf. wrong':>13}")
    for k, rows in groups.items():
        s = summarise(rows)
        print(f"{k:<20}{s['n']:>4}{pct(s['read']):>9}{pct(s['all_check_digits_valid']):>14}{pct(s['fields']):>11}{pct(s['names']):>10}{('—' if s['false_accepts'] is None else s['false_accepts']):>12}{pct(s['confirmed']):>11}{('—' if s['confirmed_wrong'] is None else s['confirmed_wrong']):>13}")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--synthetic", action="store_true")
    ap.add_argument("--n", type=int, default=10, help="pages per scenario (split across TD3/TD2/TD1)")
    ap.add_argument("--seed", type=int, default=1)
    ap.add_argument("--dir")
    ap.add_argument("--labels")
    ap.add_argument("--procs", type=int, default=4)
    a = ap.parse_args()
    if a.synthetic:
        rng = random.Random(a.seed)
        jobs, kinds = [], ["TD3", "TD3", "TD1", "TD2"]
        for sc, fn in SCENARIOS.items():
            for i in range(a.n):
                kind = kinds[i % len(kinds)]
                lines = make_mrz(kind, rng)
                jobs.append((sc, fn(render(lines, rng), rng), lines))
        with Pool(a.procs) as p:
            res = p.map(_one, jobs, chunksize=1)
        by = defaultdict(list)
        for r in res:
            by[r[0]].append(r)
        table("SYNTHETIC (OCR-B font, generated pages; NOT real documents)", by)
        table("overall", {"all": res})
    elif a.dir:
        labels = json.loads(Path(a.labels).read_text()) if a.labels else {}
        files = sorted(p for p in Path(a.dir).iterdir() if p.suffix.lower() in (".jpg", ".jpeg", ".png", ".webp"))
        with Pool(a.procs) as p:
            res = p.map(_one, [(f.name, f.read_bytes(), labels.get(f.name)) for f in files], chunksize=1)
        for r in res:
            print(f"{r[0]:<30} {r[1]:<11} all-digits-valid={r[2]}")
        table("YOUR PHOTOS", {"all": res})
    else:
        ap.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()
