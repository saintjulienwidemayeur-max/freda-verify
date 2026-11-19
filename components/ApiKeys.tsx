"use client";
import { useState } from "react";

type Env = "Live" | "Test";
type Key = { id: string; name: string; env: Env; last4: string; created: string; used: string; revoked: boolean };

const INITIAL: Key[] = [
  { id: "k1", name: "Production backend", env: "Live", last4: "a91c", created: "2026-10-02", used: "2 min ago", revoked: false },
  { id: "k2", name: "Staging", env: "Test", last4: "7d20", created: "2026-10-15", used: "3 days ago", revoked: false },
  { id: "k3", name: "Old mobile app", env: "Live", last4: "e4b8", created: "2026-08-21", used: "41 days ago", revoked: true },
];

const mask = (k: Key) => `fv_${k.env.toLowerCase()}_••••••••${k.last4}`;
const rand = () => {
  const a = new Uint8Array(16);
  crypto.getRandomValues(a);
  return Array.from(a, (b) => b.toString(16).padStart(2, "0")).join("");
};

export default function ApiKeys() {
  const [keys, setKeys] = useState<Key[]>(INITIAL);
  const [open, setOpen] = useState(false);
  const [name, setName] = useState("");
  const [env, setEnv] = useState<Env>("Test");
  const [fresh, setFresh] = useState<{ value: string; name: string } | null>(null);
  const [copied, setCopied] = useState(false);

  const create = (e: React.FormEvent) => {
    e.preventDefault();
    const secret = rand();
    const value = `fv_${env.toLowerCase()}_${secret}`;
    setKeys([{ id: secret, name: name.trim() || "Untitled key", env, last4: secret.slice(-4), created: new Date().toISOString().slice(0, 10), used: "Never", revoked: false }, ...keys]);
    setFresh({ value, name: name.trim() || "Untitled key" });
    setName(""); setOpen(false); setCopied(false);
  };
  const copy = async () => {
    try { await navigator.clipboard.writeText(fresh?.value ?? ""); setCopied(true); } catch { setCopied(false); }
  };

  return (
    <>
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <h1 className="font-display text-2xl font-extrabold tracking-tight md:text-3xl">API Keys</h1>
          <p className="mt-1 text-sm text-navy/60">Create and manage the keys your application uses to call the Freda Verify API.</p>
        </div>
        <button onClick={() => setOpen(!open)} className="rounded-full bg-blue px-5 py-2.5 text-sm font-semibold text-white hover:bg-navy">
          {open ? "Cancel" : "+ Create key"}
        </button>
      </div>

      {open && (
        <form onSubmit={create} className="mt-5 grid gap-4 rounded-2xl border border-[#e3eaf8] bg-white p-5 md:grid-cols-[1fr_auto_auto] md:items-end">
          <label className="text-sm font-medium">Key name
            <input value={name} onChange={(e) => setName(e.target.value)} placeholder="e.g. Production backend" maxLength={40}
              className="mt-1.5 block w-full rounded-xl border border-[#d6e2ff] bg-white px-3 py-2.5 text-sm font-normal" />
          </label>
          <fieldset className="text-sm font-medium"><legend className="mb-1.5">Environment</legend>
            <div className="flex gap-2">
              {(["Test", "Live"] as Env[]).map((x) => (
                <button type="button" key={x} onClick={() => setEnv(x)} aria-pressed={env === x}
                  className={`rounded-full border px-4 py-2 font-mono text-xs ${env === x ? "border-navy bg-navy text-white" : "border-[#d6e2ff]"}`}>{x}</button>
              ))}
            </div>
          </fieldset>
          <button className="rounded-full bg-blue px-5 py-2.5 text-sm font-semibold text-white hover:bg-navy">Generate</button>
        </form>
      )}

      {fresh && (
        <div className="mt-5 rounded-2xl border border-[#b7e8cf] bg-[#E7F7EF] p-5" role="status">
          <div className="text-sm font-semibold text-[#067647]">Key “{fresh.name}” created — copy it now, it won&apos;t be shown again.</div>
          <div className="mt-3 flex flex-wrap items-center gap-2">
            <code className="min-w-0 flex-1 break-all rounded-xl border border-[#b7e8cf] bg-white px-3 py-2.5 font-mono text-xs">{fresh.value}</code>
            <button onClick={copy} className="rounded-full bg-navy px-4 py-2.5 text-xs font-semibold text-white">{copied ? "Copied ✓" : "Copy"}</button>
            <button onClick={() => setFresh(null)} className="px-2 text-xs underline">Dismiss</button>
          </div>
        </div>
      )}

      <section className="mt-5 overflow-x-auto rounded-2xl border border-[#e3eaf8] bg-white" aria-label="API keys">
        <table className="w-full text-left text-sm">
          <thead className="bg-[#F6F8FC] font-mono text-[11px] text-navy/60">
            <tr>{["Name", "Key", "Env", "Created", "Last used", "Status", ""].map((h, i) => <th key={i} className="p-3 font-medium">{h}</th>)}</tr>
          </thead>
          <tbody>
            {keys.map((k) => (
              <tr key={k.id} className="border-t border-[#e3eaf8]">
                <td className="p-3 font-medium">{k.name}</td>
                <td className="p-3 font-mono text-xs text-navy/70">{mask(k)}</td>
                <td className="p-3"><span className={`rounded-full px-2.5 py-0.5 font-mono text-[11px] ${k.env === "Live" ? "bg-ice text-blue" : "bg-[#F2F4F7] text-navy/70"}`}>{k.env}</span></td>
                <td className="p-3 font-mono text-xs">{k.created}</td>
                <td className="p-3 text-navy/70">{k.used}</td>
                <td className="p-3"><span className={`rounded-full px-3 py-1 font-mono text-xs ${k.revoked ? "bg-[#FDECEA] text-[#B42318]" : "bg-[#E7F7EF] text-[#067647]"}`}>{k.revoked ? "REVOKED" : "ACTIVE"}</span></td>
                <td className="p-3 text-right">
                  {!k.revoked && <button onClick={() => setKeys(keys.map((x) => (x.id === k.id ? { ...x, revoked: true } : x)))} className="text-xs text-[#B42318] underline">Revoke</button>}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </section>

      <section className="mt-5 rounded-2xl border border-[#e3eaf8] bg-white p-5">
        <h2 className="font-display text-lg font-bold">Quick start</h2>
        <p className="mt-1 text-sm text-navy/60">Send your key in the <code className="font-mono text-xs">x-api-key</code> header. Keep it secret and never expose it in client-side code.</p>
        <pre className="mt-3 overflow-x-auto rounded-xl bg-navy p-4 font-mono text-xs leading-6 text-white">{`curl -X POST https://api.freda.dev/v1/sessions \\
  -H "x-api-key: $FREDA_KEY" \\
  -H "content-type: application/json" \\
  -d '{ "type": "kyc" }'`}</pre>
      </section>
      <p className="mt-4 text-xs text-navy/50">Demo: keys generated here exist only in this browser tab and cannot call a real API yet.</p>
    </>
  );
}
