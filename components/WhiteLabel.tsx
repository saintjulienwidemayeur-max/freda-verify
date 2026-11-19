"use client";
import { useEffect, useMemo, useRef, useState } from "react";
import HostedPreview, { T, type Cfg, type DocKey, type Step } from "./HostedPreview";

const DEFAULT: Cfg = {
  name: "Your Company", logo: null, color: "#1E4FE0", theme: "light", shape: "rounded", lang: "en",
  title: "", subtitle: "", docs: { id: true, passport: true, license: false }, domain: "", redirect: "", support: "", hidePowered: false,
};
const PRESETS = ["#1E4FE0", "#0A1647", "#12B76A", "#7A3FF2", "#E5484D", "#F79009"];
const isHex = (v: string) => /^#[0-9a-fA-F]{6}$/.test(v);
const isHost = (v: string) => /^(?=.{4,253}$)([a-z0-9]([a-z0-9-]{0,61}[a-z0-9])?\.)+[a-z]{2,}$/i.test(v);
const isUrl = (v: string) => { try { const u = new URL(v); return u.protocol === "https:"; } catch { return false; } };
const isMail = (v: string) => /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(v);

const Card = ({ title, sub, children }: { title: string; sub?: string; children: React.ReactNode }) => (
  <section className="rounded-2xl border border-[#e3eaf8] bg-white p-5">
    <h2 className="font-display text-lg font-bold">{title}</h2>{sub && <p className="mt-1 text-sm text-navy/60">{sub}</p>}
    <div className="mt-4 space-y-4">{children}</div>
  </section>
);
const input = "mt-1.5 block w-full rounded-xl border border-[#d6e2ff] bg-white px-3 py-2.5 text-sm font-normal";
const Seg = <V extends string>({ value, set, opts, label }: { value: V; set: (v: V) => void; opts: [V, string][]; label: string }) => (
  <div role="group" aria-label={label} className="flex flex-wrap gap-2">
    {opts.map(([k, l]) => (
      <button type="button" key={k} onClick={() => set(k)} aria-pressed={value === k} className={`rounded-full border px-4 py-1.5 text-sm ${value === k ? "border-navy bg-navy text-white" : "border-[#d6e2ff]"}`}>{l}</button>
    ))}
  </div>
);
const Toggle = ({ on, set, label }: { on: boolean; set: (v: boolean) => void; label: string }) => (
  <button type="button" role="switch" aria-checked={on} aria-label={label} onClick={() => set(!on)} className={`relative h-6 w-11 shrink-0 rounded-full transition-colors ${on ? "bg-blue" : "bg-[#d6e2ff]"}`}>
    <span className={`absolute top-0.5 h-5 w-5 rounded-full bg-white shadow transition-all ${on ? "left-[22px]" : "left-0.5"}`} />
  </button>
);

export default function WhiteLabel() {
  const [c, setC] = useState<Cfg>(DEFAULT);
  const [step, setStep] = useState<Step>("welcome");
  const [saved, setSaved] = useState(false);
  const [logoErr, setLogoErr] = useState("");
  const [hex, setHex] = useState(DEFAULT.color);
  const urlRef = useRef<string | null>(null);
  useEffect(() => () => { if (urlRef.current) URL.revokeObjectURL(urlRef.current); }, []);

  const set = <K extends keyof Cfg>(k: K, v: Cfg[K]) => { setC((p) => ({ ...p, [k]: v })); setSaved(false); };
  const err = useMemo(() => ({
    domain: c.domain && !isHost(c.domain) ? "Enter a valid hostname, e.g. verify.yourcompany.com" : "",
    redirect: c.redirect && !isUrl(c.redirect) ? "Must be a valid https:// URL" : "",
    support: c.support && !isMail(c.support) ? "Enter a valid email address" : "",
    docs: Object.values(c.docs).some(Boolean) ? "" : "Enable at least one document type",
  }), [c]);
  const invalid = Object.values(err).some(Boolean);

  const onLogo = (f: File | undefined) => {
    setLogoErr(""); if (!f) return;
    if (!["image/png", "image/jpeg", "image/svg+xml", "image/webp"].includes(f.type)) return setLogoErr("Use a PNG, JPG, SVG or WebP image.");
    if (f.size > 1024 * 1024) return setLogoErr("Logo must be under 1 MB.");
    if (urlRef.current) URL.revokeObjectURL(urlRef.current);
    urlRef.current = URL.createObjectURL(f); set("logo", urlRef.current);
  };
  const color = (v: string) => { setHex(v); if (isHex(v)) set("color", v.toUpperCase()); };
  const reset = () => { if (urlRef.current) { URL.revokeObjectURL(urlRef.current); urlRef.current = null; } setC(DEFAULT); setHex(DEFAULT.color); setLogoErr(""); setSaved(false); };

  return (
    <>
      <h1 className="font-display text-2xl font-extrabold tracking-tight md:text-3xl">White label</h1>
      <p className="mt-1 text-sm text-navy/60">Make the verification page look like your own brand before you send it to your customers.</p>

      <div className="mt-6 grid items-start gap-6 min-[960px]:grid-cols-[322px_1fr]">
        <form onSubmit={(e) => { e.preventDefault(); if (!invalid) setSaved(true); }} className="min-w-0 space-y-4">
          <Card title="Brand" sub="Shown at the top of the verification page.">
            <label className="block text-sm font-medium">Brand name<input value={c.name} maxLength={40} onChange={(e) => set("name", e.target.value)} className={input} /></label>
            <div className="text-sm font-medium">Logo
              <div className="mt-1.5 flex flex-wrap items-center gap-3">
                <span className="grid h-14 w-28 place-items-center overflow-hidden rounded-xl border border-[#d6e2ff] bg-[#F6F8FC]">
                  {/* eslint-disable-next-line @next/next/no-img-element */}
                  {c.logo ? <img src={c.logo} alt="Logo preview" className="max-h-12 max-w-24 object-contain" /> : <span className="text-xs font-normal text-navy/40">No logo</span>}
                </span>
                <label className="cursor-pointer rounded-full border border-[#d6e2ff] px-4 py-2 text-sm font-normal hover:bg-ice">Upload logo
                  <input type="file" accept="image/png,image/jpeg,image/svg+xml,image/webp" className="sr-only" onChange={(e) => onLogo(e.target.files?.[0])} /></label>
                {c.logo && <button type="button" onClick={() => set("logo", null)} className="text-xs underline">Remove</button>}
              </div>
              {logoErr && <p role="alert" className="mt-1 text-xs font-normal text-[#B42318]">{logoErr}</p>}
              <p className="mt-1 text-xs font-normal text-navy/50">PNG, JPG, SVG or WebP · max 1 MB.</p>
            </div>
          </Card>

          <Card title="Appearance" sub="Colors and style of the buttons and the page.">
            <div className="text-sm font-medium">Primary color
              <div className="mt-1.5 flex flex-wrap items-center gap-2">
                {PRESETS.map((p) => (
                  <button type="button" key={p} aria-label={`Use ${p}`} aria-pressed={c.color === p} onClick={() => color(p)}
                    className={`h-8 w-8 rounded-full border-2 ${c.color === p ? "border-navy" : "border-white shadow ring-1 ring-[#d6e2ff]"}`} style={{ background: p }} />
                ))}
                <input type="color" aria-label="Pick a color" value={c.color} onChange={(e) => color(e.target.value)} className="h-8 w-10 cursor-pointer rounded border border-[#d6e2ff] bg-white" />
                <input value={hex} onChange={(e) => color(e.target.value)} aria-label="Hex color" maxLength={7} className="w-28 rounded-xl border border-[#d6e2ff] px-3 py-1.5 font-mono text-xs font-normal" />
              </div>
              {!isHex(hex) && <p role="alert" className="mt-1 text-xs font-normal text-[#B42318]">Use a hex color like #1E4FE0.</p>}
            </div>
            <div className="text-sm font-medium">Theme<div className="mt-1.5"><Seg label="Theme" value={c.theme} set={(v) => set("theme", v)} opts={[["light", "Light"], ["dark", "Dark"]]} /></div></div>
            <div className="text-sm font-medium">Button shape<div className="mt-1.5"><Seg label="Button shape" value={c.shape} set={(v) => set("shape", v)} opts={[["square", "Square"], ["rounded", "Rounded"], ["pill", "Pill"]]} /></div></div>
          </Card>

          <Card title="Content" sub="Language and the welcome message. Leave blank to use the default text.">
            <div className="text-sm font-medium">Language<div className="mt-1.5"><Seg label="Language" value={c.lang} set={(v) => set("lang", v)} opts={[["en", "English"], ["fr", "Français"], ["ht", "Kreyòl"]]} /></div></div>
            <label className="block text-sm font-medium">Welcome title<input value={c.title} maxLength={60} onChange={(e) => set("title", e.target.value)} placeholder={`${T[c.lang].titleFor} ${c.name.trim() || "Your Company"}`} className={input} /></label>
            <label className="block text-sm font-medium">Welcome message<textarea value={c.subtitle} maxLength={140} rows={2} onChange={(e) => set("subtitle", e.target.value)} placeholder={T[c.lang].sub} className={input} /></label>
            <label className="block text-sm font-medium">Support email shown to your customers<input type="email" value={c.support} onChange={(e) => set("support", e.target.value)} placeholder="support@yourcompany.com" className={input} />
              {err.support && <span role="alert" className="mt-1 block text-xs font-normal text-[#B42318]">{err.support}</span>}</label>
          </Card>

          <Card title="Verification flow" sub="Which documents your customers can use.">
            {(["id", "passport", "license"] as DocKey[]).map((k) => (
              <div key={k} className="flex items-center justify-between gap-4 text-sm"><span>{T.en[k]}</span><Toggle on={c.docs[k]} set={(v) => set("docs", { ...c.docs, [k]: v })} label={T.en[k]} /></div>
            ))}
            {err.docs && <p role="alert" className="text-xs text-[#B42318]">{err.docs}</p>}
            <label className="block text-sm font-medium">Redirect after completion<input type="url" value={c.redirect} onChange={(e) => set("redirect", e.target.value)} placeholder="https://yourcompany.com/verified" className={input} />
              {err.redirect && <span role="alert" className="mt-1 block text-xs font-normal text-[#B42318]">{err.redirect}</span>}</label>
          </Card>

          <Card title="Custom domain" sub="Serve the verification page from your own domain.">
            <label className="block text-sm font-medium">Domain<input value={c.domain} onChange={(e) => set("domain", e.target.value.trim().toLowerCase())} placeholder="verify.yourcompany.com" className={`${input} font-mono`} />
              {err.domain && <span role="alert" className="mt-1 block text-xs font-normal text-[#B42318]">{err.domain}</span>}</label>
            {c.domain && !err.domain && (
              <div className="rounded-xl border border-[#e3eaf8] bg-[#F6F8FC] p-4 text-sm">
                <div className="flex items-center justify-between"><span className="font-semibold">DNS record</span><span className="rounded-full bg-[#FEF3E2] px-2.5 py-0.5 font-mono text-[11px] text-[#B54708]">NOT CONNECTED</span></div>
                <dl className="mt-2 grid grid-cols-[70px_1fr] gap-y-1 font-mono text-xs"><dt className="text-navy/55">Type</dt><dd>CNAME</dd><dt className="text-navy/55">Name</dt><dd className="break-all">{c.domain}</dd><dt className="text-navy/55">Value</dt><dd>custom.freda-verify.example</dd></dl>
                <p className="mt-2 text-xs text-navy/50">Demo: domain verification and certificates are not active yet. The target value above is an example.</p>
              </div>
            )}
          </Card>

          <Card title="Branding on the page">
            <div className="flex items-center justify-between gap-4 text-sm"><span>Hide “Powered by Freda Verify”<span className="block text-xs text-navy/50">May depend on your plan.</span></span><Toggle on={c.hidePowered} set={(v) => set("hidePowered", v)} label="Hide Powered by Freda Verify" /></div>
          </Card>

          <div className="flex flex-wrap items-center gap-3">
            <button disabled={invalid || !isHex(hex)} className="rounded-full bg-blue px-6 py-2.5 text-sm font-semibold text-white hover:bg-navy disabled:opacity-50">Save changes</button>
            <button type="button" onClick={reset} className="rounded-full border border-[#d6e2ff] px-5 py-2.5 text-sm">Reset to defaults</button>
            {saved && <span role="status" className="text-sm font-medium text-[#067647]">Saved ✓</span>}
          </div>
          <p className="text-xs text-navy/50">Demo: settings live in this browser tab only and are not stored yet.</p>
        </form>

        <aside className="min-[960px]:sticky min-[960px]:top-4 min-[960px]:order-first" aria-label="Live preview">
          <div className="rounded-2xl border border-[#e3eaf8] bg-white p-4">
            <div className="mb-4 flex items-center justify-between"><h2 className="font-display text-lg font-bold">Live preview</h2><span className="font-mono text-[10px] uppercase tracking-widest text-navy/50">Hosted page</span></div>
            <div className="mb-4 flex flex-wrap justify-center gap-1.5" role="tablist" aria-label="Preview step">
              {([["welcome", "Welcome"], ["country", "Country"], ["document", "Document"], ["selfie", "Selfie"], ["done", "Done"]] as [Step, string][]).map(([k, l]) => (
                <button key={k} role="tab" aria-selected={step === k} onClick={() => setStep(k)} className={`rounded-full px-3 py-1 text-xs ${step === k ? "bg-navy text-white" : "border border-[#d6e2ff]"}`}>{l}</button>
              ))}
            </div>
            <HostedPreview c={c} step={step} go={setStep} setLang={(l) => set("lang", l)} />
          </div>
        </aside>
      </div>
    </>
  );
}
