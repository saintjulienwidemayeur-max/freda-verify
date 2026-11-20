import Link from "next/link";

/** Honest placeholder for a page whose backend does not exist yet: no invented data. */
export default function EmptyState({ title, intro, body }: { title: string; intro: string; body: string }) {
  return (
    <>
      <h1 className="font-display text-2xl font-extrabold tracking-tight md:text-3xl">{title}</h1>
      <p className="mt-1 text-sm text-navy/60">{intro}</p>
      <section className="mt-6 rounded-2xl border border-dashed border-[#d6e2ff] bg-white p-8 text-center">
        <p className="mx-auto max-w-xl text-sm text-navy/65">{body}</p>
        <Link href="/dashboard/api-keys" className="mt-5 inline-block rounded-full border border-[#d6e2ff] px-5 py-2 text-sm font-medium text-blue hover:bg-ice">Manage API keys</Link>
      </section>
    </>
  );
}
