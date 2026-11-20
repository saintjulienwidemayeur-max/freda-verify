"use client";
import { useCallback, useEffect, useState, type FormEvent } from "react";
import { api, ApiError } from "@/lib/api";
import { can, useAuth } from "@/lib/auth";

type V = { id: string; status: string; env: string; reference: string | null; consent_given: boolean; created_at: string; expires_at: string };
const BADGE: Record<string, string> = { PENDING: "bg-[#FEF3E2] text-[#B54708]", EXPIRED: "bg-[#EEF0F4] text-navy/60", APPROVED: "bg-[#E7F7EF] text-[#067647]", REJECTED: "bg-[#FDECEA] text-[#B42318]", MANUAL_REVIEW: "bg-[#EEF4FF] text-blue" };
const when = (iso: string) => new Date(iso).toLocaleString(undefined, { month: "short", day: "2-digit", hour: "2-digit", minute: "2-digit" });

export default function Verifications() {
  const { org } = useAuth();
  const [rows, setRows] = useState<V[] | null>(null), [error, setError] = useState(""), [busy, setBusy] = useState(false);
  const [ref, setRef] = useState(""), [fresh, setFresh] = useState<{ url: string; reference: string | null } | null>(null), [copied, setCopied] = useState(false);
  const writable = can.readKeys(org);                                  // owner, admin, member

  const load = useCallback(async () => {
    if (!org) return;
    try { setRows(await api<V[]>(`/verifications?organization_id=${org.id}&limit=100`)); setError(""); } catch (e) { setError(e instanceof ApiError ? e.message : "Could not load verifications"); setRows([]); }
  }, [org]);
  useEffect(() => { setRows(null); setFresh(null); void load(); }, [load]);

  const create = async (e: FormEvent) => {
    e.preventDefault(); if (!org) return; setBusy(true); setError("");
    try {
      const v = await api<V & { url: string }>("/verifications", { method: "POST", json: { organization_id: org.id, reference: ref.trim() || undefined } });
      setFresh({ url: v.url, reference: v.reference }); setCopied(false); setRef(""); await load();
    } catch (er) { setError(er instanceof ApiError ? (er.details[0] ? `${er.details[0].field}: ${er.details[0].message}` : er.message) : "Could not create the verification"); } finally { setBusy(false); }
  };
  const copy = async () => { try { await navigator.clipboard.writeText(fresh?.url ?? ""); setCopied(true); } catch { setCopied(false); } };

  return (
    <>
      <h1 className="font-display text-2xl font-extrabold tracking-tight md:text-3xl">Verifications</h1>
      <p className="mt-1 text-sm text-navy/60">Create a verification link for one of your customers and follow its status.</p>
      <p className="mt-3 rounded-xl border border-[#d6e2ff] bg-ice p-3 text-sm text-navy/70">
        The verification engine is not released yet: a link opens your branded hosted page and records consent, but photos are not uploaded and no result is produced. Links stay <b>PENDING</b> until they expire.
      </p>

      {writable && (
        <form onSubmit={create} className="mt-5 flex flex-wrap items-end gap-3 rounded-2xl border border-[#e3eaf8] bg-white p-4">
          <label className="min-w-[14rem] flex-1 text-sm font-medium">Reference (optional)
            <input value={ref} onChange={(e) => setRef(e.target.value)} maxLength={100} placeholder="your customer id, e.g. cust-42" className="mt-1.5 block w-full rounded-xl border border-[#d6e2ff] px-3 py-2.5 text-sm font-normal" /></label>
          <button disabled={busy} className="rounded-full bg-blue px-6 py-2.5 text-sm font-semibold text-white hover:bg-navy disabled:opacity-50">{busy ? "Creating…" : "Create verification link"}</button>
        </form>
      )}

      {fresh && (
        <section className="mt-4 rounded-2xl border border-[#b7e8cf] bg-[#F3FBF7] p-4" aria-label="New verification link">
          <h2 className="font-display text-sm font-bold">Link created{fresh.reference ? ` · ${fresh.reference}` : ""}. Copy it now: it is shown only once.</h2>
          <div className="mt-2 flex flex-wrap items-center gap-2">
            <code className="min-w-0 flex-1 break-all rounded-lg bg-white p-2.5 font-mono text-xs">{fresh.url}</code>
            <button onClick={() => void copy()} className="rounded-full border border-[#d6e2ff] bg-white px-4 py-2 text-sm hover:bg-ice">{copied ? "Copied ✓" : "Copy"}</button>
            <a href={fresh.url} target="_blank" rel="noopener" className="rounded-full border border-[#d6e2ff] bg-white px-4 py-2 text-sm text-blue hover:bg-ice">Open ↗</a>
          </div>
        </section>
      )}

      {error && <p role="alert" className="mt-4 rounded-xl border border-[#f1b8b2] bg-[#FDECEA] p-3 text-sm text-[#B42318]">{error}</p>}

      <div className="mt-4 overflow-x-auto rounded-2xl border border-[#e3eaf8] bg-white">
        <table className="w-full text-left text-sm">
          <thead className="bg-[#F6F8FC] font-mono text-[11px] text-navy/60"><tr>{["Created", "Reference", "Env", "Status", "Consent", "Expires"].map((h) => <th key={h} className="p-3 font-medium">{h}</th>)}</tr></thead>
          <tbody>
            {rows === null && <tr><td colSpan={6} className="p-6 text-center text-navy/50">Loading…</td></tr>}
            {rows?.length === 0 && <tr><td colSpan={6} className="p-6 text-center text-navy/50">No verifications yet. Create a link above or call <code className="font-mono">POST /api/v1/verifications</code> with an API key.</td></tr>}
            {rows?.map((v) => (
              <tr key={v.id} className="border-t border-[#e3eaf8]">
                <td className="p-3 font-mono text-xs">{when(v.created_at)}</td><td className="p-3">{v.reference ?? <span className="text-navy/40">—</span>}</td>
                <td className="p-3 font-mono text-xs">{v.env}</td>
                <td className="p-3"><span className={`rounded-full px-2.5 py-0.5 font-mono text-xs ${BADGE[v.status] ?? ""}`}>{v.status}</span></td>
                <td className="p-3 text-xs">{v.consent_given ? "Given" : "—"}</td><td className="p-3 font-mono text-xs">{when(v.expires_at)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </>
  );
}
