import type { ReactNode } from "react";
import ApiHub from "./ApiHub";
import AmlCard from "./AmlCard";

function Sec({ id, title, sub, children }: { id?: string; title: string; sub?: string; children: ReactNode }) {
  return (
    <section id={id} className="py-16">
      <h2 className="max-w-2xl text-4xl font-extrabold tracking-tighter">{title}</h2>
      {sub && <p className="mt-3 max-w-xl text-sm">{sub}</p>}
      <div className="mt-10">{children}</div>
    </section>
  );
}

const Grid = ({ items, cols = "md:grid-cols-3" }: { items: string[][]; cols?: string }) => (
  <div className={`grid gap-4 ${cols}`}>
    {items.map(([t, d]) => (
      <div key={t} className="rounded-2xl border border-[#d6e2ff] bg-ice p-6">
        <h3 className="font-bold">{t}</h3>
        <p className="mt-2 text-sm">{d}</p>
      </div>
    ))}
  </div>
);

export function Services() {
  return (
    <Sec title="Tous les contrôles d'identité, dans un seul flux." sub="Feuille de route : seules les démos de capture sont utilisables aujourd'hui, rien ne produit encore de verdict de vérification.">
      <Grid items={[
        ["Vérification de documents · démo", "Capture guidée dans le navigateur (cadrage, passeport avec photo et lignes MRZ). Rien n'est envoyé ni authentifié ; la lecture OCR et le contrôle d'authenticité sont prévus."],
        ["Visage · démo", "Défi de rotation de la tête dans le navigateur (pas une détection de vivacité certifiée). La comparaison selfie / photo du document fournit un score indicatif au réviseur humain ; elle n'est pas mesurée sur nos clients et ne décide de rien."],
        ["Vérification d'adresse · prévu", "Non disponible."],
        ["Filtrage AML · prévu", "Aucune liste de sanctions ou de PEP n'est branchée à ce jour. Les sources de données restent à choisir."],
        ["KYB · prévu", "Non disponible."],
        ["Video KYC · prévu", "Non disponible."],
      ]} />
    </Sec>
  );
}

export function Industries() {
  return (
    <Sec id="industries" title="Conçu pour les secteurs régulés.">
      <Grid items={[
        ["Banque", "Ouverture de compte à distance et mise à jour périodique des dossiers clients."],
        ["Fintech et wallet", "Onboarding rapide et limites de transaction selon le niveau vérifié."],
        ["E-commerce", "Réduction de la fraude à l'inscription et aux paiements à risque."],
        ["Marketplaces", "Vérification des vendeurs et des prestataires avant leur premier paiement."],
        ["Télécom", "Activation de lignes et de comptes mobile money avec pièce vérifiée."],
        ["Assurance", "Souscription à distance et contrôle des bénéficiaires."],
      ]} />
    </Sec>
  );
}

export function Workflow() {
  const Box = ({ t, d, dark }: { t: string; d: string; dark?: boolean }) => (
    <div className={`rounded-2xl border border-[#d6e2ff] p-5 ${dark ? "bg-navy text-white" : ""}`}>
      <div className="font-bold">{t}</div><div className="mt-1 text-sm opacity-80">{d}</div>
    </div>
  );
  return (
    <Sec title="Le flux visé." sub="Prévu : des seuils configurables, avec revue manuelle quand le résultat est incertain. Le moteur de décision n'existe pas encore.">
      <div className="grid items-center gap-4 md:grid-cols-[1fr_auto_1fr_auto_1fr]">
        <Box t="1. Soumission" d="Document, selfie et données saisies par le client." />
        <span className="hidden text-2xl md:block">→</span>
        <Box t="2. Score de risque" d="Seuils et règles définis par votre équipe conformité." />
        <span className="hidden text-2xl md:block">→</span>
        <div className="grid gap-3">
          <Box dark t="Risque faible" d="Prévu : approbation automatique." />
          <Box t="Risque élevé" d="Prévu : contrôles supplémentaires ou revue manuelle." />
        </div>
      </div>
    </Sec>
  );
}

export function Audit() {
  return (
    <Sec title="Traçabilité." sub="Aujourd'hui : journal d'audit (qui a fait quoi, quand) et journal des requêtes API. Prévu : un dossier par vérification. L'exemple ci-dessous est une illustration du format visé, pas un enregistrement réel.">
      <pre className="overflow-x-auto rounded-2xl border border-[#d6e2ff] bg-white/60 p-5 font-mono text-xs leading-6">{`{
  "case_id": "case_20817",
  "type": "kyc",
  "checks": { "document": "pass", "face": "pass", "liveness": "pass", "aml": "review" },
  "reason_codes": ["PEP_POSSIBLE_MATCH"],
  "decision": "manual_review",
  "reviewer": "analyst_04",
  "created_at": "2026-09-30T10:14:02Z"
}`}</pre>
    </Sec>
  );
}

export function Integration() {
  return (
    <Sec id="integration" title="Intégrez comme vous voulez.">
      <Grid items={[
        ["API REST · en cours", "Clés API et journaux disponibles. Les points d'accès de vérification (documents, selfie, résultat) et les webhooks sont prévus."],
        ["SDK web et mobile · prévu", "Pas de SDK publié pour l'instant."],
        ["Page hébergée · démo", "Page de capture publique et personnalisable (marque blanche). Elle n'envoie aucune donnée à ce stade."],
      ]} />
    </Sec>
  );
}

export function Security() {
  return (
    <Sec id="security" title="Sécurité : ce qui est en place.">
      <Grid cols="md:grid-cols-2" items={[
        ["Accès protégés", "Mots de passe hachés (argon2id), double authentification TOTP, sessions révocables, rôles et isolation entre organisations."],
        ["Clés API", "Le secret n'est affiché qu'une fois ; seule une empreinte est stockée."],
        ["Journal d'audit", "Actions enregistrées de façon non modifiable au niveau de la base de données."],
        ["Prévu, pas encore en place", "Chiffrement des documents, durées de conservation, choix de la région, déploiement sur site, audit de sécurité externe."],
      ]} />
    </Sec>
  );
}

const FAQ = [
  ["Puis-je déjà vérifier des identités ?", "Pas encore. Le moteur de vérification (lecture des documents, comparaison faciale, AML) est en construction. Vous pouvez créer un compte, gérer votre équipe et vos clés API, et essayer la page de capture de démonstration."],
  ["Quels documents seront acceptés ?", "Cartes d'identité, passeports et permis sont visés. La liste dépendra des pays activés et n'est pas figée."],
  ["Les entreprises (KYB) ?", "Prévu, pas encore disponible."],
  ["Puis-je héberger la solution chez moi ?", "Pas à ce jour. Le déploiement sur site n'est pas décidé."],
  ["Y a-t-il un essai gratuit ?", "Les offres et les tarifs ne sont pas encore définis."],
];

export function Faq() {
  return (
    <Sec id="faq" title="Questions fréquentes">
      <div className="border-t border-[#d6e2ff]">
        {FAQ.map(([q, a]) => (
          <details key={q} className="group border-b border-[#d6e2ff] py-4">
            <summary className="cursor-pointer list-none font-bold">
              <span className="mr-3 inline-block transition-transform group-open:rotate-45">+</span>{q}
            </summary>
            <p className="mt-2 max-w-2xl pl-6 text-sm">{a}</p>
          </details>
        ))}
      </div>
    </Sec>
  );
}

export function Contact() {
  return (
    <Sec id="contact" title="Parlons de votre cas.">
      <a href="/signup" className="inline-flex rounded-full bg-blue px-6 py-3 text-sm font-semibold text-white hover:bg-navy">Créer un compte ↗</a>
    </Sec>
  );
}

const ICON = "h-12 w-12";
const IconFace = () => (
  <svg viewBox="0 0 48 48" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round" className={ICON} aria-hidden>
    <path d="M8 16v-6a2 2 0 0 1 2-2h6M32 8h6a2 2 0 0 1 2 2v6M40 32v6a2 2 0 0 1-2 2h-6M16 40h-6a2 2 0 0 1-2-2v-6" />
    <circle cx="24" cy="20" r="6" /><path d="M14 36c1.5-5 5.5-7.5 10-7.5S32.5 31 34 36" />
  </svg>
);
const IconId = () => (
  <svg viewBox="0 0 48 48" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round" className={ICON} aria-hidden>
    <rect x="6" y="11" width="36" height="26" rx="4" /><circle cx="17" cy="21" r="3.5" />
    <path d="M11 32c1-3.5 3.5-5 6-5s5 1.5 6 5M28 19h8M28 25h8M28 31h5" />
  </svg>
);

const PLATFORM = [
  {
    t: "Authentifier",
    d: "Objectif : confirmer qu'un utilisateur est bien réel et présent. Aujourd'hui, seule une démonstration de capture selfie avec défi de rotation de la tête existe, sans vérification serveur.",
    Icon: IconFace,
    bg: "radial-gradient(circle at 18% 28%,#fff 0,transparent 48%),radial-gradient(circle at 82% 72%,#1E4FE0 0,transparent 55%),radial-gradient(circle at 62% 18%,#8CC8FF 0,transparent 50%),#EEF4FF",
  },
  {
    t: "Vérifier",
    d: "Objectif : KYC, KYB et filtrage AML avec des contrôles de documents par pays. Ces modules sont prévus et pas encore disponibles.",
    Icon: IconId,
    bg: "radial-gradient(circle at 78% 24%,#fff 0,transparent 46%),radial-gradient(circle at 20% 76%,#1E4FE0 0,transparent 58%),radial-gradient(circle at 50% 50%,#8CC8FF 0,transparent 55%),#EEF4FF",
  },
];

export function Platform() {
  return (
    <section id="platform" className="py-16 text-center">
      <p className="font-mono text-xs uppercase tracking-widest">Une seule plateforme</p>
      <h2 className="mx-auto mt-3 max-w-3xl text-5xl font-extrabold leading-[0.95] tracking-tighter md:text-6xl">
        Authentifier. <span className="text-blue">Vérifier.</span>
      </h2>
      <p className="mx-auto mt-5 max-w-2xl text-base">
        Freda Verify est une plateforme en construction : l&apos;API, le tableau de bord et la page de vérification sont développés pas à pas. Cette page indique ce qui est disponible et ce qui est prévu.
      </p>
      <div className="mt-7 flex flex-wrap justify-center gap-3">
        <a href="/verify" className="rounded-full bg-blue px-6 py-3 text-sm font-semibold text-white hover:bg-navy">Voir la démo ↗</a>
        <a href="#integration" className="rounded-full border border-[#d6e2ff] px-6 py-3 text-sm">Commencer à construire</a>
      </div>

      <div className="mt-12 grid gap-8 md:grid-cols-2">
        {PLATFORM.map(({ t, d, Icon, bg }) => (
          <article key={t} className="group text-left">
            <div className="relative grid h-72 place-items-center overflow-hidden rounded-3xl border border-[#d6e2ff]">
              <div className="absolute inset-0 scale-125 blur-2xl transition-transform duration-700 group-hover:scale-150" style={{ background: bg }} />
              <div className="relative grid h-28 w-28 place-items-center rounded-3xl bg-white text-blue shadow-[0_10px_40px_rgba(30,79,224,.22)] transition-transform duration-300 group-hover:-translate-y-1">
                <Icon />
              </div>
            </div>
            <h3 className="mt-6 text-3xl font-bold tracking-tight">{t}</h3>
            <p className="mt-2 max-w-lg text-base opacity-80">{d}</p>
          </article>
        ))}
      </div>
    </section>
  );
}

export function Developers() {
  return (
    <section id="developers" className="py-16">
      <p className="font-mono text-xs uppercase tracking-widest">
        Pour les développeurs · Pour les agents IA · Conçu pour être ouvert
      </p>
      <h2 className="mt-3 max-w-3xl text-5xl font-extrabold leading-[0.95] tracking-tighter md:text-6xl">
        Conçu pour les développeurs et les agents IA.
      </h2>
      <p className="mt-5 max-w-2xl text-base">
        API REST avec clés de test et de production. La documentation publique, le bac à sable, les SDK et le serveur MCP sont prévus ; ils n'existent pas encore.
      </p>
      <div className="mt-7 flex flex-wrap gap-3">
        <a href="#integration" className="rounded-full bg-blue px-6 py-3 text-sm font-semibold text-white hover:bg-navy">Voir l'intégration ↗</a>
        <a href="/signup" className="rounded-full border border-[#d6e2ff] px-6 py-3 text-sm">Créer un compte pour obtenir une clé</a>
      </div>

      <div className="mt-14 grid items-center gap-10 md:grid-cols-2">
        <div>
          <p className="font-mono text-xs uppercase">01 · Une seule API</p>
          <h3 className="mt-3 text-3xl font-bold tracking-tight md:text-5xl">Une seule API pour toute l&apos;identité.</h3>
          <p className="mt-4 max-w-lg text-base opacity-80">
            Objectif : une seule clé et une seule session pour les documents, le visage, le KYC, le KYB et l&apos;AML. Seules les clés API, les journaux et la mesure d&apos;usage sont disponibles aujourd&apos;hui.
          </p>
          <a href="#integration" className="mt-6 inline-flex rounded-full border border-[#d6e2ff] px-6 py-3 text-sm">Voir l'intégration ↗</a>
        </div>
        <ApiHub />
      </div>

      <div className="mt-14 max-w-3xl overflow-hidden rounded-2xl border border-[#d6e2ff] bg-navy text-white shadow-[0_20px_60px_rgba(0,0,0,.25)]">
        <div className="flex gap-1.5 border-b border-white/15 px-4 py-3">
          {[0, 1, 2].map((i) => <span key={i} className="h-2.5 w-2.5 rounded-full bg-white/30" />)}
          <span className="ml-3 font-mono text-[11px] opacity-60">GET /api/v1/usage · disponible</span>
        </div>
        <pre className="overflow-x-auto p-5 font-mono text-xs leading-6">{`curl https://api.fredaverify.com/api/v1/usage \\
  -H "Authorization: Bearer $FREDA_KEY"

→ { "period_days": 30, "requests": 12, "errors": 0, "by_day": [...] }

# Les points d'accès /verifications (création, documents, selfie,
# résultat) et les webhooks sont prévus, pas encore disponibles.`}</pre>
      </div>
    </section>
  );
}

export function AmlScreening() {
  return (
    <section id="aml" className="py-16">
      <div className="grid items-center gap-12 md:grid-cols-2">
        <div>
          <p className="font-mono text-xs uppercase">02 · Filtrage AML · prévu</p>
          <h2 className="mt-3 text-4xl font-extrabold leading-[0.98] tracking-tighter md:text-6xl">
            Filtrage AML : prévu.
          </h2>
          <p className="mt-5 max-w-lg text-base opacity-80">
            Objectif : comparer les utilisateurs à des listes de sanctions et de personnes politiquement exposées. Aucune source de données n&apos;est branchée à ce jour et les sources (officielles ou sous licence) restent à choisir. La carte ci-contre est une illustration.
          </p>
          <a href="/signup" className="mt-7 inline-flex rounded-full bg-blue px-6 py-3 text-sm font-semibold text-white hover:bg-navy">Créer un compte ↗</a>
        </div>
        <AmlCard />
      </div>
    </section>
  );
}
