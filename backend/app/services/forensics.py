"""Pixel-level hints that a document photo may be a photo OF A SCREEN or may have been edited. ADVISORY ONLY: a flag sends the verification to a person, it never rejects by itself.

Two heuristics (both classical image statistics, no model, nothing leaves the server):
- `screen`: a photographed LCD / phone screen shows a periodic pixel grid / moire. We look for strong, isolated peaks in the 2-D Fourier spectrum of the luminance (outside the lowest frequencies),
  relative to the spectrum's median level.
- `ela` (error level analysis): the photo is re-compressed as JPEG at a fixed quality and the difference is measured block by block; a region that was pasted or retouched often has a
  different error level from the rest. We flag when a few blocks are far above the typical level.

HONEST LIMITS: thresholds are first guesses, validated only on SYNTHETIC images (a drawn card, an added periodic grid, a pasted noisy patch) and NOT on real phone photos; the hosted page already
re-encodes every photo to JPEG, which weakens ELA; a good retouch or a high-quality screen photo (retina, no moire) is NOT detected; false flags on worn or glossy cards are expected.
The result must be shown to the reviewer as 'a hint', never as proof.
"""
from __future__ import annotations

SCREEN_PEAK_RATIO = 5.0      # log-spectrum contrast of the strongest isolated off-axis peak (first guess, synthetic only)
ELA_BLOCK = 32
ELA_OUTLIER_RATIO = 4.0      # a block whose unexplained error is this many times the median block
ELA_MIN_RATIO = 7.5          # the strongest block must be at least this many times the median
ELA_MIN_CLUSTER = 4          # connected blocks
ELA_MIN_FRACTION = 0.01      # ...and at least this fraction of the blocks (a localised region, not one noisy pixel)
MAX_SIDE = 1024


def _gray(image: bytes):
    import cv2
    import numpy as np
    a = cv2.imdecode(np.frombuffer(image, np.uint8), cv2.IMREAD_COLOR)
    if a is None:
        return None, None
    k = MAX_SIDE / max(a.shape[:2])
    if k < 1:
        a = cv2.resize(a, None, fx=k, fy=k, interpolation=cv2.INTER_AREA)
    return a, cv2.cvtColor(a, cv2.COLOR_BGR2GRAY)


def screen_score(gray) -> float:
    """Strongest isolated peak of the spectrum, relative to its own neighbourhood. Axis-aligned streaks (sharp horizontal / vertical edges of a card or text) are ignored."""
    import cv2
    import numpy as np
    g = gray.astype(np.float32)
    h, w = g.shape
    win = np.outer(np.hanning(h), np.hanning(w)).astype(np.float32)
    f = np.log1p(np.abs(np.fft.fftshift(np.fft.fft2((g - g.mean()) * win))))
    cy, cx = h // 2, w // 2
    yy, xx = np.ogrid[:h, :w]
    r = np.hypot((yy - cy) / h, (xx - cx) / w)
    local = cv2.blur(f, (15, 15))
    contrast = f - local                                                  # a lone peak stands out from its surroundings; a streak or broad texture does not
    mask = (r > 0.1) & (r < 0.5) & (np.abs(yy - cy) > 3) & (np.abs(xx - cx) > 3)
    return float(contrast[mask].max()) if mask.any() else 0.0


def ela_score(bgr) -> tuple[float, float]:
    """(ratio of the strongest block error to the median block error, fraction of outlier blocks)."""
    import cv2
    import numpy as np
    ok, enc = cv2.imencode(".jpg", bgr, [cv2.IMWRITE_JPEG_QUALITY, 90])
    if not ok:
        return 0.0, 0.0
    re = cv2.imdecode(enc, cv2.IMREAD_COLOR)
    d = np.abs(bgr.astype(np.int16) - re.astype(np.int16)).mean(axis=2)
    gray = cv2.cvtColor(bgr, cv2.COLOR_BGR2GRAY).astype(np.float32)
    grad = np.hypot(cv2.Sobel(gray, cv2.CV_32F, 1, 0), cv2.Sobel(gray, cv2.CV_32F, 0, 1))
    h, w = d.shape
    hb, wb = h // ELA_BLOCK, w // ELA_BLOCK
    if hb < 3 or wb < 3:
        return 0.0, 0.0
    blk = lambda m: m[:hb * ELA_BLOCK, :wb * ELA_BLOCK].reshape(hb, ELA_BLOCK, wb, ELA_BLOCK).mean(axis=(1, 3)).ravel()   # noqa: E731
    rel = blk(d) / (blk(grad) + 8.0)                                         # error that the edges in the block do not explain
    # glare / reflections (clipped highlights) and very dark blocks are not evidence: leave them out of the statistics
    clipped = blk((gray >= 250).astype(np.float32)) > 0.02
    dark = blk(gray) < 25
    keep = ~(clipped | dark)
    if keep.sum() < 12:
        return 0.0, 0.0
    grid = rel.reshape(hb, wb)
    med = float(np.median(grid[keep.reshape(hb, wb)])) + 1e-3
    out = ((grid > ELA_OUTLIER_RATIO * med) & keep.reshape(hb, wb)).astype(np.uint8)
    # an edit is one CONNECTED region; scratches and wear give scattered single blocks: keep only clusters of >= ELA_MIN_CLUSTER touching blocks
    n, lab, stats, _ = cv2.connectedComponentsWithStats(out, connectivity=8)
    big = [i for i in range(1, n) if stats[i, cv2.CC_STAT_AREA] >= ELA_MIN_CLUSTER]
    if not big:
        return 0.0, 0.0
    mask = np.isin(lab, big)
    return float(grid[mask].max() / med), float(mask.sum() / max(int(keep.sum()), 1))


def analyse(image: bytes) -> dict:
    """Returns {'status': 'scored'|'unavailable', 'screen': {...}, 'ela': {...}, 'flagged': bool, 'reasons': [...]}. Never raises."""
    try:
        bgr, gray = _gray(image)
        if bgr is None:
            return {"status": "unavailable"}
        s = screen_score(gray)
        ratio, frac = ela_score(bgr)
        reasons = []
        if s >= SCREEN_PEAK_RATIO:
            reasons.append("possible_screen_photo")
        if frac >= ELA_MIN_FRACTION and ratio >= ELA_MIN_RATIO:
            reasons.append("possible_local_edit")
        return {"status": "scored", "screen": {"peak_ratio": round(s, 1), "threshold": SCREEN_PEAK_RATIO}, "ela": {"max_ratio": round(ratio, 1), "outlier_fraction": round(frac, 4)},
                "flagged": bool(reasons), "reasons": reasons, "calibrated": False}
    except Exception:  # noqa: BLE001  advisory: never break the pipeline
        return {"status": "unavailable"}
