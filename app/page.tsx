import Link from "next/link";
import FaceMatch from "@/components/FaceMatch";
import { Platform, Developers, AmlScreening, Services, Industries, Workflow, Audit, Integration, Security, Faq, Contact } from "@/components/Sections";

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
          <Link href="/login">Se connecter</Link>
          <Link href="/signup" className="rounded-full bg-blue px-5 py-2.5 font-semibold text-white hover:bg-navy">Essayez maintenant</Link>
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
            <a href="#contact" className="mt-8 inline-flex rounded-full bg-blue px-6 py-3 text-sm font-semibold text-white hover:bg-navy [text-shadow:none]">Start Verifying ↗</a>
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
        <div className="pb-16" />
      </section>

      </div>
      </div>
      <div className="mx-auto max-w-6xl px-5">
      <Platform />
      <section id="face-match" className="grid items-center gap-10 py-16 md:grid-cols-2">
        <div>
          <p className="font-mono text-xs uppercase tracking-widest text-blue">Correspondance faciale</p>
          <h2 className="mt-3 text-4xl font-extrabold tracking-tighter">Le selfie, comparé à la pièce d&apos;identité.</h2>
          <p className="mt-4 max-w-md text-base text-navy/80">
            Compare le selfie en direct à la photo sur la pièce d&apos;identité, sans seconde capture ni étape supplémentaire. Obtiens un score de similarité, une décision et tous les drapeaux de risque dans la même réponse.
          </p>
        </div>
        <FaceMatch />
      </section>
      <Developers />
      <AmlScreening />
      <section id="solutions" className="py-16">
        <h2 className="max-w-xl text-4xl font-extrabold tracking-tighter">One platform for every identity decision.</h2>
        <div className="mt-10 grid gap-4 md:grid-cols-4">
          {FEATURES.map(([t, d]) => (
            <div key={t} className="rounded-2xl border border-[#d6e2ff] bg-ice p-6"><h3 className="font-bold">{t}</h3><p className="mt-2 text-sm">{d}</p></div>
          ))}
        </div>
      </section>

      <Services />
      <Industries />
      <Workflow />
      <Audit />

      <Integration />
      <Security />
      <section id="pricing" className="py-16">
        <h2 className="text-4xl font-extrabold tracking-tighter">Pricing</h2>
        <div className="mt-8 grid gap-4 md:grid-cols-3">
          {PLANS.map(([n, p, d]) => (
            <div key={n} className="rounded-2xl border border-[#d6e2ff] p-6"><div className="font-bold">{n}</div><div className="my-2 text-4xl font-extrabold">{p}</div><div className="text-sm">{d}</div></div>
          ))}
        </div>
      </section>

      <Faq />
      <Contact />
      <footer id="insights" className="flex flex-wrap justify-between gap-3 border-t border-[#d6e2ff] py-8 text-sm">
        <span>© 2026 Freda Verify</span><span>Docs · Status · Privacy</span>
      </footer>
      </div>
    </div>
  );
}
