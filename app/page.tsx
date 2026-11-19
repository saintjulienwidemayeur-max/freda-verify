import Link from "next/link";
import Demo from "@/components/Demo";
import { Platform, Developers, AmlScreening, Services, Industries, Workflow, Audit, Integration, Security, Faq, Contact } from "@/components/Sections";

const LOGOS = ["Northwind", "lumen", "HALCYON", "Ardent", "kestrel.io", "VANTA"];
const FEATURES = [
  ["Fully automated", "Documents, selfies and business registries are checked in seconds, with no manual review queue."],
  ["KYC and KYB, one API", "Verify people and companies in the same flow, with the same response format."],
  ["Liveness that catches fakes", "Printed photos, replayed screens and deepfakes are stopped before a decision is made."],
  ["Built for your region", "Local IDs and registries, with data kept where your regulator expects it."],
];
const PLANS = [
  ["Starter", "$0", "100 checks / month"],
  ["Growth", "$0.40", "per verification"],
  ["Enterprise", "Custom", "volume pricing and SLA"],
];

export default function Home() {
  return (
    <div>
      <div className="bg-white">
      <div className="mx-auto max-w-6xl px-5">
      <header className="relative z-20 flex items-center justify-between py-5 text-sm">
        <Link href="/" className="flex items-center gap-2 font-display text-lg font-extrabold tracking-tight">
          {/* eslint-disable-next-line @next/next/no-img-element */}
          <img src="/logo-mark.svg" alt="" className="h-9 w-9" />Freda <span className="text-electric">Verify</span>
        </Link>
        <nav className="hidden gap-8 md:flex"><a href="#insights">Connaissances</a><a href="#solutions">Solutions</a><a href="#pricing">Tarification</a></nav>
        <div className="flex items-center gap-4">
          <Link href="/dashboard">Se connecter</Link>
          <a href="#demo" className="rounded-full bg-blue px-5 py-2.5 font-semibold text-white hover:bg-navy">Essayez maintenant</a>
        </div>
      </header>

      <section className="text-center">
        {/* Hauteur de l'image montée : mobile: bottom-[8vw] sur l'image (plus grand = plus haut), PC: pb 0.29 (plus petit = plus haut) */}
        <div
          className="relative left-1/2 w-screen -translate-x-1/2 overflow-hidden px-5 pt-14 pb-0 md:pb-[calc(100vw*941/1671*0.29)]"
        >
          <div className="relative z-10 [text-shadow:0_0_10px_#ffffff,0_0_3px_#ffffff]">
            <h1 className="mx-auto max-w-3xl text-5xl font-extrabold leading-[0.95] tracking-tighter md:text-7xl">
              Vérification d&apos;identité automatisée conçue pour la rapidité.
            </h1>
            <p className="mx-auto mt-6 max-w-lg text-base text-navy">
              Vérifiez les personnes et les entreprises en quelques secondes. Lecture de documents, reconnaissance faciale et détection de fraude en un seul appel.
            </p>
            <a href="#demo" className="mt-8 inline-flex rounded-full bg-blue px-6 py-3 text-sm font-semibold text-white hover:bg-navy [text-shadow:none]">Start Verifying ↗</a>
          </div>
          {/* Arrière-plan (mobile et PC) : ancré en bas, le haut s'estompe pour garder le texte lisible */}
          {/* eslint-disable-next-line @next/next/no-img-element */}
          <img
            src="/hero.png" alt="" aria-hidden
            className="pointer-events-none absolute bottom-[8vw] left-0 block md:bottom-0 h-auto w-full select-none opacity-80"
            style={{
              maskImage: "linear-gradient(to bottom, transparent 0%, #000 34%)",
              WebkitMaskImage: "linear-gradient(to bottom, transparent 0%, #000 34%)",
            }}
          />
        </div>
        <p className="mt-6 text-sm">Trusted by tech leaders and regional businesses</p>
        <div className="mt-5 flex flex-wrap items-center justify-center gap-x-10 gap-y-3 pb-16 text-lg font-semibold opacity-80">
          {LOGOS.map((l) => <span key={l}>{l}</span>)}
        </div>
      </section>

      </div>
      </div>
      <div className="mx-auto max-w-6xl px-5">
      <Platform />
      <Developers />
      <AmlScreening />
      <section id="solutions" className="border-t border-navy/80 py-16">
        <h2 className="max-w-xl text-4xl font-extrabold tracking-tighter">One platform for every identity decision.</h2>
        <div className="mt-10 grid gap-px border border-navy/80 bg-navy md:grid-cols-4">
          {FEATURES.map(([t, d]) => (
            <div key={t} className="bg-ice p-6"><h3 className="font-bold">{t}</h3><p className="mt-2 text-sm">{d}</p></div>
          ))}
        </div>
      </section>

      <Services />
      <Industries />
      <Workflow />
      <Audit />
      <section id="demo" className="border-t border-navy/80 py-16">
        <h2 className="mb-2 text-4xl font-extrabold tracking-tighter">See a check run.</h2>
        <p className="mb-8 text-sm">Simulated data. No account needed.</p>
        <Demo />
      </section>

      <Integration />
      <Security />
      <section id="pricing" className="border-t border-navy/80 py-16">
        <h2 className="text-4xl font-extrabold tracking-tighter">Pricing</h2>
        <div className="mt-8 grid gap-4 md:grid-cols-3">
          {PLANS.map(([n, p, d]) => (
            <div key={n} className="rounded-2xl border border-navy/80 p-6"><div className="font-bold">{n}</div><div className="my-2 text-4xl font-extrabold">{p}</div><div className="text-sm">{d}</div></div>
          ))}
        </div>
      </section>

      <Faq />
      <Contact />
      <footer id="insights" className="flex flex-wrap justify-between gap-3 border-t border-navy/80 py-8 text-sm">
        <span>© 2026 Freda Verify</span><span>Docs · Status · Privacy</span>
      </footer>
      </div>
    </div>
  );
}
