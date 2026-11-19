"use client";
import { useEffect, useRef, useState } from "react";
import { AnimatePresence, animate, motion, useInView, useReducedMotion } from "framer-motion";

const BLUE = "#1E4FE0";
const RED = "#D92D20";
const GREEN = "#12B76A";

type Photo = "man-doc" | "man-selfie" | "woman-selfie";
type Scenario = { selfie: Photo; score: number; match: boolean };
const SCENARIOS: Scenario[] = [
  { selfie: "man-selfie", score: 98, match: true },
  { selfie: "woman-selfie", score: 34, match: false },
];
// Landmarks (left eye, right eye, nose, mouth) as fractions of each cropped photo
const LM: Record<Photo, [number, number][]> = {
  "man-doc": [[0.375, 0.38], [0.625, 0.38], [0.496, 0.496], [0.496, 0.592]],
  "man-selfie": [[0.355, 0.38], [0.645, 0.38], [0.496, 0.515], [0.496, 0.625]],
  "woman-selfie": [[0.355, 0.38], [0.645, 0.382], [0.493, 0.532], [0.493, 0.618]],
};
const CHECKS = ["Qualité d'image", "Un seul visage", "Aucune occlusion"];

// Card geometry (SVG viewBox 400 x 165)
const DOC = { x: 70, y: 8 };
const SELF = { x: 230, y: 8 };
const CW = 100;
const PH = { dx: 8, dy: 8, w: 84, h: 100 };
const pt = (c: { x: number; y: number }, [fx, fy]: [number, number]) => ({ x: c.x + PH.dx + fx * PH.w, y: c.y + PH.dy + fy * PH.h });

function Photo({ x, y, src, id }: { x: number; y: number; src: Photo; id: string }) {
  return (
    <g>
      <clipPath id={id}><rect x={x + PH.dx} y={y + PH.dy} width={PH.w} height={PH.h} rx="6" /></clipPath>
      <image href={`/faces/${src}.webp`} x={x + PH.dx} y={y + PH.dy} width={PH.w} height={PH.h} preserveAspectRatio="xMidYMid slice" clipPath={`url(#${id})`} />
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

  const dl = LM["man-doc"].map((l) => pt(DOC, l));
  const sl = LM[sc.selfie].map((l) => pt(SELF, l));
  const by0 = DOC.y + PH.dy + PH.h * 0.84 - 7;
  const color = sc.match ? BLUE : RED;
  const checksOn = phase >= 3 ? CHECKS.length : 0;

  return (
    <div ref={ref} className="rounded-3xl border border-[#d6e2ff] bg-white p-5 md:p-8">
      <AnimatePresence mode="wait">
        <motion.div key={i} initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }} transition={{ duration: 0.35 }}>
          <svg viewBox="55 0 290 165" className="mx-auto w-full max-w-lg" role="img"
            aria-label={`Comparaison faciale : similarité ${sc.score} %, ${sc.match ? "correspondance approuvée" : "aucune correspondance, refusé"}`}>
            <Card {...DOC} doc /><Card {...SELF} />
            <Photo {...DOC} src="man-doc" id="clip-doc" />
            <Photo {...SELF} src={sc.selfie} id="clip-self" />
            <ellipse cx={SELF.x + PH.dx + PH.w / 2} cy={SELF.y + PH.dy + PH.h * 0.46} rx="27" ry="37" fill="none" stroke="#fff" strokeWidth="1.2" opacity=".9" />

            {dl.map((_, k) => (
              <motion.line key={`l${k}`} x1={dl[k].x} y1={dl[k].y} x2={sl[k].x} y2={sl[k].y}
                stroke={color} strokeWidth=".8" strokeDasharray={sc.match ? undefined : "3 2"}
                initial={{ pathLength: 0, opacity: 0 }} animate={phase >= 2 ? { pathLength: 1, opacity: .75 } : { pathLength: 0, opacity: 0 }}
                transition={{ duration: 0.6, delay: k * 0.08 }} />
            ))}
            {dl.flatMap((_, k) => [dl[k], sl[k]].map((c, j) => (
              <motion.circle key={`p${k}${j}`} cx={c.x} cy={c.y} r="2.1" fill={color} stroke="#fff" strokeWidth=".9"
                initial={{ scale: 0 }} animate={{ scale: phase >= 1 ? 1 : 0 }}
                transition={{ type: "spring", stiffness: 400, damping: 18, delay: k * 0.06 + j * 0.1 }}
                style={{ transformBox: "fill-box", transformOrigin: "center" }} />
            )))}

            <AnimatePresence>
              {phase >= 4 && (
                <motion.g initial={{ opacity: 0, y: 4 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0 }} transition={{ duration: 0.3 }}>
                  {(() => {
                    const w = sc.match ? 132 : 160, bx = 200 - w / 2, by = by0, cy0 = by + 7.5, ix = bx + 9;
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
