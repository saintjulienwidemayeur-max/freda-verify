"use client";
import qrcode from "qrcode-generator";
import { useCallback, useEffect, useMemo, useState, type FormEvent } from "react";
import { api, ApiError } from "@/lib/api";
import { can, useAuth } from "@/lib/auth";

type Member = { user_id: string; email: string; full_name: string; role: string };
const ROLES = ["owner", "admin", "member", "viewer"] as const;
const input = "mt-1.5 block w-full rounded-xl border border-[#d6e2ff] bg-white px-3 py-2.5 text-sm font-normal";
const err = (e: unknown) => (e instanceof ApiError ? e.message : "Something went wrong");

const Card = ({ title, sub, children }: { title: string; sub: string; children: React.ReactNode }) => (
  <section className="rounded-2xl border border-[#e3eaf8] bg-white p-5">
    <h2 className="font-display text-lg font-bold">{title}</h2><p className="mt-1 text-sm text-navy/60">{sub}</p>
    <div className="mt-4 space-y-4">{children}</div>
  </section>
);
const Msg = ({ ok, children }: { ok?: boolean; children: React.ReactNode }) => (
  <p role={ok ? "status" : "alert"} className={`rounded-xl border p-3 text-sm ${ok ? "border-[#b7e8cf] bg-[#E7F7EF] text-[#067647]" : "border-[#f1b8b2] bg-[#FDECEA] text-[#B42318]"}`}>{children}</p>
);

function Workspace() {
  const { org, reload } = useAuth();
  const [name, setName] = useState(org?.name ?? ""), [msg, setMsg] = useState<{ ok: boolean; t: string } | null>(null), [busy, setBusy] = useState(false);
  useEffect(() => setName(org?.name ?? ""), [org?.id, org?.name]);
  const save = async (e: FormEvent) => {
    e.preventDefault(); if (!org) return; setBusy(true); setMsg(null);
    try { await api(`/organizations/${org.id}`, { method: "PATCH", json: { name } }); await reload(); setMsg({ ok: true, t: "Saved ✓" }); } catch (x) { setMsg({ ok: false, t: err(x) }); } finally { setBusy(false); }
  };
  return (
    <Card title="Workspace" sub="The name shown in your dashboard.">
      <form onSubmit={save} className="space-y-3">
        <label className="block text-sm font-medium">Organization name<input value={name} onChange={(e) => setName(e.target.value)} maxLength={120} disabled={!can.rename(org)} className={input} /></label>
        {msg && <Msg ok={msg.ok}>{msg.t}</Msg>}
        {can.rename(org) ? <button disabled={busy || name.trim().length < 2} className="rounded-full bg-blue px-5 py-2.5 text-sm font-semibold text-white hover:bg-navy disabled:opacity-50">Save</button> : <p className="text-xs text-navy/50">Only owners and admins can rename the organization.</p>}
      </form>
    </Card>
  );
}

function Team() {
  const { org, user } = useAuth();
  const [members, setMembers] = useState<Member[] | null>(null), [msg, setMsg] = useState<{ ok: boolean; t: string } | null>(null);
  const [email, setEmail] = useState(""), [role, setRole] = useState<"admin" | "member" | "viewer">("member");
  const load = useCallback(async () => { if (org) try { setMembers(await api<Member[]>(`/organizations/${org.id}/members`)); } catch (x) { setMsg({ ok: false, t: err(x) }); } }, [org]);
  useEffect(() => { setMembers(null); void load(); }, [load]);
  const manage = can.manageMembers(org);
  const act = async (fn: () => Promise<unknown>, ok: string) => { setMsg(null); try { await fn(); setMsg({ ok: true, t: ok }); await load(); } catch (x) { setMsg({ ok: false, t: err(x) }); await load(); } };
  const add = (e: FormEvent) => { e.preventDefault(); void act(() => api(`/organizations/${org!.id}/members`, { method: "POST", json: { email, role } }), "Member added").then(() => setEmail("")); };
  return (
    <Card title="Team" sub="People who can access this organization and what they can do.">
      {msg && <Msg ok={msg.ok}>{msg.t}</Msg>}
      <ul className="divide-y divide-[#e3eaf8] text-sm">
        {members === null && <li className="py-3 text-navy/50">Loading…</li>}
        {members?.map((m) => (
          <li key={m.user_id} className="flex flex-wrap items-center gap-3 py-3">
            <span className="grid h-8 w-8 place-items-center rounded-full bg-blue/10 text-[11px] font-bold text-blue">{m.full_name.slice(0, 1).toUpperCase()}</span>
            <div className="min-w-0 flex-1"><div className="truncate font-medium">{m.full_name}{m.user_id === user?.id ? " (you)" : ""}</div><div className="truncate text-xs text-navy/50">{m.email}</div></div>
            {manage ? (
              <select value={m.role} aria-label={`Role of ${m.full_name}`} onChange={(e) => void act(() => api(`/organizations/${org!.id}/members/${m.user_id}`, { method: "PATCH", json: { role: e.target.value } }), "Role updated")} className="rounded-lg border border-[#d6e2ff] bg-white px-2 py-1.5 text-xs">
                {ROLES.map((r) => <option key={r} value={r}>{r}</option>)}
              </select>
            ) : <span className="rounded-full bg-[#F2F4F7] px-2.5 py-0.5 font-mono text-[11px]">{m.role}</span>}
            {manage && <button onClick={() => { if (window.confirm(`Remove ${m.full_name}?`)) void act(() => api(`/organizations/${org!.id}/members/${m.user_id}`, { method: "DELETE" }), "Member removed"); }} className="text-xs text-[#B42318] underline">Remove</button>}
          </li>
        ))}
      </ul>
      {manage && (
        <form onSubmit={add} className="grid gap-3 border-t border-[#e3eaf8] pt-4 sm:grid-cols-[1fr_auto_auto] sm:items-end">
          <label className="text-sm font-medium">Add a member by email<input type="email" required value={email} onChange={(e) => setEmail(e.target.value)} placeholder="colleague@company.com" className={input} /></label>
          <label className="text-sm font-medium">Role<select value={role} onChange={(e) => setRole(e.target.value as typeof role)} className={input}><option value="admin">admin</option><option value="member">member</option><option value="viewer">viewer</option></select></label>
          <button className="rounded-full bg-blue px-5 py-2.5 text-sm font-semibold text-white hover:bg-navy">Add</button>
          <p className="text-xs text-navy/50 sm:col-span-3">The person must already have a Freda Verify account (email invitations are not available yet).</p>
        </form>
      )}
    </Card>
  );
}

function Security() {
  const { user, reload } = useAuth();
  const [setup, setSetup] = useState<{ secret: string; otpauth_uri: string } | null>(null), [code, setCode] = useState(""), [codes, setCodes] = useState<string[] | null>(null);
  const [pw, setPw] = useState(""), [msg, setMsg] = useState<{ ok: boolean; t: string } | null>(null), [busy, setBusy] = useState(false);
  const qr = useMemo(() => { if (!setup) return ""; try { const q = qrcode(0, "M"); q.addData(setup.otpauth_uri); q.make(); return q.createSvgTag({ cellSize: 5, margin: 0, scalable: true }); } catch { return ""; } }, [setup]);
  const run = async (fn: () => Promise<void>) => { setBusy(true); setMsg(null); try { await fn(); } catch (x) { setMsg({ ok: false, t: err(x) }); } finally { setBusy(false); } };

  return (
    <Card title="Two-step verification" sub="Protect your account with a code from an authenticator app (Google Authenticator, Authy, 1Password…).">
      {msg && <Msg ok={msg.ok}>{msg.t}</Msg>}
      {codes && (
        <div className="rounded-xl border border-[#f1d9b6] bg-[#FEF3E2] p-4">
          <p className="text-sm font-semibold text-[#B54708]">Save these recovery codes now. Each works once and they will not be shown again.</p>
          <ul className="mt-3 grid grid-cols-2 gap-2 font-mono text-sm">{codes.map((c) => <li key={c} className="rounded-lg bg-white px-3 py-1.5">{c}</li>)}</ul>
          <button onClick={() => setCodes(null)} className="mt-3 text-xs underline">I saved them</button>
        </div>
      )}
      {user?.mfa_enabled ? (
        <form onSubmit={(e) => { e.preventDefault(); void run(async () => { await api("/auth/mfa/disable", { method: "POST", json: { password: pw, code } }); setPw(""); setCode(""); await reload(); setMsg({ ok: true, t: "Two-step verification disabled" }); }); }} className="space-y-3">
          <p className="text-sm"><span className="rounded-full bg-[#E7F7EF] px-2.5 py-0.5 font-mono text-[11px] text-[#067647]">ENABLED</span></p>
          <p className="text-xs text-navy/50">To turn it off, confirm your password and a current code.</p>
          <div className="grid gap-3 sm:grid-cols-2">
            <label className="text-sm font-medium">Password<input type="password" required value={pw} onChange={(e) => setPw(e.target.value)} autoComplete="current-password" className={input} /></label>
            <label className="text-sm font-medium">Code<input required value={code} onChange={(e) => setCode(e.target.value)} autoComplete="one-time-code" className={input} /></label>
          </div>
          <button disabled={busy} className="rounded-full border border-[#f1b8b2] px-5 py-2.5 text-sm font-semibold text-[#B42318] hover:bg-[#FDECEA] disabled:opacity-50">Disable</button>
        </form>
      ) : setup ? (
        <form onSubmit={(e) => { e.preventDefault(); void run(async () => { const r = await api<{ recovery_codes: string[] }>("/auth/mfa/enable", { method: "POST", json: { code } }); setCodes(r.recovery_codes); setSetup(null); setCode(""); await reload(); }); }} className="space-y-4">
          <div className="flex flex-wrap items-center gap-5">
            {qr && <div className="h-40 w-40 shrink-0 rounded-xl border border-[#e3eaf8] bg-white p-2" dangerouslySetInnerHTML={{ __html: qr }} role="img" aria-label="QR code to scan with your authenticator app" />}
            <div className="min-w-0 text-sm"><p>Scan the QR code, or enter this key manually:</p><code className="mt-1 block break-all rounded-lg bg-[#F6F8FC] px-3 py-2 font-mono text-xs">{setup.secret}</code></div>
          </div>
          <label className="block text-sm font-medium">Enter the 6-digit code to confirm<input required value={code} onChange={(e) => setCode(e.target.value)} inputMode="numeric" autoComplete="one-time-code" placeholder="123456" className={input} /></label>
          <div className="flex gap-3"><button disabled={busy} className="rounded-full bg-blue px-5 py-2.5 text-sm font-semibold text-white hover:bg-navy disabled:opacity-50">Enable</button><button type="button" onClick={() => setSetup(null)} className="rounded-full border border-[#d6e2ff] px-5 py-2.5 text-sm">Cancel</button></div>
        </form>
      ) : (
        <button disabled={busy} onClick={() => void run(async () => setSetup(await api("/auth/mfa/setup", { method: "POST" })))} className="rounded-full bg-blue px-5 py-2.5 text-sm font-semibold text-white hover:bg-navy disabled:opacity-50">Set up two-step verification</button>
      )}
    </Card>
  );
}

export default function Settings() {
  return (
    <div className="max-w-3xl space-y-4">
      <div><h1 className="font-display text-2xl font-extrabold tracking-tight md:text-3xl">Settings</h1><p className="mt-1 text-sm text-navy/60">Your workspace, team and account security.</p></div>
      <Workspace /><Team /><Security />
    </div>
  );
}
