"use client";
import { useMemo, useState } from "react";

type Status = "APPROVED" | "REJECTED" | "PENDING" | "REVIEW";
type Biz = { name: string; country: string; reg: string; ubos: number; risk: "Low" | "Medium" | "High"; status: Status; score: number; date: string };

const DATA: Biz[] = [
  { name: "Kafe Lakay SARL", country: "HT", reg: "Company registry", ubos: 2, risk: "Low", status: "APPROVED", score: 97.2, date: "2026-11-18" },
  { name: "Sunrise Trading", country: "PA", reg: "Company registry", ubos: 4, risk: "High", status: "REJECTED", score: 41.0, date: "2026-11-18" },
  { name: "Karibe Logistics", country: "HT", reg: "Tax ID (NIF)", ubos: 3, risk: "Medium", status: "REVIEW", score: 72.5, date: "2026-11-17" },
  { name: "Atlas Agro SA", country: "DO", reg: "Company registry", ubos: 1, risk: "Low", status: "APPROVED", score: 95.8, date: "2026-11-16" },
  { name: "Mapou Studio", country: "HT", reg: "Tax ID (NIF)", ubos: 2, risk: "Low", status: "PENDING", score: 0, date: "2026-11-16" },
  { name: "Blue Harbor Ltd", country: "US", reg: "Company registry", ubos: 5, risk: "Medium", status: "REVIEW", score: 68.1, date: "2026-11-14" },
  { name: "Soley Energy", country: "HT", reg: "Company registry", ubos: 3, risk: "Low", status: "APPROVED", score: 98.9, date: "2026-11-12" },
  { name: "Vant Nò Import", country: "CA", reg: "Company registry", ubos: 2, risk: "Low", status: "PENDING", score: 0, date: "2026-11-11" },
];

const BADGE: Record<Status, string> = {
  APPROVED: "bg-black text-white",
  REJECTED: "border border-black bg-white line-through",
  PENDING: "border border-dashed border-black",
  REVIEW: "border border-black bg-white",
};
const FILTERS = ["ALL", "APPROVED", "REVIEW", "PENDING", "REJECTED"] as const;

export default function Businesses() {
  const [f, setF] = useState<(typeof FILTERS)[number]>("ALL");
  const [q, setQ] = useState("");
  const [open, setOpen] = useState<string | null>(null);

  const rows = useMemo(
    () => DATA.filter((b) => (f === "ALL" || b.status === f) && b.name.toLowerCase().includes(q.trim().toLowerCase())),
    [f, q],
  );
  const count = (s: Status) => DATA.filter((b) => b.status === s).length;
  const sel = DATA.find((b) => b.name === open);

  return (
    <>
      <h1 className="text-3xl font-extrabold tracking-tighter">Businesses</h1>
      <p className="mt-1 text-sm opacity-60">KYB verifications · sample data</p>

      <div className="mt-5 grid grid-cols-2 gap-px border border-black bg-black md:grid-cols-4">
        {([["Total", DATA.length], ["Approved", count("APPROVED")], ["In review", count("REVIEW") + count("PENDING")], ["Rejected", count("REJECTED")]] as const).map(([l, v]) => (
          <div key={l} className="bg-[#e8e8e6] p-4"><div className="text-2xl font-bold">{v}</div><div className="text-xs opacity-60">{l}</div></div>
        ))}
      </div>

      <div className="mt-6 flex flex-wrap items-center gap-2">
        {FILTERS.map((x) => (
          <button key={x} onClick={() => setF(x)} aria-pressed={f === x}
            className={`rounded-full border border-black px-3 py-1 font-mono text-xs ${f === x ? "bg-black text-white" : ""}`}>{x}</button>
        ))}
        <input value={q} onChange={(e) => setQ(e.target.value)} placeholder="Search business…" aria-label="Search business"
          className="ml-auto w-full border border-black bg-transparent px-3 py-1.5 text-sm md:w-64" />
      </div>

      <div className="mt-4 overflow-x-auto border border-black">
        <table className="w-full text-left text-sm">
          <thead className="border-b border-black font-mono text-xs">
            <tr>{["Business", "Country", "Source", "UBOs", "Risk", "Status", "Score", "Date"].map((h) => <th key={h} className="p-3 font-medium">{h}</th>)}</tr>
          </thead>
          <tbody>
            {rows.map((b) => (
              <tr key={b.name} onClick={() => setOpen(b.name)} className="cursor-pointer border-b border-black/20 last:border-0 hover:bg-black/5">
                <td className="p-3 font-medium"><button className="text-left underline-offset-2 hover:underline" onClick={() => setOpen(b.name)}>{b.name}</button></td>
                <td className="p-3 font-mono">{b.country}</td><td className="p-3">{b.reg}</td><td className="p-3 font-mono">{b.ubos}</td>
                <td className="p-3">{b.risk}</td>
                <td className="p-3"><span className={`rounded-full px-3 py-1 font-mono text-xs ${BADGE[b.status]}`}>{b.status}</span></td>
                <td className="p-3 font-mono">{b.score ? `${b.score.toFixed(1)}%` : "—"}</td>
                <td className="p-3 font-mono text-xs">{b.date}</td>
              </tr>
            ))}
            {rows.length === 0 && <tr><td colSpan={8} className="p-6 text-center opacity-60">No business found.</td></tr>}
          </tbody>
        </table>
      </div>

      {sel && (
        <div className="mt-6 border border-black p-4" role="region" aria-label="Business details">
          <div className="flex items-start justify-between">
            <div><div className="text-lg font-bold">{sel.name}</div><div className="text-xs opacity-60">{sel.country} · {sel.reg}</div></div>
            <button onClick={() => setOpen(null)} className="font-mono text-xs underline">Close</button>
          </div>
          <ul className="mt-4 grid gap-2 text-sm md:grid-cols-2">
            {[
              ["Registry check", sel.status === "REJECTED" ? "Not found" : "Found"],
              ["Beneficial owners (UBO)", `${sel.ubos} identified`],
              ["Sanctions / AML screening", sel.risk === "High" ? "Match — needs review" : "Clear"],
              ["Risk level", sel.risk],
            ].map(([k, v]) => <li key={k} className="flex justify-between border-b border-black/20 pb-1"><span className="opacity-60">{k}</span><span className="font-mono">{v}</span></li>)}
          </ul>
        </div>
      )}
    </>
  );
}
