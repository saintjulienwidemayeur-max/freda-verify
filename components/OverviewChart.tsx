"use client";
import { useState } from "react";

const DAYS: [string, number][] = [
  ["Nov 13", 1130], ["Nov 14", 1560], ["Nov 15", 1370], ["Nov 16", 1980], ["Nov 17", 1770], ["Nov 18", 2350], ["Nov 19", 2320],
];
const MAX = Math.max(...DAYS.map((d) => d[1]));
const TOTAL = DAYS.reduce((a, d) => a + d[1], 0);

export default function OverviewChart() {
  const [on, setOn] = useState(DAYS.findIndex((d) => d[1] === MAX));
  return (
    <section className="rounded-2xl border border-[#e3eaf8] bg-white p-5" aria-label="Checks per day">
      <h2 className="font-display text-lg font-bold">Overview</h2>
      <p className="mt-3 text-xs text-navy/55">Avg per day</p>
      <div className="mt-1 flex items-center gap-2">
        <span className="font-display text-2xl font-bold tabular-nums">{Math.round(TOTAL / DAYS.length).toLocaleString("en-US")}</span>
        <span className="rounded-md bg-[#E7F7EF] px-1.5 py-0.5 text-[11px] font-semibold text-[#067647]">▲ 12.4%</span>
      </div>
      <div className="relative mt-10 flex h-48 items-end gap-2 sm:gap-4 md:gap-5" role="group" onMouseLeave={() => setOn(DAYS.findIndex((d) => d[1] === MAX))}>
        {DAYS.map(([d, v], i) => {
          const a = i === on;
          return (
            <button key={d} onMouseEnter={() => setOn(i)} onFocus={() => setOn(i)} aria-label={`${d}: ${v.toLocaleString("en-US")} checks`}
              className="relative flex h-full flex-1 flex-col justify-end text-center outline-none">
              {a && (
                <span className="absolute left-1/2 z-10 -translate-x-1/2 whitespace-nowrap rounded-lg bg-navy px-3 py-1.5 text-xs text-white shadow-lg"
                  style={{ bottom: `calc(${(v / MAX) * 100}% * 0.82 + 34px)` }}>
                  <span className="block text-[10px] opacity-70">{d}</span><b>{v.toLocaleString("en-US")} checks</b>
                  <span className="absolute left-1/2 top-full h-2 w-2 -translate-x-1/2 -translate-y-1 rotate-45 bg-navy" />
                </span>
              )}
              <span className="block w-full rounded-lg transition-all duration-200"
                style={{
                  height: `${(v / MAX) * 82}%`,
                  background: a
                    ? "repeating-linear-gradient(135deg,#1E4FE0 0 3px,#2E8BFF 3px 6px)"
                    : "repeating-linear-gradient(135deg,#EEF4FF 0 3px,#E1EAFB 3px 6px)",
                }} />
              <span className={`mt-2 block text-[11px] ${a ? "font-semibold text-navy" : "text-navy/50"}`}>{d.replace("Nov ", "")}</span>
            </button>
          );
        })}
      </div>
      <p className="mt-1 text-center font-mono text-[10px] uppercase tracking-widest text-navy/40">November</p>
    </section>
  );
}
