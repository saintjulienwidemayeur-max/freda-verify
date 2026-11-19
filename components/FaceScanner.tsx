"use client";
import { useEffect, useRef, useState } from "react";
import { detectFace, loadFace, type FaceInfo } from "./faceDetect";
import Scanner, { type ScanText } from "./Scanner";

export type FaceText = ScanText & {
  faceLoading: string; faceNone: string; faceMulti: string; faceSmall: string; faceBig: string; faceCenter: string; faceFront: string;
  turnL: string; turnR: string; turnWrong: string; turnOk: string; turnAgain: string; dirL: string; dirR: string; stepFace: string; stepTurn: string;
};

type Dir = "left" | "right";
const TICK = 110;
const ALIGN_MS = 800;      // good, frontal, centered face for this long → still photo is taken
// Head yaw thresholds in degrees. NEXT_PUBLIC_TURN_DEG exists ONLY so automated tests can use synthetic (perspective-warped) frames; never set it in production builds.
const FRONT_DEG = 9, TURN_DEG = Number(process.env.NEXT_PUBLIC_TURN_DEG) || 20;
const TURN_RATIO = 0.17;                      // fallback if the pose matrix is missing: nose offset between the cheeks that ≈ TURN_DEG
const TURN_TIMEOUT = 12000, TURN_HOLD = 2;

/**
 * Selfie scanner with face detection and an active head-turn challenge.
 *  1. one face, centered and big enough, looking straight → the still selfie is captured.
 *  2. the user is told (with a pointing finger) to turn their head LEFT or RIGHT (random) → success when the head pose passes the threshold.
 * Basic challenge only: NOT certified liveness (a pre-recorded or deep-faked video can still pass). See CLAUDE.md.
 * If MediaPipe cannot load it falls back to the basic quality scanner (no face detection).
 */
export default function FaceScanner({ onShot, onCancel, tx, accent, radius }: { onShot: (b: Blob) => void; onCancel: () => void; tx: FaceText; accent: string; radius: number }) {
  const wrap = useRef<HTMLDivElement>(null), vid = useRef<HTMLVideoElement>(null);
  const [err, setErr] = useState(false), [engine, setEngine] = useState<"loading" | "mp" | "fail">("loading");
  const [phase, setPhase] = useState<"align" | "turn" | "done">("align");
  const [dir, setDir] = useState<Dir>("left");
  const [hint, setHint] = useState(tx.faceLoading), [good, setGood] = useState(false), [prog, setProg] = useState(0), [flash, setFlash] = useState(false), [wrong, setWrong] = useState(false);
  const lmRef = useRef<Awaited<ReturnType<typeof loadFace>>["lm"] | null>(null);
  const fired = useRef(false);

  useEffect(() => {
    let stream: MediaStream | null = null, dead = false;
    (async () => {
      try {
        stream = await navigator.mediaDevices.getUserMedia({ video: { facingMode: "user", width: { ideal: 1280 } }, audio: false });
        if (dead) { stream.getTracks().forEach((t) => t.stop()); return; }
        if (vid.current) { vid.current.srcObject = stream; await vid.current.play().catch(() => {}); }
      } catch { setErr(true); }
    })();
    loadFace().then(({ lm }) => { if (!dead) { lmRef.current = lm; setEngine("mp"); } }).catch(() => { if (!dead) setEngine("fail"); });
    return () => { dead = true; stream?.getTracks().forEach((t) => t.stop()); };
  }, []);

  useEffect(() => {
    if (err || engine !== "mp") return;
    let stop = false, timer: ReturnType<typeof setTimeout>;
    let goodMs = 0, miss = 0, holdTurn = 0, turnStart = 0, still: Blob | null = null, curPhase: "align" | "turn" | "done" = "align", curDir: Dir = Math.random() < 0.5 ? "left" : "right";
    setDir(curDir);

    const snap = (): Promise<Blob | null> => new Promise((res) => {
      const v = vid.current!; const c = document.createElement("canvas"); c.width = v.videoWidth; c.height = v.videoHeight;
      c.getContext("2d")!.drawImage(v, 0, 0); c.toBlob((b) => res(b), "image/jpeg", 0.92);
    });
    const pose = (f: FaceInfo) => ({ yaw: f.yawDeg !== undefined ? f.yawDeg : (f.ratio ?? 0) * (TURN_DEG / TURN_RATIO), usingMatrix: f.yawDeg !== undefined });

    const tick = async () => {
      const v = vid.current, box = wrap.current?.getBoundingClientRect(), lm = lmRef.current;
      if (!v || !box || !lm || !v.videoWidth || v.readyState < 2 || fired.current || curPhase === "done") return;
      const f = detectFace(lm, v);
      const cw = box.width, ch = box.height, vw = v.videoWidth, vh = v.videoHeight, s = Math.max(cw / vw, ch / vh);
      const ox = (vw * s - cw) / 2, oy = (vh * s - ch) / 2;
      const rw = cw * 0.56, rh = ch * 0.62, sx = ((cw - rw) / 2 + ox) / s, sy = ((ch - rh) / 2 + oy) / s, sw = rw / s, sh = rh / s;

      if (curPhase === "align") {
        let msg = "", ok = false;
        if (f.count === 0) msg = tx.faceNone;
        else if (f.count > 1) msg = tx.faceMulti;
        else if (f.box) {
          const fh = ((f.box.y1 - f.box.y0) * vh) / sh, cx = ((f.box.x0 + f.box.x1) / 2) * vw, cy = ((f.box.y0 + f.box.y1) / 2) * vh;
          const { yaw } = pose(f);
          if (fh < 0.6) msg = tx.faceSmall; else if (fh > 1.12) msg = tx.faceBig;
          else if (Math.abs(cx - (sx + sw / 2)) > sw * 0.2 || Math.abs(cy - (sy + sh / 2)) > sh * 0.2) msg = tx.faceCenter;
          else if (Math.abs(yaw) > FRONT_DEG) msg = tx.faceFront;
          else ok = true;
        }
        if (ok) { goodMs += TICK; miss = 0; } else if (++miss > 1) goodMs = 0;
        setGood(goodMs > 0); setProg(Math.min(1, goodMs / ALIGN_MS)); setHint(ok ? tx.faceFront : msg || tx.faceCenter);
        if (goodMs >= ALIGN_MS) {
          still = await snap(); if (!still) { goodMs = 0; return; }
          curPhase = "turn"; setPhase("turn"); setProg(0); setGood(false); setWrong(false);
          curDir = Math.random() < 0.5 ? "left" : "right"; setDir(curDir); turnStart = performance.now(); holdTurn = 0;
          setHint(curDir === "left" ? tx.turnL : tx.turnR);
        }
        return;
      }

      // phase "turn"
      if (f.count > 1) { setHint(tx.faceMulti); return; }
      const sign = curDir === "left" ? 1 : -1;
      if (f.count === 1) {
        const moved = pose(f).yaw * sign;                      // > 0 → turned in the requested direction
        const need = TURN_DEG;
        setProg(Math.max(0, Math.min(1, moved / need)));
        if (moved >= need) holdTurn++; else holdTurn = 0;
        const opposite = moved <= -need * 0.75;
        setWrong(opposite);
        setHint(opposite ? `${tx.turnWrong} ${curDir === "left" ? tx.dirL : tx.dirR}` : curDir === "left" ? tx.turnL : tx.turnR);
        if (holdTurn >= TURN_HOLD && still) {
          fired.current = true; curPhase = "done"; setPhase("done"); setFlash(true); setHint(tx.turnOk); setGood(true); setProg(1);
          setTimeout(() => onShot(still!), 450);
        }
      }
      if (performance.now() - turnStart > TURN_TIMEOUT) {
        curDir = curDir === "left" ? "right" : "left"; setDir(curDir); turnStart = performance.now(); holdTurn = 0; setHint(tx.turnAgain);
      }
    };

    const loop = async () => {
      const t0 = performance.now();
      try { await tick(); } catch { /* skip a bad frame */ }
      if (!stop) timer = setTimeout(loop, Math.max(30, TICK - (performance.now() - t0)));
    };
    timer = setTimeout(loop, TICK);
    return () => { stop = true; clearTimeout(timer); };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [err, engine, tx]);

  if (engine === "fail") return <Scanner mode="selfie" onShot={onShot} onCancel={onCancel} tx={tx} accent={accent} radius={radius} />;
  if (err) return (
    <div className="grid flex-1 place-items-center rounded-2xl border p-6 text-center text-sm" role="alert">
      <div>{tx.denied}<button type="button" onClick={onCancel} className="mt-4 block w-full rounded-full border px-4 py-2.5 text-sm font-semibold">{tx.cancel}</button></div>
    </div>
  );

  const edge = phase === "turn" ? accent : good ? "#12B76A" : "#FFFFFF";
  const dirLabel = dir === "left" ? tx.dirL : tx.dirR;
  return (
    <div className="flex flex-1 flex-col gap-3">
      <div ref={wrap} className="relative min-h-[420px] flex-1 overflow-hidden rounded-2xl bg-black">
        <video ref={vid} playsInline muted autoPlay className="absolute inset-0 h-full w-full object-cover [transform:scaleX(-1)]" />
        <span className="pointer-events-none absolute left-1/2 top-1/2 h-[62%] w-[56%] -translate-x-1/2 -translate-y-1/2 rounded-[50%] border-4 shadow-[0_0_0_999px_rgba(0,0,0,.5)] transition-colors" style={{ borderColor: edge }} />

        {/* steps */}
        <div className="absolute left-3 top-3 flex gap-2 text-[11px] font-semibold text-white">
          {[[tx.stepFace, phase !== "align"], [tx.stepTurn, phase === "done"]].map(([l, done], i) => (
            <span key={i} className="flex items-center gap-1.5 rounded-full bg-black/55 px-2.5 py-1 backdrop-blur">
              <i className={`grid h-3.5 w-3.5 place-items-center rounded-full text-[9px] not-italic ${done ? "bg-[#12B76A]" : "bg-white/30"}`}>{done ? "✓" : i + 1}</i>{l as string}
            </span>
          ))}
        </div>

        {/* pointing finger: tells the user which way to turn */}
        {phase === "turn" && (
          <div className={`pointer-events-none absolute top-1/2 flex -translate-y-1/2 flex-col items-center gap-1 ${dir === "left" ? "left-8" : "right-8"}`} aria-hidden>
            <span className="text-[56px] leading-none drop-shadow-[0_4px_10px_rgba(0,0,0,.5)]" style={{ animation: `${dir === "left" ? "nudge-left" : "nudge-right"} 1.1s ease-in-out infinite` }}>{dir === "left" ? "👈" : "👉"}</span>
            <span className="flex gap-0.5 text-2xl font-black text-white drop-shadow">
              {(dir === "left" ? ["‹", "‹", "‹"] : ["›", "›", "›"]).map((c, i) => <b key={i} style={{ animation: `chev 1.1s ease-in-out ${(dir === "left" ? 2 - i : i) * 0.18}s infinite` }}>{c}</b>)}
            </span>
            <span className={`rounded-full px-3 py-1 text-xs font-extrabold tracking-widest text-white ${wrong ? "bg-[#D92D20]" : ""}`} style={wrong ? undefined : { background: accent }}>{dirLabel}</span>
          </div>
        )}

        <div className="absolute inset-x-3 bottom-3 rounded-2xl bg-black/65 px-4 py-3 text-center text-sm font-medium text-white backdrop-blur" role="status">
          {engine === "loading" ? tx.faceLoading : hint}
          <div className="mt-2 h-1 overflow-hidden rounded-full bg-white/25"><div className="h-full rounded-full transition-all duration-150" style={{ width: `${prog * 100}%`, background: phase === "turn" && !wrong ? accent : good ? "#12B76A" : accent }} /></div>
          <div className="mt-1.5 text-[10px] uppercase tracking-widest text-white/60">{tx.auto} · MediaPipe</div>
        </div>
        <span className={`pointer-events-none absolute inset-0 bg-white transition-opacity duration-300 ${flash ? "opacity-70" : "opacity-0"}`} />
      </div>
      <div className="flex gap-3"><button type="button" onClick={onCancel} className="rounded-full border px-5 py-3 text-sm font-semibold" style={{ borderRadius: radius }}>{tx.cancel}</button></div>
    </div>
  );
}
