"use client";
import { useCallback, useMemo, useRef, useState } from "react";
import { animate, motion } from "framer-motion";

type Phase = "idle" | "doc" | "face" | "done";
type Mode = "KYC" | "KYB";

const FIELDS: Record<Mode, [string, string][]> = {
  KYC: [["Nom", "JEAN-BAPTISTE Marc"], ["Né le", "14/03/1991"], ["N° document", "HT-4820917"], ["Expire", "12/2031"]],
  KYB: [["Raison sociale", "Kafe Lakay SARL"], ["N° registre", "812 445 903"], ["Gérant", "M. Pierre"], ["Siège", "Port-au-Prince"]],
};
const S = 13;
const k = (x: number, y: number) => `${x},${y}`;

function Mesh({ phase }: { phase: Phase }) {
  const pts = useMemo(() => {
    const o: [number, number][] = [];
    for (let y = 22; y <= 288; y += S)
      for (let x = 22; x <= 218; x += S) {
        const dx = (x - 120) / 84, dy = (y - 155) / 130;
        if (dx * dx + dy * dy <= 1) o.push([x, y]);
      }
    return o;
  }, []);
  const set = useMemo(() => new Set(pts.map(([x, y]) => k(x, y))), [pts]);
  const on = phase === "face";
  return (
    <svg viewBox="0 0 240 310" className="absolute inset-0 h-full w-full">
      <g stroke="#1E4FE0" strokeOpacity=".25" strokeWidth=".6">
        {pts.map(([x, y]) => (
          <g key={k(x, y)}>
            {set.has(k(x + S, y)) && <line x1={x} y1={y} x2={x + S} y2={y} />}
            {set.has(k(x, y + S)) && <line x1={x} y1={y} x2={x} y2={y + S} />}
          </g>
        ))}
      </g>
      <motion.g animate={{ opacity: on ? [0.4, 1, 0.4] : phase === "idle" ? 0.3 : 1 }} transition={{ duration: 1.6, repeat: on ? Infinity : 0 }}>
        {pts.map(([x, y]) => <circle key={k(x, y)} cx={x} cy={y} r="1.8" fill="#0A1647" />)}
      </motion.g>
      <g fill="none" stroke="#1E4FE0" strokeWidth="1.4" strokeLinecap="round">
        <ellipse cx="90" cy="130" rx="15" ry="6" /><ellipse cx="150" cy="130" rx="15" ry="6" />
        <path d="M120 135 L114 178 Q120 184 126 178" /><path d="M96 218 Q120 234 144 218" />
      </g>
      {on && <motion.rect x="20" width="200" height="3" fill="#0A1647" initial={{ y: 20 }} animate={{ y: [20, 285, 20] }} transition={{ duration: 2.2, repeat: Infinity, ease: "linear" }} />}
    </svg>
  );
}

export default function Demo() {
  const [mode, setMode] = useState<Mode>("KYC");
  const [phase, setPhase] = useState<Phase>("idle");
  const [score, setScore] = useState(0);
  const timers = useRef<ReturnType<typeof setTimeout>[]>([]);

  const run = useCallback(() => {
    timers.current.forEach(clearTimeout);
    setScore(0); setPhase("doc");
    timers.current = [
      setTimeout(() => setPhase("face"), 3000),
      setTimeout(() => { setPhase("done"); animate(0, 99.8, { duration: 1, onUpdate: setScore }); }, 6000),
    ];
  }, []);

  const busy = phase === "doc" || phase === "face";
  const done = phase === "done";
  const box = "relative h-80 overflow-hidden rounded-2xl border border-[#d6e2ff] bg-white/70";
  return (
    <div className="rounded-3xl border border-[#d6e2ff] bg-ice p-5">
      <div className="mb-4 flex gap-2" role="tablist">
        {(["KYC", "KYB"] as Mode[]).map((m) => (
          <button key={m} role="tab" aria-selected={mode === m} onClick={() => { setMode(m); setPhase("idle"); }}
            className={`rounded-full border border-[#d6e2ff] px-4 py-1.5 text-sm ${mode === m ? "bg-navy text-white" : ""}`}>{m}</button>
        ))}
      </div>
      <div className="grid gap-4 md:grid-cols-2">
        <div className={`${box} grid place-items-center`}>
          <div className="relative w-4/5 overflow-hidden rounded-lg border border-[#d6e2ff] bg-white p-3 font-mono text-[11px]">
            <div className="mb-2 text-[10px] tracking-wider">{mode === "KYC" ? "CARTE D'IDENTITÉ / ID CARD" : "EXTRAIT KBIS / REGISTRE"}</div>
            <div className="flex gap-3">
              <div className="h-16 w-12 shrink-0 bg-navy/80" style={{ backgroundImage: "radial-gradient(#fff 1px,transparent 1px)", backgroundSize: "4px 4px" }} />
              <div className="grid gap-1">
                {FIELDS[mode].map(([l, v], i) => (
                  <motion.div key={l} initial={false} animate={{ opacity: phase === "idle" ? 0.15 : 1 }} transition={{ delay: phase === "idle" ? 0 : 0.4 + i * 0.5 }}>
                    <span className="opacity-50">{l}</span> {v}
                  </motion.div>
                ))}
              </div>
            </div>
            {phase === "doc" && <motion.div className="absolute inset-x-0 h-[3px] bg-navy" initial={{ top: 0 }} animate={{ top: ["0%", "100%", "0%"] }} transition={{ duration: 2.4, ease: "linear", repeat: Infinity }} />}
          </div>
        </div>
        <div className={box}>
          <Mesh phase={phase} />
          <div className="absolute inset-x-0 bottom-3 text-center font-mono text-[11px]">
            {phase === "face" && <motion.span animate={{ opacity: [1, 0.2, 1] }} transition={{ duration: 1.1, repeat: Infinity }}>FACE RECOGNITION IS UNDER WAY...</motion.span>}
            {done && <span>✓ Liveness OK · Match {score.toFixed(1)}%</span>}
            {(phase === "idle" || phase === "doc") && <span className="opacity-50">Waiting for selfie</span>}
          </div>
        </div>
      </div>
      <div className="mt-4 grid grid-cols-2 gap-3 font-mono text-xs md:grid-cols-4">
        {[["Response", done ? "1.2s" : "—"], ["Match score", done ? `${score.toFixed(1)}%` : "—"], ["Liveness", done ? "PASS" : "—"], ["Decision", done ? "APPROVED" : busy ? "…" : "—"]].map(([l, v]) => (
          <div key={l} className="rounded-xl border border-[#d6e2ff] p-3"><div className="text-lg font-semibold">{v}</div><div className="opacity-60">{l}</div></div>
        ))}
      </div>
      <button onClick={run} disabled={busy} className="mt-4 rounded-full bg-blue px-6 py-3 text-sm font-semibold text-white hover:bg-navy disabled:opacity-50">
        {done ? "Run again" : `Simulate a ${mode} check`} ↗
      </button>
    </div>
  );
}
