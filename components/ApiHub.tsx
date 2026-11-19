"use client";
import { useEffect, useState } from "react";
import type { ReactNode } from "react";
import { motion, useReducedMotion } from "framer-motion";
import type { Variants } from "framer-motion";

const Svg = ({ children }: { children: ReactNode }) => (
  <svg viewBox="0 0 24 24" className="h-[52%] w-[52%]" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" aria-hidden>
    {children}
  </svg>
);

const NODES: { label: string; icon: ReactNode }[] = [
  { label: "Vérification d'ID", icon: <><rect x="3" y="6" width="18" height="13" rx="2.5" /><circle cx="9" cy="11.5" r="2" /><path d="M6 16c.5-1.5 1.8-2.3 3-2.3s2.5.8 3 2.3M14 10h4M14 13.5h4" /></> },
  { label: "Liveness", icon: <><circle cx="12" cy="12" r="3.2" /><path d="M12 3v2.5M12 18.5V21M3 12h2.5M18.5 12H21M5.6 5.6l1.8 1.8M16.6 16.6l1.8 1.8M18.4 5.6l-1.8 1.8M7.4 16.6l-1.8 1.8" /></> },
  { label: "Face Match", icon: <><circle cx="9" cy="12" r="5.5" /><circle cx="15" cy="12" r="5.5" /></> },
  { label: "Vérification d'entreprise", icon: <path d="M5 20V5a1 1 0 0 1 1-1h7a1 1 0 0 1 1 1v15M3 20h18M14 10h4a1 1 0 0 1 1 1v9M8 8h2M8 12h2M8 16h2" /> },
  { label: "Filtrage AML", icon: <><circle cx="11" cy="11" r="6.5" /><path d="M16 16l4.5 4.5" /></> },
  { label: "Preuve d'adresse", icon: <><path d="M4 11l8-7 8 7v9H4z" /><path d="M9 14.5l2 2 4-4" /></> },
  { label: "Estimation de l'âge", icon: <><circle cx="12" cy="12" r="8.5" /><path d="M12 7v5l3 2" /></> },
];

const R = 33;
const pos = (i: number) => {
  const a = ((-90 + (i * 360) / NODES.length) * Math.PI) / 180;
  return { x: 50 + R * Math.cos(a), y: 50 + R * Math.sin(a) };
};

const lineV: Variants = {
  hidden: { pathLength: 0, opacity: 0 },
  show: (i: number) => ({ pathLength: 1, opacity: 1, transition: { duration: 0.7, delay: 0.3 + i * 0.08 } }),
};
const nodeV: Variants = {
  hidden: { opacity: 0, scale: 0.4 },
  show: (i: number) => ({ opacity: 1, scale: 1, transition: { type: "spring", stiffness: 260, damping: 18, delay: 0.5 + i * 0.08 } }),
};
const hubV: Variants = {
  hidden: { opacity: 0, scale: 0.6 },
  show: { opacity: 1, scale: 1, transition: { type: "spring", stiffness: 200, damping: 16, delay: 0.1 } },
};

export default function ApiHub() {
  const reduce = useReducedMotion();
  const [active, setActive] = useState(0);
  const [tick, setTick] = useState(0);
  const [paused, setPaused] = useState(false);

  useEffect(() => {
    if (reduce || paused) return;
    const id = setInterval(() => { setActive((a) => (a + 1) % NODES.length); setTick((t) => t + 1); }, 1700);
    return () => clearInterval(id);
  }, [reduce, paused]);

  const target = pos(active);
  return (
    <motion.div
      role="img" aria-label="Freda Verify API relie la vérification d'identité, le liveness, la correspondance faciale, le KYB, l'AML, la preuve d'adresse et l'estimation de l'âge"
      className="relative mx-auto aspect-square w-full max-w-[560px]"
      initial="hidden" whileInView="show" viewport={{ once: true, margin: "-80px" }}
    >
      <div className="absolute inset-[6%] rounded-full" style={{ background: "radial-gradient(circle,#fff 0,rgba(255,255,255,0) 70%)" }} />
      <svg viewBox="0 0 100 100" className="absolute inset-0 h-full w-full" aria-hidden>
        {NODES.map((_, i) => {
          const p = pos(i); const on = i === active;
          return (
            <motion.line key={i} x1="50" y1="50" x2={p.x} y2={p.y} stroke="#1E4FE0"
              strokeWidth={on ? 0.45 : 0.22} strokeOpacity={on ? 1 : 0.22} variants={lineV} custom={i} />
          );
        })}
        {!reduce && (
          <motion.circle key={tick} r="1.1" fill="#0A1647"
            initial={{ cx: 50, cy: 50, opacity: 1 }} animate={{ cx: target.x, cy: target.y, opacity: [1, 1, 0] }}
            transition={{ duration: 1.1, ease: "easeInOut" }} />
        )}
      </svg>

      <div className="absolute left-1/2 top-1/2 h-[25%] w-[25%] -translate-x-1/2 -translate-y-1/2">
        <motion.div variants={hubV} className="grid h-full w-full place-items-center rounded-full border border-navy/80 bg-white shadow-[0_10px_50px_rgba(30,79,224,.22)]">
          <span className="text-center font-mono text-[7px] font-semibold leading-snug tracking-[0.14em] sm:text-[10px]">
            FREDA VERIFY<br />API
          </span>
        </motion.div>
      </div>

      {NODES.map((n, i) => {
        const p = pos(i); const on = i === active; const up = p.y < 49;
        return (
          <div key={n.label} className="absolute h-[10.5%] w-[10.5%] -translate-x-1/2 -translate-y-1/2" style={{ left: `${p.x}%`, top: `${p.y}%` }}
            onMouseEnter={() => { setActive(i); setTick((t) => t + 1); setPaused(true); }} onMouseLeave={() => setPaused(false)}>
            <motion.div variants={nodeV} custom={i} className="relative h-full w-full">
              <motion.div
                animate={{ scale: on ? 1.12 : 1, backgroundColor: on ? "#1E4FE0" : "#fff", color: on ? "#fff" : "#0A1647" }}
                transition={{ duration: 0.35 }}
                className="grid h-full w-full place-items-center rounded-full border border-navy/80 shadow-md"
              >
                <Svg>{n.icon}</Svg>
              </motion.div>
              <span className={`absolute left-1/2 w-20 -translate-x-1/2 text-center text-[10px] leading-tight text-navy sm:w-28 sm:text-[11px] ${up ? "bottom-full mb-1.5" : "top-full mt-1.5"} ${on ? "font-bold" : "opacity-70"}`}>
                {n.label}
              </span>
            </motion.div>
          </div>
        );
      })}
    </motion.div>
  );
}
