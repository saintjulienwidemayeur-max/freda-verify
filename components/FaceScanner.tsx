"use client";
import { useEffect, useRef, useState } from "react";
import { detectFace, loadFace, type FaceInfo } from "./faceDetect";
import type { ScanText } from "./Scanner";

export type FaceText = ScanText & {
  faceLoading: string; faceNone: string; faceMulti: string; faceSmall: string; faceBig: string; faceCenter: string; faceFront: string;
  turnL: string; turnR: string; turnWrong: string; turnOk: string; turnAgain: string; dirL: string; dirR: string; stepFace: string; stepTurn: string;
  blinkNow: string; stepAction: string; tipMore: string;
};

type Dir = "left" | "right";
type Task = { kind: "turn"; dir: Dir } | { kind: "blink" };

const TICK = 110;
const ALIGN_MS = 800;       // good, frontal, centered face for this long → the still photo is taken
const FRONT_DEG = 9;        // "looking straight" tolerance (degrees from the user's own baseline)
// Head yaw needed for a turn, in degrees. NEXT_PUBLIC_TURN_DEG exists ONLY so automated tests can use synthetic perspective-warped frames; never set it in production builds.
const TURN_DEG = Number(process.env.NEXT_PUBLIC_TURN_DEG) || 20;
const TURN_RATIO = 0.17;    // fallback if the pose matrix is missing: nose offset between the cheeks that ≈ TURN_DEG
const SOFT_AFTER = 6000;    // after this long without success the turn threshold is relaxed to 75 %
const TASK_TIMEOUT = 14000, HOLD = 2;
// Blink detection is OPT-IN (?blink=1) because it could not be validated on real faces yet. Thresholds are relative to the user's own open-eye baseline.
const BLINK_RISE = 0.25, BLINK_MIN = 0.4, BLINK_OPEN_MARGIN = 0.12;

const second = (d: Dir, blink: boolean): Task => (blink && Math.random() < 0.5 ? { kind: "blink" } : { kind: "turn", dir: d === "left" ? "right" : "left" });
const pickTasks = (blink: boolean): [Task, Task] => { const d: Dir = Math.random() < 0.5 ? "left" : "right"; return [{ kind: "turn", dir: d }, second(d, blink)]; };

/* ───────────── animated guides ───────────── */
function Hand({ dir }: { dir: Dir }) {
  // a pointing hand (index finger extended). Rotated so the finger points to the side the user must turn to.
  return (
    <svg viewBox="0 0 64 64" className="h-[68px] w-[68px] overflow-visible drop-shadow-[0_6px_12px_rgba(0,0,0,.5)]" style={{ transform: `rotate(${dir === "left" ? -90 : 90}deg)` }} aria-hidden>
      <defs><linearGradient id="hand-g" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stopColor="#ffffff" /><stop offset="1" stopColor="#dbe6ff" /></linearGradient></defs>
      <g fill="url(#hand-g)" stroke="#0A1647" strokeWidth="2.2" strokeLinejoin="round" strokeLinecap="round">
        <rect x="30" y="26" width="9" height="16" rx="4.5" /><rect x="38" y="28" width="9" height="15" rx="4.5" /><rect x="46" y="31" width="8" height="13" rx="4" />
        <path d="M18 34c0-2 1.500-3.200 3.300-3.200 1.200 0 2.200.6 2.800 1.600V20.500a3.500 3.500 0 0 1 7 0V32l.3 12.500h-3.500c-3 0-4.600-1-6-2.800L19 37c-.7-.9-1-1.800-1-3z" />
        <path d="M26 44h27v3c0 6.600-5 11-11.500 11h-5C30 58 26 54 26 48z" />
        <rect x="24.500" y="8" width="7.500" height="26" rx="3.750" />
      </g>
    </svg>
  );
}
function Chevrons({ dir, color }: { dir: Dir; color: string }) {
  return (
    <svg viewBox="0 0 54 24" className="h-6 w-[54px]" aria-hidden fill="none" stroke={color} strokeWidth="4.5" strokeLinecap="round" strokeLinejoin="round">
      {[0, 1, 2].map((i) => {
        const x = dir === "left" ? 6 + i * 14 : 14 + i * 14, d = dir === "left" ? `M${x + 8} 3 L${x} 12 L${x + 8} 21` : `M${x} 3 L${x + 8} 12 L${x} 21`;
        return <path key={i} d={d} style={{ animation: `chev 1.1s ease-in-out ${(dir === "left" ? 2 - i : i) * 0.16}s infinite` }} />;
      })}
    </svg>
  );
}
function TurnGuide({ dir, accent, wrong, label }: { dir: Dir; accent: string; wrong: boolean; label: string }) {
  return (
    <div className={`pointer-events-none absolute top-1/2 flex -translate-y-1/2 flex-col items-center gap-2 ${dir === "left" ? "left-4" : "right-4"}`} aria-hidden>
      <div style={{ animation: `${dir === "left" ? "nudge-left" : "nudge-right"} 1.2s ease-in-out infinite` }}><Hand dir={dir} /></div>
      <Chevrons dir={dir} color="#ffffff" />
      <span className="rounded-full px-3 py-1 text-xs font-extrabold tracking-widest text-white shadow" style={{ background: wrong ? "#D92D20" : accent }}>{label}</span>
    </div>
  );
}
function BlinkGuide({ accent }: { accent: string }) {
  return (
    <div className="pointer-events-none absolute inset-x-0 top-[14%] flex flex-col items-center gap-2" aria-hidden>
      <svg viewBox="0 0 64 40" className="h-14 w-24 drop-shadow-[0_6px_12px_rgba(0,0,0,.5)]">
        <path d="M4 20C12 8 22 4 32 4s20 4 28 16c-8 12-18 16-28 16S12 32 4 20z" fill="#fff" stroke="#0A1647" strokeWidth="2.4" strokeLinejoin="round" style={{ transformOrigin: "32px 20px", animation: "blink-eye 2s ease-in-out infinite" }} />
        <circle cx="32" cy="20" r="8" fill={accent} style={{ transformOrigin: "32px 20px", animation: "blink-eye 2s ease-in-out infinite" }} /><circle cx="32" cy="20" r="3.200" fill="#0A1647" style={{ transformOrigin: "32px 20px", animation: "blink-eye 2s ease-in-out infinite" }} />
      </svg>
    </div>
  );
}

/**
 * Selfie scanner: MediaPipe face detection + an ACTIVE two-step challenge with random content.
 *  1. one face, centered, big enough, looking straight → the still selfie is taken.
 *  2. task 1: turn the head LEFT or RIGHT (random);  task 2: turn the OTHER way, or blink (random). Between tasks the user must look straight again.
 * Basic challenge only: NOT certified liveness (a good replay/deepfake or a mask can still pass). If MediaPipe cannot load it FAILS CLOSED (error + retry).
 */
export default function FaceScanner({ onShot, onCancel, tx, accent, radius, debug, blink: allowBlink = false }: { onShot: (b: Blob, extra?: Blob[]) => void; onCancel: () => void; tx: FaceText; accent: string; radius: number; debug?: boolean; blink?: boolean }) {
  const wrap = useRef<HTMLDivElement>(null), vid = useRef<HTMLVideoElement>(null);
  const [err, setErr] = useState(false), [engine, setEngine] = useState<"loading" | "mp" | "fail">("loading"), [attempt, setAttempt] = useState(0);
  const [phase, setPhase] = useState<"align" | "task" | "done">("align");
  const [taskIdx, setTaskIdx] = useState(0), [tasks, setTasks] = useState<[Task, Task] | null>(null), [lookFront, setLookFront] = useState(false);
  const [hint, setHint] = useState(tx.faceLoading), [good, setGood] = useState(false), [prog, setProg] = useState(0), [flash, setFlash] = useState(false), [wrong, setWrong] = useState(false);
  const [dbg, setDbg] = useState("");
  const lmRef = useRef<Awaited<ReturnType<typeof loadFace>>["lm"] | null>(null), delegate = useRef("");
  const fired = useRef(false);

  useEffect(() => {
    let stream: MediaStream | null = null, dead = false;
    setEngine("loading"); setErr(false);
    (async () => {
      try {
        stream = await navigator.mediaDevices.getUserMedia({ video: { facingMode: "user", width: { ideal: 1280 } }, audio: false });
        if (dead) { stream.getTracks().forEach((t) => t.stop()); return; }
        if (vid.current) { vid.current.srcObject = stream; await vid.current.play().catch(() => {}); }
      } catch { if (!dead) setErr(true); }
    })();
    loadFace().then(({ lm, delegate: d }) => { if (!dead) { lmRef.current = lm; delegate.current = d; setEngine("mp"); } }).catch(() => { if (!dead) setEngine("fail"); });
    return () => { dead = true; stream?.getTracks().forEach((t) => t.stop()); };
  }, [attempt]);

  useEffect(() => {
    if (err || engine !== "mp") return;
    let stop = false, timer: ReturnType<typeof setTimeout>;
    let goodMs = 0, miss = 0, hold = 0, taskStart = 0, still: Blob | null = null, extras: Blob[] = [], midTaken = false, cur: "align" | "task" | "done" = "align", idx = 0, baseline = 0, sawOpen = false, needFront = false, frontHold = 0;
    let seq: [Task, Task] = pickTasks(allowBlink); setTasks(seq);
    let bl: [number, number] = [0, 0], blN = 0;   // open-eye blink baseline learnt while the user looks straight
    let frames = 0, fpsT = performance.now(), fps = 0;

    const snap = (): Promise<Blob | null> => new Promise((res) => {
      const v = vid.current!; const c = document.createElement("canvas"); c.width = v.videoWidth; c.height = v.videoHeight;
      c.getContext("2d")!.drawImage(v, 0, 0); c.toBlob((b) => res(b), "image/jpeg", 0.92);
    });
    const pose = (f: FaceInfo) => (f.yawDeg !== undefined ? f.yawDeg : (f.ratio ?? 0) * (TURN_DEG / TURN_RATIO)) - baseline;
    const promptFor = (t: Task) => (t.kind === "blink" ? tx.blinkNow : t.dir === "left" ? tx.turnL : tx.turnR);

    const tick = async () => {
      const v = vid.current, box = wrap.current?.getBoundingClientRect(), lm = lmRef.current;
      if (!v || !box || !lm || !v.videoWidth || v.readyState < 2 || fired.current || cur === "done") return;
      const f = detectFace(lm, v);
      frames++; if (performance.now() - fpsT > 1000) { fps = frames; frames = 0; fpsT = performance.now(); }
      const cw = box.width, ch = box.height, vw = v.videoWidth, vh = v.videoHeight, s = Math.max(cw / vw, ch / vh);
      const ox = (vw * s - cw) / 2, oy = (vh * s - ch) / 2;
      const rw = cw * 0.56, rh = ch * 0.62, sx = ((cw - rw) / 2 + ox) / s, sy = ((ch - rh) / 2 + oy) / s, sw = rw / s, sh = rh / s;
      if (debug) setDbg(`${delegate.current} ${fps}fps faces=${f.count} yaw=${f.yawDeg?.toFixed(1) ?? "-"}° ratio=${f.ratio?.toFixed(3) ?? "-"} blink=${f.blink ? f.blink.map((b) => b.toFixed(2)).join("/") : "-"} base=${baseline.toFixed(1)} ${cur}#${idx}`);

      if (cur === "align") {
        let msg = "", ok = false;
        if (f.count === 0) msg = tx.faceNone;
        else if (f.count > 1) msg = tx.faceMulti;
        else if (f.box) {
          const fh = ((f.box.y1 - f.box.y0) * vh) / sh, cx = ((f.box.x0 + f.box.x1) / 2) * vw, cy = ((f.box.y0 + f.box.y1) / 2) * vh;
          const yaw = pose(f);
          if (fh < 0.6) msg = tx.faceSmall; else if (fh > 1.12) msg = tx.faceBig;
          else if (Math.abs(cx - (sx + sw / 2)) > sw * 0.2 || Math.abs(cy - (sy + sh / 2)) > sh * 0.2) msg = tx.faceCenter;
          else if (Math.abs(yaw) > FRONT_DEG) msg = tx.faceFront;
          else ok = true;
        }
        if (ok) { goodMs += TICK; miss = 0; if (f.blink) { blN++; bl = [bl[0] + (f.blink[0] - bl[0]) / blN, bl[1] + (f.blink[1] - bl[1]) / blN]; } } else if (++miss > 1) goodMs = 0;
        if (ok && !midTaken && goodMs >= ALIGN_MS / 2) { midTaken = true; const b = await snap(); if (b) extras.push(b); }   // 2nd frontal frame (experimental PAD score uses several frames)
        setGood(goodMs > 0); setProg(Math.min(1, goodMs / ALIGN_MS)); setHint(ok ? tx.faceFront : msg || tx.faceCenter);
        if (goodMs >= ALIGN_MS) {
          still = await snap(); if (!still) { goodMs = 0; return; }
          baseline = f.yawDeg !== undefined ? f.yawDeg : (f.ratio ?? 0) * (TURN_DEG / TURN_RATIO);   // the user's own "straight" pose
          cur = "task"; setPhase("task"); idx = 0; setTaskIdx(0); setProg(0); setGood(false); setWrong(false);
          taskStart = performance.now(); hold = 0; sawOpen = false; needFront = false; setLookFront(false); setHint(promptFor(seq[0]));
        }
        return;
      }

      // phase "task"
      if (f.count > 1) { setHint(tx.faceMulti); return; }
      if (f.count === 0) return;
      const task = seq[idx], yaw = pose(f), elapsed = performance.now() - taskStart;

      if (needFront) {                                   // between the two tasks: look straight again
        if (Math.abs(yaw) <= FRONT_DEG) frontHold++; else frontHold = 0;
        setHint(tx.faceFront); setLookFront(true);
        if (frontHold >= 3) { if (extras.length < 2) { const b = await snap(); if (b) extras.push(b); } needFront = false; setLookFront(false); taskStart = performance.now(); hold = 0; sawOpen = false; setWrong(false); setHint(promptFor(task)); }
        return;
      }

      let achieved = false;
      if (task.kind === "turn") {
        const sign = task.dir === "left" ? 1 : -1, moved = yaw * sign;
        const need = elapsed > SOFT_AFTER ? TURN_DEG * 0.75 : TURN_DEG;
        setProg(Math.max(0, Math.min(1, moved / need)));
        const opposite = moved <= -need * 0.75;
        setWrong(opposite);
        setHint(opposite ? `${tx.turnWrong} ${task.dir === "left" ? tx.dirL : tx.dirR}` : elapsed > SOFT_AFTER && moved > 5 && moved < need ? tx.tipMore : promptFor(task));
        if (moved >= need) hold++; else hold = 0;
        achieved = hold >= HOLD;
      } else {
        const b = f.blink;
        if (b) {
          const lim = [Math.max(bl[0] + BLINK_RISE, BLINK_MIN), Math.max(bl[1] + BLINK_RISE, BLINK_MIN)];
          const closed = b[0] > lim[0] && b[1] > lim[1], open = b[0] < bl[0] + BLINK_OPEN_MARGIN && b[1] < bl[1] + BLINK_OPEN_MARGIN;
          if (open) sawOpen = true;
          setProg(Math.min(1, Math.max(0, Math.min(b[0] / lim[0], b[1] / lim[1]))));
          if (closed && sawOpen) achieved = true;
        }
        setHint(promptFor(task));
      }
      if (achieved) {
        if (idx === 0) { idx = 1; setTaskIdx(1); needFront = true; frontHold = 0; setProg(0); setWrong(false); setHint(tx.faceFront); setLookFront(true); return; }
        fired.current = true; cur = "done"; setPhase("done"); setFlash(true); setHint(tx.turnOk); setGood(true); setProg(1);
        setTimeout(() => onShot(still!, extras.slice(0, 2)), 450);
        return;
      }
      if (elapsed > TASK_TIMEOUT) {                      // time out: new random content for the current step
        seq = idx === 0 ? pickTasks(allowBlink) : [seq[0], second((seq[0] as { kind: "turn"; dir: Dir }).dir, allowBlink)];
        setTasks(seq); taskStart = performance.now(); hold = 0; sawOpen = false; setHint(tx.turnAgain);
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

  const task = tasks?.[taskIdx];
  const edge = phase === "task" ? accent : good ? "#12B76A" : "#FFFFFF";
  const chips: [string, boolean][] = [[tx.stepFace, phase !== "align"], [tx.stepTurn, phase === "done" || taskIdx > 0 && phase === "task"], [tx.stepAction, phase === "done"]];
  return (
    <div className="flex flex-1 flex-col gap-3">
      <div ref={wrap} className="relative min-h-[420px] flex-1 overflow-hidden rounded-2xl bg-black">
        <video ref={vid} playsInline muted autoPlay className="absolute inset-0 h-full w-full object-cover [transform:scaleX(-1)]" />
        <span className="pointer-events-none absolute left-1/2 top-1/2 h-[62%] w-[56%] -translate-x-1/2 -translate-y-1/2 rounded-[50%] border-4 shadow-[0_0_0_999px_rgba(0,0,0,.5)] transition-colors" style={{ borderColor: edge }} />

        <div className="absolute left-3 top-3 flex gap-1.5 text-[11px] font-semibold text-white">
          {chips.map(([l, done], i) => (
            <span key={i} className="flex items-center gap-1.5 rounded-full bg-black/55 px-2.5 py-1 backdrop-blur">
              <i className={`grid h-3.5 w-3.5 place-items-center rounded-full text-[9px] not-italic ${done ? "bg-[#12B76A]" : "bg-white/30"}`}>{done ? "✓" : i + 1}</i>{l}
            </span>
          ))}
        </div>
        {debug && <pre className="absolute inset-x-2 top-10 whitespace-pre-wrap rounded bg-black/70 p-1.5 text-[10px] leading-tight text-lime-300">{dbg}</pre>}

        {phase === "task" && task && !lookFront && (task.kind === "turn"
          ? <TurnGuide dir={task.dir} accent={accent} wrong={wrong} label={task.dir === "left" ? tx.dirL : tx.dirR} />
          : <BlinkGuide accent={accent} />)}

        <div className="absolute inset-x-3 bottom-3 rounded-2xl bg-black/65 px-4 py-3 text-center text-sm font-medium text-white backdrop-blur" role="status">
          {engine === "loading" ? tx.faceLoading : hint}
          <div className="mt-2 h-1 overflow-hidden rounded-full bg-white/25"><div className="h-full rounded-full transition-all duration-150" style={{ width: `${prog * 100}%`, background: phase === "task" && !wrong ? accent : good ? "#12B76A" : accent }} /></div>
          <div className="mt-1.5 text-[10px] uppercase tracking-widest text-white/60">{tx.auto} · MediaPipe</div>
        </div>
        <span className={`pointer-events-none absolute inset-0 bg-white transition-opacity duration-300 ${flash ? "opacity-70" : "opacity-0"}`} />
      </div>
      <div className="flex gap-3"><button type="button" onClick={onCancel} className="rounded-full border px-5 py-3 text-sm font-semibold" style={{ borderRadius: radius }}>{tx.cancel}</button></div>
    </div>
  );
}
