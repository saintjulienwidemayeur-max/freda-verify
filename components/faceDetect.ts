// Face detection + head pose with MediaPipe Face Landmarker (tasks-vision, Apache-2.0).
// The library, its WASM and the model are self-hosted under /vendor/mediapipe and loaded lazily. Frames never leave the browser.
import type { FaceLandmarker } from "@mediapipe/tasks-vision";

export type FaceInfo = {
  count: number;
  /** face bounding box, normalized to the video frame (0..1) */
  box?: { x0: number; y0: number; x1: number; y1: number };
  /** nose offset between the cheeks in the RAW camera image: ~0 frontal, > 0 = user turned to THEIR LEFT, < 0 = to THEIR RIGHT */
  ratio?: number;
  /** head yaw in degrees from the facial transformation matrix (same sign convention as `ratio`) */
  yawDeg?: number;
  /** eye-blink scores 0..1 (left, right) from the blendshape model */
  blink?: [number, number];
};

let p: Promise<{ lm: FaceLandmarker; delegate: string }> | null = null;

export function loadFace() {
  p ??= (async () => {
    const { FilesetResolver, FaceLandmarker } = await import("@mediapipe/tasks-vision");
    const fileset = await FilesetResolver.forVisionTasks("/vendor/mediapipe/wasm");
    const make = (delegate: "GPU" | "CPU") =>
      FaceLandmarker.createFromOptions(fileset, {
        baseOptions: { modelAssetPath: "/vendor/mediapipe/face_landmarker.task", delegate },
        runningMode: "VIDEO", numFaces: 2, outputFaceBlendshapes: true, outputFacialTransformationMatrixes: true,
      });
    try { return { lm: await make("GPU"), delegate: "GPU" }; } catch { return { lm: await make("CPU"), delegate: "CPU" }; }
  })();
  p.catch(() => { p = null; });
  return p;
}

let lastTs = 0;
export function detectFace(lm: FaceLandmarker, video: HTMLVideoElement | HTMLCanvasElement): FaceInfo {
  const ts = Math.max(performance.now(), lastTs + 1); lastTs = ts; // timestamps must strictly increase
  const r = lm.detectForVideo(video, ts);
  const faces = r.faceLandmarks;
  if (!faces.length) return { count: 0 };
  const L = faces[0];
  let x0 = 1, y0 = 1, x1 = 0, y1 = 0;
  for (const q of L) { if (q.x < x0) x0 = q.x; if (q.x > x1) x1 = q.x; if (q.y < y0) y0 = q.y; if (q.y > y1) y1 = q.y; }
  const a = L[234], b = L[454], nose = L[1];
  const minX = Math.min(a.x, b.x), maxX = Math.max(a.x, b.x);
  const ratio = maxX - minX > 0.02 ? (nose.x - minX) / (maxX - minX) - 0.5 : undefined;
  let yawDeg: number | undefined;
  const m = r.facialTransformationMatrixes?.[0]?.data;
  if (m && m.length === 16) yawDeg = (Math.atan2(m[8], m[10]) * 180) / Math.PI; // rotation about the vertical axis (sign verified by test, see CLAUDE.md)
  const cats = r.faceBlendshapes?.[0]?.categories;
  const sc = (n: string) => cats?.find((c) => c.categoryName === n)?.score ?? 0;
  const blink: [number, number] | undefined = cats?.length ? [sc("eyeBlinkLeft"), sc("eyeBlinkRight")] : undefined;
  return { count: faces.length, box: { x0, y0, x1, y1 }, ratio, yawDeg, blink };
}
