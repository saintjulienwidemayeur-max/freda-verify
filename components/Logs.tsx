"use client";
import { Fragment, useMemo, useState } from "react";

type L = { t: string; method: "POST" | "GET"; path: string; code: number; ms: number; key: string; req: string; res: string };
const LOGS: L[] = [
  { t: "19:41:07", method: "POST", path: "/v1/sessions", code: 201, ms: 212, key: "a91c", req: '{ "type": "kyc", "callback": "https://votre-app.com/webhook" }', res: '{ "id": "ses_7c21a9", "status": "created" }' },
  { t: "19:40:52", method: "GET", path: "/v1/sessions/ses_7c21a9", code: 200, ms: 64, key: "a91c", req: "—", res: '{ "id": "ses_7c21a9", "status": "approved", "score": 99.8 }' },
  { t: "19:38:19", method: "POST", path: "/v1/sessions", code: 201, ms: 198, key: "a91c", req: '{ "type": "kyb" }', res: '{ "id": "ses_91bd20", "status": "created" }' },
  { t: "19:35:44", method: "POST", path: "/v1/sessions", code: 422, ms: 41, key: "7d20", req: '{ "type": "kyx" }', res: '{ "error": "invalid_type", "message": "type must be kyc or kyb" }' },
  { t: "19:31:03", method: "GET", path: "/v1/sessions/ses_55f0c3", code: 404, ms: 38, key: "7d20", req: "—", res: '{ "error": "not_found" }' },
  { t: "19:27:30", method: "POST", path: "/v1/sessions", code: 401, ms: 12, key: "e4b8", req: '{ "type": "kyc" }', res: '{ "error": "key_revoked", "message": "This API key has been revoked" }' },
  { t: "19:20:11", method: "GET", path: "/v1/sessions/ses_3a77e1", code: 200, ms: 71, key: "a91c", req: "—", res: '{ "id": "ses_3a77e1", "status": "rejected", "score": 41.0 }' },
  { t: "19:12:58", method: "POST", path: "/v1/sessions", code: 500, ms: 1840, key: "a91c", req: '{ "type": "kyc" }', res: '{ "error": "internal_error", "message": "Please retry" }' },
  { t: "19:05:26", method: "POST", path: "/v1/sessions", code: 201, ms: 205, key: "7d20", req: '{ "type": "kyc" }', res: '{ "id": "ses_c0d4b8", "status": "created" }' },
];
const FILTERS = ["ALL", "2xx", "4xx", "5xx"] as const;
const tone = (c: number) => (c < 300 ? "bg-[#E7F7EF] text-[#067647]" : c < 500 ? "bg-[#FEF3E2] text-[#B54708]" : "bg-[#FDECEA] text-[#B42318]");

export default function Logs() {
  const [f, setF] = useState<(typeof FILTERS)[number]>("ALL");
  const [q, setQ] = useState("");
  const [open, setOpen] = useState<number | null>(null);
  const rows = useMemo(() => LOGS.filter((l) => (f === "ALL" || String(l.code)[0] === f[0]) && l.path.toLowerCase().includes(q.trim().toLowerCase())), [f, q]);
  const ok = LOGS.filter((l) => l.code < 300).length;

  return (
    <>
      <h1 className="font-display text-2xl font-extrabold tracking-tight md:text-3xl">Logs</h1>
      <p className="mt-1 text-sm text-navy/60">Every API request made with your keys, newest first.</p>

      <div className="mt-6 grid gap-4 sm:grid-cols-3">
        {[["Requests", String(LOGS.length)], ["Success rate", `${Math.round((ok / LOGS.length) * 100)}%`], ["Avg latency", `${Math.round(LOGS.reduce((a, l) => a + l.ms, 0) / LOGS.length)} ms`]].map(([l, v]) => (
          <div key={l} className="rounded-2xl border border-[#e3eaf8] bg-white p-4"><div className="text-xs text-navy/55">{l}</div><div className="mt-1 font-display text-2xl font-bold tabular-nums">{v}</div></div>
        ))}
      </div>

      <div className="mt-5 flex flex-wrap items-center gap-2">
        {FILTERS.map((x) => (
          <button key={x} onClick={() => setF(x)} aria-pressed={f === x}
            className={`rounded-full border px-3 py-1 font-mono text-xs ${f === x ? "border-navy bg-navy text-white" : "border-[#d6e2ff]"}`}>{x}</button>
        ))}
        <input value={q} onChange={(e) => setQ(e.target.value)} placeholder="Search endpoint…" aria-label="Search endpoint"
          className="ml-auto w-full rounded-full border border-[#d6e2ff] bg-white px-4 py-1.5 text-sm md:w-64" />
      </div>

      <div className="mt-4 overflow-x-auto rounded-2xl border border-[#e3eaf8] bg-white">
        <table className="w-full text-left text-sm">
          <thead className="bg-[#F6F8FC] font-mono text-[11px] text-navy/60"><tr>{["Time", "Method", "Endpoint", "Status", "Latency", "Key"].map((h) => <th key={h} className="p-3 font-medium">{h}</th>)}</tr></thead>
          <tbody>
            {rows.map((l) => {
              const i = LOGS.indexOf(l), o = open === i;
              return (
                <Fragment key={i}>
                  <tr onClick={() => setOpen(o ? null : i)} className="cursor-pointer border-t border-[#e3eaf8] hover:bg-ice/60">
                    <td className="p-3 font-mono text-xs">{l.t}</td>
                    <td className="p-3 font-mono text-xs">{l.method}</td>
                    <td className="p-3"><button aria-expanded={o} onClick={(e) => { e.stopPropagation(); setOpen(o ? null : i); }} className="text-left font-mono text-xs hover:underline">{l.path}</button></td>
                    <td className="p-3"><span className={`rounded-full px-2.5 py-0.5 font-mono text-xs ${tone(l.code)}`}>{l.code}</span></td>
                    <td className="p-3 font-mono text-xs">{l.ms} ms</td>
                    <td className="p-3 font-mono text-xs text-navy/60">…{l.key}</td>
                  </tr>
                  {o && (
                    <tr className="border-t border-[#e3eaf8] bg-[#F6F8FC]">
                      <td colSpan={6} className="p-4">
                        <div className="grid gap-3 md:grid-cols-2">
                          {[["Request", l.req], ["Response", l.res]].map(([h, b]) => (
                            <div key={h}><div className="mb-1 font-mono text-[10px] uppercase tracking-widest text-navy/50">{h}</div><pre className="overflow-x-auto rounded-xl bg-navy p-3 font-mono text-xs leading-5 text-white">{b}</pre></div>
                          ))}
                        </div>
                      </td>
                    </tr>
                  )}
                </Fragment>
              );
            })}
            {rows.length === 0 && <tr><td colSpan={6} className="p-6 text-center text-navy/50">No requests match.</td></tr>}
          </tbody>
        </table>
      </div>
    </>
  );
}
