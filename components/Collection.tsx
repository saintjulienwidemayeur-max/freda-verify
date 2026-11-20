"use client";
import { useCallback, useEffect, useState, type FormEvent } from "react";
import { api, apiBlob, ApiError } from "@/lib/api";
import { can, useAuth } from "@/lib/auth";

type Campaign = { id: string; name: string; active: boolean; created_at: string; volunteers: number; samples: Record<string, number>; url: string };

export default function Collection() {
  const { org } = useAuth(); const allowed = can.manageKeys(org);
  const [rows, setRows] = useState<Campaign[] | null>(null), [name, setName] = useState(""), [err, setErr] = useState(""), [busy, setBusy] = useState(false), [copied, setCopied] = useState("");
  const base = org ? `/organizations/${org.id}/pad-campaigns` : "";
  const load = useCallback(async () => { if (!org || !allowed) return setRows([]); try { setRows(await api<Campaign[]>(base)); setErr(""); } catch (e) { setErr(e instanceof ApiError ? e.message : "Could not load"); } }, [org, allowed, base]);
  useEffect(() => { setRows(null); void load(); const t = setInterval(() => void load(), 15000); return () => clearInterval(t); }, [load]);
  const act = async (fn: () => Promise<unknown>) => { setBusy(true); setErr(""); try { await fn(); await load(); } catch (e) { setErr(e instanceof ApiError ? e.message : "Action failed"); } finally { setBusy(false); } };
  const create = (e: FormEvent) => { e.preventDefault(); void act(async () => { await api(base, { method: "POST", json: { name: name.trim() } }); setName(""); }); };
  const copy = async (c: Campaign) => { try { await navigator.clipboard.writeText(c.url); setCopied(c.id); setTimeout(() => setCopied(""), 2000); } catch { setCopied(""); } };
  const exportZip = (c: Campaign) => void act(async () => {
    const b = await apiBlob(`${base}/${c.id}/export`); if (!b) throw new ApiError(500, "export_failed", "Export failed");
    const u = URL.createObjectURL(b); const a = document.createElement("a"); a.href = u; a.download = `pad_set_${c.name.replace(/\W+/g, "_")}.zip`; a.click(); URL.revokeObjectURL(u);
  });
  return (
    <>
      <h1 className="font-display text-2xl font-extrabold tracking-tight md:text-3xl">Photo collection</h1>
      <p className="mt-1 text-sm text-navy/60">Send one link to volunteers. They consent, then donate live selfies and (optionally) photos of a printed photo or a screen, to test fraud detection{org ? ` · ${org.name}` : ""}.</p>
      <p className="mt-3 rounded-xl border border-[#FEDF89] bg-[#FEF3E2] p-3 text-xs text-[#B54708]">The consent text shown to volunteers is a DRAFT. Have a lawyer review it before you share the link (privacy and biometric rules). Photos are encrypted, volunteers can erase their own photos, and you can delete a whole collection here.</p>
      {err && <p role="alert" className="mt-4 rounded-xl border border-[#f1b8b2] bg-[#FDECEA] p-3 text-sm text-[#B42318]">{err}</p>}
      {!allowed && <p className="mt-5 rounded-2xl border border-[#e3eaf8] bg-white p-5 text-sm text-navy/60">Only owners and admins can manage collections.</p>}
      {allowed && (
        <form onSubmit={create} className="mt-5 flex flex-wrap items-end gap-3 rounded-2xl border border-[#e3eaf8] bg-white p-5">
          <label className="min-w-0 flex-1 text-sm font-medium">Collection name<input value={name} onChange={(e) => setName(e.target.value)} placeholder="e.g. Pilot December" maxLength={80} required className="mt-1.5 block w-full rounded-xl border border-[#d6e2ff] px-3 py-2.5 text-sm font-normal" /></label>
          <button disabled={busy} className="rounded-full bg-blue px-5 py-2.5 text-sm font-semibold text-white hover:bg-navy disabled:opacity-60">Create link</button>
        </form>)}
      {allowed && (
        <div className="mt-5 space-y-3">
          {rows === null && <p className="text-sm text-navy/50">Loading…</p>}
          {rows?.length === 0 && <p className="rounded-2xl border border-[#e3eaf8] bg-white p-5 text-sm text-navy/60">No collection yet.</p>}
          {rows?.map((c) => (
            <div key={c.id} className="rounded-2xl border border-[#e3eaf8] bg-white p-4">
              <div className="flex flex-wrap items-center justify-between gap-2">
                <div><div className="font-display font-bold">{c.name} <span className={`ml-2 rounded-full px-2 py-0.5 font-mono text-xs ${c.active ? "bg-[#E7F7EF] text-[#067647]" : "bg-[#FDECEA] text-[#B42318]"}`}>{c.active ? "open" : "closed"}</span></div>
                  <div className="text-xs text-navy/55">{c.volunteers} volunteer(s) · live {c.samples.live} · print {c.samples.print} · screen {c.samples.replay} · mask {c.samples.mask}</div></div>
                <div className="flex flex-wrap gap-2 text-xs">
                  <button onClick={() => void copy(c)} className="rounded-full bg-navy px-3 py-1.5 font-semibold text-white">{copied === c.id ? "Copied ✓" : "Copy link"}</button>
                  <button disabled={busy} onClick={() => exportZip(c)} className="rounded-full border border-[#d6e2ff] px-3 py-1.5 hover:bg-ice">Export ZIP</button>
                  <button disabled={busy} onClick={() => void act(() => api(`${base}/${c.id}/active?active=${!c.active}`, { method: "POST" }))} className="rounded-full border border-[#d6e2ff] px-3 py-1.5 hover:bg-ice">{c.active ? "Close" : "Reopen"}</button>
                  <button disabled={busy} onClick={() => { if (confirm("Delete this collection and ALL its photos?")) void act(() => api(`${base}/${c.id}`, { method: "DELETE" })); }} className="rounded-full border border-[#f1b8b2] px-3 py-1.5 text-[#B42318] hover:bg-[#FDECEA]">Delete all</button>
                </div>
              </div>
              <code className="mt-2 block break-all rounded-xl bg-[#F6F8FC] px-3 py-2 font-mono text-[11px] text-navy/70">{c.url}</code>
            </div>))}
        </div>)}
      <div className="mt-6 rounded-2xl border border-[#e3eaf8] bg-white p-5 text-sm text-navy/70">
        <h2 className="font-display text-base font-bold text-navy">After the collection</h2>
        <p className="mt-1">Export the ZIP (folders <code className="font-mono text-xs">genuine/</code>, <code className="font-mono text-xs">attack_print/</code>, <code className="font-mono text-xs">attack_replay/</code>, files named with a person code), unzip it on a machine you control and run <code className="font-mono text-xs">python -m tools.pad_eval pad_set --protocol</code>. Delete the ZIP and the collection when you are done.</p>
      </div>
    </>
  );
}
