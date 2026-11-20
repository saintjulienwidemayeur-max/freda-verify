"use client";
import { useEffect, useMemo, useRef, useState } from "react";
import { api, apiBlob, ApiError } from "@/lib/api";
import { can, useAuth } from "@/lib/auth";
import HostedPreview, { T, type Cfg, type DocKey, type Step } from "./HostedPreview";

const DEFAULT: Cfg = {
  name: "", logo: null, color: "#1E4FE0", theme: "light", shape: "rounded", lang: "en",
  title: "", subtitle: "", docs: { id: true, passport: true, license: false }, domain: "", redirect: "", support: "", hidePowered: false,
};
const PRESETS = ["#1E4FE0", "#0A1647", "#12B76A", "#7A3FF2", "#E5484D", "#F79009"];
const isHex = (v: string) => /^#[0-9a-fA-F]{6}$/.test(v);
const isHost = (v: string) => /^(?=.{4,253}$)([a-z0-9]([a-z0-9-]{0,61}[a-z0-9])?\.)+[a-z]{2,}$/i.test(v);
const isUrl = (v: string) => { try { const u = new URL(v); return u.protocol === "https:"; } catch { return false; } };
const isMail = (v: string) => /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(v);

type Server = { name: string; color: string; theme: Cfg["theme"]; shape: Cfg["shape"]; lang: Cfg["lang"]; title: string; subtitle: string; support_email: string; docs: DocKey[]; redirect_url: string; domain: string; hide_powered: boolean; has_logo?: boolean };
const fromServer = (s: Server, logo: string | null): Cfg => ({
  name: s.name, logo, color: s.color.toUpperCase(), theme: s.theme, shape: s.shape, lang: s.lang, title: s.title, subtitle: s.subtitle,
  docs: { id: s.docs.includes("id"), passport: s.docs.includes("passport"), license: s.docs.includes("license") }, domain: s.domain, redirect: s.redirect_url, support: s.support_email, hidePowered: s.hide_powered,
});
const toServer = (c: Cfg): Server => ({
  name: c.name.trim(), color: c.color, theme: c.theme, shape: c.shape, lang: c.lang, title: c.title.trim(), subtitle: c.subtitle.trim(), support_email: c.support.trim(),
  docs: (["id", "passport", "license"] as DocKey[]).filter((k) => c.docs[k]), redirect_url: c.redirect.trim(), domain: c.domain.trim().toLowerCase(), hide_powered: c.hidePowered,
});

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
  const { org } = useAuth();
  const [saved, setSaved] = useState(false);
  const [loading, setLoading] = useState(true), [busy, setBusy] = useState(false), [srvErr, setSrvErr] = useState("");
  const writable = can.editBranding(org);
  const [logoErr, setLogoErr] = useState(""), [logoBusy, setLogoBusy] = useState(false);
  const [hex, setHex] = useState(DEFAULT.color);
  const urlRef = useRef<string | null>(null);
  // load the saved settings of the organization (the logo is not stored yet, so it stays empty after a reload)
  useEffect(() => {
    if (!org) return;
    let live = true; setLoading(true); setSrvErr("");
    api<Server>(`/organizations/${org.id}/branding`)
      .then(async (s) => {
        let logo: string | null = null;
        if (s.has_logo) { try { const b = await apiBlob(`/organizations/${org.id}/branding/logo`); if (b) logo = URL.createObjectURL(b); } catch { /* shown without logo */ } }
        if (!live) { if (logo) URL.revokeObjectURL(logo); return; }
        if (urlRef.current) URL.revokeObjectURL(urlRef.current);
        urlRef.current = logo;
        const n = fromServer(s, logo); setC(n); setHex(n.color); setSaved(false);
      })
      .catch((e) => { if (live) setSrvErr(e instanceof ApiError ? e.message : "Could not load your settings"); })
      .finally(() => { if (live) setLoading(false); });
    return () => { live = false; };
  }, [org?.id]); // eslint-disable-line react-hooks/exhaustive-deps
  useEffect(() => () => { if (urlRef.current) URL.revokeObjectURL(urlRef.current); }, []);

  const set = <K extends keyof Cfg>(k: K, v: Cfg[K]) => { setC((p) => ({ ...p, [k]: v })); setSaved(false); };
  const err = useMemo(() => ({
    domain: c.domain && !isHost(c.domain) ? "Enter a valid hostname, e.g. verify.yourcompany.com" : "",
    redirect: c.redirect && !isUrl(c.redirect) ? "Must be a valid https:// URL" : "",
    support: c.support && !isMail(c.support) ? "Enter a valid email address" : "",
    docs: Object.values(c.docs).some(Boolean) ? "" : "Enable at least one document type",
  }), [c]);
  const invalid = Object.values(err).some(Boolean);
  const pageUrl = useMemo(() => {
    const q = new URLSearchParams({ color: c.color.replace("#", ""), theme: c.theme, shape: c.shape, lang: c.lang,
      docs: (["id", "passport", "license"] as DocKey[]).filter((k) => c.docs[k]).join(",") });
    if (c.name.trim()) q.set("name", c.name.trim());
    if (c.title.trim()) q.set("title", c.title.trim());
    if (c.subtitle.trim()) q.set("subtitle", c.subtitle.trim());
    if (isMail(c.support)) q.set("support", c.support);
    return `/verify?${q.toString()}`;
  }, [c]);

  const onLogo = (f: File | undefined) => {
    setLogoErr(""); if (!f || !org) return;
    if (!writable) return setLogoErr("Your role cannot change the logo.");
    if (!["image/png", "image/jpeg", "image/webp"].includes(f.type)) return setLogoErr("Use a PNG, JPG or WebP image (SVG is not accepted).");
    if (f.size > 512 * 1024) return setLogoErr("Logo must be under 512 KB.");
    setLogoBusy(true);
    api(`/organizations/${org.id}/branding/logo`, { method: "PUT", blob: f })
      .then(() => { if (urlRef.current) URL.revokeObjectURL(urlRef.current); urlRef.current = URL.createObjectURL(f); setC((p) => ({ ...p, logo: urlRef.current })); })
      .catch((er) => setLogoErr(er instanceof ApiError ? er.message : "Could not upload the logo"))
      .finally(() => setLogoBusy(false));
  };
  const removeLogo = () => {
    if (!org) return;
    setLogoBusy(true); setLogoErr("");
    api(`/organizations/${org.id}/branding/logo`, { method: "DELETE" })
      .then(() => { if (urlRef.current) { URL.revokeObjectURL(urlRef.current); urlRef.current = null; } setC((p) => ({ ...p, logo: null })); })
      .catch((er) => setLogoErr(er instanceof ApiError ? er.message : "Could not remove the logo"))
      .finally(() => setLogoBusy(false));
  };
  const color = (v: string) => { setHex(v); if (isHex(v)) set("color", v.toUpperCase()); };
  const reset = () => { setC({ ...DEFAULT, logo: c.logo }); setHex(DEFAULT.color); setLogoErr(""); setSaved(false); };

  return (
    <>
      <h1 className="font-display text-2xl font-extrabold tracking-tight md:text-3xl">White label</h1>
      <p className="mt-1 text-sm text-navy/60">Make the verification page look like your own brand before you send it to your customers.</p>

      <div className="mt-6 grid items-start gap-6 min-[960px]:grid-cols-[322px_1fr]">
        <form onSubmit={(e) => {
          e.preventDefault();
          if (invalid || !org || !writable) return;
          setBusy(true); setSrvErr(""); setSaved(false);
          api<Server>(`/organizations/${org.id}/branding`, { method: "PUT", json: toServer(c) })
            .then(() => setSaved(true))
            .catch((er) => setSrvErr(er instanceof ApiError ? (er.details[0] ? `${er.details[0].field}: ${er.details[0].message}` : er.message) : "Could not save"))
            .finally(() => setBusy(false));
        }} className="min-w-0 space-y-4">
          <Card title="Brand" sub="Shown at the top of the verification page.">
            <label className="block text-sm font-medium">Brand name<input value={c.name} maxLength={40} onChange={(e) => set("name", e.target.value)} placeholder="Freda Verify (default)" className={input} />
              <span className="mt-1 block text-xs font-normal text-navy/50">Leave empty to use the Freda Verify name and logo.</span></label>
            <div className="text-sm font-medium">Logo
              <div className="mt-1.5 flex flex-wrap items-center gap-3">
                <span className="grid h-14 w-28 place-items-center overflow-hidden rounded-xl border border-[#d6e2ff] bg-[#F6F8FC]">
                  {/* eslint-disable-next-line @next/next/no-img-element */}
                  {c.logo ? <img src={c.logo} alt="Logo preview" className="max-h-12 max-w-24 object-contain" /> : c.name.trim() ? <span className="text-xs font-normal text-navy/40">No logo</span> : <img src="/logo-mark.svg" alt="Freda Verify default logo" className="h-10 w-10" />}
                </span>
                <label className="cursor-pointer rounded-full border border-[#d6e2ff] px-4 py-2 text-sm font-normal hover:bg-ice">Upload logo
                  <input type="file" accept="image/png,image/jpeg,image/webp" disabled={logoBusy || !writable} className="sr-only" onChange={(e) => { onLogo(e.target.files?.[0]); e.target.value = ""; }} /></label>
                {c.logo && <button type="button" disabled={logoBusy || !writable} onClick={removeLogo} className="text-xs underline disabled:opacity-50">Remove</button>}
                {logoBusy && <span className="text-xs text-navy/50">Saving…</span>}
              </div>
              {logoErr && <p role="alert" className="mt-1 text-xs font-normal text-[#B42318]">{logoErr}</p>}
              <p className="mt-1 text-xs font-normal text-navy/50">PNG, JPG or WebP · max 512 KB · saved as soon as you upload it.</p>
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
            <label className="block text-sm font-medium">Welcome title<input value={c.title} maxLength={60} onChange={(e) => set("title", e.target.value)} placeholder={`${T[c.lang].titleFor} ${c.name.trim() || "Freda Verify"}`} className={input} /></label>
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
                <p className="mt-2 text-xs text-navy/50">The domain is saved, but verification and certificates are not active yet. The target value above is an example.</p>
              </div>
            )}
          </Card>

          <Card title="Branding on the page">
            <div className="flex items-center justify-between gap-4 text-sm"><span>Hide “Powered by Freda Verify”<span className="block text-xs text-navy/50">May depend on your plan.</span></span><Toggle on={c.hidePowered} set={(v) => set("hidePowered", v)} label="Hide Powered by Freda Verify" /></div>
          </Card>

          <div className="flex flex-wrap items-center gap-3">
            <button disabled={invalid || !isHex(hex) || busy || loading || !writable} className="rounded-full bg-blue px-6 py-2.5 text-sm font-semibold text-white hover:bg-navy disabled:opacity-50">{busy ? "Saving…" : "Save changes"}</button>
            <button type="button" onClick={reset} className="rounded-full border border-[#d6e2ff] px-5 py-2.5 text-sm">Reset to defaults</button>
            {saved && <span role="status" className="text-sm font-medium text-[#067647]">Saved ✓</span>}
          </div>
          {srvErr && <p role="alert" className="rounded-xl border border-[#f1b8b2] bg-[#FDECEA] p-3 text-sm text-[#B42318]">{srvErr}</p>}
          {!writable && <p className="text-xs text-navy/60">Your role can view these settings but not change them.</p>}
          <p className="text-xs text-navy/50">Settings are saved to your workspace. Not active yet: custom-domain verification and the redirect URL. The logo is saved with your workspace but is not served to your customers yet. The hosted page does not read these saved settings yet; the “Open the live page” link passes them in the URL.</p>
        </form>

        <aside className="min-[960px]:sticky min-[960px]:top-4 min-[960px]:order-first" aria-label="Live preview">
          <div className="rounded-2xl border border-[#e3eaf8] bg-white p-4">
            <div className="mb-4 flex items-center justify-between"><h2 className="font-display text-lg font-bold">Live preview</h2><span className="font-mono text-[10px] uppercase tracking-widest text-navy/50">Hosted page</span></div>
            <a href={pageUrl} target="_blank" rel="noopener" className="mb-4 flex items-center justify-center gap-1.5 rounded-full border border-[#d6e2ff] py-2 text-sm font-semibold text-blue hover:bg-ice">Open the live page ↗</a>
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
