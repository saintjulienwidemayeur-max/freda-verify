"use client";
import { useCallback, useEffect, useState, type FormEvent } from "react";
import { api, ApiError } from "@/lib/api";
import { can, useAuth } from "@/lib/auth";

type Hook = { id: string; url: string; description: string | null; active: boolean; created_at: string };
type Delivery = { id: string; event: string; status: string; attempts: number; response_code: number | null; last_error: string | null; created_at: string; delivered_at: string | null };
const TONE: Record<string, string> = { delivered: "bg-[#E7F7EF] text-[#067647]", failed: "bg-[#FDECEA] text-[#B42318]", pending: "bg-[#FEF3E2] text-[#B54708]" };

const SAMPLE = `import hmac, hashlib, time

def is_valid(secret: str, raw_body: bytes, header: str) -> bool:
    parts = dict(p.split("=", 1) for p in header.split(","))
    if abs(time.time() - int(parts["t"])) > 300:      # replay window: 5 minutes
        return False
    expected = hmac.new(secret.encode(), parts["t"].encode() + b"." + raw_body, hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, parts["v1"])`;

export default function Webhooks() {
  const { org } = useAuth();
  const allowed = can.manageKeys(org);
  const [hooks, setHooks] = useState<Hook[] | null>(null), [error, setError] = useState(""), [busy, setBusy] = useState(false);
  const [url, setUrl] = useState(""), [desc, setDesc] = useState(""), [fresh, setFresh] = useState<{ secret: string; url: string } | null>(null), [copied, setCopied] = useState(false);
  const [open, setOpen] = useState<string | null>(null), [rows, setRows] = useState<Delivery[]>([]);
  const base = org ? `/organizations/${org.id}/webhooks` : "";

  const load = useCallback(async () => {
    if (!org || !allowed) return setHooks([]);
    try { setHooks(await api<Hook[]>(base)); setError(""); } catch (e) { setError(e instanceof ApiError ? e.message : "Could not load webhooks"); }
  }, [org, allowed, base]);
  useEffect(() => { setHooks(null); setFresh(null); setOpen(null); void load(); }, [load]);
  const loadRows = useCallback(async (id: string) => { try { setRows(await api<Delivery[]>(`${base}/${id}/deliveries`)); } catch { setRows([]); } }, [base]);
  useEffect(() => { if (open) void loadRows(open); }, [open, loadRows]);

  const act = async (fn: () => Promise<unknown>, fail: string) => { setBusy(true); setError(""); try { await fn(); } catch (e) { setError(e instanceof ApiError ? e.message : fail); } finally { setBusy(false); } };
  const create = (e: FormEvent) => { e.preventDefault(); void act(async () => {
    const h = await api<Hook & { secret: string }>(base, { method: "POST", json: { url: url.trim(), description: desc.trim() || null } });
    setFresh({ secret: h.secret, url: h.url }); setCopied(false); setUrl(""); setDesc(""); await load();
  }, "Could not add the webhook"); };
  const remove = (id: string) => void act(async () => { await api(`${base}/${id}`, { method: "DELETE" }); if (open === id) setOpen(null); await load(); }, "Could not delete");
  const test = (id: string) => void act(async () => { await api(`${base}/${id}/test`, { method: "POST" }); setOpen(id); setTimeout(() => void loadRows(id), 1500); }, "Could not send the test");
  const resend = (id: string, d: string) => void act(async () => { await api(`${base}/${id}/deliveries/${d}/resend`, { method: "POST" }); setTimeout(() => void loadRows(id), 1500); }, "Could not resend");

  return (
    <>
      <h1 className="font-display text-2xl font-extrabold tracking-tight md:text-3xl">Webhooks</h1>
      <p className="mt-1 text-sm text-navy/60">Freda Verify calls your server when a verification is submitted or decided{org ? ` · ${org.name}` : ""}. Events: <code className="font-mono text-xs">verification.submitted</code>, <code className="font-mono text-xs">verification.approved</code>, <code className="font-mono text-xs">verification.rejected</code>.</p>
      {error && <p role="alert" className="mt-4 rounded-xl border border-[#f1b8b2] bg-[#FDECEA] p-3 text-sm text-[#B42318]">{error}</p>}
      {!allowed && <p className="mt-5 rounded-2xl border border-[#e3eaf8] bg-white p-5 text-sm text-navy/60">Only owners and admins can manage webhooks.</p>}

      {allowed && (
        <form onSubmit={create} className="mt-5 grid gap-4 rounded-2xl border border-[#e3eaf8] bg-white p-5 md:grid-cols-[2fr_1fr_auto] md:items-end">
          <label className="text-sm font-medium">Endpoint URL (https only)
            <input value={url} onChange={(e) => setUrl(e.target.value)} placeholder="https://api.example.com/freda-webhook" maxLength={500} required className="mt-1.5 block w-full rounded-xl border border-[#d6e2ff] px-3 py-2.5 text-sm font-normal" /></label>
          <label className="text-sm font-medium">Label (optional)
            <input value={desc} onChange={(e) => setDesc(e.target.value)} maxLength={100} className="mt-1.5 block w-full rounded-xl border border-[#d6e2ff] px-3 py-2.5 text-sm font-normal" /></label>
          <button disabled={busy} className="rounded-full bg-blue px-5 py-2.5 text-sm font-semibold text-white hover:bg-navy disabled:opacity-60">Add</button>
        </form>
      )}

      {fresh && (
        <div className="mt-5 rounded-2xl border border-[#b7e8cf] bg-[#E7F7EF] p-5" role="status">
          <div className="text-sm font-semibold text-[#067647]">Signing secret for {fresh.url} — copy it now. It will not be shown again.</div>
          <div className="mt-3 flex flex-wrap items-center gap-2">
            <code className="min-w-0 flex-1 break-all rounded-xl border border-[#b7e8cf] bg-white px-3 py-2.5 font-mono text-xs">{fresh.secret}</code>
            <button onClick={async () => { try { await navigator.clipboard.writeText(fresh.secret); setCopied(true); } catch { setCopied(false); } }} className="rounded-full bg-navy px-4 py-2.5 text-xs font-semibold text-white">{copied ? "Copied ✓" : "Copy"}</button>
            <button onClick={() => setFresh(null)} className="px-2 text-xs underline">Dismiss</button>
          </div>
        </div>
      )}

      {allowed && (
        <div className="mt-5 space-y-3">
          {hooks === null && <p className="text-sm text-navy/50">Loading…</p>}
          {hooks?.length === 0 && <p className="rounded-2xl border border-[#e3eaf8] bg-white p-5 text-sm text-navy/60">No webhook yet. Add the URL of your server above.</p>}
          {hooks?.map((h) => (
            <div key={h.id} className="rounded-2xl border border-[#e3eaf8] bg-white p-4">
              <div className="flex flex-wrap items-center justify-between gap-2">
                <div className="min-w-0"><div className="break-all font-mono text-sm">{h.url}</div>{h.description && <div className="text-xs text-navy/55">{h.description}</div>}</div>
                <div className="flex gap-2 text-xs">
                  <button disabled={busy} onClick={() => test(h.id)} className="rounded-full border border-[#d6e2ff] px-3 py-1 hover:bg-ice">Send test</button>
                  <button onClick={() => setOpen(open === h.id ? null : h.id)} className="rounded-full border border-[#d6e2ff] px-3 py-1 hover:bg-ice">{open === h.id ? "Hide deliveries" : "Deliveries"}</button>
                  <button disabled={busy} onClick={() => { if (confirm("Delete this webhook?")) remove(h.id); }} className="rounded-full border border-[#f1b8b2] px-3 py-1 text-[#B42318] hover:bg-[#FDECEA]">Delete</button>
                </div>
              </div>
              {open === h.id && (
                <div className="mt-3 overflow-x-auto">
                  {rows.length === 0 ? <p className="text-xs text-navy/50">No delivery yet.</p> : (
                    <table className="w-full text-left text-xs"><thead className="text-navy/50"><tr><th className="py-1">Event</th><th>Status</th><th>Attempts</th><th>Response</th><th>When</th><th /></tr></thead>
                      <tbody>{rows.map((d) => (
                        <tr key={d.id} className="border-t border-[#eef2fb]"><td className="py-1.5 font-mono">{d.event}</td>
                          <td><span className={`rounded-full px-2 py-0.5 ${TONE[d.status] ?? ""}`}>{d.status}</span></td><td>{d.attempts}</td><td>{d.response_code ?? d.last_error ?? "—"}</td>
                          <td>{new Date(d.created_at).toLocaleString()}</td><td>{d.status === "failed" && <button onClick={() => resend(h.id, d.id)} className="underline">Resend</button>}</td></tr>))}</tbody></table>)}
                </div>)}
            </div>))}
        </div>
      )}

      <div className="mt-6 rounded-2xl border border-[#e3eaf8] bg-white p-5 text-sm">
        <h2 className="font-display text-base font-bold">How to verify a webhook</h2>
        <p className="mt-1 text-navy/60">Each request has the header <code className="font-mono text-xs">Freda-Signature: t=…,v1=…</code>. Recompute the HMAC-SHA256 of <code className="font-mono text-xs">&lt;t&gt;.&lt;raw body&gt;</code> with your secret and refuse anything older than 5 minutes. Payloads contain only ids, your reference and the status, never personal data: call <code className="font-mono text-xs">GET /api/v1/verifications/{"{id}"}/result</code> with your API key to read the result.</p>
        <pre className="mt-3 overflow-x-auto rounded-xl bg-[#F6F8FC] p-3 font-mono text-xs">{SAMPLE}</pre>
        <p className="mt-3 text-xs text-navy/50">Limits today: 3 attempts per event (1 s then 4 s apart), no retry after a server restart; resend by hand from the Deliveries list. The `decision` is made by a person; automatic checks are advisory.</p>
      </div>
    </>
  );
}
