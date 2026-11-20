/* eslint-disable @typescript-eslint/no-explicit-any */
// Strict document checks, run in the browser on the perspective-corrected crop (OpenCV.js + MediaPipe).
// A passport page is accepted ONLY if: it has a passport-page shape, a face photo on the left AND the two machine-readable lines (MRZ) at the bottom.
// An ID card / licence front needs the card shape + a face photo; the back needs the card shape.
// These are heuristics: they reject random objects, plain faces, screens of other shapes, but they do NOT prove the document is genuine.
import type { FaceLandmarker } from "@mediapipe/tasks-vision";
import { aspectOk, detectCard, rectify, type DocKind } from "./cardDetect";
import { detectFace } from "./faceDetect";

export type Side = "front" | "back";
export type Reject = "shape" | "face" | "mrz" | "unavailable";
export type Verdict = { ok: true } | { ok: false; reject: Reject };

export const needsFace = (kind: DocKind, side: Side) => kind === "passport" || side === "front";

/** Two dense, full-width text lines in the bottom ~30 % of a passport data page (the MRZ). */
export function mrzOk(cv: any, canvas: HTMLCanvasElement): boolean {
  const src = cv.imread(canvas), gray = new cv.Mat(), bw = new cv.Mat();
  try {
    cv.cvtColor(src, gray, cv.COLOR_RGBA2GRAY);
    const H = gray.rows, W = gray.cols, y0 = Math.floor(H * 0.66);
    const roi = gray.roi(new cv.Rect(0, y0, W, H - y0));
    try { cv.adaptiveThreshold(roi, bw, 255, cv.ADAPTIVE_THRESH_GAUSSIAN_C, cv.THRESH_BINARY_INV, 25, 14); } finally { roi.delete(); }
    const rh = bw.rows, rw = bw.cols, d = bw.data as Uint8Array;
    const rowDen = new Float32Array(rh), rowMin = new Int32Array(rh).fill(rw), rowMax = new Int32Array(rh).fill(-1);
    for (let y = 0; y < rh; y++) for (let x = 0; x < rw; x++) if (d[y * rw + x]) { rowDen[y]++; if (x < rowMin[y]) rowMin[y] = x; if (x > rowMax[y]) rowMax[y] = x; }
    const isText = (y: number) => { const den = rowDen[y] / rw; return den > 0.05 && den < 0.7 && rowMax[y] - rowMin[y] > rw * 0.6; };
    const bands: [number, number][] = []; let s = -1;
    for (let y = 0; y <= rh; y++) { const t = y < rh && isText(y); if (t && s < 0) s = y; if (!t && s >= 0) { bands.push([s, y - 1]); s = -1; } }
    const minH = H * 0.015, maxH = H * 0.075;
    let good = 0;
    for (const [a, b] of bands) {
      const h = b - a + 1; if (h < minH || h > maxH) continue;
      const cols = new Uint8Array(rw); let x0 = rw, x1 = -1;
      for (let y = a; y <= b; y++) for (let x = 0; x < rw; x++) if (d[y * rw + x]) { cols[x] = 1; if (x < x0) x0 = x; if (x > x1) x1 = x; }
      const occ = cols.reduce((n, v) => n + v, 0) / rw;
      if (x1 - x0 > rw * 0.78 && occ > 0.5) good++;
    }
    return good >= 2;
  } finally { src.delete(); gray.delete(); bw.delete(); }
}

/** Validates an already rectified (landscape) crop. */
export function validateDoc(cv: any, lm: FaceLandmarker | null, kind: DocKind, side: Side, crop: HTMLCanvasElement): Verdict {
  if (!aspectOk(kind, crop.width / crop.height)) return { ok: false, reject: "shape" };
  if (needsFace(kind, side)) {
    if (!lm) return { ok: false, reject: "unavailable" };
    const f = detectFace(lm, crop);
    const b = f.box;
    const fh = b ? (b.y1 - b.y0) : 0, cx = b ? (b.x0 + b.x1) / 2 : 1;
    // the portrait must be a real printed-size photo: 20–85 % of the page height; on a passport it sits on the left half
    if (f.count < 1 || !b || fh < 0.2 || fh > 0.85 || (kind === "passport" && cx > 0.55)) return { ok: false, reject: "face" };
  }
  if (kind === "passport" && !mrzOk(cv, crop)) return { ok: false, reject: "mrz" };
  return { ok: true };
}

function rotate90(c: HTMLCanvasElement): HTMLCanvasElement {
  const o = document.createElement("canvas"); o.width = c.height; o.height = c.width;
  const g = o.getContext("2d")!; g.translate(o.width, 0); g.rotate(Math.PI / 2); g.drawImage(c, 0, 0);
  return o;
}

/** Validates an uploaded image: finds the document, flattens it, then runs the same checks as the live scanner. */
export async function validateFile(cv: any, lm: FaceLandmarker | null, kind: DocKind, side: Side, file: Blob): Promise<{ ok: true; blob: Blob } | { ok: false; reject: Reject }> {
  let bmp: ImageBitmap;
  try { bmp = await createImageBitmap(file); } catch { return { ok: false, reject: "shape" }; }
  const k = Math.min(1, 1600 / Math.max(bmp.width, bmp.height));
  const full = document.createElement("canvas"); full.width = Math.round(bmp.width * k); full.height = Math.round(bmp.height * k);
  full.getContext("2d")!.drawImage(bmp, 0, 0, full.width, full.height); bmp.close?.();
  const det = document.createElement("canvas"); det.width = 320; det.height = Math.max(24, Math.round((320 * full.height) / full.width));
  det.getContext("2d", { willReadFrequently: true })!.drawImage(full, 0, 0, det.width, det.height);
  const q = detectCard(cv, det);
  let crop: HTMLCanvasElement;
  if (q && aspectOk(kind, q.ratio)) crop = rectify(cv, full, q);
  else if (!q && aspectOk(kind, full.width / full.height)) crop = full.width >= full.height ? full : rotate90(full);   // already a tight crop of the page (no visible outline): the face and MRZ checks below still apply
  else return { ok: false, reject: "shape" };
  const v = validateDoc(cv, lm, kind, side, crop);
  if (!v.ok) return v;
  const blob = await new Promise<Blob | null>((res) => crop.toBlob((b) => res(b), "image/jpeg", 0.92));
  return blob ? { ok: true, blob } : { ok: false, reject: "shape" };
}
