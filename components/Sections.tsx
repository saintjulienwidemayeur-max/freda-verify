import type { ReactNode } from "react";
import ApiHub from "./ApiHub";
import AmlCard from "./AmlCard";

function Sec({ id, title, sub, children }: { id?: string; title: string; sub?: string; children: ReactNode }) {
  return (
    <section id={id} className="border-t border-black py-16">
      <h2 className="max-w-2xl text-4xl font-extrabold tracking-tighter">{title}</h2>
      {sub && <p className="mt-3 max-w-xl text-sm">{sub}</p>}
      <div className="mt-10">{children}</div>
    </section>
  );
}

const Grid = ({ items, cols = "md:grid-cols-3" }: { items: string[][]; cols?: string }) => (
  <div className={`grid gap-px border border-black bg-black ${cols}`}>
    {items.map(([t, d]) => (
      <div key={t} className="bg-[#e8e8e6] p-6">
        <h3 className="font-bold">{t}</h3>
        <p className="mt-2 text-sm">{d}</p>
      </div>
    ))}
  </div>
);

export function Services() {
  return (
    <Sec title="Tous les contrôles d'identité, dans un seul flux." sub="Activez uniquement ce dont votre conformité a besoin, sans assembler plusieurs fournisseurs.">
      <Grid items={[
        ["Vérification de documents", "Lecture et contrôle d'authenticité des pièces d'identité, passeports et registres."],
        ["Visage et liveness", "Comparaison selfie / document et détection des photos, écrans et deepfakes."],
        ["Vérification d'adresse", "Validation de l'adresse à partir de justificatifs et de sources officielles."],
        ["Filtrage AML", "Listes de sanctions, PEP et médias négatifs, avec surveillance continue."],
        ["KYB", "Vérification des entreprises, de leurs registres et de leurs bénéficiaires effectifs."],
        ["Video KYC", "Session vidéo en direct ou enregistrée pour les cas à risque élevé."],
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
    <div className={`rounded-2xl border border-black p-5 ${dark ? "bg-black text-white" : ""}`}>
      <div className="font-bold">{t}</div><div className="mt-1 text-sm opacity-80">{d}</div>
    </div>
  );
  return (
    <Sec title="Un flux que vous configurez." sub="Définissez vos seuils : les profils à faible risque passent seuls, les autres reçoivent des contrôles supplémentaires.">
      <div className="grid items-center gap-4 md:grid-cols-[1fr_auto_1fr_auto_1fr]">
        <Box t="1. Soumission" d="Document, selfie et données saisies par le client." />
        <span className="hidden text-2xl md:block">→</span>
        <Box t="2. Score de risque" d="Seuils et règles définis par votre équipe conformité." />
        <span className="hidden text-2xl md:block">→</span>
        <div className="grid gap-3">
          <Box dark t="Risque faible" d="Approbation automatique en secondes." />
          <Box t="Risque élevé" d="AML, video KYC ou revue manuelle." />
        </div>
      </div>
    </Sec>
  );
}

export function Audit() {
  return (
    <Sec title="Chaque décision est traçable." sub="Vérifications, alertes, codes de raison et contexte du dossier sont réunis dans un seul enregistrement.">
      <pre className="overflow-x-auto rounded-2xl border border-black bg-white/60 p-5 font-mono text-xs leading-6">{`{
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
        ["API REST", "Un appel avec le document et le selfie, une réponse JSON avec la décision."],
        ["SDK web et mobile", "Composants prêts à l'emploi pour capturer documents et visages."],
        ["Page hébergée", "Un lien à envoyer au client, sans développement de votre côté."],
      ]} />
    </Sec>
  );
}

export function Security() {
  return (
    <Sec id="security" title="Vos données restent sous votre contrôle.">
      <Grid cols="md:grid-cols-2" items={[
        ["Déploiement sur site", "Hébergez la suite sur vos propres serveurs si vos données ne doivent pas sortir de votre infrastructure."],
        ["Données dans votre région", "Choisissez où les données sont stockées pour respecter votre régulateur."],
        ["Chiffrement et rétention", "Données chiffrées, durées de conservation configurables, suppression sur demande."],
        ["Journal d'audit", "Accès et actions enregistrés pour vos contrôles internes et externes."],
      ]} />
    </Sec>
  );
}

const FAQ = [
  ["Combien de temps dure une vérification ?", "La plupart des vérifications automatiques se terminent en quelques secondes. Les cas à risque élevé peuvent passer par une revue supplémentaire."],
  ["Quels documents sont acceptés ?", "Cartes d'identité, passeports, permis et registres d'entreprise. La liste complète dépend des pays activés."],
  ["Puis-je vérifier des entreprises ?", "Oui. Le KYB lit les registres et identifie les bénéficiaires effectifs."],
  ["Puis-je héberger la solution chez moi ?", "Oui, une option sur site est prévue pour les organisations qui doivent garder leurs données en interne."],
  ["Y a-t-il un essai gratuit ?", "Oui. Le plan Starter permet de tester avec un volume limité, sans engagement."],
];

export function Faq() {
  return (
    <Sec id="faq" title="Questions fréquentes">
      <div className="border-t border-black">
        {FAQ.map(([q, a]) => (
          <details key={q} className="group border-b border-black py-4">
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
      <a href="mailto:contact@example.com" className="inline-flex rounded-full bg-black px-6 py-3 text-sm text-white">Parler à l&apos;équipe ↗</a>
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
    d: "Confirmez qu'un utilisateur est bien réel et bien présent : authentification biométrique, détection de vivacité, estimation de l'âge, contrôle de l'adresse IP et de l'appareil, et code à usage unique par téléphone ou e-mail pour renforcer la confiance.",
    Icon: IconFace,
    bg: "radial-gradient(circle at 18% 28%,#fff 0,transparent 48%),radial-gradient(circle at 82% 72%,#3a3a3a 0,transparent 55%),radial-gradient(circle at 62% 18%,#b8b8b8 0,transparent 50%),#d8d8d5",
  },
  {
    t: "Vérifier",
    d: "KYC, KYB et filtrage AML, avec des contrôles de documents adaptés à chaque personne et à chaque entreprise. Vous activez les pays, les types de pièces et les sources de données dont votre conformité a besoin.",
    Icon: IconId,
    bg: "radial-gradient(circle at 78% 24%,#fff 0,transparent 46%),radial-gradient(circle at 20% 76%,#1f1f1f 0,transparent 55%),radial-gradient(circle at 50% 50%,#9a9a9a 0,transparent 52%),#e0e0dd",
  },
];

export function Platform() {
  return (
    <section id="platform" className="border-t border-black py-16 text-center">
      <p className="font-mono text-xs uppercase tracking-widest">Une seule plateforme</p>
      <h2 className="mx-auto mt-3 max-w-3xl text-5xl font-extrabold leading-[0.95] tracking-tighter md:text-6xl">
        Authentifier. <span className="opacity-40">Vérifier.</span>
      </h2>
      <p className="mx-auto mt-5 max-w-2xl text-base">
        Construisez et déployez vos parcours d&apos;identité avec une seule API. Utilisez nos modules prêts à l&apos;emploi ou composez les vôtres, de l&apos;authentification biométrique à la vérification des entreprises.
      </p>
      <div className="mt-7 flex flex-wrap justify-center gap-3">
        <a href="#demo" className="rounded-full bg-black px-6 py-3 text-sm text-white">Voir la vérification ↗</a>
        <a href="#integration" className="rounded-full border border-black px-6 py-3 text-sm">Commencer à construire</a>
      </div>

      <div className="mt-12 grid gap-8 md:grid-cols-2">
        {PLATFORM.map(({ t, d, Icon, bg }) => (
          <article key={t} className="group text-left">
            <div className="relative grid h-72 place-items-center overflow-hidden rounded-3xl border border-black">
              <div className="absolute inset-0 scale-125 blur-2xl transition-transform duration-700 group-hover:scale-150" style={{ background: bg }} />
              <div className="relative grid h-28 w-28 place-items-center rounded-3xl bg-white shadow-[0_10px_40px_rgba(0,0,0,.18)] transition-transform duration-300 group-hover:-translate-y-1">
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
    <section id="developers" className="border-t border-black py-16">
      <p className="font-mono text-xs uppercase tracking-widest">
        Pour les développeurs · Pour les agents IA · Conçu pour être ouvert
      </p>
      <h2 className="mt-3 max-w-3xl text-5xl font-extrabold leading-[0.95] tracking-tighter md:text-6xl">
        Conçu pour les développeurs et les agents IA.
      </h2>
      <p className="mt-5 max-w-2xl text-base">
        Une API unique pour vérifier des identités. Documentation publique, bac à sable immédiat, serveur MCP et SDK pour les principaux langages.
        Une équipe intègre en un après-midi ; un agent IA y arrive avec une seule instruction grâce à MCP.
      </p>
      <div className="mt-7 flex flex-wrap gap-3">
        <a href="#integration" className="rounded-full bg-black px-6 py-3 text-sm text-white">Lire la documentation ↗</a>
        <a href="#contact" className="rounded-full border border-black px-6 py-3 text-sm">Obtenir une clé API</a>
      </div>

      <div className="mt-14 grid items-center gap-10 md:grid-cols-2">
        <div>
          <p className="font-mono text-xs uppercase">01 · Une seule API</p>
          <h3 className="mt-3 text-3xl font-bold tracking-tight md:text-5xl">Une seule API pour toute l&apos;identité.</h3>
          <p className="mt-4 max-w-lg text-base opacity-80">
            Un seul appel couvre la vérification de documents, la reconnaissance faciale, le liveness, le KYC, le KYB et le filtrage AML.
            Même clé, même moteur de flux, modules enchaînables dans une seule session, sans travail d&apos;intégration supplémentaire entre eux.
          </p>
          <a href="#integration" className="mt-6 inline-flex rounded-full border border-black px-6 py-3 text-sm">Lire la documentation API ↗</a>
        </div>
        <ApiHub />
      </div>

      <div className="mt-14 max-w-3xl overflow-hidden rounded-2xl border border-black bg-black text-white shadow-[0_20px_60px_rgba(0,0,0,.25)]">
        <div className="flex gap-1.5 border-b border-white/15 px-4 py-3">
          {[0, 1, 2].map((i) => <span key={i} className="h-2.5 w-2.5 rounded-full bg-white/30" />)}
          <span className="ml-3 font-mono text-[11px] opacity-60">POST /v1/sessions</span>
        </div>
        <pre className="overflow-x-auto p-5 font-mono text-xs leading-6">{`curl -X POST https://api.freda.dev/v1/sessions \\
  -H "x-api-key: $FREDA_KEY" \\
  -d '{ "workflow": "kyc_standard",
        "callback": "https://votre-app.com/webhook" }'

→ {
    "session_id": "ses_7c21a9",
    "url": "https://verify.freda.dev/ses_7c21a9",
    "status": "created"
  }`}</pre>
      </div>
    </section>
  );
}

export function AmlScreening() {
  return (
    <section id="aml" className="border-t border-black py-16">
      <div className="grid items-center gap-12 md:grid-cols-2">
        <div>
          <p className="font-mono text-xs uppercase">02 · Filtrage AML</p>
          <h2 className="mt-3 text-4xl font-extrabold leading-[0.98] tracking-tighter md:text-6xl">
            Filtrez chaque utilisateur. Restez filtré pour toujours.
          </h2>
          <p className="mt-5 max-w-lg text-base opacity-80">
            Comparez chaque nouvel utilisateur à de nombreuses listes anti-blanchiment d&apos;argent (AML) dès l&apos;inscription.
            Choisissez les catégories qui comptent pour vous : sanctions, personnes politiquement exposées, médias défavorables.
            Gardez-les sous surveillance chaque jour, sans rien faire de plus.
          </p>
          <a href="#contact" className="mt-7 inline-flex rounded-full bg-black px-6 py-3 text-sm text-white">Parler à l&apos;équipe ↗</a>
        </div>
        <AmlCard />
      </div>
    </section>
  );
}
