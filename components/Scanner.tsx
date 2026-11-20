"use client";
import { useEffect, useRef, useState } from "react";
import { aspectOk, detectCard, loadCv, rectify, type DocKind, type Quad } from "./cardDetect";
import { needsFace, validateDoc, type Reject, type Side } from "./docValidate";
import { loadFace } from "./faceDetect";

export type ScanText = {
  place: string; face: string; hold: string; dark: string; glare: string; blur: string; auto: string; done: string; capNow: string; denied: string; cancel: string;
  loading: string; closer: string; far: string; center: string; found: string; fitFrame: string; guideChecking: string; capNowBtn: string;
  scanFail: string; retry: string; showPassport: string; showId: string; docRej: string; rejShape: string; rejFace: string; rejMrz: string; rejUnavail: string;
};

const TICK = 140;                       // analysis interval (ms)
const NEED = 1100;                      // good time before the automatic capture (ms)
const BLUR_MIN = 30, DARK = 55, BRIGHT = 252, GLARE = 0.5, QUAD_MOVE = 0.025;   // a pale passport page is bright but not glare: only clipped pixels count

/**
 * Document scanner with automatic capture (document side only; the selfie uses FaceScanner).
 *  1. OpenCV.js finds the card edges; the user is guided (closer / back / center) and the shape must match the chosen document (passport page ≠ ID card).
 *  2. After ~1.1 s of a steady, well-exposed, sharp document the frame is flattened and STRICTLY validated (face photo, passport MRZ lines).
 *  3. Only a validated crop is returned. If OpenCV / MediaPipe cannot load the scanner FAILS CLOSED (error + retry); it never accepts "anything".
 */
export default function Scanner({ kind, side, onShot, onCancel, tx, accent, radius, debug }: {
  kind: DocKind; side: Side; onShot: (b: Blob) => void; onCancel: () => void; tx: ScanText; accent: string; radius: number; debug?: boolean;
}) {
  const wrap = useRef<HTMLDivElement>(null), vid = useRef<HTMLVideoElement>(null);
  const [err, setErr] = useState(false), [engine, setEngine] = useState<"loading" | "ready" | "fail">("loading"), [attempt, setAttempt] = useState(0);
  const [hint, setHint] = useState(tx.loading), [prog, setProg] = useState(0), [good, setGood] = useState(false), [flash, setFlash] = useState(false);
  const [quad, setQuad] = useState<[number, number][] | null>(null), [rej, setRej] = useState<Reject | null>(null), [dbg, setDbg] = useState(""), [diag, setDiag] = useState(""), [showManual, setShowManual] = useState(false);
  const manualRef = useRef<() => void>(() => {});
  const fired = useRef(false), cvRef = useRef<any>(null), lmRef = useRef<any>(null), lastQuad = useRef<Quad | null>(null); // eslint-disable-line @typescript-eslint/no-explicit-any
  const wantFace = needsFace(kind, side);

  useEffect(() => {
    let stream: MediaStream | null = null, dead = false;
    setEngine("loading"); setErr(false);
    (async () => {
      try {
        stream = await navigator.mediaDevices.getUserMedia({ video: { facingMode: "environment", width: { ideal: 1280 } }, audio: false });
        if (dead) { stream.getTracks().forEach((t) => t.stop()); return; }
        if (vid.current) { vid.current.srcObject = stream; await vid.current.play().catch(() => {}); }
      } catch { if (!dead) setErr(true); }
    })();
    Promise.all([loadCv(), wantFace ? loadFace() : Promise.resolve(null)])
      .then(([c, f]) => { if (dead) return; cvRef.current = c.cv; lmRef.current = f ? f.lm : null; setEngine("ready"); })
      .catch(() => { if (!dead) setEngine("fail"); });
    return () => { dead = true; stream?.getTracks().forEach((t) => t.stop()); };
  }, [attempt, wantFace]);

  useEffect(() => {
    if (err || engine !== "ready") return;
    const work = document.createElement("canvas"), det = document.createElement("canvas");
    let prev: Float32Array | null = null, prevQuad: Quad | null = null, goodMs = 0, miss = 0, stop = false, cooldown = 0, timer: ReturnType<typeof setTimeout>;
    let lastGuide = 0, guideOk = 0, guideWhy: Reject | null = null, steadyMs = 0;
    const t0 = performance.now(), manualTimer = setTimeout(() => setShowManual(true), 5000);
    manualRef.current = () => {
      const v = vid.current, box = wrap.current?.getBoundingClientRect();
      if (!v || !box || !v.videoWidth || fired.current) return;
      const cw = box.width, ch = box.height, vw = v.videoWidth, vh = v.videoHeight, s = Math.max(cw / vw, ch / vh), ox = (vw * s - cw) / 2, oy = (vh * s - ch) / 2;
      const rw = cw * 0.86, rh = rw / (kind === "passport" ? 1.42 : 1.586);
      const sx = ((cw - rw) / 2 + ox) / s, sy = ((ch - rh) / 2 + oy) / s, sw = rw / s, sh = rh / s;
      const c = document.createElement("canvas"); c.width = Math.round(sw); c.height = Math.round(sh);
      c.getContext("2d")!.drawImage(v, sx, sy, sw, sh, 0, 0, c.width, c.height);
      fired.current = true; setFlash(true); setRej(null);
      c.toBlob((b) => { if (b) onShot(b); else fired.current = false; }, "image/jpeg", 0.92);   // the server still checks a passport page for its MRZ text
    };

    const capture = () => {
      const v = vid.current; if (!v || !v.videoWidth || fired.current || !lastQuad.current) return;
      fired.current = true;
      const full = document.createElement("canvas"); full.width = v.videoWidth; full.height = v.videoHeight;
      full.getContext("2d")!.drawImage(v, 0, 0);
      let verdict; let crop: HTMLCanvasElement | null = null;
      try { crop = rectify(cvRef.current, full, lastQuad.current); verdict = validateDoc(cvRef.current, lmRef.current, kind, side, crop); } catch { verdict = { ok: false as const, reject: "unavailable" as Reject }; }
      if (!verdict.ok) { setRej(verdict.reject); goodMs = 0; cooldown = performance.now() + 3500; fired.current = false; return; }
      setFlash(true); setRej(null);
      crop!.toBlob((b) => { if (b) onShot(b); else fired.current = false; }, "image/jpeg", 0.92);
    };

    const tick = () => {
      const v = vid.current, box = wrap.current?.getBoundingClientRect();
      if (!v || !box || !v.videoWidth || fired.current) return;
      const cw = box.width, ch = box.height, vw = v.videoWidth, vh = v.videoHeight, s = Math.max(cw / vw, ch / vh);
      const ox = (vw * s - cw) / 2, oy = (vh * s - ch) / 2;
      const rw = cw * 0.86, rh = rw / (kind === "passport" ? 1.42 : 1.586);
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
      const dark = mean < DARK, glare = mean > BRIGHT || hot / (W * H) > GLARE, blur = sharp < BLUR_MIN;
      let motion = 99;                                                    // mean absolute pixel change since the previous analysed frame
      if (prev && prev.length === g.length) { let acc = 0; for (let i = 0; i < g.length; i++) acc += Math.abs(g[i] - prev[i]); motion = acc / g.length; }
      prev = g;

      const DW = 320, DH = Math.round((DW * vh) / vw);
      det.width = DW; det.height = DH; det.getContext("2d", { willReadFrequently: true })!.drawImage(v, 0, 0, DW, DH);
      const q = detectCard(cvRef.current, det);
      lastQuad.current = q;
      let placement: "ok" | "none" | "wrong" | "small" | "big" | "off" = "ok", stable = true, fill = 0;
      if (!q) { placement = "none"; setQuad(null); }
      else {
        setQuad(q.pts.map(([x, y]) => [x * vw * s - ox, y * vh * s - oy] as [number, number]));
        const xs = q.pts.map((p) => p[0] * vw), ys = q.pts.map((p) => p[1] * vh);
        fill = (q.area * vw * vh) / (sw * sh);
        const cx = (Math.max(...xs) + Math.min(...xs)) / 2, cy = (Math.max(...ys) + Math.min(...ys)) / 2;
        if (!aspectOk(kind, q.ratio)) placement = "wrong";
        else if (fill < 0.55) placement = "small"; else if (fill > 1.35) placement = "big";
        else if (Math.abs(cx - (sx + sw / 2)) > sw * 0.18 || Math.abs(cy - (sy + sh / 2)) > sh * 0.25) placement = "off";
        if (prevQuad) stable = q.pts.every(([x, y], i) => Math.hypot(x - prevQuad!.pts[i][0], y - prevQuad!.pts[i][1]) < QUAD_MOVE);
      }
      prevQuad = q;

      const cooling = performance.now() < cooldown;
      // PASSPORT fallback when no page outline is found (page held open, busy background, plastic sleeve...): the user aligns the photo page with the frame
      // and we validate the frame area itself with the same strict checks (photo on the left + the two MRZ lines). Never used for ID cards (no content check on the back).
      const quadGood = !!q && aspectOk(kind, q.ratio);
      if (kind === "passport" && !quadGood && !dark && !blur && !cooling && !fired.current && performance.now() - lastGuide > 1300) {
        lastGuide = performance.now();
        const gc = document.createElement("canvas"); gc.width = Math.round(sw); gc.height = Math.round(sh);
        gc.getContext("2d")!.drawImage(v, sx, sy, sw, sh, 0, 0, gc.width, gc.height);
        let gv: ReturnType<typeof validateDoc>;
        try { gv = validateDoc(cvRef.current, lmRef.current, kind, side, gc); } catch { gv = { ok: false, reject: "unavailable" }; }
        if (gv.ok) {
          guideOk++; guideWhy = null;
          if (guideOk >= 2 && !fired.current) {
            fired.current = true; setFlash(true); setRej(null);
            gc.toBlob((b) => { if (b) onShot(b); else fired.current = false; }, "image/jpeg", 0.92);
          }
        } else { guideOk = Math.max(0, guideOk - 1); guideWhy = gv.reject; }       // one noisy frame must not erase the progress
      }
      if (quadGood) { guideOk = 0; guideWhy = null; steadyMs = 0; }
      // PASSPORT automatic capture when the frame checks cannot confirm (real phones: glare, sleeve, hand shake): if the page is held steady, sharp and lit for ~3 s,
      // take the picture anyway. The SERVER then decides (it refuses a photo without readable MRZ text), so this never accepts a wrong document by itself.
      if (kind === "passport" && !quadGood && !dark && !blur && !cooling && !fired.current && motion < 7) steadyMs += TICK; else steadyMs = 0;   // brightness is not a blocker here: a pale page is normal and the server judges the photo
      if (steadyMs >= 3000 && !fired.current) { steadyMs = 0; cooldown = performance.now() + 6000; manualRef.current(); }
      const ok = placement === "ok" && !dark && !glare && !blur && stable && !cooling;
      if (ok) { goodMs += TICK; miss = 0; } else if (++miss > 1) { goodMs = 0; }
      setGood(goodMs > 0 || guideOk > 0); setProg(Math.min(1, Math.max(goodMs / NEED, guideOk / 2, steadyMs / 3000)));
      if (placement !== "ok" || goodMs === 0) { if (!cooling) setRej(null); }
      const guideHint = kind === "passport" && !quadGood
        ? (guideOk > 0 ? tx.guideChecking : guideWhy === "face" ? tx.rejFace : guideWhy === "mrz" ? tx.rejMrz : tx.fitFrame) : null;
      setHint(
        guideHint && placement !== "ok" && (placement === "none" || placement === "wrong") ? guideHint
        : placement === "none" ? tx.place : placement === "wrong" ? (kind === "passport" ? tx.showPassport : tx.showId) : placement === "small" ? tx.closer : placement === "big" ? tx.far : placement === "off" ? tx.center
        : dark ? tx.dark : glare ? tx.glare : blur ? tx.blur : !stable ? tx.hold : tx.found);
      setDiag(`${placement}${kind === "passport" && !quadGood ? ` · frame check: ${guideOk > 0 ? "ok " + guideOk + "/2" : guideWhy ?? "…"}` : ""}${dark ? " · dark" : glare ? " · bright" : blur ? " · blurry" : ""}`);
      if (debug) setDbg(`guide ok=${guideOk} why=${guideWhy ?? "-"} cv ratio=${q ? (Math.max(q.ratio, 1 / q.ratio)).toFixed(2) : "-"} fill=${fill.toFixed(2)} mean=${mean.toFixed(0)} sharp=${sharp.toFixed(0)} stable=${stable} ${placement}`);
      if (goodMs >= NEED) capture();
    };

    const step = () => {
      const t0 = performance.now();
      try { tick(); } catch { /* skip a bad frame */ }
      if (!stop) timer = setTimeout(step, Math.max(30, TICK - (performance.now() - t0)));
    };
    timer = setTimeout(step, TICK);
    return () => { stop = true; clearTimeout(timer); clearTimeout(manualTimer); void prev; void t0; };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [err, engine, kind, side, tx]);

  if (err) return (
    <div className="grid flex-1 place-items-center rounded-2xl border p-6 text-center text-sm" role="alert">
      <div>{tx.denied}<button type="button" onClick={onCancel} className="mt-4 block w-full rounded-full border px-4 py-2.5 text-sm font-semibold">{tx.cancel}</button></div>
    </div>
  );
  if (engine === "fail") return (
    <div className="grid flex-1 place-items-center rounded-2xl border p-6 text-center text-sm" role="alert">
      <div>{tx.scanFail}
        <button type="button" onClick={() => setAttempt((a) => a + 1)} className="mt-4 block w-full rounded-full px-4 py-2.5 text-sm font-semibold text-white" style={{ background: accent }}>{tx.retry}</button>
        <button type="button" onClick={onCancel} className="mt-2 block w-full rounded-full border px-4 py-2.5 text-sm font-semibold">{tx.cancel}</button></div>
    </div>
  );

  const edge = good ? "#12B76A" : "#FFFFFF";
  const rejText = rej === "shape" ? tx.rejShape : rej === "face" ? tx.rejFace : rej === "mrz" ? tx.rejMrz : rej === "unavailable" ? tx.rejUnavail : "";
  return (
    <div className="flex flex-1 flex-col gap-3">
      <div ref={wrap} className="relative min-h-[380px] flex-1 overflow-hidden rounded-2xl bg-black">
        <video ref={vid} playsInline muted autoPlay className="absolute inset-0 h-full w-full object-cover" />
        <span className={`pointer-events-none absolute left-1/2 top-1/2 w-[86%] -translate-x-1/2 -translate-y-1/2 rounded-2xl shadow-[0_0_0_999px_rgba(0,0,0,.5)] ${kind === "passport" ? "aspect-[1.42]" : "aspect-[1.586]"}`}>
          {(["left-0 top-0 border-l-4 border-t-4 rounded-tl-2xl", "right-0 top-0 border-r-4 border-t-4 rounded-tr-2xl", "left-0 bottom-0 border-l-4 border-b-4 rounded-bl-2xl", "right-0 bottom-0 border-r-4 border-b-4 rounded-br-2xl"]).map((c) => (
            <i key={c} className={`absolute h-8 w-8 transition-colors ${c}`} style={{ borderColor: edge }} />
          ))}
          {!quad && engine === "ready" && <i className="absolute inset-x-2 h-0.5 animate-[scan-line_2.4s_ease-in-out_infinite] rounded-full" style={{ background: accent, boxShadow: `0 0 12px ${accent}` }} />}
        </span>
        {quad && (
          <svg className="pointer-events-none absolute inset-0 h-full w-full" aria-hidden>
            <polygon points={quad.map((p) => p.join(",")).join(" ")} fill={good ? "rgba(18,183,106,.22)" : "rgba(46,139,255,.18)"} stroke={good ? "#12B76A" : "#2E8BFF"} strokeWidth="3" strokeLinejoin="round" />
            {quad.map(([x, y], i) => <circle key={i} cx={x} cy={y} r="5" fill={good ? "#12B76A" : "#2E8BFF"} stroke="#fff" strokeWidth="2" />)}
          </svg>
        )}
        {debug && <pre className="absolute left-2 top-2 max-w-[92%] whitespace-pre-wrap rounded bg-black/70 p-1.5 text-[10px] leading-tight text-lime-300">{dbg}</pre>}
        {rej && (
          <div className="absolute inset-x-3 top-3 rounded-2xl bg-[#B42318] px-4 py-3 text-sm font-medium text-white shadow-lg" role="alert">
            <b className="block">{tx.docRej}</b>{rejText}
          </div>
        )}
        <div className="absolute inset-x-3 bottom-3 rounded-2xl bg-black/65 px-4 py-3 text-center text-sm font-medium text-white backdrop-blur" role="status">
          {engine === "loading" ? tx.loading : hint}
          <div className="mt-2 h-1 overflow-hidden rounded-full bg-white/25"><div className="h-full rounded-full transition-all duration-150" style={{ width: `${prog * 100}%`, background: good ? "#12B76A" : accent }} /></div>
          <div className="mt-1.5 text-[10px] uppercase tracking-widest text-white/60">{tx.auto} · {diag || "…"}</div>
        </div>
        <span className={`pointer-events-none absolute inset-0 bg-white transition-opacity duration-300 ${flash ? "opacity-80" : "opacity-0"}`} />
      </div>
      <div className="flex gap-3">{showManual && <button type="button" onClick={() => manualRef.current()} className="flex-1 rounded-full px-5 py-3 text-sm font-semibold text-white" style={{ background: accent, borderRadius: radius }}>{tx.capNowBtn}</button>}<button type="button" onClick={onCancel} className="rounded-full border px-5 py-3 text-sm font-semibold" style={{ borderRadius: radius }}>{tx.cancel}</button></div>
    </div>
  );
}
