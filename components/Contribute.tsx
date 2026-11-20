"use client";
import { useCallback, useEffect, useRef, useState } from "react";
import { API_URL } from "@/lib/api";

/* Public volunteer page: consent -> 3 live selfies -> (optional) 2 photos of a printed photo -> (optional) 2 photos of a screen. The consent text is a DRAFT that a lawyer must review (D9). */
type L = "ht" | "fr" | "en";
const CONSENT_VERSION = "draft-1";
const LIGHTS = ["window", "indoor", "dim", "outdoor", "backlight", "other"] as const;
const T = {
  ht: {
    title: "Ede nou teste pwoteksyon kont fwod", intro: "Freda Verify ap teste yon sistèm ki dwe rekonèt si yon moun vrèman devan kamera a, oswa si se yon foto enprime oswa yon ekran. Nou bezwen kèk foto ou.",
    consentH: "Konsantman (bouyon, poko revize pa yon avoka)", consent: [
      "Mwen dakò pou Freda Verify pran foto figi mwen ki mwen voye yo sou paj sa a.",
      "Se sèlman pou teste ak amelyore sistèm detèksyon fwod la. Pa gen okenn desizyon sou mwen.",
      "Foto yo sere chifre. Sèlman ekip Freda Verify ki otorize ka wè yo. Yo pa pataje ak okenn lòt moun, e yo pa voye bay okenn sèvis IA ekstèn.",
      "Yo kenbe jiskaske m mande yo efase, oswa jiskaske tès la fini. Mwen ka efase tout foto m yo kounye a ak bouton ki sou paj la.",
      "Mwen gen omwen 18 an. Mwen ka kite nenpòt ki lè."], check: "Mwen li epi mwen dakò", skin: "Koulè po (opsyonèl, ou deside)", skinHint: "ex. fonse, mwayen, klè", start: "Kòmanse",
    live: "Foto ou menm (3)", liveHow: "Gade dirèk nan kamera a. Chanje kote ou ye pou chak foto (fenèt, andedan, limyè fèb).", print: "Foto yon foto enprime (opsyonèl)", printHow: "Si ou gen yon foto enprime (ou menm oswa yon lòt moun ki dakò), kenbe l devan kamera a epi pran yon foto.",
    replay: "Foto yon ekran (opsyonèl)", replayHow: "Louvri yon foto yon figi sou yon lòt telefòn oswa òdinatè, kenbe l devan kamera a epi pran yon foto.", skip: "Pa gen", take: "Pran foto", retake: "Refè", next: "Swivan", light: "Limyè",
    lights: { window: "Bò fenèt", indoor: "Andedan", dim: "Limyè fèb", outdoor: "Deyò", backlight: "Limyè dèyè", other: "Lòt" }, done: "Mèsi anpil!", doneText: "Foto ou yo anrejistre.", erase: "Efase tout foto m yo kounye a", erased: "Tout foto ou yo efase.", err: "Gen yon pwoblèm. Eseye ankò.", cam: "Nou pa ka louvri kamera a. Pèmèt kamera a, oswa chwazi yon foto.", pick: "Chwazi yon foto", invalid: "Lyen an pa valid oswa fèmen.", sent: "voye",
  },
  fr: {
    title: "Aidez-nous à tester la protection contre la fraude", intro: "Freda Verify teste un système qui doit reconnaître si une personne est vraiment devant la caméra, ou s'il s'agit d'une photo imprimée ou d'un écran. Nous avons besoin de quelques photos de vous.",
    consentH: "Consentement (brouillon, pas encore relu par un avocat)", consent: [
      "J'accepte que Freda Verify utilise les photos de mon visage que j'envoie sur cette page.",
      "Uniquement pour tester et améliorer le système de détection de fraude. Aucune décision n'est prise à mon sujet.",
      "Les photos sont stockées chiffrées. Seule l'équipe Freda Verify autorisée peut les voir. Elles ne sont ni partagées, ni envoyées à un service d'IA externe.",
      "Elles sont conservées jusqu'à ce que je demande leur suppression, ou jusqu'à la fin du test. Je peux supprimer toutes mes photos maintenant avec le bouton de la page.",
      "J'ai au moins 18 ans. Je peux arrêter à tout moment."], check: "J'ai lu et j'accepte", skin: "Teint de peau (facultatif, vous décidez)", skinHint: "ex. foncé, moyen, clair", start: "Commencer",
    live: "Photos de vous (3)", liveHow: "Regardez droit la caméra. Changez d'endroit à chaque photo (fenêtre, intérieur, lumière faible).", print: "Photo d'une photo imprimée (facultatif)", printHow: "Si vous avez une photo imprimée (de vous ou d'une personne d'accord), tenez-la devant la caméra et prenez une photo.",
    replay: "Photo d'un écran (facultatif)", replayHow: "Affichez la photo d'un visage sur un autre téléphone ou ordinateur, tenez-le devant la caméra et prenez une photo.", skip: "Passer", take: "Prendre la photo", retake: "Refaire", next: "Suivant", light: "Lumière",
    lights: { window: "Près d'une fenêtre", indoor: "Intérieur", dim: "Lumière faible", outdoor: "Extérieur", backlight: "Contre-jour", other: "Autre" }, done: "Merci beaucoup !", doneText: "Vos photos sont enregistrées.", erase: "Supprimer toutes mes photos maintenant", erased: "Toutes vos photos sont supprimées.", err: "Un problème est survenu. Réessayez.", cam: "Impossible d'ouvrir la caméra. Autorisez-la, ou choisissez une photo.", pick: "Choisir une photo", invalid: "Ce lien n'est pas valide ou est fermé.", sent: "envoyée",
  },
  en: {
    title: "Help us test fraud protection", intro: "Freda Verify is testing a system that must tell whether a real person is in front of the camera, or just a printed photo or a screen. We need a few photos of you.",
    consentH: "Consent (draft, not yet reviewed by a lawyer)", consent: [
      "I agree that Freda Verify may use the photos of my face that I send on this page.",
      "Only to test and improve the fraud-detection system. No decision is made about me.",
      "Photos are stored encrypted. Only authorised Freda Verify staff can see them. They are not shared and not sent to any outside AI service.",
      "They are kept until I ask for them to be deleted, or until the test ends. I can delete all my photos now with the button on this page.",
      "I am at least 18. I can stop at any time."], check: "I have read and I agree", skin: "Skin tone (optional, you decide)", skinHint: "e.g. dark, medium, light", start: "Start",
    live: "Photos of you (3)", liveHow: "Look straight at the camera. Change place for each photo (window, indoors, dim light).", print: "Photo of a printed photo (optional)", printHow: "If you have a printed photo (of you or of a person who agrees), hold it in front of the camera and take a photo.",
    replay: "Photo of a screen (optional)", replayHow: "Show a photo of a face on another phone or computer, hold it in front of the camera and take a photo.", skip: "Skip", take: "Take photo", retake: "Retake", next: "Next", light: "Light",
    lights: { window: "Near a window", indoor: "Indoors", dim: "Dim light", outdoor: "Outdoors", backlight: "Backlit", other: "Other" }, done: "Thank you!", doneText: "Your photos are saved.", erase: "Delete all my photos now", erased: "All your photos are deleted.", err: "Something went wrong. Please try again.", cam: "Cannot open the camera. Allow it, or choose a photo.", pick: "Choose a photo", invalid: "This link is not valid or is closed.", sent: "sent",
  },
} as const;

const call = (path: string, tok: string, init?: RequestInit) => fetch(`${API_URL}/api/v1${path}`, { ...init, headers: { ...(init?.headers as Record<string, string>), Authorization: `Bearer ${tok}` }, credentials: "omit" });
type Kind = "live" | "print" | "replay";
const STEPS: { kind: Kind; slots: number; optional: boolean }[] = [{ kind: "live", slots: 3, optional: false }, { kind: "print", slots: 2, optional: true }, { kind: "replay", slots: 2, optional: true }];

async function toJpeg(src: HTMLVideoElement | HTMLImageElement, w: number, h: number): Promise<Blob | null> {
  const k = Math.min(1, 1280 / Math.max(w, h)); const c = document.createElement("canvas"); c.width = Math.round(w * k); c.height = Math.round(h * k);
  c.getContext("2d")!.drawImage(src, 0, 0, c.width, c.height);
  return new Promise((r) => c.toBlob((b) => r(b), "image/jpeg", 0.9));
}

export default function Contribute() {
  const [lang, setLang] = useState<L>("ht"), t = T[lang];
  const [ctoken, setCtoken] = useState(""), [ptoken, setPtoken] = useState(""), [state, setState] = useState<"loading" | "invalid" | "welcome" | "capture" | "done" | "erased">("loading");
  const [agree, setAgree] = useState(false), [skin, setSkin] = useState(""), [busy, setBusy] = useState(false), [err, setErr] = useState("");
  const [step, setStep] = useState(0), [slot, setSlot] = useState(1), [light, setLight] = useState<string>("indoor"), [camOk, setCamOk] = useState(true), [shot, setShot] = useState<{ url: string; blob: Blob } | null>(null);
  const [sent, setSent] = useState<Record<string, number>>({});
  const vid = useRef<HTMLVideoElement>(null), stream = useRef<MediaStream | null>(null);

  useEffect(() => {
    const m = /^#c=(fvc_[A-Za-z0-9_-]{20,100})$/.exec(window.location.hash); const nav = navigator.language.slice(0, 2);
    setLang(nav === "fr" ? "fr" : nav === "en" ? "en" : "ht");
    if (!m) return setState("invalid");
    setCtoken(m[1]);
    call("/collect/info", m[1]).then((r) => setState(r.ok ? "welcome" : "invalid")).catch(() => setState("invalid"));
  }, []);

  const stop = () => { stream.current?.getTracks().forEach((x) => x.stop()); stream.current = null; };
  const openCam = useCallback(async () => {
    stop(); setCamOk(true);
    try { const s = await navigator.mediaDevices.getUserMedia({ video: { facingMode: "user", width: { ideal: 1280 } }, audio: false }); stream.current = s; if (vid.current) { vid.current.srcObject = s; await vid.current.play().catch(() => {}); } } catch { setCamOk(false); }
  }, []);
  useEffect(() => { if (state === "capture" && !shot) void openCam(); return stop; }, [state, step, slot, shot, openCam]);

  const begin = async () => {
    setBusy(true); setErr("");
    try {
      const r = await call("/collect/start", ctoken, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ consent: true, consent_version: CONSENT_VERSION, skin_label: skin.trim() || null }) });
      if (!r.ok) throw new Error(); const j = (await r.json()) as { token: string }; setPtoken(j.token); setState("capture");
    } catch { setErr(t.err); } finally { setBusy(false); }
  };
  const snap = async () => { const v = vid.current; if (!v || !v.videoWidth) return; const b = await toJpeg(v, v.videoWidth, v.videoHeight); if (b) setShot({ url: URL.createObjectURL(b), blob: b }); };
  const pickFile = async (f: File | undefined) => {
    if (!f) return; const img = new Image(); const u = URL.createObjectURL(f);
    img.onload = async () => { const b = await toJpeg(img, img.naturalWidth, img.naturalHeight); URL.revokeObjectURL(u); if (b) setShot({ url: URL.createObjectURL(b), blob: b }); }; img.src = u;
  };
  const cur = STEPS[step];
  const upload = async () => {
    if (!shot) return; setBusy(true); setErr("");
    try {
      const r = await call(`/collect/samples/${cur.kind}/${slot}?light=${light}`, ptoken, { method: "PUT", headers: { "Content-Type": "image/jpeg" }, body: shot.blob });
      if (!r.ok) throw new Error();
      setSent((s) => ({ ...s, [cur.kind]: Math.max(s[cur.kind] ?? 0, slot) })); URL.revokeObjectURL(shot.url); setShot(null);
      if (slot < cur.slots) setSlot(slot + 1); else advance();
    } catch { setErr(t.err); } finally { setBusy(false); }
  };
  const advance = async () => {
    if (step + 1 < STEPS.length) { setStep(step + 1); setSlot(1); return; }
    await call("/collect/finish", ptoken, { method: "POST" }).catch(() => null); stop(); setState("done");
  };
  const erase = async () => { setBusy(true); try { await call("/collect/me", ptoken, { method: "DELETE" }); stop(); setState("erased"); } catch { setErr(t.err); } finally { setBusy(false); } };

  const card = "mx-auto w-full max-w-md rounded-2xl border border-[#e3eaf8] bg-white p-5 shadow-sm";
  const btn = "rounded-full bg-blue px-6 py-3 text-sm font-semibold text-white hover:bg-navy disabled:opacity-50";
  return (
    <main className="min-h-screen bg-[#F6F8FC] px-4 py-6 text-navy">
      <div className="mx-auto mb-4 flex max-w-md items-center justify-between"><span className="font-display text-lg font-extrabold">Freda Verify</span>
        <div className="flex gap-1 text-xs">{(["ht", "fr", "en"] as L[]).map((x) => <button key={x} onClick={() => setLang(x)} aria-pressed={lang === x} className={`rounded-full border px-2.5 py-1 uppercase ${lang === x ? "border-navy bg-navy text-white" : "border-[#d6e2ff]"}`}>{x}</button>)}</div></div>

      {state === "loading" && <p className="text-center text-sm text-navy/50">…</p>}
      {state === "invalid" && <div className={card}><p className="text-sm">{t.invalid}</p></div>}

      {state === "welcome" && (
        <div className={card}>
          <h1 className="font-display text-xl font-extrabold">{t.title}</h1><p className="mt-2 text-sm text-navy/70">{t.intro}</p>
          <h2 className="mt-4 text-sm font-bold">{t.consentH}</h2>
          <ul className="mt-2 list-disc space-y-1.5 pl-5 text-sm text-navy/75">{t.consent.map((c) => <li key={c}>{c}</li>)}</ul>
          <label className="mt-4 block text-sm font-medium">{t.skin}<input value={skin} onChange={(e) => setSkin(e.target.value)} maxLength={24} placeholder={t.skinHint} className="mt-1 block w-full rounded-xl border border-[#d6e2ff] px-3 py-2.5 text-sm font-normal" /></label>
          <label className="mt-4 flex items-start gap-2 text-sm font-medium"><input type="checkbox" checked={agree} onChange={(e) => setAgree(e.target.checked)} className="mt-1 h-4 w-4" />{t.check}</label>
          {err && <p role="alert" className="mt-3 text-sm text-[#B42318]">{err}</p>}
          <button disabled={!agree || busy} onClick={begin} className={`${btn} mt-4 w-full`}>{t.start}</button>
        </div>)}

      {state === "capture" && (
        <div className={card}>
          <div className="flex items-center justify-between text-xs text-navy/50"><span>{step + 1}/{STEPS.length}</span><span>{slot}/{cur.slots}</span></div>
          <h1 className="mt-1 font-display text-lg font-extrabold">{t[cur.kind]}</h1>
          <p className="mt-1 text-sm text-navy/70">{cur.kind === "live" ? t.liveHow : cur.kind === "print" ? t.printHow : t.replayHow}</p>
          <div className="relative mt-3 overflow-hidden rounded-xl bg-black">
            {shot ? /* eslint-disable-next-line @next/next/no-img-element */ <img src={shot.url} alt="" className="w-full" /> : <video ref={vid} playsInline muted className="aspect-[3/4] w-full scale-x-[-1] object-cover" />}
          </div>
          {!camOk && !shot && <p className="mt-2 text-sm text-[#B54708]">{t.cam}</p>}
          <label className="mt-3 block text-sm font-medium">{t.light}
            <select value={light} onChange={(e) => setLight(e.target.value)} className="mt-1 block w-full rounded-xl border border-[#d6e2ff] bg-white px-3 py-2.5 text-sm font-normal">{LIGHTS.map((l) => <option key={l} value={l}>{t.lights[l]}</option>)}</select></label>
          {err && <p role="alert" className="mt-3 text-sm text-[#B42318]">{err}</p>}
          <div className="mt-3 flex flex-wrap gap-2">
            {!shot ? (<>
              <button onClick={snap} disabled={!camOk} className={btn}>{t.take}</button>
              <label className="cursor-pointer rounded-full border border-[#d6e2ff] px-4 py-3 text-sm font-semibold">{t.pick}<input type="file" accept="image/*" capture="user" hidden onChange={(e) => void pickFile(e.target.files?.[0])} /></label>
            </>) : (<>
              <button onClick={upload} disabled={busy} className={btn}>{t.next}</button>
              <button onClick={() => { URL.revokeObjectURL(shot.url); setShot(null); }} className="rounded-full border border-[#d6e2ff] px-4 py-3 text-sm font-semibold">{t.retake}</button>
            </>)}
            {cur.optional && !shot && <button onClick={() => void advance()} className="px-3 py-3 text-sm underline">{t.skip}</button>}
          </div>
          <p className="mt-3 text-xs text-navy/50">{Object.entries(sent).map(([k, n]) => `${t[k as Kind]}: ${n} ${t.sent}`).join(" · ")}</p>
        </div>)}

      {state === "done" && <div className={card}><h1 className="font-display text-xl font-extrabold">{t.done}</h1><p className="mt-2 text-sm text-navy/70">{t.doneText}</p>
        {err && <p role="alert" className="mt-3 text-sm text-[#B42318]">{err}</p>}<button onClick={erase} disabled={busy} className="mt-4 rounded-full border border-[#f1b8b2] px-5 py-2.5 text-sm font-semibold text-[#B42318]">{t.erase}</button></div>}
      {state === "erased" && <div className={card}><p className="text-sm">{t.erased}</p></div>}
    </main>
  );
}
