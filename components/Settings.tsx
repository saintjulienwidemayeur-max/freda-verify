"use client";
import { useState } from "react";

const Toggle = ({ on, set, label }: { on: boolean; set: (v: boolean) => void; label: string }) => (
  <button type="button" role="switch" aria-checked={on} aria-label={label} onClick={() => set(!on)}
    className={`relative h-6 w-11 shrink-0 rounded-full transition-colors ${on ? "bg-blue" : "bg-[#d6e2ff]"}`}>
    <span className={`absolute top-0.5 h-5 w-5 rounded-full bg-white shadow transition-all ${on ? "left-[22px]" : "left-0.5"}`} />
  </button>
);
const Card = ({ title, sub, children }: { title: string; sub: string; children: React.ReactNode }) => (
  <section className="rounded-2xl border border-[#e3eaf8] bg-white p-5">
    <h2 className="font-display text-lg font-bold">{title}</h2><p className="mt-1 text-sm text-navy/60">{sub}</p>
    <div className="mt-4 space-y-4">{children}</div>
  </section>
);
const input = "mt-1.5 block w-full rounded-xl border border-[#d6e2ff] bg-white px-3 py-2.5 text-sm font-normal";

export default function Settings() {
  const [name, setName] = useState("Demo workspace");
  const [lang, setLang] = useState("fr");
  const [hook, setHook] = useState("");
  const [n, setN] = useState({ approved: true, rejected: true, review: true, weekly: false });
  const [saved, setSaved] = useState(false);
  const mark = () => setSaved(false);

  return (
    <form onSubmit={(e) => { e.preventDefault(); setSaved(true); }} className="max-w-3xl space-y-4">
      <div>
        <h1 className="font-display text-2xl font-extrabold tracking-tight md:text-3xl">Settings</h1>
        <p className="mt-1 text-sm text-navy/60">Manage your workspace, webhooks and notifications.</p>
      </div>

      <Card title="Workspace" sub="How your workspace appears in the dashboard.">
        <label className="block text-sm font-medium">Workspace name<input value={name} onChange={(e) => { setName(e.target.value); mark(); }} maxLength={40} className={input} /></label>
        <label className="block text-sm font-medium">Language
          <select value={lang} onChange={(e) => { setLang(e.target.value); mark(); }} className={input}>
            <option value="fr">Français</option><option value="en">English</option><option value="ht">Kreyòl ayisyen</option>
          </select>
        </label>
      </Card>

      <Card title="Webhook" sub="We send a POST request to this URL when a verification is completed.">
        <label className="block text-sm font-medium">Endpoint URL
          <input type="url" value={hook} onChange={(e) => { setHook(e.target.value); mark(); }} placeholder="https://votre-app.com/webhook" className={input} />
        </label>
      </Card>

      <Card title="Notifications" sub="Choose which events you want to be notified about.">
        {([["approved", "Verification approved"], ["rejected", "Verification rejected"], ["review", "Manual review needed"], ["weekly", "Weekly summary"]] as const).map(([k, l]) => (
          <div key={k} className="flex items-center justify-between gap-4 text-sm"><span>{l}</span><Toggle on={n[k]} set={(v) => { setN({ ...n, [k]: v }); mark(); }} label={l} /></div>
        ))}
      </Card>

      <div className="flex items-center gap-4">
        <button className="rounded-full bg-blue px-6 py-2.5 text-sm font-semibold text-white hover:bg-navy">Save changes</button>
        {saved && <span role="status" className="text-sm font-medium text-[#067647]">Saved ✓</span>}
      </div>
      <p className="text-xs text-navy/50">Demo: settings are kept in this browser tab only and are not stored yet.</p>
    </form>
  );
}
