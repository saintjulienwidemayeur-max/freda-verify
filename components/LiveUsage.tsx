"use client";
import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import { useAuth } from "@/lib/auth";

/** Real numbers from the backend (last 30 days of API requests). Everything else on the Overview page is still sample data. */
export default function LiveUsage() {
  const { org } = useAuth();
  const [u, setU] = useState<{ requests: number; errors: number } | null | "error">(null);
  useEffect(() => { if (!org) return; setU(null); api<{ requests: number; errors: number }>(`/usage?organization_id=${org.id}`).then(setU).catch(() => setU("error")); }, [org]);
  const show = (v: number | undefined) => (u === null ? "…" : u === "error" || v === undefined ? "—" : v.toLocaleString("en-US"));
  const d = typeof u === "object" && u ? u : undefined;
  return (
    <section className="mt-6 rounded-2xl border border-[#b7e8cf] bg-[#F3FBF7] p-4" aria-label="Live API usage">
      <div className="flex items-center justify-between"><h2 className="font-display text-sm font-bold">API usage · last 30 days{org ? ` · ${org.name}` : ""}</h2><span className="rounded-full bg-[#E7F7EF] px-2.5 py-0.5 font-mono text-[10px] uppercase tracking-widest text-[#067647]">Live data</span></div>
      <div className="mt-3 grid grid-cols-2 gap-3 sm:max-w-md">
        <div className="rounded-xl bg-white p-3"><div className="font-display text-2xl font-bold tabular-nums">{show(d?.requests)}</div><div className="text-xs text-navy/55">Requests</div></div>
        <div className="rounded-xl bg-white p-3"><div className="font-display text-2xl font-bold tabular-nums">{show(d?.errors)}</div><div className="text-xs text-navy/55">Errors (4xx/5xx)</div></div>
      </div>
    </section>
  );
}
