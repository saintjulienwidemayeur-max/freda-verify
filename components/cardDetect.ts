/* eslint-disable @typescript-eslint/no-explicit-any */
// Card/document edge detection with OpenCV.js (Apache-2.0, self-hosted at /vendor/opencv.js, loaded lazily).
// Everything runs in the browser; no frame ever leaves the device.

export type Pt = [number, number];
/** Corners normalized to the analysed frame (0..1): top-left, top-right, bottom-right, bottom-left. */
export type Quad = { pts: [Pt, Pt, Pt, Pt]; ratio: number; area: number };

let cvP: Promise<{ cv: any }> | null = null;

/** Resolves with a wrapper object on purpose: the `cv` module is a thenable, resolving a promise with it would never settle. */
export function loadCv(): Promise<{ cv: any }> {
  if (cvP) return cvP;
  cvP = new Promise((resolve, reject) => {
    const w = window as any;
    if (w.cv?.Mat) return resolve({ cv: w.cv });
    const s = document.createElement("script");
    s.src = "/vendor/opencv.js"; s.async = true;
    const to = setTimeout(() => reject(new Error("opencv timeout")), 30000);
    s.onload = () => {
      const cv = w.cv;
      if (cv?.Mat) { clearTimeout(to); resolve({ cv }); }
      else if (cv) cv.onRuntimeInitialized = () => { clearTimeout(to); resolve({ cv: w.cv }); };
      else { clearTimeout(to); reject(new Error("opencv missing")); }
    };
    s.onerror = () => { clearTimeout(to); reject(new Error("opencv load")); };
    document.head.appendChild(s);
  });
  cvP.catch(() => { cvP = null; });
  return cvP;
}

const dist = (a: Pt, b: Pt) => Math.hypot(a[0] - b[0], a[1] - b[1]);
function order(p: Pt[]): [Pt, Pt, Pt, Pt] {
  const s = p.map(([x, y]) => x + y), d = p.map(([x, y]) => y - x);
  return [p[s.indexOf(Math.min(...s))], p[d.indexOf(Math.min(...d))], p[s.indexOf(Math.max(...s))], p[d.indexOf(Math.max(...d))]];
}
function angleOk(q: Pt[]) {
  for (let i = 0; i < 4; i++) {
    const a = q[(i + 3) % 4], b = q[i], c = q[(i + 1) % 4];
    const v1 = [a[0] - b[0], a[1] - b[1]], v2 = [c[0] - b[0], c[1] - b[1]];
    const cos = (v1[0] * v2[0] + v1[1] * v2[1]) / (Math.hypot(v1[0], v1[1]) * Math.hypot(v2[0], v2[1]) || 1);
    if (Math.abs(cos) > 0.42) return false; // corners must be roughly 65°–115°
  }
  return true;
}

/** Finds the largest convex 4-corner contour with a card/passport-page aspect ratio. `canvas` holds the downscaled frame. */
export function detectCard(cv: any, canvas: HTMLCanvasElement): Quad | null {
  const W = canvas.width, H = canvas.height;
  const src = cv.imread(canvas), gray = new cv.Mat(), edges = new cv.Mat(), kernel = cv.getStructuringElement(cv.MORPH_RECT, new cv.Size(3, 3));
  const contours = new cv.MatVector(), hier = new cv.Mat();
  let best: Quad | null = null;
  try {
    cv.cvtColor(src, gray, cv.COLOR_RGBA2GRAY);
    cv.GaussianBlur(gray, gray, new cv.Size(5, 5), 0);
    cv.Canny(gray, edges, 40, 120);
    cv.dilate(edges, edges, kernel);
    cv.findContours(edges, contours, hier, cv.RETR_LIST, cv.CHAIN_APPROX_SIMPLE);
    const minArea = W * H * 0.035;
    for (let i = 0; i < contours.size(); i++) {
      const cnt = contours.get(i);
      try {
        const area = cv.contourArea(cnt);
        if (area < minArea || (best && area <= best.area * W * H)) continue;
        const approx = new cv.Mat();
        try {
          cv.approxPolyDP(cnt, approx, 0.02 * cv.arcLength(cnt, true), true);
          if (approx.rows !== 4 || !cv.isContourConvex(approx)) continue;
          const raw: Pt[] = []; for (let k = 0; k < 4; k++) raw.push([approx.data32S[k * 2], approx.data32S[k * 2 + 1]]);
          const q = order(raw); if (!angleOk(q)) continue;
          const w = (dist(q[0], q[1]) + dist(q[3], q[2])) / 2, h = (dist(q[0], q[3]) + dist(q[1], q[2])) / 2;
          const ratio = w / h, r = Math.max(ratio, 1 / ratio);
          if (r < 1.2 || r > 1.9) continue;              // ID-1 ≈ 1.586, passport page ≈ 1.42
          best = { pts: q.map(([x, y]) => [x / W, y / H]) as Quad["pts"], ratio, area: area / (W * H) };
        } finally { approx.delete(); }
      } finally { cnt.delete(); }
    }
  } finally { src.delete(); gray.delete(); edges.delete(); kernel.delete(); contours.delete(); hier.delete(); }
  return best;
}

/** Perspective-corrects the detected card from a full-resolution frame into a flat, upright crop. */
export function rectify(cv: any, frame: HTMLCanvasElement, q0: Quad, outW = 1000): HTMLCanvasElement {
  // always output a LANDSCAPE crop: if the card is held vertically, start from the next corner (rotates the crop by 90°)
  const q: Quad = q0.ratio >= 1 ? q0 : { ...q0, pts: [q0.pts[1], q0.pts[2], q0.pts[3], q0.pts[0]], ratio: 1 / q0.ratio };
  const w = frame.width, h = frame.height, outH = Math.round(outW / q.ratio);
  const src = cv.imread(frame), dst = new cv.Mat();
  // pull the corners 1.2 % towards the centre so the dilated contour margin (background) is cropped out
  const cx = q.pts.reduce((a, p) => a + p[0], 0) / 4, cy = q.pts.reduce((a, p) => a + p[1], 0) / 4, k = 0.988;
  const sp = cv.matFromArray(4, 1, cv.CV_32FC2, q.pts.flatMap(([x, y]) => [(cx + (x - cx) * k) * w, (cy + (y - cy) * k) * h]));
  const dp = cv.matFromArray(4, 1, cv.CV_32FC2, [0, 0, outW, 0, outW, outH, 0, outH]);
  const M = cv.getPerspectiveTransform(sp, dp);
  const out = document.createElement("canvas");
  try {
    cv.warpPerspective(src, dst, M, new cv.Size(outW, outH), cv.INTER_LINEAR, cv.BORDER_REPLICATE);
    out.width = outW; out.height = outH; cv.imshow(out, dst);
  } finally { src.delete(); dst.delete(); sp.delete(); dp.delete(); M.delete(); }
  return out;
}

export type DocKind = "id" | "passport" | "license";
/** Accepted width/height range per document: passport data page ≈ 1.42 (125×88 mm), ID-1 card ≈ 1.586 (85.6×54 mm). */
export const aspectRange = (kind: DocKind): [number, number] => (kind === "passport" ? [1.3, 1.56] : [1.45, 1.75]);
export const aspectOk = (kind: DocKind, ratio: number) => { const r = Math.max(ratio, 1 / ratio), [lo, hi] = aspectRange(kind); return r >= lo && r <= hi; };
