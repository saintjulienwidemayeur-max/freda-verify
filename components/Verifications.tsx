"use client";
import { useMemo, useState } from "react";
import Media from "./Media";

type Status = "APPROVED" | "REVIEW" | "PENDING" | "REJECTED";
type Person = {
  id: string; name: string; doc: string; country: string; docNo: string; dob: string; when: string;
  status: Status; score: number; liveness: boolean | null; age: string; aml: "Clear" | "Match" | "—"; reason?: string; face?: "man" | "woman";
};

const DATA: Person[] = [
  { id: "ver_9f31a2", name: "Marc Jean-Baptiste", doc: "ID card", country: "HT", docNo: "HT-••••917", dob: "1991-03-14", when: "Today, 19:41", status: "APPROVED", score: 99.8, liveness: true, age: "34", aml: "Clear", face: "man" },
  { id: "ver_9f2e10", name: "Nadège Pierre", doc: "Passport", country: "HT", docNo: "PA••••204", dob: "1994-07-02", when: "Today, 19:12", status: "REVIEW", score: 72.4, liveness: true, age: "31", aml: "Clear", reason: "Face match below auto-approve threshold", face: "woman" },
  { id: "ver_9f2a6c", name: "Jonas Étienne", doc: "ID card", country: "HT", docNo: "HT-••••553", dob: "1988-11-23", when: "Today, 18:47", status: "APPROVED", score: 98.6, liveness: true, age: "37", aml: "Clear" },
  { id: "ver_9f1b77", name: "Carla Dessalines", doc: "Driver's license", country: "DO", docNo: "DL••••881", dob: "1996-01-30", when: "Today, 17:30", status: "PENDING", score: 0, liveness: null, age: "—", aml: "—" },
  { id: "ver_9f0c42", name: "Ricardo Alvarez", doc: "Passport", country: "PA", docNo: "PN••••392", dob: "1985-05-09", when: "Today, 16:05", status: "REJECTED", score: 31.2, liveness: false, age: "40", aml: "Clear", reason: "Liveness failed: replayed screen detected" },
  { id: "ver_9ef8d3", name: "Widlyne Charles", doc: "ID card", country: "HT", docNo: "HT-••••120", dob: "1999-09-18", when: "Yesterday, 21:22", status: "APPROVED", score: 97.1, liveness: true, age: "27", aml: "Clear" },
  { id: "ver_9ee210", name: "Samuel Brun", doc: "Passport", country: "CA", docNo: "CA••••774", dob: "1979-12-04", when: "Yesterday, 15:48", status: "REVIEW", score: 80.9, liveness: true, age: "46", aml: "Match", reason: "Possible sanctions list match — manual check needed" },
  { id: "ver_9ed4a9", name: "Fabienne Louis", doc: "ID card", country: "HT", docNo: "HT-••••068", dob: "1992-06-27", when: "Yesterday, 11:03", status: "APPROVED", score: 99.1, liveness: true, age: "33", aml: "Clear" },
  { id: "ver_9ec1be", name: "Peterson Joseph", doc: "Driver's license", country: "HT", docNo: "DL••••415", dob: "2009-02-11", when: "2 days ago", status: "REJECTED", score: 88.0, liveness: true, age: "16", aml: "Clear", reason: "Under minimum age (18)" },
  { id: "ver_9eb7f0", name: "Mireille Toussaint", doc: "ID card", country: "HT", docNo: "HT-••••336", dob: "1990-04-15", when: "2 days ago", status: "APPROVED", score: 96.5, liveness: true, age: "36", aml: "Clear" },
];

const BADGE: Record<Status, string> = {
  APPROVED: "bg-[#E7F7EF] text-[#067647]", REJECTED: "bg-[#FDECEA] text-[#B42318]",
  REVIEW: "bg-[#FEF3E2] text-[#B54708]", PENDING: "bg-[#F2F4F7] text-navy/70",
};
const FILTERS = ["ALL", "APPROVED", "REVIEW", "PENDING", "REJECTED"] as const;
const initials = (n: string) => n.split(" ").map((w) => w[0]).slice(0, 2).join("");

type Check = [string, "ok" | "bad" | "warn" | "wait", string];
const checks = (p: Person): Check[] => [
  ["Document authenticity", p.status === "PENDING" ? "wait" : "ok", p.status === "PENDING" ? "Waiting" : "Genuine"],
  ["Face match", p.status === "PENDING" ? "wait" : p.score >= 90 ? "ok" : p.score >= 60 ? "warn" : "bad", p.status === "PENDING" ? "Waiting" : `${p.score.toFixed(1)}%`],
  ["Liveness", p.liveness === null ? "wait" : p.liveness ? "ok" : "bad", p.liveness === null ? "Waiting" : p.liveness ? "Passed" : "Failed"],
  ["Age estimation", p.age === "—" ? "wait" : p.reason?.includes("age") ? "bad" : "ok", p.age === "—" ? "Waiting" : `${p.age} yrs`],
  ["AML screening", p.aml === "—" ? "wait" : p.aml === "Clear" ? "ok" : "warn", p.aml === "—" ? "Waiting" : p.aml],
];
const DOT = { ok: "bg-ok", bad: "bg-bad", warn: "bg-warn", wait: "bg-[#c3d3f5]" };

export default function Verifications() {
  const [list, setList] = useState(DATA);
  const [f, setF] = useState<(typeof FILTERS)[number]>("ALL");
  const [q, setQ] = useState("");
  const [sel, setSel] = useState<string>(DATA[1].id);

  const rows = useMemo(() => list.filter((p) => (f === "ALL" || p.status === f) && p.name.toLowerCase().includes(q.trim().toLowerCase())), [list, f, q]);
  const count = (s: Status) => list.filter((p) => p.status === s).length;
  const p = list.find((x) => x.id === sel);
  const decide = (s: Status) => setList(list.map((x) => (x.id === sel ? { ...x, status: s, reason: s === "REJECTED" ? "Rejected manually by reviewer" : undefined } : x)));

  return (
    <>
      <h1 className="font-display text-2xl font-extrabold tracking-tight md:text-3xl">Verifications</h1>
      <p className="mt-1 text-sm text-navy/60">People who just verified their identity through your application.</p>

      <div className="mt-6 grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
        {([["Verified", count("APPROVED")], ["Needs review", count("REVIEW")], ["Pending", count("PENDING")], ["Rejected", count("REJECTED")]] as const).map(([l, v]) => (
          <div key={l} className="rounded-2xl border border-[#e3eaf8] bg-white p-4"><div className="font-display text-2xl font-bold tabular-nums">{v}</div><div className="text-xs text-navy/55">{l}</div></div>
        ))}
      </div>

      <div className="mt-5 flex flex-wrap items-center gap-2">
        {FILTERS.map((x) => (
          <button key={x} onClick={() => setF(x)} aria-pressed={f === x} className={`rounded-full border px-3 py-1 font-mono text-xs ${f === x ? "border-navy bg-navy text-white" : "border-[#d6e2ff]"}`}>{x}</button>
        ))}
        <input value={q} onChange={(e) => setQ(e.target.value)} placeholder="Search person…" aria-label="Search person" className="ml-auto w-full rounded-full border border-[#d6e2ff] bg-white px-4 py-1.5 text-sm md:w-64" />
      </div>

      <div className="mt-4 grid items-start gap-4 xl:grid-cols-[1fr_360px]">
        <div className="min-w-0 overflow-x-auto rounded-2xl border border-[#e3eaf8] bg-white">
          <table className="w-full text-left text-sm">
            <thead className="bg-[#F6F8FC] font-mono text-[11px] text-navy/60"><tr>{["Person", "Document", "Country", "Status", "Match", "When"].map((h) => <th key={h} className="p-3 font-medium">{h}</th>)}</tr></thead>
            <tbody>
              {rows.map((x) => (
                <tr key={x.id} onClick={() => setSel(x.id)} className={`cursor-pointer border-t border-[#e3eaf8] hover:bg-ice/60 ${x.id === sel ? "bg-ice" : ""}`}>
                  <td className="p-3"><button onClick={() => setSel(x.id)} aria-pressed={x.id === sel} className="flex items-center gap-3 text-left">
                    <span className="grid h-8 w-8 shrink-0 place-items-center rounded-full bg-blue/10 text-[11px] font-bold text-blue">{initials(x.name)}</span><span className="font-medium">{x.name}</span></button></td>
                  <td className="p-3 text-navy/70">{x.doc}</td><td className="p-3 font-mono text-xs">{x.country}</td>
                  <td className="p-3"><span className={`rounded-full px-3 py-1 font-mono text-xs ${BADGE[x.status]}`}>{x.status}</span></td>
                  <td className="p-3 font-mono text-xs">{x.score ? `${x.score.toFixed(1)}%` : "—"}</td>
                  <td className="p-3 text-xs text-navy/60">{x.when}</td>
                </tr>
              ))}
              {rows.length === 0 && <tr><td colSpan={6} className="p-6 text-center text-navy/50">No one found.</td></tr>}
            </tbody>
          </table>
        </div>

        {p && (
          <aside className="rounded-2xl border border-[#e3eaf8] bg-white p-5 xl:sticky xl:top-4" aria-label="Verification details">
            <div className="flex items-center gap-3">
              <span className="grid h-12 w-12 place-items-center rounded-full bg-blue text-sm font-bold text-white">{initials(p.name)}</span>
              <div className="min-w-0"><div className="truncate font-display text-lg font-bold">{p.name}</div><span className={`rounded-full px-2.5 py-0.5 font-mono text-[11px] ${BADGE[p.status]}`}>{p.status}</span></div>
            </div>
            <dl className="mt-4 grid grid-cols-2 gap-y-2 text-sm">
              {[["Verification ID", p.id], ["Submitted", p.when], ["Document", p.doc], ["Country", p.country], ["Document no.", p.docNo], ["Date of birth", p.dob]].map(([k, v]) => (
                <div key={k} className="contents"><dt className="text-navy/55">{k}</dt><dd className="truncate text-right font-mono text-xs leading-5">{v}</dd></div>
              ))}
            </dl>
            <h3 className="mt-5 font-display text-sm font-bold">Checks</h3>
            <ul className="mt-2 divide-y divide-[#e3eaf8] text-sm">
              {checks(p).map(([k, s, v]) => (
                <li key={k} className="flex items-center justify-between py-2"><span className="flex items-center gap-2"><span className={`h-2 w-2 rounded-full ${DOT[s]}`} />{k}</span><span className="font-mono text-xs">{v}</span></li>
              ))}
            </ul>
            <Media key={p.id} p={p} />
            {p.reason && <p className="mt-4 rounded-xl border border-[#f1d9b6] bg-[#FEF3E2] p-3 text-xs text-[#B54708]">{p.reason}</p>}
            {(p.status === "REVIEW" || p.status === "PENDING") && (
              <div className="mt-4 flex gap-2">
                <button onClick={() => decide("APPROVED")} className="flex-1 rounded-full bg-blue py-2.5 text-sm font-semibold text-white hover:bg-navy">Approve</button>
                <button onClick={() => decide("REJECTED")} className="flex-1 rounded-full border border-[#f1b8b2] py-2.5 text-sm font-semibold text-[#B42318] hover:bg-[#FDECEA]">Reject</button>
              </div>
            )}
          </aside>
        )}
      </div>
      <p className="mt-4 text-xs text-navy/50">Demo: sample people and decisions. Approve/Reject only change this browser tab.</p>
    </>
  );
}
