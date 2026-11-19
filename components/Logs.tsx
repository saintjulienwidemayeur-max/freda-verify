"use client";
import { useCallback, useEffect, useState } from "react";
import { api, ApiError } from "@/lib/api";
import { can, useAuth } from "@/lib/auth";

type Req = { id: number; created_at: string; method: string; path: string; status: number; latency_ms: number; api_key_prefix: string | null; request_id: string };
type Aud = { id: number; created_at: string; action: string; actor_user_id: string | null; actor_api_key_id: string | null; target_type: string | null; target_id: string | null; ip: string | null };
const FILTERS = [["ALL", undefined], ["2xx", 2], ["4xx", 4], ["5xx", 5]] as const;
const tone = (c: number) => (c < 300 ? "bg-[#E7F7EF] text-[#067647]" : c < 500 ? "bg-[#FEF3E2] text-[#B54708]" : "bg-[#FDECEA] text-[#B42318]");
const when = (iso: string) => new Date(iso).toLocaleString(undefined, { month: "short", day: "2-digit", hour: "2-digit", minute: "2-digit", second: "2-digit" });

export default function Logs() {
  const { org } = useAuth();
  const [tab, setTab] = useState<"requests" | "audit">("requests");
  const [cls, setCls] = useState<number | undefined>();
  const [reqs, setReqs] = useState<Req[] | null>(null), [aud, setAud] = useState<Aud[] | null>(null), [error, setError] = useState(""), [more, setMore] = useState(false);

  const load = useCallback(async (append = false) => {
    if (!org) return;
    try {
      if (tab === "requests") {
        const last = append && reqs?.length ? `&before_id=${reqs[reqs.length - 1].id}` : "";
        const rows = await api<Req[]>(`/organizations/${org.id}/request-logs?limit=50${cls ? `&status_class=${cls}` : ""}${last}`);
        setReqs(append ? [...(reqs ?? []), ...rows] : rows); setMore(rows.length === 50);
      } else {
        const last = append && aud?.length ? `&before_id=${aud[aud.length - 1].id}` : "";
        const rows = await api<Aud[]>(`/organizations/${org.id}/audit-logs?limit=50${last}`);
        setAud(append ? [...(aud ?? []), ...rows] : rows); setMore(rows.length === 50);
      }
      setError("");
    } catch (e) { setError(e instanceof ApiError ? (e.status === 403 ? "Your role cannot view this log." : e.message) : "Could not load logs"); if (tab === "requests") setReqs([]); else setAud([]); }
  }, [org, tab, cls, reqs, aud]);
  // eslint-disable-next-line react-hooks/exhaustive-deps
  useEffect(() => { setReqs(null); setAud(null); void load(false); }, [org?.id, tab, cls]);

  const rows = tab === "requests" ? reqs : aud;
  return (
    <>
      <h1 className="font-display text-2xl font-extrabold tracking-tight md:text-3xl">Logs</h1>
      <p className="mt-1 text-sm text-navy/60">API requests made with your keys, and the audit trail of who changed what. No request bodies, headers or IP addresses are stored in the request log.</p>

      <div className="mt-5 flex flex-wrap items-center gap-2">
        {([["requests", "API requests"], ["audit", "Audit trail"]] as const).map(([k, l]) => (
          <button key={k} onClick={() => { setTab(k); setMore(false); }} aria-pressed={tab === k} disabled={k === "audit" && !can.audit(org)} className={`rounded-full border px-4 py-1.5 text-sm disabled:opacity-40 ${tab === k ? "border-navy bg-navy text-white" : "border-[#d6e2ff]"}`}>{l}</button>
        ))}
        {tab === "requests" && <span className="mx-1 h-5 w-px bg-[#d6e2ff]" />}
        {tab === "requests" && FILTERS.map(([l, v]) => (
          <button key={l} onClick={() => setCls(v)} aria-pressed={cls === v} className={`rounded-full border px-3 py-1 font-mono text-xs ${cls === v ? "border-navy bg-navy text-white" : "border-[#d6e2ff]"}`}>{l}</button>
        ))}
      </div>

      {error && <p role="alert" className="mt-4 rounded-xl border border-[#f1b8b2] bg-[#FDECEA] p-3 text-sm text-[#B42318]">{error}</p>}

      <div className="mt-4 overflow-x-auto rounded-2xl border border-[#e3eaf8] bg-white">
        <table className="w-full text-left text-sm">
          <thead className="bg-[#F6F8FC] font-mono text-[11px] text-navy/60"><tr>{(tab === "requests" ? ["Time", "Method", "Endpoint", "Status", "Latency", "Key"] : ["Time", "Action", "Target", "Actor", "IP"]).map((h) => <th key={h} className="p-3 font-medium">{h}</th>)}</tr></thead>
          <tbody>
            {rows === null && <tr><td colSpan={6} className="p-6 text-center text-navy/50">Loading…</td></tr>}
            {rows?.length === 0 && <tr><td colSpan={6} className="p-6 text-center text-navy/50">{tab === "requests" ? "No requests yet. Call the API with one of your keys and they will appear here." : "Nothing recorded yet."}</td></tr>}
            {tab === "requests" && reqs?.map((r) => (
              <tr key={r.id} className="border-t border-[#e3eaf8]">
                <td className="p-3 font-mono text-xs">{when(r.created_at)}</td><td className="p-3 font-mono text-xs">{r.method}</td><td className="p-3 font-mono text-xs">{r.path}</td>
                <td className="p-3"><span className={`rounded-full px-2.5 py-0.5 font-mono text-xs ${tone(r.status)}`}>{r.status}</span></td>
                <td className="p-3 font-mono text-xs">{r.latency_ms} ms</td><td className="p-3 font-mono text-xs text-navy/60">{r.api_key_prefix ?? "dashboard"}</td>
              </tr>
            ))}
            {tab === "audit" && aud?.map((r) => (
              <tr key={r.id} className="border-t border-[#e3eaf8]">
                <td className="p-3 font-mono text-xs">{when(r.created_at)}</td><td className="p-3 font-mono text-xs">{r.action}</td>
                <td className="p-3 font-mono text-xs text-navy/70">{r.target_type ? `${r.target_type}${r.target_id ? ` ${r.target_id.slice(0, 8)}…` : ""}` : "—"}</td>
                <td className="p-3 font-mono text-xs text-navy/70">{r.actor_user_id ? `user ${r.actor_user_id.slice(0, 8)}…` : r.actor_api_key_id ? "api key" : "—"}</td><td className="p-3 font-mono text-xs text-navy/60">{r.ip ?? "—"}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      {more && <button onClick={() => void load(true)} className="mt-4 rounded-full border border-[#d6e2ff] px-5 py-2 text-sm font-medium hover:bg-ice">Load more</button>}
    </>
  );
}
