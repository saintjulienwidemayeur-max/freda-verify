"use client";
import { useCallback, useEffect, useState, type FormEvent } from "react";
import { api, apiBlob, ApiError } from "@/lib/api";
import { can, useAuth } from "@/lib/auth";

type V = { id: string; status: string; env: string; reference: string | null; consent_given: boolean; created_at: string; expires_at: string; submitted_at: string | null; decided_at: string | null; decision_reason: string | null; media_count: number };
type Media = { kind: string; doc_type: string | null; country: string | null; size: number; purge_after: string };
const LABEL: Record<string, string> = { document_front: "Document · front", document_back: "Document · back", selfie: "Selfie" };

/** Review panel: photos are decrypted by the API only for owners/admins and every view is audited. No automated analysis exists: a person decides. */
function Review({ v, orgId, onChange, onClose }: { v: V; orgId: string; onChange: () => void; onClose: () => void }) {
  const { org } = useAuth();
  const admin = org?.role === "owner" || org?.role === "admin";
  const [media, setMedia] = useState<Media[] | null>(null), [imgs, setImgs] = useState<Record<string, string>>({}), [err, setErr] = useState(""), [reason, setReason] = useState(""), [busy, setBusy] = useState(false);
  const base = `/organizations/${orgId}/verifications/${v.id}`;
  useEffect(() => {
    let live = true; const made: string[] = [];
    (async () => {
      try {
        const m = await api<Media[]>(`${base}/media`); if (!live) return; setMedia(m);
        if (!admin) return;
        const out: Record<string, string> = {};
        for (const x of m) { const b = await apiBlob(`${base}/media/${x.kind}`); if (b) { const u = URL.createObjectURL(b); made.push(u); out[x.kind] = u; } }
        if (live) setImgs(out);
      } catch (e) { if (live) setErr(e instanceof ApiError ? e.message : "Could not load the photos"); }
    })();
    return () => { live = false; made.forEach((u) => URL.revokeObjectURL(u)); };
  }, [base, admin, v.media_count]);
  const act = async (fn: () => Promise<unknown>) => { setBusy(true); setErr(""); try { await fn(); onChange(); } catch (e) { setErr(e instanceof ApiError ? e.message : "Action failed"); } finally { setBusy(false); } };
  return (
    <section className="mt-4 rounded-2xl border border-[#e3eaf8] bg-white p-5" aria-label="Verification review">
      <div className="flex items-start justify-between gap-3">
        <div><h2 className="font-display text-lg font-bold">{v.reference ?? "Verification"} <span className={`ml-2 rounded-full px-2.5 py-0.5 font-mono text-xs ${BADGE[v.status] ?? ""}`}>{v.status}</span></h2>
          <p className="mt-1 font-mono text-[11px] text-navy/50">{v.id}</p></div>
        <button onClick={onClose} className="rounded-full border border-[#d6e2ff] px-3 py-1 text-sm hover:bg-ice">Close</button>
      </div>
      {err && <p role="alert" className="mt-3 rounded-xl border border-[#f1b8b2] bg-[#FDECEA] p-3 text-sm text-[#B42318]">{err}</p>}
      {media === null && <p className="mt-3 text-sm text-navy/50">Loading…</p>}
      {media?.length === 0 && <p className="mt-3 text-sm text-navy/55">No photos stored{v.submitted_at ? " (deleted or past the retention period)" : " yet"}.</p>}
      {media && media.length > 0 && !admin && <p className="mt-3 text-sm text-navy/60">{media.length} photo(s) stored. Only owners and admins can view them.</p>}
      <div className="mt-3 grid gap-3 sm:grid-cols-3">
        {media?.map((m) => (
          <figure key={m.kind} className="rounded-xl border border-[#e3eaf8] p-2">
            {imgs[m.kind] ? /* eslint-disable-next-line @next/next/no-img-element */ <img src={imgs[m.kind]} alt={LABEL[m.kind]} className="max-h-56 w-full rounded-lg object-contain bg-[#F6F8FC]" /> : <div className="grid h-32 place-items-center rounded-lg bg-[#F6F8FC] text-xs text-navy/40">{admin ? "Loading…" : "Hidden"}</div>}
            <figcaption className="mt-1.5 text-xs text-navy/60"><b>{LABEL[m.kind]}</b>{m.doc_type ? ` · ${m.doc_type}` : ""}{m.country ? ` · ${m.country}` : ""}<br />Deleted automatically on {new Date(m.purge_after).toLocaleDateString()}</figcaption>
          </figure>
        ))}
      </div>
      {v.decision_reason && <p className="mt-3 text-sm">Decision note: {v.decision_reason}</p>}
      {admin && v.status === "MANUAL_REVIEW" && (
        <div className="mt-4 flex flex-wrap items-end gap-3 border-t border-[#e3eaf8] pt-4">
          <label className="min-w-[14rem] flex-1 text-sm font-medium">Note (optional)<input value={reason} maxLength={200} onChange={(e) => setReason(e.target.value)} className="mt-1.5 block w-full rounded-xl border border-[#d6e2ff] px-3 py-2 text-sm font-normal" /></label>
          <button disabled={busy} onClick={() => void act(() => api(`${base}/decision`, { method: "POST", json: { decision: "APPROVED", reason: reason.trim() || undefined } }))} className="rounded-full bg-[#12B76A] px-5 py-2 text-sm font-semibold text-white disabled:opacity-50">Approve</button>
          <button disabled={busy} onClick={() => void act(() => api(`${base}/decision`, { method: "POST", json: { decision: "REJECTED", reason: reason.trim() || undefined } }))} className="rounded-full bg-[#D92D20] px-5 py-2 text-sm font-semibold text-white disabled:opacity-50">Reject</button>
        </div>
      )}
      {admin && media && media.length > 0 && (
        <button disabled={busy} onClick={() => { if (confirm("Delete all photos of this verification now? This cannot be undone.")) void act(() => api(`${base}/media`, { method: "DELETE" })); }} className="mt-3 text-sm text-[#B42318] underline disabled:opacity-50">Delete photos now</button>
      )}
      <p className="mt-3 text-xs text-navy/45">This is a manual review: no automated check (document authenticity, face match, liveness, AML) has been run on these photos.</p>
    </section>
  );
}
const BADGE: Record<string, string> = { PENDING: "bg-[#FEF3E2] text-[#B54708]", EXPIRED: "bg-[#EEF0F4] text-navy/60", APPROVED: "bg-[#E7F7EF] text-[#067647]", REJECTED: "bg-[#FDECEA] text-[#B42318]", MANUAL_REVIEW: "bg-[#EEF4FF] text-blue" };
const when = (iso: string) => new Date(iso).toLocaleString(undefined, { month: "short", day: "2-digit", hour: "2-digit", minute: "2-digit" });

export default function Verifications() {
  const { org } = useAuth();
  const [rows, setRows] = useState<V[] | null>(null), [error, setError] = useState(""), [busy, setBusy] = useState(false);
  const [ref, setRef] = useState(""), [fresh, setFresh] = useState<{ url: string; reference: string | null } | null>(null), [copied, setCopied] = useState(false);
  const writable = can.readKeys(org);                                  // owner, admin, member
  const [open, setOpen] = useState<string | null>(null);

  const load = useCallback(async () => {
    if (!org) return;
    try { setRows(await api<V[]>(`/verifications?organization_id=${org.id}&limit=100`)); setError(""); } catch (e) { setError(e instanceof ApiError ? e.message : "Could not load verifications"); setRows([]); }
  }, [org]);
  useEffect(() => { setRows(null); setFresh(null); setOpen(null); void load(); }, [load]);

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
        Customers send their ID photos and selfie through the link; photos are stored encrypted and deleted automatically after the retention period. There is no automated verification yet: submitted verifications wait in <b>MANUAL_REVIEW</b> for a person to approve or reject them.
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

      {org && rows?.find((x) => x.id === open) && <Review key={open} v={rows.find((x) => x.id === open)!} orgId={org.id} onChange={() => void load()} onClose={() => setOpen(null)} />}

      <div className="mt-4 overflow-x-auto rounded-2xl border border-[#e3eaf8] bg-white">
        <table className="w-full text-left text-sm">
          <thead className="bg-[#F6F8FC] font-mono text-[11px] text-navy/60"><tr>{["Created", "Reference", "Env", "Status", "Photos", "Expires", ""].map((h) => <th key={h} className="p-3 font-medium">{h}</th>)}</tr></thead>
          <tbody>
            {rows === null && <tr><td colSpan={7} className="p-6 text-center text-navy/50">Loading…</td></tr>}
            {rows?.length === 0 && <tr><td colSpan={7} className="p-6 text-center text-navy/50">No verifications yet. Create a link above or call <code className="font-mono">POST /api/v1/verifications</code> with an API key.</td></tr>}
            {rows?.map((v) => (
              <tr key={v.id} className="border-t border-[#e3eaf8]">
                <td className="p-3 font-mono text-xs">{when(v.created_at)}</td><td className="p-3">{v.reference ?? <span className="text-navy/40">—</span>}</td>
                <td className="p-3 font-mono text-xs">{v.env}</td>
                <td className="p-3"><span className={`rounded-full px-2.5 py-0.5 font-mono text-xs ${BADGE[v.status] ?? ""}`}>{v.status}</span></td>
                <td className="p-3 text-xs">{v.media_count || "—"}</td><td className="p-3 font-mono text-xs">{when(v.expires_at)}</td>
                <td className="p-3"><button onClick={() => setOpen(open === v.id ? null : v.id)} className="rounded-full border border-[#d6e2ff] px-3 py-1 text-xs hover:bg-ice">{open === v.id ? "Hide" : "Open"}</button></td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </>
  );
}
