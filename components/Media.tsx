"use client";
import { useEffect, useState } from "react";

export type MediaPerson = { name: string; doc: string; docNo: string; dob: string; country: string; face?: "man" | "woman" };

const STEPS: [number, string, number][] = [[0, "Look at the camera", 0], [2.5, "Turn your head left", -4], [5, "Turn your head right", 4], [7, "Blink", 0]];
const DUR = 8;
const fmt = (s: number) => `0:${String(Math.floor(s)).padStart(2, "0")}`;

function Silhouette() {
  return (
    <svg viewBox="0 0 100 120" className="h-full w-full" aria-hidden>
      <rect width="100" height="120" fill="#E3EAF8" />
      <circle cx="50" cy="46" r="20" fill="#B7C6E6" /><path d="M12 120c2-26 18-38 38-38s36 12 38 38z" fill="#B7C6E6" />
    </svg>
  );
}
function Photo({ p, gray }: { p: MediaPerson; gray?: boolean }) {
  if (!p.face) return <Silhouette />;
  const src = gray ? `/faces/${p.face}-doc.webp` : `/faces/${p.face}-selfie.webp`;
  // eslint-disable-next-line @next/next/no-img-element
  return <img src={src} alt="" className="h-full w-full object-cover" />;
}

export function FaceVideo({ p }: { p: MediaPerson }) {
  const [t, setT] = useState(0);
  const [play, setPlay] = useState(false);
  useEffect(() => {
    if (!play) return;
    const id = setInterval(() => setT((v) => { if (v + 0.1 >= DUR) { setPlay(false); return DUR; } return v + 0.1; }), 100);
    return () => clearInterval(id);
  }, [play]);
  const step = [...STEPS].reverse().find((s) => t >= s[0]) ?? STEPS[0];
  return (
    <div className="relative aspect-[4/3] w-full overflow-hidden rounded-xl bg-navy" role="group" aria-label="Selfie video">
      <div className="absolute inset-0 transition-transform duration-700 ease-out" style={{ transform: `translateX(${step[2]}%) scale(1.15)` }}><Photo p={p} /></div>
      <div className="pointer-events-none absolute left-1/2 top-[46%] h-[72%] w-[46%] -translate-x-1/2 -translate-y-1/2 rounded-[50%] border-2 border-white/80" />
      {t > 0 && <span className="absolute left-3 top-3 rounded-full bg-navy/80 px-2.5 py-1 text-[11px] text-white">{step[1]}</span>}
      <span className="absolute right-3 top-3 flex items-center gap-1.5 rounded-full bg-navy/80 px-2 py-1 font-mono text-[10px] text-white"><span className={`h-1.5 w-1.5 rounded-full ${play ? "bg-bad" : "bg-white/50"}`} />LIVENESS</span>
      <div className="absolute inset-x-0 bottom-0 flex items-center gap-3 bg-gradient-to-t from-navy/85 to-transparent px-3 pb-2.5 pt-8 text-white">
        <button onClick={() => { if (t >= DUR) setT(0); setPlay(!play); }} aria-label={play ? "Pause video" : "Play video"} className="grid h-8 w-8 shrink-0 place-items-center rounded-full bg-white text-navy">
          {play ? <svg viewBox="0 0 24 24" className="h-4 w-4" fill="currentColor"><rect x="6" y="5" width="4" height="14" rx="1" /><rect x="14" y="5" width="4" height="14" rx="1" /></svg>
            : <svg viewBox="0 0 24 24" className="h-4 w-4" fill="currentColor"><path d="M8 5v14l11-7z" /></svg>}
        </button>
        <div className="h-1 flex-1 overflow-hidden rounded-full bg-white/30"><div className="h-full bg-white" style={{ width: `${(t / DUR) * 100}%` }} /></div>
        <span className="font-mono text-[10px]">{fmt(t)} / {fmt(DUR)}</span>
      </div>
    </div>
  );
}

export function IdCard({ p, side, big }: { p: MediaPerson; side: "front" | "back"; big?: boolean }) {
  const [last, ...rest] = [...p.name.split(" ")].reverse();
  const mrz1 = `ID${p.country}<<${last.toUpperCase()}<<${rest.reverse().join("<").toUpperCase()}`.padEnd(30, "<").slice(0, 30);
  const mrz2 = `${p.docNo.replace(/[^A-Z0-9]/gi, "")}<${p.dob.replace(/-/g, "").slice(2)}`.toUpperCase().padEnd(30, "<").slice(0, 30);
  return (
    <div className="relative flex aspect-[1.586] w-full flex-col overflow-hidden rounded-xl border border-[#c9d8f5] bg-gradient-to-br from-white via-ice to-[#dbe6ff] text-navy shadow-sm"
      style={{ fontSize: big ? 16 : 11 }} role="img" aria-label={`${p.doc} ${side}`}>
      <div className="flex items-center justify-between bg-navy px-[1em] py-[0.5em] text-[0.72em] font-semibold uppercase tracking-widest text-white"><span>{p.doc}</span><span>{side === "front" ? "Front" : "Back"}</span></div>
      {side === "front" ? (
        <div className="flex flex-1 items-center gap-[1em] p-[1em]">
          <div className="h-[8.5em] w-[7em] shrink-0 overflow-hidden rounded-md border border-[#c9d8f5]"><Photo p={p} gray /></div>
          <dl className="min-w-0 flex-1 space-y-[0.55em] leading-tight">
            {[["Name", p.name], ["Date of birth", p.dob], ["Document no.", p.docNo], ["Country", p.country]].map(([k, v]) => (
              <div key={k}><dt className="text-[0.62em] uppercase tracking-wider text-navy/50">{k}</dt><dd className="truncate text-[0.95em] font-semibold">{v}</dd></div>
            ))}
          </dl>
        </div>
      ) : (
        <div className="flex flex-1 flex-col justify-between p-[1em]">
          <div className="h-[2.2em] rounded-sm" style={{ background: "repeating-linear-gradient(90deg,#0A1647 0 2px,transparent 2px 4px,#0A1647 4px 5px,transparent 5px 8px)" }} />
          <div className="space-y-[0.4em]"><div className="h-[0.5em] w-3/4 rounded bg-navy/15" /><div className="h-[0.5em] w-1/2 rounded bg-navy/15" /></div>
          <div className="rounded-md bg-white/70 p-[0.6em] font-mono text-[0.72em] leading-[1.4] tracking-[0.1em]"><div className="truncate">{mrz1}</div><div className="truncate">{mrz2}</div></div>
        </div>
      )}
    </div>
  );
}

type Big = "video" | "front" | "back" | null;

export default function Media({ p }: { p: MediaPerson }) {
  const [big, setBig] = useState<Big>(null);
  useEffect(() => {
    if (!big) return;
    const k = (e: KeyboardEvent) => e.key === "Escape" && setBig(null);
    window.addEventListener("keydown", k);
    return () => window.removeEventListener("keydown", k);
  }, [big]);
  const zoom = (b: Big, label: string) => (
    <button onClick={() => setBig(b)} className="mt-1.5 text-[11px] font-medium text-blue hover:underline">{label} ⤢</button>
  );
  return (
    <section className="mt-5" aria-label="Captured media">
      <h3 className="font-display text-sm font-bold">Captured media</h3>
      <div className="mt-2"><FaceVideo p={p} />{zoom("video", "Enlarge video")}</div>
      <div className="mt-3 grid gap-3">
        <div><IdCard p={p} side="front" />{zoom("front", "Front")}</div>
        <div><IdCard p={p} side="back" />{zoom("back", "Back")}</div>
      </div>
      {!p.face && <p className="mt-2 text-[11px] text-navy/45">Sample placeholder — no photo in this demo record.</p>}
      {big && (
        <div className="fixed inset-0 z-50 grid place-items-center bg-navy/70 p-4" role="dialog" aria-modal="true" aria-label="Media preview" onClick={() => setBig(null)}>
          <div className="w-full max-w-xl" onClick={(e) => e.stopPropagation()}>
            <div className="mb-2 flex items-center justify-between text-white"><span className="text-sm font-semibold">{p.name} · {big === "video" ? "Selfie video" : `${p.doc} (${big})`}</span><button onClick={() => setBig(null)} className="rounded-full border border-white/40 px-3 py-1 text-xs">Close ✕</button></div>
            {big === "video" ? <FaceVideo p={p} /> : <IdCard p={p} side={big} big />}
          </div>
        </div>
      )}
    </section>
  );
}
