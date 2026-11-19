"use client";
import { useEffect, useRef, useState } from "react";
import { AnimatePresence, animate, motion, useInView, useReducedMotion } from "framer-motion";

const BLUE = "#1E4FE0";
const RED = "#D92D20";
const GREEN = "#12B76A";

type Scenario = { selfie: "same" | "other"; score: number; match: boolean };
const SCENARIOS: Scenario[] = [
  { selfie: "same", score: 98, match: true },
  { selfie: "other", score: 34, match: false },
];
const CHECKS = ["Qualité d'image", "Un seul visage", "Aucune occlusion"];

// Card geometry (SVG viewBox 400 x 190)
const DOC = { x: 70, y: 8 };
const SELF = { x: 230, y: 8 };
const CW = 100;
const PH = { dx: 8, dy: 8, w: 84, h: 100 };
const face = (c: { x: number; y: number }) => ({ cx: c.x + PH.dx + PH.w / 2, cy: c.y + PH.dy + 46 });
const LANDMARKS: [number, number][] = [[-8, -5], [8, -5], [0, 5], [0, 14]];

function Person({ x, y, variant, doc }: { x: number; y: number; variant: "man" | "woman"; doc?: boolean }) {
  const { cx, cy } = face({ x, y });
  const skin = doc ? "#C9CDD6" : variant === "man" ? "#B9A595" : "#D2B8A6";
  const hair = doc ? "#3B4252" : "#1C1F2A";
  const shirt = doc ? "#5B6478" : "#0A1647";
  const px = x + PH.dx, py = y + PH.dy;
  return (
    <g>
      <clipPath id={`clip-${x}`}><rect x={px} y={py} width={PH.w} height={PH.h} rx="6" /></clipPath>
      <g clipPath={`url(#clip-${x})`}>
        <rect x={px} y={py} width={PH.w} height={PH.h} fill={doc ? "#E7EAF0" : "#DDE6F6"} />
        {variant === "woman" && <path d={`M${cx - 24} ${cy - 6} Q${cx - 26} ${cy + 40} ${cx - 30} ${cy + 52} L${cx + 30} ${cy + 52} Q${cx + 26} ${cy + 40} ${cx + 24} ${cy - 6} Z`} fill={hair} />}
        <path d={`M${cx - 38} ${py + PH.h} Q${cx - 34} ${cy + 30} ${cx} ${cy + 28} Q${cx + 34} ${cy + 30} ${cx + 38} ${py + PH.h} Z`} fill={shirt} />
        <rect x={cx - 7} y={cy + 16} width="14" height="14" fill={skin} />
        <ellipse cx={cx} cy={cy} rx="18" ry="23" fill={skin} />
        {variant === "man"
          ? <path d={`M${cx - 18} ${cy - 6} Q${cx - 20} ${cy - 26} ${cx} ${cy - 26} Q${cx + 20} ${cy - 26} ${cx + 18} ${cy - 6} Q${cx + 12} ${cy - 18} ${cx} ${cy - 18} Q${cx - 12} ${cy - 18} ${cx - 18} ${cy - 6} Z`} fill={hair} />
          : <path d={`M${cx - 20} ${cy + 2} Q${cx - 24} ${cy - 28} ${cx} ${cy - 27} Q${cx + 24} ${cy - 28} ${cx + 20} ${cy + 2} Q${cx + 14} ${cy - 16} ${cx + 2} ${cy - 18} Q${cx - 12} ${cy - 12} ${cx - 20} ${cy + 2} Z`} fill={hair} />}
        <g fill={hair} opacity=".75">
          <ellipse cx={cx - 7} cy={cy - 4} rx="2.2" ry="1.4" /><ellipse cx={cx + 7} cy={cy - 4} rx="2.2" ry="1.4" />
        </g>
        <path d={`M${cx - 4} ${cy + 13} Q${cx} ${cy + 15} ${cx + 4} ${cy + 13}`} stroke={hair} strokeWidth="1" fill="none" opacity=".6" />
      </g>
    </g>
  );
}

function Card({ x, y, doc }: { x: number; y: number; doc?: boolean }) {
  return (
    <g>
      <rect x={x} y={y} width={CW} height={doc ? 132 : 116} rx="8" fill="#fff" stroke="#d6e2ff" />
      {doc && <><rect x={x + 8} y={y + 115} width="70" height="3" rx="1.5" fill="#E3E8F2" /><rect x={x + 8} y={y + 122} width="44" height="3" rx="1.5" fill="#E3E8F2" /></>}
      <text x={x + CW / 2} y={y + 150} textAnchor="middle" fontSize="6.5" letterSpacing="1.2" fill="#0A1647" opacity=".7" fontFamily="var(--m), monospace">
        {doc ? "PORTRAIT DU DOCUMENT" : "SELFIE EN DIRECT"}
      </text>
    </g>
  );
}

export default function FaceMatch() {
  const ref = useRef<HTMLDivElement>(null);
  const inView = useInView(ref, { amount: 0.4 });
  const reduce = useReducedMotion();
  const [i, setI] = useState(0);
  const [phase, setPhase] = useState(0);
  const [score, setScore] = useState(0);
  const sc = SCENARIOS[i];

  useEffect(() => {
    if (reduce) { setPhase(4); setScore(sc.score); return; }
    if (!inView) return;
    setPhase(0); setScore(0);
    const t: ReturnType<typeof setTimeout>[] = [];
    let stop: (() => void) | undefined;
    t.push(setTimeout(() => setPhase(1), 600));
    t.push(setTimeout(() => {
      setPhase(2);
      stop = animate(0, sc.score, { duration: 1.3, ease: "easeOut", onUpdate: (v) => setScore(Math.round(v)) }).stop;
    }, 1200));
    t.push(setTimeout(() => setPhase(3), 2700));
    t.push(setTimeout(() => setPhase(4), 3800));
    t.push(setTimeout(() => setI((n) => (n + 1) % SCENARIOS.length), 6800));
    return () => { t.forEach(clearTimeout); stop?.(); };
  }, [i, inView, reduce, sc.score]);

  const d = face(DOC), s = face(SELF);
  const color = sc.match ? BLUE : RED;
  const checksOn = phase >= 3 ? CHECKS.length : 0;

  return (
    <div ref={ref} className="rounded-3xl border border-[#d6e2ff] bg-white p-5 md:p-8">
      <AnimatePresence mode="wait">
        <motion.div key={i} initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }} transition={{ duration: 0.35 }}>
          <svg viewBox="55 0 290 165" className="mx-auto w-full max-w-lg" role="img"
            aria-label={`Comparaison faciale : similarité ${sc.score} %, ${sc.match ? "correspondance approuvée" : "aucune correspondance, refusé"}`}>
            <Card {...DOC} doc /><Card {...SELF} />
            <Person {...DOC} variant="man" doc />
            <Person {...SELF} variant={sc.selfie === "same" ? "man" : "woman"} />
            <ellipse cx={s.cx} cy={s.cy + 2} rx="26" ry="34" fill="none" stroke="#fff" strokeWidth="1.2" opacity=".9" />

            {LANDMARKS.map(([lx, ly], k) => (
              <motion.line key={`l${k}`} x1={d.cx + lx} y1={d.cy + ly} x2={s.cx + lx} y2={s.cy + ly}
                stroke={color} strokeWidth=".8" strokeDasharray={sc.match ? undefined : "3 2"}
                initial={{ pathLength: 0, opacity: 0 }} animate={phase >= 2 ? { pathLength: 1, opacity: .75 } : { pathLength: 0, opacity: 0 }}
                transition={{ duration: 0.6, delay: k * 0.08 }} />
            ))}
            {LANDMARKS.flatMap(([lx, ly], k) => [d, s].map((c, j) => (
              <motion.circle key={`p${k}${j}`} cx={c.cx + lx} cy={c.cy + ly} r="2.1" fill={color} stroke="#fff" strokeWidth=".9"
                initial={{ scale: 0 }} animate={{ scale: phase >= 1 ? 1 : 0 }}
                transition={{ type: "spring", stiffness: 400, damping: 18, delay: k * 0.06 + j * 0.1 }}
                style={{ transformBox: "fill-box", transformOrigin: "center" }} />
            )))}

            <AnimatePresence>
              {phase >= 4 && (
                <motion.g initial={{ opacity: 0, y: 4 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0 }} transition={{ duration: 0.3 }}>
                  {(() => {
                    const w = sc.match ? 132 : 160, bx = 200 - w / 2, by = d.cy - 14, cy0 = by + 7.5, ix = bx + 9;
                    return (<>
                      <rect x={bx} y={by} width={w} height="15" rx="7.5" fill={sc.match ? "#E7F7EF" : "#FDECEA"} stroke={sc.match ? "#b7e8cf" : "#f6c7c2"} />
                      <circle cx={ix} cy={cy0} r="3.6" fill={sc.match ? GREEN : RED} />
                      <path d={sc.match ? `M${ix - 1.6} ${cy0} l1.2 1.2 l2.2 -2.4` : `M${ix - 1.4} ${cy0 - 1.4} l2.8 2.8 M${ix + 1.4} ${cy0 - 1.4} l-2.8 2.8`}
                        stroke="#fff" strokeWidth=".9" fill="none" strokeLinecap="round" />
                      <text x={ix + 7} y={cy0 + 2.2} fontSize="6" fontWeight="700" letterSpacing=".8"
                        fill={sc.match ? "#067647" : "#B42318"} fontFamily="var(--f), sans-serif">
                        {sc.match ? "CORRESPONDANCE · APPROUVÉ" : "AUCUNE CORRESPONDANCE · REFUSÉ"}
                      </text>
                    </>);
                  })()}
                </motion.g>
              )}
            </AnimatePresence>
          </svg>

          <div className={`mt-2 text-center transition-opacity duration-300 ${phase >= 2 ? "opacity-100" : "opacity-0"}`}>
            <div className="font-mono text-[10px] uppercase tracking-widest opacity-60">Similarité</div>
            <div className="font-display text-4xl font-bold tabular-nums">{score}<span className="text-lg">%</span></div>
            <div className="mx-auto mt-2 h-1 w-32 overflow-hidden rounded-full bg-ice">
              <div className="h-full rounded-full bg-blue transition-[width] duration-100" style={{ width: `${score}%` }} />
            </div>
          </div>

          <ul className="mt-5 flex flex-wrap justify-center gap-2">
            {CHECKS.map((c, k) => {
              const on = k < checksOn;
              return (
                <motion.li key={c} animate={{ opacity: phase === 0 ? 0.5 : 1 }}
                  className={`flex items-center gap-1.5 rounded-full border px-3 py-1 text-xs transition-colors duration-300 ${on ? "border-[#b7e8cf] bg-[#E7F7EF] font-medium text-navy" : "border-[#d6e2ff] text-navy/60"}`}
                  style={{ transitionDelay: on ? `${k * 150}ms` : "0ms" }}>
                  <span className={`grid h-3.5 w-3.5 place-items-center rounded-full transition-colors duration-300 ${on ? "bg-ok text-white" : "border border-[#c3d3f5]"}`}
                    style={{ transitionDelay: on ? `${k * 150}ms` : "0ms" }}>
                    {on && <svg viewBox="0 0 12 12" className="h-2.5 w-2.5" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" aria-hidden><path d="M3 6.2l2 2 4-4.4" /></svg>}
                  </span>
                  {c}
                </motion.li>
              );
            })}
          </ul>
          <p className="mt-4 text-center font-mono text-[10px] uppercase tracking-widest opacity-60">Même flux que la vérification du document</p>
        </motion.div>
      </AnimatePresence>
    </div>
  );
}
