"use client";
import { useState } from "react";

/** Real API requests per day (from /usage). `data` = [label, count][] oldest → newest. */
export default function OverviewChart({ data }: { data: [string, number][] }) {
  const MAX = Math.max(1, ...data.map((d) => d[1]));
  const TOTAL = data.reduce((a, d) => a + d[1], 0);
  const peak = Math.max(0, data.findIndex((d) => d[1] === Math.max(...data.map((x) => x[1]))));
  const [hover, setHover] = useState<number | null>(null);
  const on = hover ?? peak;
  return (
    <section className="rounded-2xl border border-[#e3eaf8] bg-white p-5" aria-label="API requests per day">
      <h2 className="font-display text-lg font-bold">API requests per day</h2>
      <p className="mt-3 text-xs text-navy/55">Average per day · last {data.length} days</p>
      <div className="mt-1 font-display text-2xl font-bold tabular-nums">{data.length ? (TOTAL / data.length).toLocaleString("en-US", { maximumFractionDigits: 1 }) : "0"}</div>
      {TOTAL === 0 ? (
        <p className="mt-8 rounded-xl border border-dashed border-[#d6e2ff] p-8 text-center text-sm text-navy/55">No requests yet. Call the API with one of your keys and the chart will fill in.</p>
      ) : (
        <div className="relative mt-10 flex h-48 items-end gap-1.5 sm:gap-2" role="group" onMouseLeave={() => setHover(null)}>
          {data.map(([d, v], i) => {
            const a = i === on;
            return (
              <button key={d} onMouseEnter={() => setHover(i)} onFocus={() => setHover(i)} aria-label={`${d}: ${v.toLocaleString("en-US")} requests`}
                className="relative flex h-full min-w-0 flex-1 flex-col justify-end text-center outline-none">
                {a && (
                  <span className="absolute left-1/2 z-10 -translate-x-1/2 whitespace-nowrap rounded-lg bg-navy px-3 py-1.5 text-xs text-white shadow-lg"
                    style={{ bottom: `calc(${(v / MAX) * 100}% * 0.82 + 34px)` }}>
                    <span className="block text-[10px] opacity-70">{d}</span><b>{v.toLocaleString("en-US")} requests</b>
                  </span>
                )}
                <span className="block w-full rounded-md transition-all duration-200"
                  style={{ height: `${Math.max(v > 0 ? 3 : 1, (v / MAX) * 82)}%`, background: a ? "repeating-linear-gradient(135deg,#1E4FE0 0 3px,#2E8BFF 3px 6px)" : "repeating-linear-gradient(135deg,#EEF4FF 0 3px,#E1EAFB 3px 6px)" }} />
                {(data.length <= 14 || i % 5 === 0) && <span className={`mt-2 block truncate text-[10px] ${a ? "font-semibold text-navy" : "text-navy/50"}`}>{d.slice(-2)}</span>}
              </button>
            );
          })}
        </div>
      )}
    </section>
  );
}
