"use client";
import { useEffect, useRef, useState } from "react";
import { detectCard, loadCv, rectify, type Quad } from "./cardDetect";

type Mode = "doc" | "selfie";
export type ScanText = { place: string; face: string; hold: string; dark: string; glare: string; blur: string; auto: string; done: string; capNow: string; denied: string; cancel: string; loading: string; closer: string; far: string; center: string; found: string };

const TICK = 140;                                   // analysis interval (ms)
const NEED: Record<Mode, number> = { doc: 1100, selfie: 3000 }; // good time before auto capture (selfie includes a 3-2-1 countdown)
const BLUR_MIN = 30, STABLE_MAX = 5, DARK = 55, BRIGHT = 225, GLARE = 0.18, QUAD_MOVE = 0.025;

type Engine = "loading" | "cv" | "basic";

/**
 * Camera scanner with automatic capture.
 * doc    → OpenCV.js finds the card's 4 edges, checks fit/stability/exposure/sharpness, then captures a perspective-corrected crop.
 *          If OpenCV cannot load, it falls back to the basic quality heuristics (no real detection).
 * selfie → basic heuristics (exposure, glare, sharpness, stability) + 3-2-1 countdown. No face detection yet.
 */
export default function Scanner({ mode, onShot, onCancel, tx, accent, radius }: {
  mode: Mode; onShot: (b: Blob) => void; onCancel: () => void; tx: ScanText; accent: string; radius: number;
}) {
  const wrap = useRef<HTMLDivElement>(null), vid = useRef<HTMLVideoElement>(null);
  const [err, setErr] = useState(false), [hint, setHint] = useState(mode === "doc" ? tx.loading : tx.face);
  const [prog, setProg] = useState(0), [good, setGood] = useState(false), [flash, setFlash] = useState(false), [count, setCount] = useState<number | null>(null), [manual, setManual] = useState(false);
  const [quad, setQuad] = useState<[number, number][] | null>(null);
  const [engine, setEngine] = useState<Engine>(mode === "doc" ? "loading" : "basic");
  const fired = useRef(false), cvRef = useRef<any>(null); // eslint-disable-line @typescript-eslint/no-explicit-any
  const lastQuad = useRef<Quad | null>(null);

  useEffect(() => {
    let stream: MediaStream | null = null, dead = false;
    (async () => {
      try {
        stream = await navigator.mediaDevices.getUserMedia({ video: { facingMode: mode === "selfie" ? "user" : "environment", width: { ideal: 1280 } }, audio: false });
        if (dead) { stream.getTracks().forEach((t) => t.stop()); return; }
        if (vid.current) { vid.current.srcObject = stream; await vid.current.play().catch(() => {}); }
      } catch { setErr(true); }
    })();
    if (mode === "doc") loadCv().then(({ cv }) => { if (!dead) { cvRef.current = cv; setEngine("cv"); } }).catch(() => { if (!dead) setEngine("basic"); });
    const m = setTimeout(() => setManual(true), 9000);
    return () => { dead = true; clearTimeout(m); stream?.getTracks().forEach((t) => t.stop()); };
  }, [mode]);

  const capture = () => {
    const v = vid.current; if (!v || !v.videoWidth || fired.current) return;
    fired.current = true; setFlash(true);
    let cv: HTMLCanvasElement = document.createElement("canvas"); cv.width = v.videoWidth; cv.height = v.videoHeight;
    cv.getContext("2d")!.drawImage(v, 0, 0);
    if (mode === "doc" && cvRef.current && lastQuad.current) { try { cv = rectify(cvRef.current, cv, lastQuad.current); } catch { /* keep the raw frame */ } }
    cv.toBlob((b) => { if (b) onShot(b); else fired.current = false; }, "image/jpeg", 0.92);
  };

  useEffect(() => {
    if (err || engine === "loading") return;
    const work = document.createElement("canvas"), det = document.createElement("canvas");
    let prev: Float32Array | null = null, prevQuad: Quad | null = null, goodMs = 0, miss = 0, stop = false, timer: ReturnType<typeof setTimeout>;
    const step = () => {
      const t0 = performance.now();
      try { tick(); } catch { /* skip a bad frame */ }
      if (!stop) timer = setTimeout(step, Math.max(30, TICK - (performance.now() - t0)));
    };
    const tick = () => {
      const v = vid.current, box = wrap.current?.getBoundingClientRect();
      if (!v || !box || !v.videoWidth || fired.current) return;
      const cw = box.width, ch = box.height, vw = v.videoWidth, vh = v.videoHeight, s = Math.max(cw / vw, ch / vh);
      const ox = (vw * s - cw) / 2, oy = (vh * s - ch) / 2;
      const rw = mode === "doc" ? cw * 0.86 : cw * 0.56, rh = mode === "doc" ? rw / 1.586 : ch * 0.62;
      const sx = ((cw - rw) / 2 + ox) / s, sy = ((ch - rh) / 2 + oy) / s, sw = rw / s, sh = rh / s;
      // exposure / glare / sharpness / stability on the guide area
      const W = 160, H = Math.max(24, Math.round((W * sh) / sw));
      work.width = W; work.height = H;
      const ctx = work.getContext("2d", { willReadFrequently: true })!; ctx.drawImage(v, sx, sy, sw, sh, 0, 0, W, H);
      const d = ctx.getImageData(0, 0, W, H).data, g = new Float32Array(W * H);
      let sum = 0, hot = 0;
      for (let i = 0; i < W * H; i++) { const y = 0.299 * d[i * 4] + 0.587 * d[i * 4 + 1] + 0.114 * d[i * 4 + 2]; g[i] = y; sum += y; if (y > 250) hot++; }
      const mean = sum / (W * H);
      let m = 0, m2 = 0, n = 0;
      for (let y = 1; y < H - 1; y++) for (let x = 1; x < W - 1; x++) { const i = y * W + x, l = 4 * g[i] - g[i - 1] - g[i + 1] - g[i - W] - g[i + W]; m += l; m2 += l * l; n++; }
      const sharp = m2 / n - (m / n) ** 2;
      let diff = 99;
      if (prev && prev.length === g.length) { diff = 0; for (let i = 0; i < g.length; i++) diff += Math.abs(g[i] - prev[i]); diff /= g.length; }
      prev = g;
      const dark = mean < DARK, glare = mean > BRIGHT || hot / (W * H) > GLARE, blur = sharp < BLUR_MIN, moving = diff > STABLE_MAX;

      let placement: "ok" | "none" | "small" | "big" | "off" = "ok", qStable = true;
      if (mode === "doc" && engine === "cv" && cvRef.current) {
        const DW = 320, DH = Math.round((DW * vh) / vw);
        det.width = DW; det.height = DH; det.getContext("2d", { willReadFrequently: true })!.drawImage(v, 0, 0, DW, DH);
        const q = detectCard(cvRef.current, det);
        lastQuad.current = q;
        if (!q) { placement = "none"; setQuad(null); }
        else {
          setQuad(q.pts.map(([x, y]) => [x * vw * s - ox, y * vh * s - oy] as [number, number]));
          const xs = q.pts.map((p) => p[0] * vw), ys = q.pts.map((p) => p[1] * vh);
          const fill = (q.area * vw * vh) / (sw * sh), cx = (Math.max(...xs) + Math.min(...xs)) / 2, cy = (Math.max(...ys) + Math.min(...ys)) / 2;
          if (fill < 0.55) placement = "small"; else if (fill > 1.35) placement = "big";
          else if (Math.abs(cx - (sx + sw / 2)) > sw * 0.18 || Math.abs(cy - (sy + sh / 2)) > sh * 0.25) placement = "off";
          if (prevQuad) qStable = q.pts.every(([x, y], i) => Math.hypot(x - prevQuad!.pts[i][0], y - prevQuad!.pts[i][1]) < QUAD_MOVE);
        }
        prevQuad = q;
      }

      const frameMoving = mode === "doc" && engine === "cv" ? !qStable : moving;
      const ok = placement === "ok" && !dark && !glare && !blur && !frameMoving;
      if (ok) { goodMs += TICK; miss = 0; } else if (++miss > 1) { goodMs = 0; }
      const need = NEED[mode];
      setGood(goodMs > 0);
      setProg(Math.min(1, goodMs / need));
      setHint(
        placement === "none" ? tx.place : placement === "small" ? tx.closer : placement === "big" ? tx.far : placement === "off" ? tx.center
        : dark ? tx.dark : glare ? tx.glare : blur ? tx.blur : frameMoving ? tx.hold : goodMs > 0 ? (mode === "doc" && engine === "cv" ? tx.found : tx.hold) : mode === "doc" ? tx.place : tx.face);
      setCount(mode === "selfie" && goodMs >= 900 ? Math.max(1, Math.ceil((need - goodMs) / 700)) : null);
      if (goodMs >= need) capture();
    };
    timer = setTimeout(step, TICK);
    return () => { stop = true; clearTimeout(timer); };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [err, mode, tx, engine]);

  if (err) return (
    <div className="grid flex-1 place-items-center rounded-2xl border p-6 text-center text-sm" role="alert">
      <div>{tx.denied}<button type="button" onClick={onCancel} className="mt-4 block w-full rounded-full border px-4 py-2.5 text-sm font-semibold">{tx.cancel}</button></div>
    </div>
  );

  const edge = good ? "#12B76A" : "#FFFFFF";
  return (
    <div className="flex flex-1 flex-col gap-3">
      <div ref={wrap} className="relative min-h-[380px] flex-1 overflow-hidden rounded-2xl bg-black">
        <video ref={vid} playsInline muted autoPlay className={`absolute inset-0 h-full w-full object-cover ${mode === "selfie" ? "[transform:scaleX(-1)]" : ""}`} />
        {mode === "doc" ? (
          <span className="pointer-events-none absolute left-1/2 top-1/2 aspect-[1.586] w-[86%] -translate-x-1/2 -translate-y-1/2 rounded-2xl shadow-[0_0_0_999px_rgba(0,0,0,.5)]">
            {(["left-0 top-0 border-l-4 border-t-4 rounded-tl-2xl", "right-0 top-0 border-r-4 border-t-4 rounded-tr-2xl", "left-0 bottom-0 border-l-4 border-b-4 rounded-bl-2xl", "right-0 bottom-0 border-r-4 border-b-4 rounded-br-2xl"]).map((c) => (
              <i key={c} className={`absolute h-8 w-8 transition-colors ${c}`} style={{ borderColor: edge }} />
            ))}
            {!quad && engine !== "loading" && <i className="absolute inset-x-2 h-0.5 animate-[scan-line_2.4s_ease-in-out_infinite] rounded-full" style={{ background: accent, boxShadow: `0 0 12px ${accent}` }} />}
          </span>
        ) : (
          <span className="pointer-events-none absolute left-1/2 top-1/2 h-[62%] w-[56%] -translate-x-1/2 -translate-y-1/2 rounded-[50%] border-4 shadow-[0_0_0_999px_rgba(0,0,0,.5)] transition-colors" style={{ borderColor: edge }} />
        )}
        {quad && (
          <svg className="pointer-events-none absolute inset-0 h-full w-full" aria-hidden>
            <polygon points={quad.map((p) => p.join(",")).join(" ")} fill={good ? "rgba(18,183,106,.22)" : "rgba(46,139,255,.18)"} stroke={good ? "#12B76A" : "#2E8BFF"} strokeWidth="3" strokeLinejoin="round" />
            {quad.map(([x, y], i) => <circle key={i} cx={x} cy={y} r="5" fill={good ? "#12B76A" : "#2E8BFF"} stroke="#fff" strokeWidth="2" />)}
          </svg>
        )}
        {count !== null && <span className="pointer-events-none absolute inset-0 grid place-items-center text-7xl font-extrabold text-white drop-shadow-lg" aria-live="assertive">{count}</span>}
        <div className="absolute inset-x-3 bottom-3 rounded-2xl bg-black/65 px-4 py-3 text-center text-sm font-medium text-white backdrop-blur" role="status">
          {engine === "loading" ? tx.loading : hint}
          <div className="mt-2 h-1 overflow-hidden rounded-full bg-white/25"><div className="h-full rounded-full transition-all duration-150" style={{ width: `${prog * 100}%`, background: good ? "#12B76A" : accent }} /></div>
          <div className="mt-1.5 text-[10px] uppercase tracking-widest text-white/60">{tx.auto}{mode === "doc" ? ` · ${engine === "cv" ? "OpenCV" : engine === "basic" ? "basic" : "…"}` : ""}</div>
        </div>
        <span className={`pointer-events-none absolute inset-0 bg-white transition-opacity duration-300 ${flash ? "opacity-80" : "opacity-0"}`} />
      </div>
      <div className="flex gap-3">
        <button type="button" onClick={onCancel} className="rounded-full border px-5 py-3 text-sm font-semibold" style={{ borderRadius: radius }}>{tx.cancel}</button>
        {manual && <button type="button" onClick={capture} className="flex-1 border px-5 py-3 text-sm font-semibold" style={{ borderRadius: radius, borderColor: accent, color: accent }}>{tx.capNow}</button>}
      </div>
    </div>
  );
}
