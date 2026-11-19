"use client";
import { useCallback, useEffect, useState, type FormEvent } from "react";
import { API_URL, api, ApiError } from "@/lib/api";
import { can, useAuth } from "@/lib/auth";

type Key = { id: string; name: string; env: "test" | "live"; prefix: string; last4: string; created_at: string; last_used_at: string | null; revoked_at: string | null };
const ago = (iso: string | null) => {
  if (!iso) return "Never";
  const s = Math.max(0, (Date.now() - new Date(iso).getTime()) / 1000);
  return s < 60 ? "just now" : s < 3600 ? `${Math.floor(s / 60)} min ago` : s < 86400 ? `${Math.floor(s / 3600)} h ago` : `${Math.floor(s / 86400)} d ago`;
};

export default function ApiKeys() {
  const { org } = useAuth();
  const [keys, setKeys] = useState<Key[] | null>(null), [error, setError] = useState(""), [busy, setBusy] = useState(false);
  const [open, setOpen] = useState(false), [name, setName] = useState(""), [env, setEnv] = useState<"test" | "live">("test");
  const [fresh, setFresh] = useState<{ secret: string; name: string } | null>(null), [copied, setCopied] = useState(false), [confirm, setConfirm] = useState<string | null>(null);

  const load = useCallback(async () => {
    if (!org || !can.readKeys(org)) return setKeys([]);
    try { setKeys(await api<Key[]>(`/organizations/${org.id}/api-keys`)); setError(""); } catch (e) { setError(e instanceof ApiError ? e.message : "Could not load keys"); }
  }, [org]);
  useEffect(() => { setKeys(null); setFresh(null); void load(); }, [load]);

  const create = async (e: FormEvent) => {
    e.preventDefault(); if (!org) return; setBusy(true); setError("");
    try {
      const k = await api<Key & { secret: string }>(`/organizations/${org.id}/api-keys`, { method: "POST", json: { name: name.trim() || "Untitled key", env } });
      setFresh({ secret: k.secret, name: k.name }); setCopied(false); setOpen(false); setName(""); await load();
    } catch (err) { setError(err instanceof ApiError ? err.message : "Could not create the key"); } finally { setBusy(false); }
  };
  const revoke = async (id: string) => {
    if (!org) return; setConfirm(null);
    try { await api(`/organizations/${org.id}/api-keys/${id}`, { method: "DELETE" }); await load(); } catch (err) { setError(err instanceof ApiError ? err.message : "Could not revoke the key"); }
  };
  const copy = async () => { try { await navigator.clipboard.writeText(fresh?.secret ?? ""); setCopied(true); } catch { setCopied(false); } };

  const writable = can.manageKeys(org);
  return (
    <>
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <h1 className="font-display text-2xl font-extrabold tracking-tight md:text-3xl">API Keys</h1>
          <p className="mt-1 text-sm text-navy/60">Keys your application uses to call the Freda Verify API{org ? ` · ${org.name}` : ""}.</p>
        </div>
        {writable && <button onClick={() => setOpen(!open)} className="rounded-full bg-blue px-5 py-2.5 text-sm font-semibold text-white hover:bg-navy">{open ? "Cancel" : "+ Create key"}</button>}
      </div>

      {error && <p role="alert" className="mt-4 rounded-xl border border-[#f1b8b2] bg-[#FDECEA] p-3 text-sm text-[#B42318]">{error}</p>}

      {open && (
        <form onSubmit={create} className="mt-5 grid gap-4 rounded-2xl border border-[#e3eaf8] bg-white p-5 md:grid-cols-[1fr_auto_auto] md:items-end">
          <label className="text-sm font-medium">Key name
            <input value={name} onChange={(e) => setName(e.target.value)} placeholder="e.g. Production backend" maxLength={80} className="mt-1.5 block w-full rounded-xl border border-[#d6e2ff] bg-white px-3 py-2.5 text-sm font-normal" /></label>
          <fieldset className="text-sm font-medium"><legend className="mb-1.5">Environment</legend>
            <div className="flex gap-2">{(["test", "live"] as const).map((x) => (
              <button type="button" key={x} onClick={() => setEnv(x)} aria-pressed={env === x} className={`rounded-full border px-4 py-2 font-mono text-xs capitalize ${env === x ? "border-navy bg-navy text-white" : "border-[#d6e2ff]"}`}>{x}</button>))}</div></fieldset>
          <button disabled={busy} className="rounded-full bg-blue px-5 py-2.5 text-sm font-semibold text-white hover:bg-navy disabled:opacity-60">Generate</button>
          {env === "live" && <p className="text-xs text-[#B54708] md:col-span-3">Live keys run real verifications. Keep them on your server and never put them in a web page or mobile app.</p>}
        </form>
      )}

      {fresh && (
        <div className="mt-5 rounded-2xl border border-[#b7e8cf] bg-[#E7F7EF] p-5" role="status">
          <div className="text-sm font-semibold text-[#067647]">Key “{fresh.name}” created — copy it now. It will not be shown again.</div>
          <div className="mt-3 flex flex-wrap items-center gap-2">
            <code className="min-w-0 flex-1 break-all rounded-xl border border-[#b7e8cf] bg-white px-3 py-2.5 font-mono text-xs">{fresh.secret}</code>
            <button onClick={copy} className="rounded-full bg-navy px-4 py-2.5 text-xs font-semibold text-white">{copied ? "Copied ✓" : "Copy"}</button>
            <button onClick={() => setFresh(null)} className="px-2 text-xs underline">Dismiss</button>
          </div>
        </div>
      )}

      <section className="mt-5 overflow-x-auto rounded-2xl border border-[#e3eaf8] bg-white" aria-label="API keys">
        <table className="w-full text-left text-sm">
          <thead className="bg-[#F6F8FC] font-mono text-[11px] text-navy/60"><tr>{["Name", "Key", "Env", "Created", "Last used", "Status", ""].map((h, i) => <th key={i} className="p-3 font-medium">{h}</th>)}</tr></thead>
          <tbody>
            {keys === null && <tr><td colSpan={7} className="p-6 text-center text-navy/50">Loading…</td></tr>}
            {keys?.length === 0 && <tr><td colSpan={7} className="p-6 text-center text-navy/50">{can.readKeys(org) ? "No keys yet." : "Your role cannot view API keys."}</td></tr>}
            {keys?.map((k) => (
              <tr key={k.id} className="border-t border-[#e3eaf8]">
                <td className="p-3 font-medium">{k.name}</td>
                <td className="p-3 font-mono text-xs text-navy/70">{k.prefix}••••{k.last4}</td>
                <td className="p-3"><span className={`rounded-full px-2.5 py-0.5 font-mono text-[11px] ${k.env === "live" ? "bg-ice text-blue" : "bg-[#F2F4F7] text-navy/70"}`}>{k.env}</span></td>
                <td className="p-3 font-mono text-xs">{k.created_at.slice(0, 10)}</td>
                <td className="p-3 text-navy/70">{ago(k.last_used_at)}</td>
                <td className="p-3"><span className={`rounded-full px-3 py-1 font-mono text-xs ${k.revoked_at ? "bg-[#FDECEA] text-[#B42318]" : "bg-[#E7F7EF] text-[#067647]"}`}>{k.revoked_at ? "REVOKED" : "ACTIVE"}</span></td>
                <td className="p-3 text-right">
                  {writable && !k.revoked_at && (confirm === k.id
                    ? <span className="text-xs"><button onClick={() => void revoke(k.id)} className="font-semibold text-[#B42318] underline">Confirm</button> · <button onClick={() => setConfirm(null)} className="underline">Cancel</button></span>
                    : <button onClick={() => setConfirm(k.id)} className="text-xs text-[#B42318] underline">Revoke</button>)}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </section>

      <section className="mt-5 rounded-2xl border border-[#e3eaf8] bg-white p-5">
        <h2 className="font-display text-lg font-bold">Quick start</h2>
        <p className="mt-1 text-sm text-navy/60">Send the key as a Bearer token. Keep it secret and never expose it in client-side code.</p>
        <pre className="mt-3 overflow-x-auto rounded-xl bg-navy p-4 font-mono text-xs leading-6 text-white">{`curl ${API_URL || "https://YOUR-API"}/api/v1/organizations \\
  -H "Authorization: Bearer $FREDA_KEY"`}</pre>
      </section>
    </>
  );
}
