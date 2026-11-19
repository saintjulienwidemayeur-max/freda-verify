"use client";
import { useEffect, useRef, useState } from "react";
import { AnimatePresence, motion, useInView, useReducedMotion } from "framer-motion";

const BLUE = "#1E4FE0";
const GREEN = "#12B76A";

const USERS = [
  { name: "Marc Jean-Baptiste", init: "MJ" },
  { name: "Nadège Pierre", init: "NP" },
  { name: "Jonas Étienne", init: "JE" },
];
const STEPS = ["Sanctions", "Personnes politiquement exposées", "Médias défavorables", "Surveillance quotidienne"];
const STEP_MS = 1700;
const DONE_MS = 3400;

const CheckIcon = ({ cls = "h-3 w-3" }: { cls?: string }) => (
  <svg viewBox="0 0 12 12" className={cls} fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden>
    <path d="M2.5 6.2l2.4 2.4 4.6-5" />
  </svg>
);
const Check = ({ cls = "h-5 w-5" }: { cls?: string }) => (
  <span className={`grid ${cls} shrink-0 place-items-center rounded-full bg-[#12B76A] text-white`}><CheckIcon /></span>
);
const Spin = () => <span className="block h-[18px] w-[18px] animate-spin rounded-full border-[2.5px] border-[#d5dcf5] border-t-[#1E4FE0]" />;
const Person = ({ cls }: { cls: string }) => (
  <svg viewBox="0 0 48 48" className={cls} fill="#8CC8FF" aria-hidden>
    <circle cx="24" cy="17" r="8" /><path d="M8 42c1.5-9 8-13 16-13s14.5 4 16 13z" />
  </svg>
);
const Paper = ({ cls }: { cls: string }) => (
  <svg viewBox="0 0 48 48" className={cls} fill="none" stroke="#8CC8FF" strokeWidth="3.5" strokeLinecap="round" aria-hidden>
    <rect x="9" y="8" width="30" height="32" rx="4" /><path d="M16 17h16M16 24h16M16 31h9" />
  </svg>
);

function Preview({ s }: { s: number }) {
  if (s === 0)
    return (
      <div className="flex h-full items-center justify-center">
        <div className="relative flex h-[52px] w-[150px] items-center gap-3 overflow-hidden rounded-lg bg-white px-3 shadow-[0_2px_10px_rgba(0,0,0,.1)]">
          <Person cls="h-7 w-7" />
          <div className="grid gap-1.5"><div className="h-[2px] w-[76px] bg-blue" /><div className="h-[2px] w-[46px] bg-sky" /></div>
          <motion.div className="absolute inset-x-0 h-[2px]" style={{ background: BLUE }}
            initial={{ top: "10%" }} animate={{ top: ["10%", "96%"] }} transition={{ duration: 1.1, ease: "easeInOut", repeat: Infinity, repeatType: "reverse" }} />
        </div>
      </div>
    );
  if (s === 1)
    return (
      <div className="flex h-full items-center justify-center">
        <div className="relative grid h-[66px] w-[66px] place-items-center rounded-full bg-white">
          <svg viewBox="0 0 80 80" className="absolute inset-0 -rotate-90" aria-hidden>
            <circle cx="40" cy="40" r="37" fill="none" stroke="#dbe6ff" strokeWidth="3" />
            <motion.circle cx="40" cy="40" r="37" fill="none" stroke={BLUE} strokeWidth="3.5" strokeLinecap="round"
              initial={{ pathLength: 0.1 }} animate={{ pathLength: 1 }} transition={{ duration: 1.4, ease: "easeInOut" }} />
          </svg>
          <Person cls="h-9 w-9" />
        </div>
      </div>
    );
  if (s === 2)
    return (
      <div className="flex h-full items-center justify-center">
        <div className="grid h-[50px] w-[50px] place-items-center rounded-full border border-[#dbe6ff] bg-white"><Person cls="h-7 w-7" /></div>
        <motion.div className="h-[2px] w-9" style={{ background: BLUE, originX: 0 }} initial={{ scaleX: 0 }} animate={{ scaleX: 1 }} transition={{ duration: 0.7, delay: 0.2 }} />
        <div className="-ml-0.5 grid h-[58px] w-[58px] place-items-center rounded-full border-2 bg-[#f6f8ff]" style={{ borderColor: "#dbe6ff", borderTopColor: BLUE }}><Person cls="h-8 w-8" /></div>
        <div className="ml-5 grid h-[48px] w-[48px] place-items-center rounded-xl bg-white shadow-[0_2px_10px_rgba(0,0,0,.1)]"><Paper cls="h-7 w-7" /></div>
      </div>
    );
  return (
    <div className="flex h-full flex-col items-center justify-center gap-1.5">
      {["Sanctions", "PEP", "Médias"].map((l, i) => (
        <motion.div key={l} className="flex h-[22px] w-[58%] items-center justify-between rounded-lg border border-[#dbe6ff] bg-white px-3 text-[9px] uppercase tracking-[0.12em] text-navy/70"
          initial={{ opacity: 0, y: 6 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: i * 0.3 }}>
          {l}
          <motion.span initial={{ scale: 0 }} animate={{ scale: 1 }} transition={{ delay: i * 0.3 + 0.3, type: "spring", stiffness: 300, damping: 16 }}>
            <Check cls="h-3.5 w-3.5" />
          </motion.span>
        </motion.div>
      ))}
    </div>
  );
}

export default function AmlCard() {
  const reduce = useReducedMotion();
  const ref = useRef<HTMLDivElement>(null);
  const inView = useInView(ref, { margin: "-80px" });
  const [u, setU] = useState(0);
  const [step, setStep] = useState(0);
  const [ms, setMs] = useState(0);
  const user = USERS[u];
  const done = reduce || step >= STEPS.length;
  const cur = reduce ? STEPS.length : step;
  const shown = Math.min(cur, STEPS.length - 1);

  useEffect(() => {
    if (reduce || !inView) return;
    const id = setTimeout(() => {
      if (step < STEPS.length) setStep(step + 1);
      else { setU((u + 1) % USERS.length); setStep(0); setMs(0); }
    }, step < STEPS.length ? STEP_MS : DONE_MS);
    return () => clearTimeout(id);
  }, [step, u, inView, reduce]);

  useEffect(() => {
    if (reduce || !inView || done) return;
    const id = setInterval(() => setMs((m) => m + 60), 60);
    return () => clearInterval(id);
  }, [inView, done, reduce, u]);

  const pick = (i: number) => { setU(i); setStep(0); setMs(0); };
  const secs = (reduce || done ? 1.3 : Math.min(ms / 1000 / (STEP_MS / 1000) * 0.325, 1.3)).toFixed(2);

  return (
    <div ref={ref} className="mx-auto w-full max-w-[480px]">
      <div className="mb-2 flex items-center justify-end gap-1.5 text-[9px] tracking-[0.18em] text-navy/70" role="tablist" aria-label="Utilisateurs simulés">
        <span className="mr-1">FILE</span>
        {USERS.map((x, i) => (
          <button key={x.init} role="tab" aria-selected={u === i} onClick={() => pick(i)}
            className={`grid h-6 w-6 place-items-center rounded-full border text-[9px] tracking-normal ${u === i ? "border-[#dbe6ff] bg-ice text-navy/70" : "border-[#dbe6ff] text-sky"}`}>
            {x.init}
          </button>
        ))}
      </div>

      <div className="rounded-[28px] border border-[#dbe6ff] bg-white p-5 shadow-[0_8px_30px_rgba(0,0,0,.05)]">
        <div className="flex items-center gap-3 border-b border-[#dbe6ff] pb-4">
          <div className="grid h-11 w-11 shrink-0 place-items-center rounded-full bg-[#e9eefc] text-[13px] font-medium text-blue">{user.init}</div>
          <div className="min-w-0 flex-1">
            <div className="truncate text-[17px] font-medium leading-tight text-navy">{user.name}</div>
            <div className="mt-0.5 text-[8.5px] uppercase tracking-[0.14em] text-navy/70">Nouvel utilisateur · AML complet</div>
          </div>
          <span className="text-[13px] font-semibold text-navy">{secs}<span className="ml-0.5 text-[8px] font-normal">s</span></span>
          <div className="flex w-[100px] justify-end">
            <AnimatePresence>
              {done && (
                <motion.span initial={{ opacity: 0, scale: 0.9 }} animate={{ opacity: 1, scale: 1 }} exit={{ opacity: 0 }}
                  className="flex items-center gap-1 rounded-full border border-[#b7e8cf] bg-[#E7F7EF] px-3 py-1 text-[8.5px] font-medium tracking-wider text-[#067647]">
                  <CheckIcon cls="h-2.5 w-2.5" />APPROUVÉ
                </motion.span>
              )}
            </AnimatePresence>
          </div>
        </div>

        <div className="relative mt-4 h-[110px] overflow-hidden rounded-[18px] border border-[#dbe6ff] bg-ice">
          <span className="absolute left-3.5 top-2.5 text-[8.5px] uppercase tracking-[0.14em] text-navy/70">{STEPS[shown]}</span>
          <AnimatePresence mode="wait">
            <motion.div key={`${u}-${shown}`} className="h-full pt-4" initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }} transition={{ duration: 0.25 }}>
              <Preview s={shown} />
            </motion.div>
          </AnimatePresence>
        </div>

        <ul className="-mx-2 mt-2.5">
          {STEPS.map((label, i) => {
            const active = cur === i;
            return (
              <motion.li key={label} animate={{ backgroundColor: active ? "#EEF4FF" : "#ffffff" }}
                className={`flex min-h-[44px] items-center justify-between gap-3 rounded-xl px-2 text-[10.5px] uppercase tracking-[0.12em] text-navy ${active || i === STEPS.length - 1 ? "" : "border-b border-[#dbe6ff]"}`}>
                <span className="px-0.5">{label}</span>
                <span className="grid h-5 w-5 place-items-center">{cur > i ? <Check /> : active ? <Spin /> : null}</span>
              </motion.li>
            );
          })}
        </ul>

        <div className="mt-3 flex h-10 items-center justify-between px-0.5">
          <span className="text-[9px] uppercase tracking-[0.14em] text-navy/70">Total des contrôles</span>
          <AnimatePresence>
            {done && <motion.span initial={{ opacity: 0, y: 6 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0 }} className="text-[26px] leading-none text-navy">4/4</motion.span>}
          </AnimatePresence>
        </div>
        <div className="mt-1 flex h-4 items-center px-0.5 text-[10px] text-navy/70">
          <AnimatePresence>
            {done && (
              <motion.span initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }} className="flex items-center gap-2">
                <span className="h-1.5 w-1.5 rounded-full" style={{ background: GREEN }} />POST /webhooks/freda · status: Approved
              </motion.span>
            )}
          </AnimatePresence>
        </div>
      </div>
    </div>
  );
}
