"use client";
import { useCallback, useEffect, useState, type FormEvent } from "react";
import { api, apiBlob, ApiError } from "@/lib/api";
import { can, useAuth } from "@/lib/auth";

type V = { id: string; status: string; env: string; reference: string | null; consent_given: boolean; created_at: string; expires_at: string; submitted_at: string | null; decided_at: string | null; decision_reason: string | null; media_count: number };
type Media = { kind: string; doc_type: string | null; country: string | null; size: number; purge_after: string | null };
type Mrz = { format: string; document_type: string; issuing_country: string; surname: string; given_names: string; document_number: string; nationality: string; birth_date: string | null; sex: string; expiry_date: string | null; checks: Record<string, boolean>; all_checks_passed: boolean; expired: boolean | null; ocr_corrections: number; warnings: string[] };
type Face = { status: string; score: number | null; band: string | null; doc_faces: number; selfie_faces: number; threshold: number; model: string };
type Pad = { status: string; real_probability: number | null; band: string | null; per_model: Record<string, number> };
type Checks = { engine_available: boolean; face_available?: boolean; face?: Face | null; pad_available?: boolean; pad?: Pad | null; mrz: { status: string; source: string | null; created_at: string; result: Mrz | null; agreeing?: number } | null };
const CHECK_LABEL: Record<string, string> = { document_number: "Document number", birth_date: "Birth date", expiry_date: "Expiry date", optional_data: "Optional data", composite: "Overall (composite)" };
const LABEL: Record<string, string> = { document_front: "Document · front", document_back: "Document · back", selfie: "Selfie" };

type Verdict = { level: "pass" | "review" | "fail"; title: string; reasons: { ok: boolean; text: string }[] };
/** Recommendation shown to the reviewer ONLY. It never decides: a person presses Approve or Reject. It is built from the two advisory checks, so it says nothing about liveness, authenticity or AML. */
function verdict(c: Checks | null): Verdict | null {
  if (!c || !c.mrz) return null;
  const reasons: Verdict["reasons"] = []; let fail = false, review = false;
  const m = c.mrz.result;
  if (!m) { review = true; reasons.push({ ok: false, text: "No machine-readable zone could be read: check the document yourself." }); }
  else {
    const core = !!m.checks.document_number && !!m.checks.birth_date && !!m.checks.expiry_date;
    if (m.all_checks_passed) reasons.push({ ok: true, text: "Document check digits are all valid." });
    else if (core) { review = true; reasons.push({ ok: false, text: "Main fields are valid but the overall check failed (the end of the line was probably cut off)." }); }
    else { review = true; reasons.push({ ok: false, text: "Document check digits do not match (reading error or altered document)." }); }
    if ((c.mrz.agreeing ?? 0) >= 2) reasons.push({ ok: true, text: `${c.mrz.agreeing} independent readings agree.` });
    else if (m.all_checks_passed) { review = true; reasons.push({ ok: false, text: "Only one reading: compare the document number with the photo." }); }
    if (m.expired) { fail = true; reasons.push({ ok: false, text: "The document is expired." }); } else if (m.expired === false) reasons.push({ ok: true, text: "The document is not expired." });
  }
  const f = c.face;
  if (c.face_available === false) { review = true; reasons.push({ ok: false, text: "Face comparison is not available on the server." }); }
  else if (!f) return null;
  else if (f.status === "compared" && f.score !== null) {
    if (f.band === "high" || f.band === "possible") reasons.push({ ok: true, text: `Face similarity ${f.score.toFixed(2)} (${f.band === "high" ? "strong" : "moderate"}).` });
    else { review = true; reasons.push({ ok: false, text: `Face similarity is low (${f.score.toFixed(2)}): often a photo-quality issue, but it can be a different person.` }); }
  } else { review = true; reasons.push({ ok: false, text: f.status === "ambiguous" ? "Several faces in the selfie: no score." : "No face could be compared." }); }
  if (fail) return { level: "fail", title: "Recommendation: do NOT approve", reasons };
  if (review) return { level: "review", title: "Recommendation: needs your review", reasons };
  return { level: "pass", title: "Recommendation: looks consistent, you can approve", reasons };
}

/** Review panel: photos are decrypted by the API only for owners/admins and every view is audited. No automated analysis exists: a person decides. */
function Review({ v, orgId, onChange, onClose }: { v: V; orgId: string; onChange: () => void; onClose: () => void }) {
  const { org } = useAuth();
  const admin = org?.role === "owner" || org?.role === "admin";
  const [checks, setChecks] = useState<Checks | null>(null), [media, setMedia] = useState<Media[] | null>(null), [imgs, setImgs] = useState<Record<string, string>>({}), [err, setErr] = useState(""), [reason, setReason] = useState(""), [busy, setBusy] = useState(false);
  const base = `/organizations/${orgId}/verifications/${v.id}`;
  useEffect(() => {
    let live = true; const made: string[] = [];
    (async () => {
      try {
        const m = await api<Media[]>(`${base}/media`); if (!live) return; setMedia(m);
        if (!admin) return;
        api<Checks>(`${base}/checks`).then((c) => { if (live) setChecks(c); }).catch(() => {});
        const out: Record<string, string> = {};
        for (const x of m) { const b = await apiBlob(`${base}/media/${x.kind}`); if (b) { const u = URL.createObjectURL(b); made.push(u); out[x.kind] = u; } }
        if (live) setImgs(out);
      } catch (e) { if (live) setErr(e instanceof ApiError ? e.message : "Could not load the photos"); }
    })();
    return () => { live = false; made.forEach((u) => URL.revokeObjectURL(u)); };
  }, [base, admin, v.media_count]);
  // The readings run in the background a few seconds after the customer submits: poll (max ~2 min) until both results exist, so the reviewer does not see a stale "Not read yet".
  const waiting = admin && !!media && media.length > 0 && v.status === "MANUAL_REVIEW" && (!checks || !checks.mrz || (checks.face_available !== false && !checks.face) || (checks.pad_available !== false && !checks.pad));
  useEffect(() => {
    if (!waiting) return;
    let live = true, tries = 0;
    const t = setInterval(() => {
      if (++tries > 30) { clearInterval(t); return; }
      api<Checks>(`${base}/checks`).then((c) => { if (live) setChecks(c); }).catch(() => {});
    }, 4000);
    return () => { live = false; clearInterval(t); };
  }, [waiting, base]);
  const act = async (fn: () => Promise<unknown>) => { setBusy(true); setErr(""); try { await fn(); onChange(); } catch (e) { setErr(e instanceof ApiError ? e.message : "Action failed"); } finally { setBusy(false); } };
  return (
    <section className="mt-4 rounded-2xl border border-[#e3eaf8] bg-white p-5" aria-label="Verification review">
      <div className="flex items-start justify-between gap-3">
        <div><h2 className="font-display text-lg font-bold">{v.reference ?? "Verification"} <span className={`ml-2 rounded-full px-2.5 py-0.5 font-mono text-xs ${BADGE[v.status] ?? ""}`}>{v.status}</span></h2>
          <p className="mt-1 font-mono text-[11px] text-navy/50">{v.id}</p></div>
        <button onClick={onClose} className="rounded-full border border-[#d6e2ff] px-3 py-1 text-sm hover:bg-ice">Close</button>
      </div>
      {err && <p role="alert" className="mt-3 rounded-xl border border-[#f1b8b2] bg-[#FDECEA] p-3 text-sm text-[#B42318]">{err}</p>}
      {media === null && <p className="mt-3 text-sm text-navy/50">Loading…</p>}
      {media?.length === 0 && <p className="mt-3 text-sm text-navy/55">No photos stored{v.submitted_at ? " (deleted or past the retention period)" : " yet"}.</p>}
      {media && media.length > 0 && !admin && <p className="mt-3 text-sm text-navy/60">{media.length} photo(s) stored. Only owners and admins can view them.</p>}
      <div className="mt-3 grid gap-3 sm:grid-cols-3">
        {media?.map((m) => (
          <figure key={m.kind} className="rounded-xl border border-[#e3eaf8] p-2">
            {imgs[m.kind] ? /* eslint-disable-next-line @next/next/no-img-element */ <img src={imgs[m.kind]} alt={LABEL[m.kind]} className="max-h-56 w-full rounded-lg object-contain bg-[#F6F8FC]" /> : <div className="grid h-32 place-items-center rounded-lg bg-[#F6F8FC] text-xs text-navy/40">{admin ? "Loading…" : "Hidden"}</div>}
            <figcaption className="mt-1.5 text-xs text-navy/60"><b>{LABEL[m.kind]}</b>{m.doc_type ? ` · ${m.doc_type}` : ""}{m.country ? ` · ${m.country}` : ""}<br />{m.purge_after ? `Deleted automatically on ${new Date(m.purge_after).toLocaleDateString()}` : "Kept until a person deletes it"}</figcaption>
          </figure>
        ))}
      </div>
      {admin && (() => { const vd = verdict(checks); if (!vd) return null; const tone = vd.level === "pass" ? "border-[#ABEFC6] bg-[#E7F7EF] text-[#067647]" : vd.level === "fail" ? "border-[#FDA29B] bg-[#FDECEA] text-[#B42318]" : "border-[#FEDF89] bg-[#FEF3E2] text-[#B54708]";
        return (
          <div className={`mt-4 rounded-xl border p-4 ${tone}`} aria-label="Recommendation">
            <p className="font-display text-base font-bold">{vd.level === "pass" ? "✓ " : vd.level === "fail" ? "✗ " : "! "}{vd.title}</p>
            <ul className="mt-2 space-y-1 text-sm">{vd.reasons.map((r) => <li key={r.text}>{r.ok ? "✓" : "•"} {r.text}</li>)}</ul>
            <p className="mt-2 text-xs opacity-80">Advice only. These checks do NOT cover liveness (a replayed video or a mask can pass), whether the document is genuine, or sanctions/PEP screening. You decide with Approve or Reject.</p>
          </div>); })()}
      {admin && media && media.length > 0 && (
        <div className="mt-4 rounded-xl border border-[#e3eaf8] p-4" aria-label="MRZ reading">
          <div className="flex flex-wrap items-center justify-between gap-2">
            <h3 className="font-display text-sm font-bold">Machine-readable zone (automatic reading)</h3>
            <button disabled={busy} onClick={() => void act(async () => setChecks(await api<Checks>(`${base}/checks/mrz`, { method: "POST" })))} className="rounded-full border border-[#d6e2ff] px-3 py-1 text-xs hover:bg-ice disabled:opacity-50">Read again</button>
          </div>
          {!checks && <p className="mt-2 text-sm text-navy/50">Loading…</p>}
          {checks && !checks.mrz && <p className="mt-2 text-sm text-navy/55">Not read yet. It runs a few seconds after the customer submits and this panel refreshes by itself; you can also use “Read again”.</p>}
          {checks?.mrz?.status === "unavailable" && <p className="mt-2 text-sm text-[#B54708]">The reading engine is not installed on the server.</p>}
          {checks?.mrz?.status === "unreadable" && <p className="mt-2 text-sm text-navy/60">No machine-readable zone could be read from the document photos (the document may have none, or the photo is unclear). Check the photos yourself.</p>}
          {checks?.mrz?.result && (() => { const r = checks.mrz!.result!; return (
            <div className="mt-3 text-sm">
              {(() => { const core = !!r.checks.document_number && !!r.checks.birth_date && !!r.checks.expiry_date; const partial = !r.all_checks_passed && core;
                return <span className={`rounded-full px-2.5 py-0.5 font-mono text-xs ${r.all_checks_passed ? "bg-[#E7F7EF] text-[#067647]" : partial ? "bg-[#FEF3E2] text-[#B54708]" : "bg-[#FDECEA] text-[#B42318]"}`}>{r.all_checks_passed ? "All check digits valid" : partial ? "Main fields valid · overall check failed (end of line probably cut off)" : "Check digits do NOT match"}</span>; })()}
              {(checks.mrz!.agreeing ?? 0) >= 2 ? <span className="ml-2 rounded-full bg-[#E7F7EF] px-2.5 py-0.5 font-mono text-xs text-[#067647]">{checks.mrz!.agreeing} readings agree</span> : <span className="ml-2 rounded-full bg-[#FEF3E2] px-2.5 py-0.5 font-mono text-xs text-[#B54708]">single reading: verify on the photo</span>}
              {r.expired && <span className="ml-2 rounded-full bg-[#FDECEA] px-2.5 py-0.5 font-mono text-xs text-[#B42318]">EXPIRED</span>}
              <dl className="mt-3 grid grid-cols-[9rem_1fr] gap-y-1 text-xs">
                {([["Format", r.format], ["Document type", r.document_type], ["Issuing country", r.issuing_country], ["Surname", r.surname], ["Given names", r.given_names], ["Document number", r.document_number], ["Nationality", r.nationality], ["Birth date", r.birth_date ?? "—"], ["Sex", r.sex], ["Expiry date", r.expiry_date ?? "—"]] as [string, string][]).map(([k, val]) => (<div key={k} className="contents"><dt className="text-navy/55">{k}</dt><dd className="font-mono">{val}</dd></div>))}
              </dl>
              <ul className="mt-3 flex flex-wrap gap-2 text-xs">{Object.entries(r.checks).map(([k, ok]) => <li key={k} className={`rounded-full px-2.5 py-0.5 ${ok ? "bg-[#E7F7EF] text-[#067647]" : "bg-[#FDECEA] text-[#B42318]"}`}>{ok ? "✓" : "✗"} {CHECK_LABEL[k] ?? k}</li>)}</ul>
              {r.ocr_corrections > 0 && <p className="mt-2 text-xs text-[#B54708]">{r.ocr_corrections} character(s) were auto-corrected (typical OCR confusions): compare with the photo.</p>}
              {r.warnings.length > 0 && <ul className="mt-2 list-disc pl-5 text-xs text-[#B54708]">{r.warnings.map((w) => <li key={w}>{w}</li>)}</ul>}
            </div>); })()}
          <p className="mt-3 text-xs text-navy/45">Read by OCR from the photo; it can contain errors. One check digit is a single digit: a wrong reading passes it about 1 time in 10, so compare the document number with the photo, especially for a single reading. Nationality, sex and names have no check digit. Valid check digits show the text is internally consistent, not that the document is genuine. Accuracy was measured on generated pages and checked on only two real documents: treat it as advice.</p>
        </div>
      )}

      {admin && media && media.length > 0 && (
        <div className="mt-4 rounded-xl border border-[#e3eaf8] p-4" aria-label="Face comparison">
          <div className="flex flex-wrap items-center justify-between gap-2">
            <h3 className="font-display text-sm font-bold">Face comparison: document photo vs selfie (advisory)</h3>
            <button disabled={busy} onClick={() => void act(async () => { const r = await api<{ face: Face | null }>(`${base}/checks/face`, { method: "POST" }); setChecks((c) => (c ? { ...c, face: r.face } : c)); })} className="rounded-full border border-[#d6e2ff] px-3 py-1 text-xs hover:bg-ice disabled:opacity-50">Compare again</button>
          </div>
          {!checks && <p className="mt-2 text-sm text-navy/50">Loading…</p>}
          {checks && checks.face_available === false && <p className="mt-2 text-sm text-[#B54708]">The comparison engine is not installed on the server.</p>}
          {checks && checks.face_available !== false && !checks.face && <p className="mt-2 text-sm text-navy/55">Not computed yet (it needs the document front and the selfie). It refreshes by itself; you can also use “Compare again”.</p>}
          {checks?.face?.status === "no_doc_face" && <p className="mt-2 text-sm text-navy/60">No face could be found on the document photo. Look at the photos yourself.</p>}
          {checks?.face?.status === "no_selfie" && <p className="mt-2 text-sm text-navy/60">No face could be found on the selfie. Look at the photos yourself.</p>}
          {checks?.face?.status === "ambiguous" && <p className="mt-2 text-sm text-[#B54708]">The selfie shows several faces of similar size (for example the person and the ID portrait), so no score was computed. Look at the photos yourself.</p>}
          {checks?.face?.status === "error" && <p className="mt-2 text-sm text-[#B54708]">The comparison failed on these images.</p>}
          {checks?.face?.status === "compared" && checks.face.score !== null && (
            <div className="mt-3 text-sm">
              <span className={`rounded-full px-2.5 py-0.5 font-mono text-xs ${checks.face.band === "high" ? "bg-[#E7F7EF] text-[#067647]" : checks.face.band === "possible" ? "bg-[#FEF3E2] text-[#B54708]" : "bg-[#FDECEA] text-[#B42318]"}`}>
                {checks.face.band === "high" ? "Strong similarity" : checks.face.band === "possible" ? "Moderate similarity" : "Low similarity"} · score {checks.face.score.toFixed(2)}
              </span>
              <span className="ml-2 text-xs text-navy/50">threshold {checks.face.threshold} · {checks.face.model}</span>
              {checks.face.band === "low" && <p className="mt-2 text-xs text-[#B54708]">Below the model threshold. This does not prove it is another person: a small printed passport photo, lighting, angle or blur often lower the score for the same person. Compare the two photos yourself.</p>}
            </div>
          )}
          <p className="mt-3 text-xs text-navy/45">Experimental and advisory only: a person decides. In our first test on 17 real pairs, the same person typically scored 0.35 to 0.70 (median 0.49, so “Moderate” is normal) and different people mostly stayed below 0.30; indicative only. The model was not measured on our customers (skin tones, ages, photo quality), and a small printed photo is harder to match than a selfie. Always look at the two photos. No face template is stored, only this number.</p>
        </div>
      )}

      {admin && media && media.length > 0 && (
        <div className="mt-4 rounded-xl border border-[#e3eaf8] p-4" aria-label="Presentation attack check">
          <div className="flex flex-wrap items-center justify-between gap-2">
            <h3 className="font-display text-sm font-bold">Live capture check (experimental, selfie only)</h3>
            <button disabled={busy} onClick={() => void act(async () => { const r = await api<{ pad: Pad | null; pad_available: boolean }>(`${base}/checks/pad`, { method: "POST" }); setChecks((c) => (c ? { ...c, pad: r.pad, pad_available: r.pad_available } : c)); })} className="rounded-full border border-[#d6e2ff] px-3 py-1 text-xs hover:bg-ice disabled:opacity-50">Run again</button>
          </div>
          {!checks && <p className="mt-2 text-sm text-navy/50">Loading…</p>}
          {checks && checks.pad_available === false && <p className="mt-2 text-sm text-[#B54708]">The model is not installed on the server.</p>}
          {checks && checks.pad_available !== false && !checks.pad && <p className="mt-2 text-sm text-navy/55">Not computed yet; it refreshes by itself, or use “Run again”.</p>}
          {checks?.pad?.status === "no_face" && <p className="mt-2 text-sm text-navy/60">No face could be found in the selfie. Look at the photo yourself.</p>}
          {checks?.pad?.status === "error" && <p className="mt-2 text-sm text-[#B54708]">The check failed on this image.</p>}
          {checks?.pad?.status === "scored" && checks.pad.real_probability !== null && (
            <div className="mt-2">
              <span className={`rounded-full px-2.5 py-0.5 font-mono text-xs ${checks.pad.band === "high" ? "bg-[#E7F7EF] text-[#067647]" : checks.pad.band === "low" ? "bg-[#FDECEA] text-[#B42318]" : "bg-[#FEF3E2] text-[#B54708]"}`}>
                {checks.pad.band === "high" ? "Looks like a live capture" : checks.pad.band === "low" ? "Looks like a photo or a screen" : "Uncertain"} · {Math.round(checks.pad.real_probability * 100)} %
              </span>
              <span className="ml-2 text-xs text-navy/50">{Object.entries(checks.pad.per_model).map(([k, x]) => `${k} ${Math.round(x * 100)} %`).join(" · ")}</span>
            </div>)}
          <p className="mt-3 text-xs leading-relaxed text-navy/50">Experimental and advisory: a person decides. It is NOT certified liveness. It looks at one still image for signs of a printed photo or a screen; it has not been tested on masks, deepfakes or a virtual camera, nor measured on our users (skin tones, phones, lighting), and its thresholds are not calibrated. A good score does not prove the person was present. This is separate from the face comparison above.</p>
        </div>
      )}

      {v.decision_reason && <p className="mt-3 text-sm">Decision note: {v.decision_reason}</p>}
      {admin && v.status === "MANUAL_REVIEW" && (
        <div className="mt-4 flex flex-wrap items-end gap-3 border-t border-[#e3eaf8] pt-4">
          <label className="min-w-[14rem] flex-1 text-sm font-medium">Note (optional)<input value={reason} maxLength={200} onChange={(e) => setReason(e.target.value)} className="mt-1.5 block w-full rounded-xl border border-[#d6e2ff] px-3 py-2 text-sm font-normal" /></label>
          <button disabled={busy} onClick={() => void act(() => api(`${base}/decision`, { method: "POST", json: { decision: "APPROVED", reason: reason.trim() || undefined } }))} className="rounded-full bg-[#12B76A] px-5 py-2 text-sm font-semibold text-white disabled:opacity-50">Approve</button>
          <button disabled={busy} onClick={() => void act(() => api(`${base}/decision`, { method: "POST", json: { decision: "REJECTED", reason: reason.trim() || undefined } }))} className="rounded-full bg-[#D92D20] px-5 py-2 text-sm font-semibold text-white disabled:opacity-50">Reject</button>
        </div>
      )}
      {admin && media && media.length > 0 && (
        <button disabled={busy} onClick={() => { if (confirm("Delete all photos of this verification now? This cannot be undone.")) void act(() => api(`${base}/media`, { method: "DELETE" })); }} className="mt-3 text-sm text-[#B42318] underline disabled:opacity-50">Delete photos now</button>
      )}
      <p className="mt-3 text-xs text-navy/45">This is a manual review: no automated check (document authenticity, face match, liveness, AML) has been run on these photos.</p>
    </section>
  );
}
const BADGE: Record<string, string> = { PENDING: "bg-[#FEF3E2] text-[#B54708]", EXPIRED: "bg-[#EEF0F4] text-navy/60", APPROVED: "bg-[#E7F7EF] text-[#067647]", REJECTED: "bg-[#FDECEA] text-[#B42318]", MANUAL_REVIEW: "bg-[#EEF4FF] text-blue" };
const when = (iso: string) => new Date(iso).toLocaleString(undefined, { month: "short", day: "2-digit", hour: "2-digit", minute: "2-digit" });

export default function Verifications() {
  const { org } = useAuth();
  const [rows, setRows] = useState<V[] | null>(null), [error, setError] = useState(""), [busy, setBusy] = useState(false);
  const [ref, setRef] = useState(""), [fresh, setFresh] = useState<{ url: string; reference: string | null } | null>(null), [copied, setCopied] = useState(false);
  const writable = can.readKeys(org);                                  // owner, admin, member
  const [open, setOpen] = useState<string | null>(null);

  const load = useCallback(async () => {
    if (!org) return;
    try { setRows(await api<V[]>(`/verifications?organization_id=${org.id}&limit=100`)); setError(""); } catch (e) { setError(e instanceof ApiError ? e.message : "Could not load verifications"); setRows([]); }
  }, [org]);
  useEffect(() => { setRows(null); setFresh(null); setOpen(null); void load(); }, [load]);

  const create = async (e: FormEvent) => {
    e.preventDefault(); if (!org) return; setBusy(true); setError("");
    try {
      const v = await api<V & { url: string }>("/verifications", { method: "POST", json: { organization_id: org.id, reference: ref.trim() || undefined } });
      setFresh({ url: v.url, reference: v.reference }); setCopied(false); setRef(""); await load();
    } catch (er) { setError(er instanceof ApiError ? (er.details[0] ? `${er.details[0].field}: ${er.details[0].message}` : er.message) : "Could not create the verification"); } finally { setBusy(false); }
  };
  const copy = async () => { try { await navigator.clipboard.writeText(fresh?.url ?? ""); setCopied(true); } catch { setCopied(false); } };

  return (
    <>
      <h1 className="font-display text-2xl font-extrabold tracking-tight md:text-3xl">Verifications</h1>
      <p className="mt-1 text-sm text-navy/60">Create a verification link for one of your customers and follow its status.</p>
      <p className="mt-3 rounded-xl border border-[#d6e2ff] bg-ice p-3 text-sm text-navy/70">
        Customers send their ID photos and selfie through the link; photos are stored encrypted and kept until you delete them. The server reads the passport/ID MRZ with OCR and checks its check digits, but there is no automated decision: submitted verifications wait in <b>MANUAL_REVIEW</b> for a person to approve or reject them.
      </p>

      {writable && (
        <form onSubmit={create} className="mt-5 flex flex-wrap items-end gap-3 rounded-2xl border border-[#e3eaf8] bg-white p-4">
          <label className="min-w-[14rem] flex-1 text-sm font-medium">Reference (optional)
            <input value={ref} onChange={(e) => setRef(e.target.value)} maxLength={100} placeholder="your customer id, e.g. cust-42" className="mt-1.5 block w-full rounded-xl border border-[#d6e2ff] px-3 py-2.5 text-sm font-normal" /></label>
          <button disabled={busy} className="rounded-full bg-blue px-6 py-2.5 text-sm font-semibold text-white hover:bg-navy disabled:opacity-50">{busy ? "Creating…" : "Create verification link"}</button>
        </form>
      )}

      {fresh && (
        <section className="mt-4 rounded-2xl border border-[#b7e8cf] bg-[#F3FBF7] p-4" aria-label="New verification link">
          <h2 className="font-display text-sm font-bold">Link created{fresh.reference ? ` · ${fresh.reference}` : ""}. Copy it now: it is shown only once.</h2>
          <div className="mt-2 flex flex-wrap items-center gap-2">
            <code className="min-w-0 flex-1 break-all rounded-lg bg-white p-2.5 font-mono text-xs">{fresh.url}</code>
            <button onClick={() => void copy()} className="rounded-full border border-[#d6e2ff] bg-white px-4 py-2 text-sm hover:bg-ice">{copied ? "Copied ✓" : "Copy"}</button>
            <a href={fresh.url} target="_blank" rel="noopener" className="rounded-full border border-[#d6e2ff] bg-white px-4 py-2 text-sm text-blue hover:bg-ice">Open ↗</a>
          </div>
        </section>
      )}

      {error && <p role="alert" className="mt-4 rounded-xl border border-[#f1b8b2] bg-[#FDECEA] p-3 text-sm text-[#B42318]">{error}</p>}

      {org && rows?.find((x) => x.id === open) && <Review key={open} v={rows.find((x) => x.id === open)!} orgId={org.id} onChange={() => void load()} onClose={() => setOpen(null)} />}

      <div className="mt-4 overflow-x-auto rounded-2xl border border-[#e3eaf8] bg-white">
        <table className="w-full text-left text-sm">
          <thead className="bg-[#F6F8FC] font-mono text-[11px] text-navy/60"><tr>{["Created", "Reference", "Env", "Status", "Photos", "Expires", ""].map((h) => <th key={h} className="p-3 font-medium">{h}</th>)}</tr></thead>
          <tbody>
            {rows === null && <tr><td colSpan={7} className="p-6 text-center text-navy/50">Loading…</td></tr>}
            {rows?.length === 0 && <tr><td colSpan={7} className="p-6 text-center text-navy/50">No verifications yet. Create a link above or call <code className="font-mono">POST /api/v1/verifications</code> with an API key.</td></tr>}
            {rows?.map((v) => (
              <tr key={v.id} className="border-t border-[#e3eaf8]">
                <td className="p-3 font-mono text-xs">{when(v.created_at)}</td><td className="p-3">{v.reference ?? <span className="text-navy/40">—</span>}</td>
                <td className="p-3 font-mono text-xs">{v.env}</td>
                <td className="p-3"><span className={`rounded-full px-2.5 py-0.5 font-mono text-xs ${BADGE[v.status] ?? ""}`}>{v.status}</span></td>
                <td className="p-3 text-xs">{v.media_count || "—"}</td><td className="p-3 font-mono text-xs">{when(v.expires_at)}</td>
                <td className="p-3"><button onClick={() => setOpen(open === v.id ? null : v.id)} className="rounded-full border border-[#d6e2ff] px-3 py-1 text-xs hover:bg-ice">{open === v.id ? "Hide" : "Open"}</button></td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </>
  );
}
