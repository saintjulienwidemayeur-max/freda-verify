"use client";
import Link from "next/link";
import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import OverviewChart from "./OverviewChart";

type Usage = { requests: number; errors: number; period_days: number; by_day: { day: string; requests: number }[] };
type Key = { id: string; revoked_at?: string | null; is_active?: boolean };
type Req = { id: number; created_at: string; method: string; path: string; status: number; latency_ms: number; api_key_prefix: string | null };
type Data = { usage?: Usage; keys?: number; members?: number; reqs?: Req[] };

const tone = (c: number) => (c < 300 ? "bg-[#E7F7EF] text-[#067647]" : c < 500 ? "bg-[#FEF3E2] text-[#B54708]" : "bg-[#FDECEA] text-[#B42318]");
const when = (iso: string) => new Date(iso).toLocaleString(undefined, { month: "short", day: "2-digit", hour: "2-digit", minute: "2-digit" });
const num = (v: number | undefined, loading: boolean) => (loading ? "…" : v === undefined ? "—" : v.toLocaleString("en-US"));

/** Last `days` days (UTC dates, oldest first), filling missing days with 0. */
function series(u: Usage | undefined, days = 30): [string, number][] {
  const m = new Map((u?.by_day ?? []).map((d) => [String(d.day).slice(0, 10), d.requests]));
  const out: [string, number][] = [];
  for (let i = days - 1; i >= 0; i--) { const k = new Date(Date.now() - i * 864e5).toISOString().slice(0, 10); out.push([k, m.get(k) ?? 0]); }
  return out;
}

/** Overview built only from real backend data. Verification results do not exist yet (no engine), so none are shown. */
export default function Overview() {
  const { org, user } = useAuth();
  const [d, setD] = useState<Data | null>(null);
  useEffect(() => {
    if (!org) return;
    let live = true; setD(null);
    void Promise.allSettled([
      api<Usage>(`/usage?organization_id=${org.id}`),
      api<Key[]>(`/organizations/${org.id}/api-keys`),
      api<unknown[]>(`/organizations/${org.id}/members`),
      api<Req[]>(`/organizations/${org.id}/request-logs?limit=8`),
    ]).then(([u, k, m, r]) => {
      if (!live) return;
      setD({
        usage: u.status === "fulfilled" ? u.value : undefined,
        keys: k.status === "fulfilled" ? k.value.filter((x) => !x.revoked_at && x.is_active !== false).length : undefined,
        members: m.status === "fulfilled" ? m.value.length : undefined,
        reqs: r.status === "fulfilled" ? r.value : undefined,
      });
    });
    return () => { live = false; };
  }, [org]);
  const loading = d === null;
  const first = user?.full_name?.split(/\s+/)[0];
  const stats: [string, number | undefined][] = [
    ["API requests (30 days)", d?.usage?.requests], ["Errors (4xx/5xx)", d?.usage?.errors], ["Active API keys", d?.keys], ["Team members", d?.members],
  ];

  return (
    <>
      <h1 className="font-display text-2xl font-extrabold tracking-tight md:text-3xl">Welcome{first ? `, ${first}` : ""}</h1>
      <p className="mt-1 text-sm text-navy/60">{org ? `${org.name} · ` : ""}live figures from your workspace.</p>

      <div className="mt-5 grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
        {stats.map(([l, v]) => (
          <div key={l} className="rounded-2xl border border-[#e3eaf8] bg-white p-4">
            <div className="text-sm font-medium text-navy/70">{l}</div>
            <div className="mt-3 font-display text-3xl font-bold tabular-nums">{num(v, loading)}</div>
          </div>
        ))}
      </div>

      <div className="mt-4 grid gap-4 xl:grid-cols-[1fr_380px]">
        <div className="min-w-0 space-y-4">
          <OverviewChart data={series(d?.usage)} />
          <section className="rounded-2xl border border-[#e3eaf8] bg-white p-5" aria-label="Verifications">
            <h2 className="font-display text-lg font-bold">Verifications</h2>
            <p className="mt-3 rounded-xl border border-dashed border-[#d6e2ff] p-6 text-sm text-navy/60">
              No verification results: the verification engine is not released, so links you create stay pending and no photo is uploaded. <Link href="/dashboard/verifications" className="font-medium text-blue hover:underline">Create or review verification links →</Link>
            </p>
          </section>
        </div>

        <section className="rounded-2xl border border-[#e3eaf8] bg-white p-5" aria-label="Recent API activity">
          <div className="flex items-center justify-between"><h2 className="font-display text-lg font-bold">Recent API activity</h2><Link href="/dashboard/logs" className="text-sm font-medium text-blue hover:underline">View logs →</Link></div>
          {loading && <p className="mt-4 text-sm text-navy/50">Loading…</p>}
          {!loading && !d?.reqs?.length && <p className="mt-4 text-sm text-navy/55">No requests yet. Call the API with one of your keys and they will appear here.</p>}
          <ul className="mt-3 divide-y divide-[#e3eaf8]">
            {d?.reqs?.map((r) => (
              <li key={r.id} className="py-3 text-sm">
                <div className="flex items-center gap-2"><span className={`rounded-full px-2 py-0.5 font-mono text-[11px] ${tone(r.status)}`}>{r.status}</span><span className="truncate font-mono text-xs">{r.method} {r.path}</span></div>
                <div className="mt-1 text-xs text-navy/45">{when(r.created_at)} · {r.latency_ms} ms · {r.api_key_prefix ?? "dashboard"}</div>
              </li>
            ))}
          </ul>
        </section>
      </div>
    </>
  );
}
