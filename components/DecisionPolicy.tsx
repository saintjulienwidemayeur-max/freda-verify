"use client";
import { useCallback, useEffect, useState } from "react";
import { api, ApiError } from "@/lib/api";
import { can, useAuth } from "@/lib/auth";

type Policy = { mode: "manual" | "auto"; uncertain: "review" | "reject"; face_min: number; require_pad: boolean; id_cards: "review" | "face_and_data" | "face_only" };

/** Decision mode of the organization. In AUTO mode the system approves / rejects submitted verifications by fixed rules; a person can always override an automatic decision. */
export default function DecisionPolicy() {
  const { org } = useAuth(); const admin = can.manageKeys(org);
  const [p, setP] = useState<Policy | null>(null), [saved, setSaved] = useState(false), [err, setErr] = useState(""), [busy, setBusy] = useState(false);
  const base = org ? `/organizations/${org.id}/decision-policy` : "";
  const load = useCallback(async () => { if (!org) return; try { setP(await api<Policy>(base)); } catch { /* shown as loading */ } }, [org, base]);
  useEffect(() => { setP(null); void load(); }, [load]);
  if (!p) return null;
  const save = async (next: Policy) => { setBusy(true); setErr(""); setSaved(false); try { setP(await api<Policy>(base, { method: "PUT", json: next })); setSaved(true); } catch (e) { setErr(e instanceof ApiError ? e.message : "Could not save"); } finally { setBusy(false); } };
  const set = (k: Partial<Policy>) => setP({ ...p, ...k });
  return (
    <section className="mt-5 rounded-2xl border border-[#e3eaf8] bg-white p-5" aria-label="Decision mode">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <h2 className="font-display text-base font-bold">Decision mode</h2>
        <span className={`rounded-full px-2.5 py-0.5 font-mono text-xs ${p.mode === "auto" ? "bg-[#E7F7EF] text-[#067647]" : "bg-[#FEF3E2] text-[#B54708]"}`}>{p.mode === "auto" ? "Automatic" : "Manual (a person decides)"}</span>
      </div>
      <p className="mt-1 text-sm text-navy/60">Automatic: the system approves or rejects a submitted verification by the rules below and tells the customer. A person can always override it from the review panel. Every automatic decision is audited.</p>
      <div className="mt-4 grid gap-4 md:grid-cols-2">
        <label className="text-sm font-medium">Mode
          <select disabled={!admin} value={p.mode} onChange={(e) => set({ mode: e.target.value as Policy["mode"] })} className="mt-1.5 block w-full rounded-xl border border-[#d6e2ff] bg-white px-3 py-2.5 text-sm font-normal">
            <option value="manual">Manual: a person decides</option><option value="auto">Automatic</option></select></label>
        <label className="text-sm font-medium">When the result is not clear
          <select disabled={!admin || p.mode === "manual"} value={p.uncertain} onChange={(e) => set({ uncertain: e.target.value as Policy["uncertain"] })} className="mt-1.5 block w-full rounded-xl border border-[#d6e2ff] bg-white px-3 py-2.5 text-sm font-normal">
            <option value="review">Send to a person (recommended)</option><option value="reject">Reject automatically</option></select></label>
        <label className="text-sm font-medium">Minimum face similarity to approve ({p.face_min.toFixed(2)})
          <input type="range" min={0.2} max={0.9} step={0.01} disabled={!admin || p.mode === "manual"} value={p.face_min} onChange={(e) => set({ face_min: Number(e.target.value) })} className="mt-2 block w-full" />
          <span className="text-xs font-normal text-navy/50">Published model threshold 0.363. In our tests ~13 % of the same people scored below it and ~1 % of different people reached it.</span></label>
        <label className="text-sm font-medium md:col-span-2">ID cards and licences (no machine-readable zone)
          <select disabled={!admin || p.mode === "manual"} value={p.id_cards} onChange={(e) => set({ id_cards: e.target.value as Policy["id_cards"] })} className="mt-1.5 block w-full rounded-xl border border-[#d6e2ff] bg-white px-3 py-2.5 text-sm font-normal">
            <option value="review">Always send to a person (recommended)</option>
            <option value="face_and_data">Approve if the face matches AND the printed text agrees with the data the customer declared</option>
            <option value="face_only">Approve if the face matches (NO document check: risky)</option></select>
          {p.id_cards === "face_only" && <span className="mt-1 block text-xs font-normal text-[#B42318]">Anyone who shows a forged or someone else&apos;s card with a matching face would be approved. Nothing verifies the document content.</span>}
          {p.id_cards === "face_and_data" && <span className="mt-1 block text-xs font-normal text-[#B54708]">Needs at least 2 declared fields (name + birth date or ID number) when you create the verification. Reading printed text is unreliable and a forged card can carry the declared data.</span>}</label>
        <label className="flex items-start gap-2 text-sm font-medium"><input type="checkbox" disabled={!admin || p.mode === "manual"} checked={p.require_pad} onChange={(e) => set({ require_pad: e.target.checked })} className="mt-1 h-4 w-4" />
          <span>Also require the experimental live-capture score<span className="block text-xs font-normal text-navy/50">Not recommended yet: in our tests about 1 live person in 5 scored low.</span></span></label>
      </div>
      <ul className="mt-4 list-disc space-y-1 pl-5 text-xs text-navy/60">
        <li><b>Approved</b> only if (passports): every document check digit is valid, at least 2 independent readings agree, the document is not expired, and the face similarity reaches the minimum.</li>
        <li><b>Rejected</b> automatically only for an objective failure: an expired document whose expiry date was read correctly.</li>
        <li>Anything else is “not clear”: sent to a person, or rejected if you chose that. Rejecting unclear cases WILL turn away some real people.</li>
        <li>These checks are not certified: they do not prove the person is live or the document genuine, and they do not cover sanctions or PEP screening.</li>
      </ul>
      {err && <p role="alert" className="mt-3 text-sm text-[#B42318]">{err}</p>}
      {admin && <div className="mt-4 flex items-center gap-3"><button disabled={busy} onClick={() => void save(p)} className="rounded-full bg-blue px-5 py-2.5 text-sm font-semibold text-white hover:bg-navy disabled:opacity-60">Save</button>{saved && <span className="text-sm text-[#067647]">Saved ✓</span>}</div>}
    </section>
  );
}
