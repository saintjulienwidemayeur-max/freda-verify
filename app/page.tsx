import Link from "next/link";
import FaceMatch from "@/components/FaceMatch";
import { Platform, Developers, AmlScreening, Services, Industries, Workflow, Audit, Integration, Security, Faq, Contact } from "@/components/Sections";

const FEATURES = [
  ["Un seul compte, une seule API", "Comptes, équipes, rôles et clés API (test et live) sont disponibles aujourd'hui."],
  ["Page de vérification marque blanche", "Configurez le nom, les couleurs et la langue de la page que voient vos clients. Version de démonstration pour l'instant."],
  ["Traçabilité", "Journal des requêtes API et journal d'audit des actions, déjà actifs dans le tableau de bord."],
  ["KYC, KYB, AML : prévu", "Le moteur de vérification (documents, visage, AML, entreprises) est en cours de construction et n'est pas encore disponible."],
];
const PLANS = [
  ["Starter", "À définir", "offre d'essai prévue"],
  ["Growth", "À définir", "tarif par vérification"],
  ["Enterprise", "Sur devis", "volumes et engagements"],
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
              Vérification d&apos;identité pour les entreprises. En construction.
            </h1>
            <p className="mx-auto mt-6 max-w-lg text-base text-navy">
              Freda Verify prépare une API de vérification d&apos;identité (KYC, KYB, AML). Aujourd&apos;hui : comptes, clés API, journaux et une page de vérification de démonstration. Le moteur de vérification n&apos;est pas encore disponible.
            </p>
            <Link href="/signup" className="mt-8 inline-flex rounded-full bg-blue px-6 py-3 text-sm font-semibold text-white hover:bg-navy [text-shadow:none]">Créer un compte ↗</Link>
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
            Prévu : comparer le selfie à la photo de la pièce d&apos;identité et renvoyer un score de similarité. Cette comparaison n&apos;existe pas encore ; l&apos;animation ci-contre est une illustration, ses scores sont scriptés.
          </p>
        </div>
        <FaceMatch />
      </section>
      <Developers />
      <AmlScreening />
      <section id="solutions" className="py-16">
        <h2 className="max-w-xl text-4xl font-extrabold tracking-tighter">Ce qui existe, et ce qui est prévu.</h2>
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
        <h2 className="text-4xl font-extrabold tracking-tighter">Tarification</h2>
        <p className="mt-3 max-w-xl text-sm">Les tarifs ne sont pas encore fixés.</p>
        <div className="mt-8 grid gap-4 md:grid-cols-3">
          {PLANS.map(([n, p, d]) => (
            <div key={n} className="rounded-2xl border border-[#d6e2ff] p-6"><div className="font-bold">{n}</div><div className="my-2 text-4xl font-extrabold">{p}</div><div className="text-sm">{d}</div></div>
          ))}
        </div>
      </section>

      <Faq />
      <Contact />
      <footer id="insights" className="flex flex-wrap justify-between gap-3 border-t border-[#d6e2ff] py-8 text-sm">
        <span>© 2026 Freda Verify</span><span>Version préliminaire</span>
      </footer>
      </div>
    </div>
  );
}
