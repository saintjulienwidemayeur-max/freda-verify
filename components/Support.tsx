import Link from "next/link";

const FAQ: [string, string][] = [
  ["How long does a verification take?", "Most KYC and KYB checks return a decision in a few seconds. Cases flagged for manual review take longer."],
  ["What is the difference between Test and Live keys?", "Test keys let you try the API without real checks. Live keys run real verifications and are billed."],
  ["What happens if a key is compromised?", "Revoke it immediately from the API Keys page and create a new one. Revoked keys stop working right away."],
  ["Why was a verification rejected?", "Open the request in Logs to see the response, including the score and the reason code returned with the decision."],
  ["Where is my data stored?", "Data is kept in the region you choose, with encryption and a configurable retention period."],
];
const LINKS: [string, string, string][] = [
  ["API Keys", "/dashboard/api-keys", "Create, copy and revoke keys."],
  ["Logs", "/dashboard/logs", "Inspect requests and responses."],
  ["Integration guide", "/#integration", "REST API, SDKs and hosted page."],
];

export default function Support() {
  return (
    <div className="max-w-3xl space-y-4">
      <div>
        <h1 className="font-display text-2xl font-extrabold tracking-tight md:text-3xl">Support &amp; Help</h1>
        <p className="mt-1 text-sm text-navy/60">Find answers fast, or get in touch with the team.</p>
      </div>

      <div className="flex items-center gap-3 rounded-2xl border border-[#b7e8cf] bg-[#E7F7EF] p-4 text-sm">
        <span className="h-2.5 w-2.5 rounded-full bg-ok" /><span className="font-semibold text-[#067647]">All systems operational</span><span className="text-navy/55">· sample status</span>
      </div>

      <section className="grid gap-4 sm:grid-cols-3">
        {LINKS.map(([t, href, d]) => (
          <Link key={t} href={href} className="rounded-2xl border border-[#e3eaf8] bg-white p-4 hover:border-blue">
            <div className="font-display font-bold">{t} <span className="text-blue">↗</span></div><p className="mt-1 text-sm text-navy/60">{d}</p>
          </Link>
        ))}
      </section>

      <section className="rounded-2xl border border-[#e3eaf8] bg-white p-5">
        <h2 className="font-display text-lg font-bold">Frequently asked questions</h2>
        <div className="mt-3 divide-y divide-[#e3eaf8]">
          {FAQ.map(([q, a]) => (
            <details key={q} className="group py-3">
              <summary className="flex cursor-pointer list-none items-center justify-between gap-3 text-sm font-medium">{q}<span className="text-blue transition-transform group-open:rotate-45">+</span></summary>
              <p className="mt-2 text-sm text-navy/70">{a}</p>
            </details>
          ))}
        </div>
      </section>

      <section className="rounded-2xl border border-[#e3eaf8] bg-white p-5">
        <h2 className="font-display text-lg font-bold">Still need help?</h2>
        <p className="mt-1 text-sm text-navy/60">Tell us about your case and we will get back to you.</p>
        <Link href="/#contact" className="mt-4 inline-flex rounded-full bg-blue px-6 py-2.5 text-sm font-semibold text-white hover:bg-navy">Contact the team</Link>
      </section>
    </div>
  );
}
