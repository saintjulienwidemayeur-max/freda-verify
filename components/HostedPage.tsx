"use client";
import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { COUNTRIES, DOC_ICON, Ic, LANGS, RADIUS, T, flag, fold, isMail, onColor, termsLabel } from "./HostedPreview";
import type { Cfg, DocKey, Lang, Shape, Theme } from "./HostedPreview";

/* ───────────── config from URL (demo): every value is validated, text is rendered as text ───────────── */
const DEFAULTS: Cfg = {
  name: "Your Company", logo: null, color: "#1E4FE0", theme: "light", shape: "rounded", lang: "en",
  title: "", subtitle: "", docs: { id: true, passport: true, license: false }, domain: "", redirect: "", support: "", hidePowered: false,
};
const clean = (v: string | null, max: number) => (v ?? "").replace(/[\u0000-\u001f<>]/g, "").trim().slice(0, max);
function readConfig(search: string): Cfg {
  const q = new URLSearchParams(search);
  const color = q.get("color") ?? "";
  const docsParam = q.get("docs");
  const docs: Record<DocKey, boolean> = { id: false, passport: false, license: false };
  (docsParam ?? "id,passport").split(",").forEach((d) => { if (d === "id" || d === "passport" || d === "license") docs[d] = true; });
  if (!Object.values(docs).some(Boolean)) docs.id = true;
  const lang = q.get("lang"), theme = q.get("theme"), shape = q.get("shape");
  const support = clean(q.get("support"), 80);
  return {
    ...DEFAULTS,
    name: clean(q.get("name"), 40) || DEFAULTS.name,
    color: /^#?[0-9a-fA-F]{6}$/.test(color) ? `#${color.replace("#", "").toUpperCase()}` : DEFAULTS.color,
    theme: (theme === "dark" ? "dark" : "light") as Theme,
    shape: (["square", "rounded", "pill"].includes(shape ?? "") ? shape : "rounded") as Shape,
    lang: (LANGS as string[]).includes(lang ?? "") ? (lang as Lang) : "en",
    title: clean(q.get("title"), 60), subtitle: clean(q.get("subtitle"), 140),
    docs, support: isMail(support) ? support : "", hidePowered: false,
  };
}

/* ───────────── local image quality check (runs only in the browser) ───────────── */
type Quality = { dark: boolean; bright: boolean; blur: boolean };
async function analyze(blob: Blob): Promise<Quality> {
  try {
    const bmp = await createImageBitmap(blob);
    const w = 256, h = Math.max(8, Math.round((bmp.height * w) / bmp.width));
    const cv = document.createElement("canvas"); cv.width = w; cv.height = h;
    const ctx = cv.getContext("2d", { willReadFrequently: true })!; ctx.drawImage(bmp, 0, 0, w, h); bmp.close?.();
    const d = ctx.getImageData(0, 0, w, h).data, g = new Float32Array(w * h);
    let sum = 0, hot = 0;
    for (let i = 0; i < w * h; i++) { const v = 0.299 * d[i * 4] + 0.587 * d[i * 4 + 1] + 0.114 * d[i * 4 + 2]; g[i] = v; sum += v; if (v > 250) hot++; }
    const mean = sum / (w * h);
    let m = 0, m2 = 0, n = 0;
    for (let y = 1; y < h - 1; y++) for (let x = 1; x < w - 1; x++) {
      const i = y * w + x, l = 4 * g[i] - g[i - 1] - g[i + 1] - g[i - w] - g[i + w];
      m += l; m2 += l * l; n++;
    }
    const variance = m2 / n - (m / n) ** 2;
    return { dark: mean < 55, bright: mean > 225 || hot / (w * h) > 0.18, blur: variance < QUALITY_BLUR };
  } catch { return { dark: false, bright: false, blur: false }; }
}
const QUALITY_BLUR = 30;
const issues = (q: Quality, t: typeof T.en) => [q.dark && t.qDark, q.bright && t.qBright, q.blur && t.qBlur].filter(Boolean) as string[];

type Shot = { url: string; q: Quality };
type PStep = "welcome" | "country" | "document" | "front" | "back" | "selfie" | "review" | "done";

/* ───────────── live camera ───────────── */
function Camera({ facing, onShot, onClose, label, cancel, denied, accent, accentFg, radius }: {
  facing: "user" | "environment"; onShot: (b: Blob) => void; onClose: () => void; label: string; cancel: string; denied: string; accent: string; accentFg: string; radius: number;
}) {
  const ref = useRef<HTMLVideoElement>(null);
  const [err, setErr] = useState(false);
  useEffect(() => {
    let stream: MediaStream | null = null, dead = false;
    (async () => {
      try {
        stream = await navigator.mediaDevices.getUserMedia({ video: { facingMode: facing, width: { ideal: 1280 } }, audio: false });
        if (dead) { stream.getTracks().forEach((t) => t.stop()); return; }
        if (ref.current) { ref.current.srcObject = stream; await ref.current.play().catch(() => {}); }
      } catch { setErr(true); }
    })();
    return () => { dead = true; stream?.getTracks().forEach((t) => t.stop()); };
  }, [facing]);
  const snap = () => {
    const v = ref.current; if (!v || !v.videoWidth) return;
    const cv = document.createElement("canvas"); cv.width = v.videoWidth; cv.height = v.videoHeight;
    cv.getContext("2d")!.drawImage(v, 0, 0);
    cv.toBlob((b) => b && onShot(b), "image/jpeg", 0.88);
  };
  if (err) return (
    <div className="grid flex-1 place-items-center rounded-2xl bg-black/5 p-6 text-center text-sm" role="alert">
      <div>{denied}<button type="button" onClick={onClose} className="mt-4 block w-full rounded-full border px-4 py-2 text-sm font-semibold">{cancel}</button></div>
    </div>
  );
  return (
    <div className="flex flex-1 flex-col gap-3">
      <div className="relative flex-1 overflow-hidden rounded-2xl bg-black">
        <video ref={ref} playsInline muted autoPlay className={`absolute inset-0 h-full w-full object-cover ${facing === "user" ? "[transform:scaleX(-1)]" : ""}`} />
        {facing === "user"
          ? <span className="pointer-events-none absolute left-1/2 top-1/2 h-[62%] w-[56%] -translate-x-1/2 -translate-y-1/2 rounded-[50%] border-[3px] border-white/90 shadow-[0_0_0_999px_rgba(0,0,0,.45)]" />
          : <span className="pointer-events-none absolute left-1/2 top-1/2 aspect-[1.586] w-[86%] -translate-x-1/2 -translate-y-1/2 rounded-2xl border-[3px] border-white/90 shadow-[0_0_0_999px_rgba(0,0,0,.45)]" />}
      </div>
      <div className="flex gap-3">
        <button type="button" onClick={onClose} className="rounded-full border px-5 py-3 text-sm font-semibold" style={{ borderRadius: radius }}>{cancel}</button>
        <button type="button" onClick={snap} className="flex-1 py-3 text-sm font-semibold" style={{ background: accent, color: accentFg, borderRadius: radius }}>{label}</button>
      </div>
    </div>
  );
}

export default function HostedPage() {
  const [c, setC] = useState<Cfg>(DEFAULTS);
  const [ready, setReady] = useState(false);
  const [step, setStep] = useState<PStep>("welcome");
  const [country, setCountry] = useState("HT");
  const [q, setQ] = useState("");
  const [kind, setKind] = useState<DocKey | null>(null);
  const [shots, setShots] = useState<{ front?: Shot; back?: Shot; selfie?: Shot }>({});
  const [cam, setCam] = useState(false);
  const [busy, setBusy] = useState(false);
  const [agree, setAgree] = useState(false);
  const [langOpen, setLangOpen] = useState(false);
  const urls = useRef<Set<string>>(new Set());

  useEffect(() => { setC(readConfig(window.location.search)); setReady(true); }, []);
  useEffect(() => () => { urls.current.forEach((u) => URL.revokeObjectURL(u)); urls.current.clear(); }, []);
  useEffect(() => { document.documentElement.lang = c.lang; }, [c.lang]);

  const t = T[c.lang];
  const dark = c.theme === "dark", fg = onColor(c.color), r = RADIUS[c.shape], card = Math.min(r, 16);
  const bg = dark ? "#0A1647" : "#FFFFFF", tx = dark ? "#FFFFFF" : "#0A1647";
  const mut = dark ? "rgba(255,255,255,.65)" : "rgba(10,22,71,.58)", line = dark ? "rgba(255,255,255,.16)" : "#E6ECF7";
  const soft = dark ? "rgba(255,255,255,.07)" : "#F5F7FC", tint = `${c.color}1A`;
  const name = c.name;

  const names = useMemo(() => {
    let dn: Intl.DisplayNames | null = null;
    try { dn = new Intl.DisplayNames([c.lang === "ht" ? "fr" : c.lang], { type: "region" }); } catch { dn = null; }
    return Object.fromEntries(COUNTRIES.map((cc) => [cc, dn?.of(cc) ?? cc])) as Record<string, string>;
  }, [c.lang]);
  const list = COUNTRIES.filter((cc) => fold(names[cc]).includes(fold(q)));
  const docs = (["id", "passport", "license"] as DocKey[]).filter((k) => c.docs[k]);
  const sides = kind === "passport" ? (["front", "selfie"] as const) : (["front", "back", "selfie"] as const);

  const order: PStep[] = kind === "passport" ? ["country", "document", "front", "selfie", "review"] : ["country", "document", "front", "back", "selfie", "review"];
  const idx = order.indexOf(step);
  const progress = step === "welcome" ? 0 : step === "done" ? 1 : (idx + 1) / (order.length + 1);
  const prev = () => { if (step === "country") setStep("welcome"); else if (idx > 0) setStep(order[idx - 1]); setCam(false); };

  const setShot = useCallback(async (key: "front" | "back" | "selfie", blob: Blob) => {
    setBusy(true);
    const url = URL.createObjectURL(blob); urls.current.add(url);
    const quality = await analyze(blob);
    setShots((s) => { if (s[key]) { URL.revokeObjectURL(s[key]!.url); urls.current.delete(s[key]!.url); } return { ...s, [key]: { url, q: quality } }; });
    setCam(false); setBusy(false);
  }, []);
  const drop = (key: "front" | "back" | "selfie") => setShots((s) => { if (s[key]) { URL.revokeObjectURL(s[key]!.url); urls.current.delete(s[key]!.url); } const n = { ...s }; delete n[key]; return n; });
  const wipe = () => { urls.current.forEach((u) => URL.revokeObjectURL(u)); urls.current.clear(); setShots({}); };
  const finish = () => { wipe(); setStep("done"); };
  const restart = () => { wipe(); setKind(null); setAgree(false); setStep("welcome"); };

  const Btn = ({ children, onClick, disabled, ghost }: { children: React.ReactNode; onClick?: () => void; disabled?: boolean; ghost?: boolean }) => (
    <button type="button" onClick={onClick} disabled={disabled} className="w-full py-3.5 text-[15px] font-semibold transition-opacity hover:opacity-90 disabled:opacity-40"
      style={ghost ? { border: `1px solid ${line}`, borderRadius: r } : { background: c.color, color: fg, borderRadius: r }}>{children}</button>
  );
  const Logo = () => c.logo ? null : <span className="grid h-11 w-11 place-items-center rounded-xl text-lg font-bold" style={{ background: c.color, color: fg }}>{name[0]?.toUpperCase()}</span>;
  const Secured = () => (
    <div className="mt-3 flex items-center justify-center gap-1.5 text-[11px]" style={{ color: mut }}>
      {t.secured}
      {/* eslint-disable-next-line @next/next/no-img-element */}
      <img src="/logo-mark.svg" alt="" className="h-4 w-4" /><span className="font-semibold">Freda Verify</span>
    </div>
  );
  const Chips = ({ s }: { s: Shot }) => {
    const list = issues(s.q, t);
    return list.length === 0
      ? <p className="flex items-center gap-1.5 text-sm font-medium text-[#12B76A]"><Ic d="M5 12.5l4.500 4.500L19 7.500" className="h-4 w-4" />{t.qGood}</p>
      : <ul className="space-y-1 text-sm font-medium text-[#F79009]" role="alert">{list.map((x) => <li key={x} className="flex items-center gap-1.5"><Ic d="M12 9v4M12 17h.01M10.300 3.900L1.800 18a2 2 0 0 0 1.700 3h17a2 2 0 0 0 1.700-3L13.700 3.900a2 2 0 0 0-3.400 0z" className="h-4 w-4" />{x}</li>)}</ul>;
  };

  /* capture screen for front / back / selfie */
  const capture = (key: "front" | "back" | "selfie") => {
    const isSelfie = key === "selfie";
    const title = isSelfie ? t.selfieT : kind === "passport" ? t.pageT : key === "front" ? t.frontT : t.backT;
    const sub = isSelfie ? t.selfieS : kind === "passport" ? t.pageS : key === "front" ? t.frontS : t.backS;
    const s = shots[key];
    const next = () => setStep(isSelfie ? "review" : order[idx + 1]);
    const bad = s ? issues(s.q, t).length > 0 : false;
    return (<>
      <h2 className="mt-4 font-display text-2xl font-extrabold leading-tight tracking-tight">{title}</h2>
      <p className="mt-1 text-[15px]" style={{ color: mut }}>{sub}</p>
      {cam ? (
        <div className="mt-4 flex min-h-[380px] flex-1 flex-col">
          <Camera facing={isSelfie ? "user" : "environment"} onShot={(b) => setShot(key, b)} onClose={() => setCam(false)} label={t.capture} cancel={t.cancel} denied={t.camDenied} accent={c.color} accentFg={fg} radius={r} />
        </div>
      ) : s ? (
        <div className="mt-4 flex flex-1 flex-col gap-3">
          {/* eslint-disable-next-line @next/next/no-img-element */}
          <img src={s.url} alt={title} className={`max-h-[46vh] w-full rounded-2xl object-contain ${isSelfie ? "aspect-[3/4] object-cover" : ""}`} style={{ background: soft }} />
          <Chips s={s} />
          <div className="mt-auto space-y-2 pt-2">
            <Btn onClick={() => { drop(key); }} ghost={!bad}>{t.retake}</Btn>
            {bad ? <button type="button" onClick={next} className="w-full py-2 text-sm font-semibold" style={{ color: c.color }}>{t.useAnyway}</button> : <Btn onClick={next}>{t.cont}</Btn>}
          </div>
        </div>
      ) : (
        <div className="mt-4 flex flex-1 flex-col">
          <div className="grid flex-1 place-items-center rounded-2xl border-2 border-dashed p-6 text-center" style={{ borderColor: c.color, background: tint }}>
            <div>
              {isSelfie
                ? <span className="mx-auto block h-40 w-32 rounded-[50%] border-[3px] border-dashed" style={{ borderColor: c.color }} />
                : <span className="mx-auto grid h-16 w-24 place-items-center rounded-xl border-[3px] border-dashed" style={{ borderColor: c.color, color: c.color }}><Ic d={DOC_ICON[kind ?? "id"]} className="h-7 w-7" /></span>}
              <p className="mt-4 text-sm" style={{ color: mut }}>{isSelfie ? t.selfieTips : t.tips}</p>
            </div>
          </div>
          <div className="space-y-2 pt-4">
            <Btn onClick={() => setCam(true)} disabled={busy}>{t.takeCam}</Btn>
            {!isSelfie && (
              <label className="block w-full cursor-pointer py-3.5 text-center text-[15px] font-semibold" style={{ border: `1px solid ${line}`, borderRadius: r }}>
                {t.upload}
                <input type="file" accept="image/jpeg,image/png,image/webp" capture="environment" className="sr-only"
                  onChange={(e) => { const f = e.target.files?.[0]; e.target.value = ""; if (f && f.size < 15 * 1024 * 1024) void setShot(key, f); }} />
              </label>
            )}
          </div>
        </div>
      )}
    </>);
  };

  if (!ready) return <div className="min-h-screen bg-white" />;

  return (
    <main className="min-h-[100dvh] sm:py-6" style={{ background: dark ? "#050C2B" : "#F1F4FB", color: tx }}>
      <div className="mx-auto flex min-h-[100dvh] w-full max-w-[440px] flex-col px-5 pb-5 pt-3 sm:min-h-[760px] sm:rounded-[2rem] sm:shadow-[0_24px_70px_rgba(10,22,71,.18)]" style={{ background: bg }}>
        <div role="status" className="mx-auto mb-2 rounded-full px-3 py-1 text-[11px] font-semibold" style={{ background: "#FEF3E2", color: "#B54708" }}>{t.demoBanner}</div>

        {step !== "welcome" && step !== "done" && (
          <div className="flex items-center gap-3">
            <button type="button" onClick={prev} aria-label="Back" className="grid h-9 w-9 shrink-0 place-items-center rounded-full" style={{ background: soft }}><Ic d="M15 6l-6 6 6 6" /></button>
            <div className="h-1.5 flex-1 overflow-hidden rounded-full" style={{ background: line }}><div className="h-full rounded-full transition-all duration-500" style={{ width: `${progress * 100}%`, background: c.color }} /></div>
          </div>
        )}

        {step === "welcome" && (<>
          <div className="relative mt-1 flex justify-end">
            <button type="button" onClick={() => setLangOpen(!langOpen)} aria-label="Language" aria-expanded={langOpen} className="flex items-center gap-1.5 rounded-full px-3 py-2 text-xs font-medium" style={{ background: soft }}>
              <Ic d="M12 21a9 9 0 1 0 0-18 9 9 0 0 0 0 18zM3.600 9h16.800M3.600 15h16.800M12 3a14 14 0 0 1 0 18M12 3a14 14 0 0 0 0 18" className="h-4 w-4" />{c.lang.toUpperCase()}<Ic d="M6 9l6 6 6-6" className="h-3 w-3" />
            </button>
            {langOpen && (
              <ul className="absolute right-0 top-11 z-10 w-32 overflow-hidden rounded-xl text-xs shadow-lg" style={{ background: bg, border: `1px solid ${line}` }}>
                {LANGS.map((l) => (<li key={l}><button type="button" onClick={() => { setC({ ...c, lang: l }); setLangOpen(false); }} className="flex w-full items-center justify-between px-3 py-2.5 text-left" style={{ background: l === c.lang ? tint : "transparent" }}>{{ en: "English", fr: "Français", ht: "Kreyòl" }[l]}{l === c.lang && <span style={{ color: c.color }}>✓</span>}</button></li>))}
              </ul>
            )}
          </div>
          <div className="mt-4 flex flex-col items-center text-center"><Logo />
            <h1 className="mt-4 font-display text-[30px] font-extrabold leading-[1.1] tracking-tight">{c.title || `${t.titleFor} ${name}`}</h1>
            <p className="mt-3 text-[15px] leading-snug" style={{ color: mut }}>{c.subtitle || t.sub}</p>
          </div>
          <div className="flex flex-1 items-center justify-center py-8">
            <ol className="relative space-y-7 pl-6">
              <span className="absolute left-0 top-0 h-full w-1 rounded-full" style={{ background: line }} />
              <span className="absolute left-0 top-0 h-1/2 w-1 rounded-full" style={{ background: `linear-gradient(${c.color}, ${c.color}66)` }} />
              {[t.idv, t.facev].map((x, i) => (<li key={x}><div className="text-[11px] font-semibold uppercase tracking-[0.18em]" style={{ color: mut }}>{t.step} {i + 1}</div><div className="text-xl font-bold" style={{ color: i === 0 ? tx : mut }}>{x}</div></li>))}
            </ol>
          </div>
          <label className="mb-3 flex items-start gap-2.5 text-[13px] leading-snug" style={{ color: mut }}>
            <input type="checkbox" checked={agree} onChange={(e) => setAgree(e.target.checked)} className="mt-0.5 h-4 w-4 shrink-0" style={{ accentColor: c.color }} />
            <span>{t.agreePre} <span className="font-medium" style={{ color: c.color }}>{termsLabel(c.lang, name)}</span> {t.agreePost}</span>
          </label>
          <Btn onClick={() => setStep("country")} disabled={!agree}>{t.start}</Btn>
          {c.support && <p className="mt-2 break-all text-center text-xs" style={{ color: mut }}>{t.help} {c.support}</p>}
          <Secured />
        </>)}

        {step === "country" && (<>
          <h2 className="mt-4 font-display text-2xl font-extrabold leading-tight tracking-tight">{t.countryT}</h2>
          <p className="mt-1 text-[15px]" style={{ color: mut }}>{t.countryS}</p>
          <label className="mt-4 flex items-center gap-2 px-3.5 py-3 text-sm focus-within:ring-2" style={{ background: soft, borderRadius: card, ["--tw-ring-color" as string]: c.color }}>
            <Ic d="M11 18a7 7 0 1 0 0-14 7 7 0 0 0 0 14zM20 20l-4-4" className="h-4 w-4 shrink-0" />
            <input value={q} onChange={(e) => setQ(e.target.value)} placeholder={t.search} aria-label={t.search} className="w-full bg-transparent outline-none placeholder:opacity-60" style={{ color: tx }} />
          </label>
          <ul className="-mx-1 mt-2 max-h-[46vh] min-h-0 flex-1 overflow-y-auto px-1" role="listbox" aria-label={t.countryT}>
            {list.length === 0 && <li className="py-8 text-center text-sm" style={{ color: mut }}>{t.none}</li>}
            {list.map((cc) => { const on = cc === country; return (
              <li key={cc} role="option" aria-selected={on}>
                <button type="button" onClick={() => setCountry(cc)} className="flex w-full items-center gap-3 px-3 py-3 text-left text-[15px]" style={{ background: on ? tint : "transparent", borderRadius: card }}>
                  <span className="text-2xl leading-none">{flag(cc)}</span><span className={on ? "font-semibold" : ""}>{names[cc]}</span>
                  {on && <span className="ml-auto grid h-5 w-5 place-items-center rounded-full" style={{ background: c.color, color: fg }}><Ic d="M5 12.5l4.500 4.500L19 7.500" className="h-3 w-3" /></span>}
                </button>
              </li>); })}
          </ul>
          <div className="pt-4"><Btn onClick={() => setStep("document")}>{t.cont}</Btn></div><Secured />
        </>)}

        {step === "document" && (<>
          <h2 className="mt-4 font-display text-2xl font-extrabold leading-tight tracking-tight">{t.docT}</h2>
          <p className="mt-1 text-[15px]" style={{ color: mut }}>{t.docS}</p>
          <div className="mt-4 flex items-center gap-2 px-3.5 py-3 text-sm" style={{ background: soft, borderRadius: card }}>
            <span className="text-xl leading-none">{flag(country)}</span><span className="shrink-0" style={{ color: mut }}>{t.issued}</span><span className="min-w-0 truncate font-semibold">{names[country]}</span>
            <button type="button" onClick={() => setStep("country")} className="ml-auto shrink-0 font-semibold" style={{ color: c.color }}>{t.change}</button>
          </div>
          <ul className="mt-4 space-y-3">
            {docs.map((k) => (<li key={k}>
              <button type="button" onClick={() => { setKind(k); wipe(); setStep("front"); }} className="flex w-full items-center gap-4 border p-4 text-left" style={{ borderColor: line, borderRadius: card }}>
                <span className="grid h-11 w-11 shrink-0 place-items-center rounded-xl" style={{ background: tint, color: c.color }}><Ic d={DOC_ICON[k]} className="h-6 w-6" /></span>
                <span className="min-w-0 flex-1"><span className="block text-base font-semibold">{t[k]}</span><span className="block text-sm" style={{ color: mut }}>{t[`${k}S` as "idS"]}</span></span>
                <Ic d="M9 6l6 6-6 6" className="h-5 w-5 opacity-50" />
              </button></li>))}
          </ul>
          <p className="mt-auto flex items-center justify-center gap-1.5 pt-6 text-center text-xs" style={{ color: mut }}><Ic d="M12 3l7 3v5c0 4.500-3 8-7 10-4-2-7-5.500-7-10V6z" className="h-3.5 w-3.5" />{t.tips}</p><Secured />
        </>)}

        {(step === "front" || step === "back" || step === "selfie") && capture(step)}

        {step === "review" && (<>
          <h2 className="mt-4 font-display text-2xl font-extrabold leading-tight tracking-tight">{t.reviewT}</h2>
          <p className="mt-1 text-[15px]" style={{ color: mut }}>{t.reviewS}</p>
          <div className="mt-4 grid grid-cols-2 gap-3">
            {sides.map((k) => { const s = shots[k]; const label = k === "selfie" ? t.lblSelfie : kind === "passport" ? t.lblPage : k === "front" ? t.lblFront : t.lblBack; return (
              <div key={k}>
                {/* eslint-disable-next-line @next/next/no-img-element */}
                {s && <img src={s.url} alt={label} className="aspect-[4/3] w-full rounded-xl object-cover" style={{ background: soft }} />}
                <div className="mt-1.5 flex items-center justify-between text-xs"><span className="font-semibold">{label}</span>
                  <button type="button" onClick={() => { drop(k); setStep(k); }} className="font-semibold" style={{ color: c.color }}>{t.retake}</button></div>
              </div>); })}
          </div>
          <div className="mt-auto space-y-3 pt-6"><Btn onClick={finish} disabled={sides.some((k) => !shots[k])}>{t.submit}</Btn></div><Secured />
        </>)}

        {step === "done" && (<>
          <div className="flex flex-1 flex-col items-center justify-center py-10 text-center">
            <div className="relative grid h-28 w-28 place-items-center"><span className="absolute inset-0 rounded-full" style={{ background: tint }} /><span className="absolute inset-4 rounded-full" style={{ background: `${c.color}33` }} />
              <span className="relative grid h-16 w-16 place-items-center rounded-full" style={{ background: c.color, color: fg }}><Ic d="M5 12.5l4.500 4.500L19 7.500" className="h-8 w-8" /></span></div>
            <h2 className="mt-6 font-display text-2xl font-extrabold tracking-tight">{t.demoDoneT}</h2>
            <p className="mt-3 max-w-xs text-[15px] leading-snug" style={{ color: mut }}>{t.demoDone}</p>
          </div>
          <Btn onClick={restart}>{t.back} {name}</Btn><Secured />
        </>)}
      </div>
    </main>
  );
}
