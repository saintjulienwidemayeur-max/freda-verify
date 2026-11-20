"use client";
import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { COUNTRIES, DOC_ICON, Ic, LANGS, RADIUS, T, flag, fold, isMail, onColor, termsLabel } from "./HostedPreview";
import type { Cfg, DocKey, Lang, Shape, Theme } from "./HostedPreview";
import Scanner from "./Scanner";
import { loadCv } from "./cardDetect";
import { loadFace } from "./faceDetect";
import { needsFace, validateFile, type Reject } from "./docValidate";
import FaceScanner from "./FaceScanner";
import qrcode from "qrcode-generator";
import { API_URL } from "@/lib/api";

/* ───────────── config from URL (demo): every value is validated, text is rendered as text ───────────── */
const DEFAULTS: Cfg = {
  name: "", logo: null, color: "#1E4FE0", theme: "light", shape: "rounded", lang: "en",
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
    name: clean(q.get("name"), 40),
    color: /^#?[0-9a-fA-F]{6}$/.test(color) ? `#${color.replace("#", "").toUpperCase()}` : DEFAULTS.color,
    theme: (theme === "dark" ? "dark" : "light") as Theme,
    shape: (["square", "rounded", "pill"].includes(shape ?? "") ? shape : "rounded") as Shape,
    lang: (LANGS as string[]).includes(lang ?? "") ? (lang as Lang) : "en",
    title: clean(q.get("title"), 60), subtitle: clean(q.get("subtitle"), 140),
    docs, support: isMail(support) ? support : "", hidePowered: false,
  };
}

/* ───────────── real session (token in the URL fragment, sent only to the API as a Bearer header) ───────────── */
type SessionData = { status: string; consent_given: boolean; branding: { name: string; color: string; theme: Theme; shape: Shape; lang: Lang; title: string; subtitle: string; support_email: string; docs: string[]; hide_powered: boolean; has_logo: boolean } };
const sessionFetch = (path: string, token: string, init?: RequestInit) => fetch(`${API_URL}/api/v1${path}`, { ...init, headers: { ...(init?.headers as Record<string, string>), Authorization: `Bearer ${token}` }, credentials: "omit" });
const tokenFromHash = (): string => { const m = /^#s=(fvs_[A-Za-z0-9_-]{20,100})$/.exec(window.location.hash); return m ? m[1] : ""; };

/* ───────────── desktop detection + QR ───────────── */
const isDesktop = () => {
  const mobileUA = /Android|iPhone|iPad|iPod|Mobile|Silk|Opera Mini/i.test(navigator.userAgent);
  const touchTablet = navigator.maxTouchPoints > 1 && window.matchMedia("(pointer: coarse)").matches; // iPadOS reports a desktop UA
  return !(mobileUA || touchTablet);
};
function Qr({ value }: { value: string }) {
  const svg = useMemo(() => {
    try { const q = qrcode(0, "M"); q.addData(value); q.make(); return q.createSvgTag({ cellSize: 6, margin: 0, scalable: true }); } catch { return ""; }
  }, [value]);
  if (!svg) return null;
  // the SVG is generated locally from the URL (only <rect>/<path> modules), never from user HTML
  return <div role="img" aria-label="QR code" className="aspect-square w-full" dangerouslySetInnerHTML={{ __html: svg }} />;
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
type PStep = "qr" | "welcome" | "country" | "document" | "front" | "back" | "selfie" | "done";

export default function HostedPage() {
  const [c, setC] = useState<Cfg>(DEFAULTS);
  const [ready, setReady] = useState(false);
  const [step, setStep] = useState<PStep>("welcome");
  const [country, setCountry] = useState("HT");
  const [q, setQ] = useState("");
  const [kind, setKind] = useState<DocKey | null>(null);
  const [shots, setShots] = useState<{ front?: Shot; back?: Shot; selfie?: Shot }>({});
  const [cam, setCam] = useState(false);
  const fresh = useRef<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [agree, setAgree] = useState(false);
  const [langOpen, setLangOpen] = useState(false);
  const urls = useRef<Set<string>>(new Set());

  const [link, setLink] = useState("");
  const [debug, setDebug] = useState(false);
  const [blinkOn, setBlinkOn] = useState(false);
  const [upErr, setUpErr] = useState<Reject | null>(null);
  const [sendErr, setSendErr] = useState(false);
  const [copied, setCopied] = useState(false);
  const [token, setToken] = useState("");
  const [sessErr, setSessErr] = useState(false);
  useEffect(() => {
    const tk = tokenFromHash();
    setToken(tk);
    if (tk && API_URL) {
      // real session: branding (and logo) come from the organization's saved settings, not from the URL
      void (async () => {
        try {
          const r = await sessionFetch("/session", tk);
          if (!r.ok) throw new Error(String(r.status));
          const d = (await r.json()) as SessionData; const b = d.branding;
          let logo: string | null = null;
          if (b.has_logo) { try { const lr = await sessionFetch("/session/logo", tk); if (lr.ok) { logo = URL.createObjectURL(await lr.blob()); urls.current.add(logo); } } catch { /* page works without the logo */ } }
          const docs: Record<DocKey, boolean> = { id: b.docs.includes("id"), passport: b.docs.includes("passport"), license: b.docs.includes("license") };
          setC({ ...DEFAULTS, name: b.name, logo, color: b.color.toUpperCase(), theme: b.theme, shape: b.shape, lang: b.lang, title: b.title, subtitle: b.subtitle, docs, support: b.support_email, hidePowered: b.hide_powered });
        } catch { setSessErr(true); }
        setReady(true);
      })();
    } else if (tk) { setSessErr(true); }
    else setC(readConfig(window.location.search));
    setDebug(new URLSearchParams(window.location.search).get("debug") === "1");
    setBlinkOn(new URLSearchParams(window.location.search).get("blink") === "1");
    const u = new URL(window.location.href); const stay = u.searchParams.get("desktop") === "1"; u.searchParams.delete("desktop"); u.hash = tk ? `#s=${tk}` : "";  // the phone needs the same session link
    setLink(u.toString());
    if (isDesktop() && !stay) setStep("qr");
    if (!(tk && API_URL)) setReady(true);
  }, []);
  // start loading the heavy engines as soon as the user reaches the document step, so the scanners open instantly
  useEffect(() => { if (step === "document" || step === "front" || step === "back") { loadCv().catch(() => {}); loadFace().catch(() => {}); } }, [step]);
  useEffect(() => () => { urls.current.forEach((u) => URL.revokeObjectURL(u)); urls.current.clear(); }, []);
  useEffect(() => { document.documentElement.lang = c.lang; }, [c.lang]);

  const t = T[c.lang];
  const dark = c.theme === "dark", fg = onColor(c.color), r = RADIUS[c.shape], card = Math.min(r, 16);
  const bg = dark ? "#0A1647" : "#FFFFFF", tx = dark ? "#FFFFFF" : "#0A1647";
  const mut = dark ? "rgba(255,255,255,.65)" : "rgba(10,22,71,.58)", line = dark ? "rgba(255,255,255,.16)" : "#E6ECF7";
  const soft = dark ? "rgba(255,255,255,.07)" : "#F5F7FC", tint = `${c.color}1A`;
  const custom = c.name.trim().length > 0;
  const name = c.name.trim() || "Freda Verify"; // default brand when the client has not filled the white label

  const scanTx = useMemo(() => ({ place: t.scanPlace, face: t.scanFace, hold: t.scanHold, dark: t.scanDark, glare: t.scanGlare, blur: t.scanBlur, auto: t.scanAuto, done: t.scanDone, capNow: t.capNow, denied: t.camDenied, cancel: t.cancel, loading: t.scanLoading, closer: t.scanCloser, far: t.scanFar, center: t.scanCenter, fitFrame: t.scanFit, capNowBtn: t.capNow, guideChecking: t.scanGuide, found: t.scanFound,
    scanFail: t.scanFail, retry: t.retry, showPassport: t.showPassport, showId: t.showId, docRej: t.docRej, rejShape: t.rejShape, rejFace: t.rejFace, rejMrz: t.rejMrz, rejUnavail: t.rejUnavail, blinkNow: t.blinkNow, stepAction: t.stepAction, tipMore: t.tipMore,
    faceLoading: t.faceLoading, faceNone: t.faceNone, faceMulti: t.faceMulti, faceSmall: t.faceSmall, faceBig: t.faceBig, faceCenter: t.faceCenter, faceFront: t.faceFront, turnL: t.turnL, turnR: t.turnR, turnWrong: t.turnWrong, turnOk: t.turnOk, turnAgain: t.turnAgain, dirL: t.dirL, dirR: t.dirR, stepFace: t.stepFace, stepTurn: t.stepTurn }), [t]);
  const names = useMemo(() => {
    let dn: Intl.DisplayNames | null = null;
    try { dn = new Intl.DisplayNames([c.lang === "ht" ? "fr" : c.lang], { type: "region" }); } catch { dn = null; }
    return Object.fromEntries(COUNTRIES.map((cc) => [cc, dn?.of(cc) ?? cc])) as Record<string, string>;
  }, [c.lang]);
  const list = COUNTRIES.filter((cc) => fold(names[cc]).includes(fold(q)));
  const docs = (["id", "passport", "license"] as DocKey[]).filter((k) => c.docs[k]);
  const order: PStep[] = kind === "passport" ? ["country", "document", "front", "selfie"] : ["country", "document", "front", "back", "selfie"];
  const idx = order.indexOf(step);
  const progress = step === "welcome" ? 0 : step === "done" ? 1 : (idx + 1) / (order.length + 1);
  const prev = () => { if (step === "country") setStep("welcome"); else if (idx > 0) setStep(order[idx - 1]); setCam(false); };

  const setShot = useCallback(async (key: "front" | "back" | "selfie", blob: Blob, extra?: Blob[]) => {
    setBusy(true); setSendErr(false);
    if (token) {   // real session: the photo is sent (encrypted at rest, reviewed by a person) BEFORE it is accepted on screen
      try {
        const q = key === "selfie" ? "" : `?doc_type=${kind ?? "id"}&country=${country}`;
        const r = await sessionFetch(`/session/media/${key === "selfie" ? "selfie" : `document_${key}`}${q}`, token, { method: "PUT", headers: { "Content-Type": blob.type }, body: blob });
        if (!r.ok) {
          const code = ((await r.json().catch(() => null)) as { error?: { code?: string } } | null)?.error?.code;
          if (code === "mrz_not_found") { setUpErr("mrz"); setBusy(false); setCam(false); return; }   // the server could not read the passport's two bottom lines
          throw new Error(String(r.status));
        }
      } catch { setSendErr(true); setBusy(false); setCam(false); return; }
      // extra frontal frames of the selfie (best effort: a failure here never blocks the verification; they only feed the experimental live-capture score)
      if (key === "selfie" && extra?.length) {
        await Promise.all(extra.slice(0, 2).map((b, i) => sessionFetch(`/session/media/selfie_${i + 2}`, token, { method: "PUT", headers: { "Content-Type": b.type }, body: b }).catch(() => null)));
      }
    }
    const url = URL.createObjectURL(blob); urls.current.add(url); fresh.current = url;
    const quality = await analyze(blob);
    setShots((s) => { if (s[key]) { URL.revokeObjectURL(s[key]!.url); urls.current.delete(s[key]!.url); } return { ...s, [key]: { url, q: quality } }; });
    setCam(false); setBusy(false);
  }, [token, kind, country]);
  const drop = (key: "front" | "back" | "selfie") => setShots((s) => { if (s[key]) { URL.revokeObjectURL(s[key]!.url); urls.current.delete(s[key]!.url); } const n = { ...s }; delete n[key]; return n; });
  const wipe = () => { urls.current.forEach((u) => URL.revokeObjectURL(u)); urls.current.clear(); setShots({}); };
  // open the scanner automatically on each capture step; auto-advance after a fresh good capture
  useEffect(() => { setUpErr(null); setCam((step === "front" || step === "back" || step === "selfie") && !shots[step]); }, [step]); // eslint-disable-line react-hooks/exhaustive-deps
  useEffect(() => {
    if (step !== "front" && step !== "back" && step !== "selfie") return;
    const s = shots[step];
    if (!s || fresh.current !== s.url || issues(s.q, T[c.lang]).length > 0) return;
    const tm = setTimeout(() => { fresh.current = null; if (step === "selfie") void finish(); else setStep(order[order.indexOf(step) + 1]); }, step === "selfie" ? 250 : 1300);
    return () => clearTimeout(tm);
  }); // eslint-disable-line react-hooks/exhaustive-deps
  const finish = async () => {
    if (token) {
      setBusy(true); setSendErr(false);
      try { const r = await sessionFetch("/session/complete", token, { method: "POST" }); if (!r.ok) throw new Error(String(r.status)); } catch { setSendErr(true); setBusy(false); return; }
      setBusy(false);
    }
    wipe(); setStep("done");
  };
  const restart = () => { wipe(); setKind(null); setAgree(false); setStep("welcome"); };

  const Btn = ({ children, onClick, disabled, ghost }: { children: React.ReactNode; onClick?: () => void; disabled?: boolean; ghost?: boolean }) => (
    <button type="button" onClick={onClick} disabled={disabled} className="w-full py-3.5 text-[15px] font-semibold transition-opacity hover:opacity-90 disabled:opacity-40"
      style={ghost ? { border: `1px solid ${line}`, borderRadius: r } : { background: c.color, color: fg, borderRadius: r }}>{children}</button>
  );
  const Logo = () => c.logo
    // eslint-disable-next-line @next/next/no-img-element
    ? <img src={c.logo} alt={name} className="h-12 max-w-[9rem] object-contain" />
    : custom
    ? <span className="grid h-11 w-11 place-items-center rounded-xl text-lg font-bold" style={{ background: c.color, color: fg }}>{name[0]?.toUpperCase()}</span>
    // eslint-disable-next-line @next/next/no-img-element
    : <img src="/logo-mark.svg" alt="Freda Verify" className="h-12 w-12" />;
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

  // an uploaded photo goes through the SAME strict checks as the live scanner; it is stored as the flattened, validated crop
  const uploadDoc = async (key: "front" | "back", file: File) => {
    setBusy(true); setUpErr(null);
    try {
      const [{ cv }, f] = await Promise.all([loadCv(), needsFace(kind ?? "id", key) ? loadFace() : Promise.resolve(null)]);
      const v = await validateFile(cv, f ? f.lm : null, kind ?? "id", key, file);
      if (!v.ok) { setUpErr(v.reject); setBusy(false); return; }
      await setShot(key, v.blob);
    } catch { setUpErr("unavailable"); setBusy(false); }
  };

  /* capture screen for front / back / selfie */
  const capture = (key: "front" | "back" | "selfie") => {
    const isSelfie = key === "selfie";
    const title = isSelfie ? t.selfieT : kind === "passport" ? t.pageT : key === "front" ? t.frontT : t.backT;
    const sub = isSelfie ? t.selfieS : kind === "passport" ? t.pageS : key === "front" ? t.frontS : t.backS;
    const s = shots[key];
    const next = () => { if (isSelfie) void finish(); else setStep(order[idx + 1]); };
    const bad = s ? issues(s.q, t).length > 0 : false;
    return (<>
      <h2 className="mt-4 font-display text-2xl font-extrabold leading-tight tracking-tight">{title}</h2>
      <p className="mt-1 text-[15px]" style={{ color: mut }}>{sub}</p>
      {cam ? (
        <div className="mt-4 flex min-h-[380px] flex-1 flex-col">
          {isSelfie
            ? <FaceScanner onShot={(b, extra) => setShot(key, b, extra)} onCancel={() => setCam(false)} accent={c.color} radius={r} tx={scanTx} debug={debug} blink={blinkOn} />
            : <Scanner kind={kind ?? "id"} side={key === "back" ? "back" : "front"} onShot={(b) => setShot(key, b)} onCancel={() => setCam(false)} accent={c.color} radius={r} tx={scanTx} debug={debug} />}
        </div>
      ) : s ? (
        <div className="mt-4 flex flex-1 flex-col gap-3">
          {/* eslint-disable-next-line @next/next/no-img-element */}
          <img src={s.url} alt={title} className={`max-h-[46vh] w-full rounded-2xl object-contain ${isSelfie ? "aspect-[3/4] object-cover" : ""}`} style={{ background: soft }} />
          {!bad && <p className="flex items-center gap-1.5 text-sm font-semibold" style={{ color: c.color }}><Ic d="M5 12.5l4.500 4.500L19 7.500" className="h-4 w-4" />{t.scanDone}</p>}
          <Chips s={s} />
          <div className="mt-auto space-y-2 pt-2">
            <Btn onClick={() => { fresh.current = null; drop(key); setCam(true); }} ghost={!bad}>{t.retake}</Btn>
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
                {busy ? "…" : t.upload}
                <input type="file" accept="image/jpeg,image/png,image/webp" capture="environment" className="sr-only" disabled={busy}
                  onChange={(e) => { const f = e.target.files?.[0]; e.target.value = ""; if (f && f.size < 15 * 1024 * 1024) void uploadDoc(key as "front" | "back", f); }} />
              </label>
            )}
            {sendErr && <p role="alert" className="mt-3 rounded-xl p-3 text-sm" style={{ background: "#FDECEA", color: "#B42318" }}>{t.sendFail}</p>}
            {upErr && !isSelfie && (
              <div className="rounded-2xl px-4 py-3 text-sm font-medium text-white" style={{ background: "#B42318" }} role="alert">
                <b className="block">{t.docRej}</b>{upErr === "shape" ? t.rejShape : upErr === "face" ? t.rejFace : upErr === "mrz" ? t.rejMrz : t.rejUnavail}
              </div>
            )}
          </div>
        </div>
      )}
    </>);
  };

  if (!ready) return <div className="min-h-screen bg-white" />;
  if (sessErr) return <main className="grid min-h-screen place-items-center bg-white p-6 text-center text-navy"><div><img src="/logo-mark.svg" alt="" className="mx-auto h-12 w-12" /><h1 className="mt-4 font-display text-2xl font-bold">This verification link is not valid</h1><p className="mt-2 max-w-sm text-sm text-navy/70">It may have expired or been mistyped. Ask the company that sent it for a new link.</p></div></main>;

  return (
    <main className="min-h-[100dvh] sm:py-6" style={{ background: dark ? "#050C2B" : "#F1F4FB", color: tx }}>
      <div className="mx-auto flex min-h-[100dvh] w-full max-w-[440px] flex-col px-5 pb-5 pt-3 sm:min-h-[760px] sm:rounded-[2rem] sm:shadow-[0_24px_70px_rgba(10,22,71,.18)]" style={{ background: bg }}>
        {!token && <div role="status" className="mx-auto mb-2 rounded-full px-3 py-1 text-[11px] font-semibold" style={{ background: "#FEF3E2", color: "#B54708" }}>{t.demoBanner}</div>}

        {step !== "qr" && step !== "welcome" && step !== "done" && (
          <div className="flex items-center gap-3">
            <button type="button" onClick={prev} aria-label="Back" className="grid h-9 w-9 shrink-0 place-items-center rounded-full" style={{ background: soft }}><Ic d="M15 6l-6 6 6 6" /></button>
            <div className="h-1.5 flex-1 overflow-hidden rounded-full" style={{ background: line }}><div className="h-full rounded-full transition-all duration-500" style={{ width: `${progress * 100}%`, background: c.color }} /></div>
          </div>
        )}

        {step === "qr" && (<>
          <div className="flex flex-1 flex-col items-center justify-center py-6 text-center">
            <Logo />
            <h1 className="mt-4 font-display text-[28px] font-extrabold leading-[1.1] tracking-tight">{t.qrTitle}</h1>
            <p className="mt-3 max-w-xs text-[15px] leading-snug" style={{ color: mut }}>{t.qrSub}</p>
            <div className="mt-6 w-[236px] rounded-3xl bg-white p-4 shadow-[0_10px_40px_rgba(10,22,71,.16)]" style={{ border: `1px solid ${line}` }}><Qr value={link} /></div>
            {!token && <p className="mt-4 max-w-[17rem] truncate text-xs" style={{ color: mut }} title={link}>{link.replace(/^https?:\/\//, "")}</p>}
            <button type="button" onClick={async () => { try { await navigator.clipboard.writeText(link); setCopied(true); setTimeout(() => setCopied(false), 2000); } catch { setCopied(false); } }}
              className="mt-2 rounded-full px-4 py-2 text-sm font-semibold" style={{ color: c.color, background: tint }}>{copied ? `✓ ${t.qrCopied}` : t.qrCopy}</button>
            <p className="mt-5 max-w-xs text-xs leading-snug" style={{ color: mut }}>{t.qrWhy}</p>
          </div>
          <Btn ghost onClick={() => setStep("welcome")}>{t.qrHere}</Btn><Secured />
        </>)}

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
          {token && <p className="mb-3 text-[12px] leading-snug" style={{ color: mut }}>{t.sendNote.replace("{n}", name)}</p>}
          <Btn onClick={() => { if (token) void sessionFetch("/session/consent", token, { method: "POST" }).catch(() => {}); setStep("country"); }} disabled={!agree}>{t.start}</Btn>
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

        {step === "done" && (<>
          <div className="flex flex-1 flex-col items-center justify-center py-10 text-center">
            <div className="relative grid h-28 w-28 place-items-center"><span className="absolute inset-0 rounded-full" style={{ background: tint }} /><span className="absolute inset-4 rounded-full" style={{ background: `${c.color}33` }} />
              <span className="relative grid h-16 w-16 place-items-center rounded-full" style={{ background: c.color, color: fg }}><Ic d="M5 12.5l4.500 4.500L19 7.500" className="h-8 w-8" /></span></div>
            <h2 className="mt-6 font-display text-2xl font-extrabold tracking-tight">{token ? t.doneT : t.demoDoneT}</h2>
            <p className="mt-3 max-w-xs text-[15px] leading-snug" style={{ color: mut }}>{token ? t.doneS : t.demoDone}</p>
          </div>
          <Btn onClick={restart}>{t.back} {name}</Btn><Secured />
        </>)}
      </div>
    </main>
  );
}
