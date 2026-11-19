# CLAUDE.md — FREDA VERIFY

Permanent technical reference and development guide for **Freda Verify**.
Last updated: 2026-11-19. Keep this file in sync with the code (rule 16, section 12).

> **Read this first:** today the repository is a **frontend-only prototype** (landing site + sample dashboard).
> There is **no backend, no database, no authentication, no AI/OCR and no real verification**.
> Everything a dashboard shows is hard-coded sample data. See section 3.5 (mock inventory).
> Never describe any feature as working, production-ready or "verified" unless section 3 says it is real.

---

## 1. Project identity

| | |
|---|---|
| Name | **FREDA VERIFY** |
| Category | Identity verification, KYC, KYB, AML and fraud-prevention SaaS |
| Vision | "Verify identities. Detect fraud. Protect businesses." |
| Positioning | Independent platform with its own API, verification engine, dashboard, SDK and customer management. Comparable in scope to Didit / Sumsub / Veriff. |
| First customers | Freda Pay and other Freda Group products, then fintechs, banks, PSPs, e-commerce, crypto platforms (subject to law) and any business needing identity verification. |
| Languages of the product | Landing page: French (some English). Dashboard: English. Team communication: Haitian Creole / French / English. |

### Brand tokens (already applied in the frontend)

Source: the "Freda Verify Idantite Vizyel" brand pack (logo, colors, typography).

| Token (Tailwind) | Hex | Use |
|---|---|---|
| `navy` | `#0A1647` | Main text, dark backgrounds |
| `blue` | `#1E4FE0` | Primary color, buttons |
| `electric` | `#2E8BFF` | Accents, gradients, "Verify" in the wordmark |
| `sky` | `#8CC8FF` | Face mesh, illustrations |
| `ice` | `#EEF4FF` | Secondary background |
| `ok` / `warn` / `bad` | `#12B76A` / `#F79009` / `#D92D20` | Status: Verified / In review / Rejected |

Fonts: **Plus Jakarta Sans** (headings, `font-display`), **Inter** (body), **IBM Plex Mono** (technical labels).
Dashboard surface: `#F6F8FC` page, white cards, `#e3eaf8` borders, `rounded-2xl`.
Assets: `public/logo-mark.svg` (used), `public/logo.png`, `public/logo-white.png` (unused for now), `app/icon.png`, `app/apple-icon.png`.

---

## 2. Objectives (target platform)

1. Identity document verification (passport, national ID, driver's license) with OCR and MRZ.
2. Selfie capture, face comparison, liveness / anti-spoofing.
3. Document fraud detection.
4. AML: PEP, sanctions, watchlists, name + DOB matching, screening history.
5. Risk scoring, configurable thresholds, decision engine, manual review.
6. KYB business verification.
7. REST API, webhooks, API keys (test/live), hosted verification page, SDKs.
8. Analytics, audit logs, multi-tenant SaaS with organization-level isolation.

---

## 3. Current state of the repository (as built)

### 3.1 Stack actually in use

| Layer | Reality |
|---|---|
| Framework | **Next.js 15.5 (App Router)** + **React 19** + **TypeScript 5.9 (strict)** |
| Styling | Tailwind CSS 3.4 (+ PostCSS, Autoprefixer); design tokens in `tailwind.config.ts` |
| Animation | `framer-motion` 12 (v11 broke the build with React 19 types, see git history) |
| Fonts | `next/font/google` (Inter, Plus Jakarta Sans, IBM Plex Mono). **Build needs network** to fetch them. |
| Output | **Static export** (`output: "export"` in `next.config.mjs`) → `out/` |
| Hosting | Render **Static Site**: build `npm install && npm run build`, publish dir `out` |
| Backend / DB / auth / tests / CI / Docker | **None** |
| Lockfile | `package-lock.json` (npm) |
| Source size | ~1,800 lines of TSX |

Important consequences of the static export:
- No API routes, no middleware, no server components that need a server, no `next start` (it errors by design).
- Dynamic routes need `generateStaticParams`; client-side routing of `/dashboard/*` relies on the static `.html` files. If Render returns 404 on a sub-page, add a Rewrite (`/dashboard/x` → `/dashboard/x.html`).
- The backend will be a **separate service** (FastAPI, section 4).

### 3.2 Git / deployment state

- Development branch: `claude/eloquent-thompson-o5zagp` (pushed). **Not merged into `main`.** No PR exists. Do not open a PR unless asked.
- Render: set to this branch or merge to `main` first (open decision, section 14).
- Commit attribution: end commit messages with the `Co-Authored-By` and `Claude-Session` lines given by the harness.

### 3.3 Routes and files

```
app/
  layout.tsx                    fonts + metadata
  page.tsx                      landing page (French/English mix)
  globals.css                   Tailwind base + brand colors + focus ring
  icon.png, apple-icon.png      favicons from brand pack
  verify/page.tsx               PUBLIC hosted verification page for end users (demo mode, see 3.5)
  dashboard/
    page.tsx                    Overview (stat cards, chart, recent verifications, activity)
    verifications/page.tsx      People verified (KYC): list + detail + media
    businesses/page.tsx         Businesses (KYB) list + detail
    api-keys/page.tsx           API keys UI
    white-label/page.tsx        White-label config + live preview of the hosted verification page
    logs/page.tsx               API request logs UI
    settings/page.tsx           Workspace, webhook URL, notifications
    support/page.tsx            FAQ, links, contact
components/
  DashShell.tsx                 Sidebar (collapsible) + top bar, used by all dashboard pages
  OverviewChart.tsx             Interactive bar chart
  Verifications.tsx             People list/filter/search/detail/approve-reject
  Media.tsx                     Selfie "video" player + ID front/back + lightbox
  Scanner.tsx                   Camera scanner with AUTOMATIC capture. Documents: OpenCV.js card-edge detection + fit/stability/exposure/sharpness, captures a perspective-corrected crop. Selfie: heuristics + 3-2-1 countdown
  FaceScanner.tsx               Selfie scanner: MediaPipe face detection (one face, centered, frontal) + ACTIVE head-turn challenge (random LEFT/RIGHT, animated pointing finger 👈/👉 + chevrons + label), then success. Falls back to the basic scanner if MediaPipe cannot load
  faceDetect.ts                 MediaPipe Face Landmarker loader + detectFace (478 landmarks, face box, head yaw from the facial transformation matrix + nose/cheek ratio fallback)
  cardDetect.ts                 OpenCV.js loader (lazy, /vendor/opencv.js) + detectCard (Canny + contours + 4-corner/aspect/angle filter) + rectify (perspective warp)
  HostedPage.tsx                Real end-user flow at /verify: consent, country, document, camera/upload, local quality check, review, demo finish. Config via URL params
  HostedPreview.tsx             Mock of the end-user hosted verification page (welcome, country, document, selfie, done), driven by the white-label config
  WhiteLabel.tsx                Branding form (name, logo, colors, theme, shape, language, texts, docs, domain, redirect) + phone preview
  Businesses.tsx, ApiKeys.tsx, Logs.tsx, Settings.tsx, Support.tsx
  FaceMatch.tsx                 Landing animation (document photo vs selfie)
  Sections.tsx                  Landing sections (Platform, Developers, AML, services, FAQ...)
  AmlCard.tsx, ApiHub.tsx       Landing animations
public/ faces/*.webp, hero.png, logo*.{svg,png}
public/vendor/ opencv.js (OpenCV 4.10 via @techstark/opencv-js, Apache-2.0, ~10 MB, loaded only by /verify), opencv.LICENSE.txt
public/vendor/mediapipe/ wasm/vision_wasm_internal.{js,wasm} (MediaPipe Tasks Vision 1.2.3, Apache-2.0, ~15 MB), face_landmarker.task (3.7 MB model), NOTICE.txt, LICENSE-Apache-2.0.txt
```

Not yet existing: login / sign-up / password reset, hosted verification page for end users, Customers, Organizations, Developers, Webhooks and Analytics pages (see gap analysis, section 11).

### 3.4 Conventions found in the code

- Client components start with `"use client"`; pages are thin server components that wrap a client component in `DashShell`.
- Styling is Tailwind utility classes; colors come from the tokens above. Status badge colors live next to each table (`BADGE` maps).
- Images: optimized WebP in `public/faces` (336×400, 7–11 KB). Use `<img>` (static export, `images.unoptimized`).
- Accessibility basics present: `aria-pressed` on filters, `aria-label`s, `role=dialog` on the media lightbox, reduced-motion CSS.
- Verified for each change: `npx tsc --noEmit` + `npm run build` + a headless-browser check. There are **no automated tests yet**.

### 3.5 Mock inventory (everything below is FAKE and must be replaced)

| Where | What is simulated |
|---|---|
| `components/Verifications.tsx` | 10 hard-coded people, scores, checks, reasons. Approve/Reject only changes React state (lost on refresh). |
| `components/Media.tsx` | The "video" is a **photo animated with CSS**, not a real recording. ID front/back are **generic drawn cards**, not real documents. Only 2 demo photos exist (`public/faces`). |
| `components/Businesses.tsx` | 8 hard-coded companies. |
| `components/ApiKeys.tsx` | Keys are random hex generated in the browser (`crypto.getRandomValues`); not stored, not valid for any API. **Real secret keys must never be generated or shown by frontend code.** |
| `components/Logs.tsx` | 9 hard-coded request logs. |
| `components/Settings.tsx` | Form state in memory only. Nothing saved. |
| `components/HostedPage.tsx` (`/verify`) | **Public page. Real UI, no backend.** The scanner opens the camera automatically on each capture step and **captures automatically** (`components/Scanner.tsx`): it analyses the frame area every 140 ms (brightness, glare, sharpness via Laplacian variance, frame-to-frame stability) and captures after ~1.3 s of good frames (selfie: ~3 s with a visible 3-2-1 countdown); a manual "Capture now" appears after 9 s and an upload fallback exists. **Documents now use OpenCV.js card-edge detection** (`cardDetect.ts`): it finds a convex 4-corner shape with a card/passport-page aspect ratio (1.2–1.9) and 65–115° corners, checks fit ("Move closer / back / center"), corner stability, exposure, glare and sharpness, then captures a perspective-corrected, upright crop (~1000 px wide). Limits: it detects a card-SHAPED rectangle, not a genuine document (a credit card, a card-shaped object or a screen can pass); low contrast against the background can miss the edges; no OCR, no document-type classification, no tamper checks. If OpenCV cannot load it falls back to the basic quality heuristics (any sharp steady scene triggers capture). **Selfie (`FaceScanner.tsx`)**: MediaPipe Face Landmarker (self-hosted, in-browser) requires exactly one face, centered in the oval, big enough and frontal (yaw within ±9°) for ~0.8 s, takes the still photo, then **asks the user to turn their head LEFT or RIGHT (random)** showing an animated pointing finger (👈/👉) with chevrons and a direction label. Success = head yaw ≥ 20° in the requested direction for 2 consecutive frames (≈ nose/cheek ratio 0.17 as fallback); the wrong direction shows "Other way"; after 12 s the direction flips ("Let's try again"). Sign convention (verified): yaw > 0 = user's LEFT, < 0 = user's RIGHT, from `atan2(m[8], m[10])` of the facial transformation matrix; the preview is mirrored so the finger points to the same side the user sees. **Limits: this is a basic active challenge, NOT certified liveness.** A replayed video, a deep-fake or a 3D mask can pass; no PAD, no texture/depth analysis, no server-side re-check, no face matching against the document. It was tested only with synthetic perspective-warped frames (≈5° effective yaw) using a test-only build flag `NEXT_PUBLIC_TURN_DEG` (**never set it in production**; default 20°) and never with real head turns on real phones: thresholds must be tuned on real devices. If MediaPipe cannot load, the selfie falls back to basic image-quality heuristics only. Document authenticity, face matching and certified liveness belong to Phases 2–3. Camera (`getUserMedia`) and file input work; a local quality check (brightness, glare, blur via canvas) runs in the browser. Photos live only in memory (`blob:` URLs), are never uploaded (no network request is made), and are deleted on submit/restart. The final screen says "Demo complete — no verification was performed" and **never shows a verdict**. Branding comes from URL params (`name,color,theme,shape,lang,docs,title,subtitle,support`), validated and rendered as text; `redirect` and logo are deliberately NOT accepted from the URL (open-redirect / untrusted-image risk). Do not wire any upload to this page until the backend, consent and retention requirements (sections 5, 8, white-label requirements) are met. |
| `components/WhiteLabel.tsx` | Branding config lives in React state only (logo is an in-memory object URL). Custom-domain "DNS record" and its target value are examples; no domain or certificate is verified. The phone preview (`HostedPreview.tsx`) is a clickable mock of a hosted page that does not exist yet: no camera, no upload, no real country/document rules (country list is a fixed sample of 24 ISO codes, names via `Intl.DisplayNames`; Kreyòl falls back to French names). |
| `app/dashboard/page.tsx`, `OverviewChart.tsx` | All numbers (12,480 checks, 96.4%, charts, activity) are invented. |
| `components/FaceMatch.tsx` | Marketing animation; scores 98 % / 34 % are scripted. |
| `components/Support.tsx` | "All systems operational" is static text. |

Every dashboard page shows a "Sample data" badge and/or a "Demo:" note. Keep these until the page is backed by real data (rule 14).

### 3.6 Landing-page claims that are NOT true yet

The public copy describes capabilities that do not exist. Review before any public launch (legal and reputational risk):

| Claim (landing) | Reality today |
|---|---|
| "Fully automated … no manual review queue" (`app/page.tsx`) | Not implemented. Also contradicts the intended Manual Review module. |
| "Liveness that catches fakes: printed photos, replayed screens and deepfakes are stopped" | No liveness exists. Do not claim until tested (section 8, ISO 30107-3 style testing). |
| "Filtrage AML: sanctions, PEP, adverse media, continuous monitoring" | No AML data or engine. |
| "KYB reads registries and identifies beneficial owners", "Video KYC", "Vérification d'adresse" | Not implemented. |
| "Déploiement sur site", "Données dans votre région", "Chiffrement", "Journal d'audit" | None implemented. |
| Pricing: Starter $0 / 100 checks, Growth $0.40, Enterprise custom | Placeholder numbers, not decided. |
| API example `POST https://api.freda.dev/v1/sessions` + header `x-api-key` | Domain and endpoint do not exist; also differ from the target API (section 6). |
| Audit JSON example (`case_20817`, `analyst_04`) | Illustrative only. |

---

## 4. Target architecture

### 4.1 Technology (all commercial-use compatible; verify every license, section 9)

- **Frontend:** React + TypeScript + Tailwind (already Next.js; see decision D1).
- **Backend:** Python 3.12, **FastAPI**, Pydantic v2, REST `/api/v1`, modular services.
- **Database:** PostgreSQL, SQLAlchemy 2.x, Alembic migrations.
- **Background jobs:** a queue worker (e.g. Celery/RQ/Arq with Redis) for OCR, face and AML jobs.
- **Document/AI:** PaddleOCR (Apache-2.0), OpenCV (Apache-2.0), DeepFace and other face models (license of *each model weight* to be verified), self-hosted.
- **Storage:** S3-compatible object storage (MinIO in dev), encrypted, private, signed URLs.
- **Infra:** Docker + Docker Compose, config via environment variables, secrets never in git.
- No mandatory paid external KYC API.

### 4.2 Proposed repository layout (do not move existing code until approved, D2)

```
/                       current Next.js app stays where it is for now
backend/                FastAPI app
  app/{api,core,models,schemas,services,workers}/
  alembic/  tests/
infra/                  docker-compose.yml, Dockerfiles, MinIO/Postgres/Redis config
docs/                   API reference, runbooks, DPIA/privacy notes
CLAUDE.md
```

Later, if desired, move the web app to `apps/web` in a monorepo.

### 4.3 Core modules

| ID | Module | Scope | Status |
|---|---|---|---|
| A | Authentication | register, login, reset, MFA, RBAC, sessions | not started |
| B | Organizations | multi-tenant isolation, team, permissions, settings | not started |
| C | Document engine | upload, quality, OCR, classification, MRZ, expiry, consistency, tamper hints | not started |
| D | Biometric engine | selfie, face detect/compare, liveness, anti-spoofing, confidence | not started |
| E | AML engine | PEP, sanctions, watchlists, name/DOB matching, history | not started |
| F | Risk engine | document/biometric/AML risk, indicators, thresholds | not started |
| G | Decision engine | APPROVED / REJECTED / PENDING / MANUAL_REVIEW / EXPIRED | not started |
| H | Verification management | sessions, links, progress, storage, manual review, reports | UI mock only |
| I | Developer platform | API keys, test/live, docs, webhooks, logs, usage, SDK docs | UI mock only |
| J | Administration | platform admins, monitoring, fraud, audit, config | not started |

Rule: **never auto-reject solely on an uncertain AI score.** Low confidence → `MANUAL_REVIEW`.

---

## 5. Verification workflow (target)

1. Business creates a verification (API or dashboard) → unique ID, auditable history.
2. Freda Verify issues a secure session + hosted link (short-lived, single-use token).
3. End user opens the hosted page, gives consent, uploads the document, captures a selfie.
4. Document engine: quality → classification → OCR/MRZ → validation.
5. Biometric engine: face detection → comparison → liveness.
6. AML screening when enabled and legally appropriate.
7. Risk engine combines evidence; decision engine sets the status.
8. Result stored securely; webhook sent (signed); business fetches the result via API.

State machine (API names) and how the current UI names map to it:

| API status | Meaning | Current UI label |
|---|---|---|
| `PENDING` | session created / in progress | PENDING |
| `MANUAL_REVIEW` | evidence uncertain, needs a human | REVIEW |
| `APPROVED` | passed | APPROVED |
| `REJECTED` | failed with reason codes | REJECTED |
| `EXPIRED` | session or document expired | (missing in UI) |

Every transition is written to an append-only audit trail (actor, time, reason code).

---

## 6. API design

Base path `/api/v1`, versioned. OpenAPI generated by FastAPI is the source of truth; document every endpoint.

```
POST /api/v1/verifications
GET  /api/v1/verifications/{id}
POST /api/v1/verifications/{id}/documents
POST /api/v1/verifications/{id}/selfie
POST /api/v1/verifications/{id}/complete
GET  /api/v1/verifications/{id}/result
GET  /api/v1/organizations        POST /api/v1/organizations
GET  /api/v1/usage
GET  /api/v1/webhooks             POST /api/v1/webhooks
```

Requirements: bearer authentication, separate **test** and **live** keys, input validation, rate limiting, `Idempotency-Key` support, structured errors, versioning, HMAC-signed webhooks (timestamp + signature header, replay window), audit logging.

Error shape (proposal):
```json
{ "error": { "code": "invalid_document", "message": "…", "request_id": "req_…", "details": [] } }
```

Mismatches to reconcile (D3): landing page and API Keys page use `x-api-key` + `/v1/sessions`; this spec uses `Authorization: Bearer` + `/api/v1/verifications`. Pick one and update the UI/copy.

---

## 7. Data model (first sketch)

`organizations`, `users`, `memberships(role)`, `api_keys(hash, prefix, env, last_used)`, `verifications(status, org_id, …)`, `verification_events` (audit), `documents` (object-store key, type, extracted fields encrypted), `selfies`, `face_matches`, `liveness_results`, `aml_screenings` + `aml_hits`, `risk_assessments`, `reviews`, `webhooks`, `webhook_deliveries`, `usage_records`, `audit_logs`.
Every tenant-owned table carries `organization_id`; enforce isolation in the data layer (and consider PostgreSQL row-level security).

---

## 8. Security and privacy

Biometrics and identity documents are **highly sensitive personal data**.

Required: TLS everywhere; encryption at rest (disk + field-level for identity numbers); private object storage with signed, short-lived URLs; organization-level isolation; RBAC; MFA for dashboard users; API-key hashing (show once, store hash + prefix); rate limiting; audit trails; secret management via env/secret store; retention policies and verified secure deletion; backups + restore tests; consent capture and privacy notices; DPIA-style review.

Never log: raw documents, selfies, full ID numbers, passwords, API secrets, tokens. Mask identity numbers in UI (already done in the sample UI: `HT-••••917`).

Liveness rule: **never claim reliable liveness** until the implemented technology is tested against presentation attacks (printed photo, screen replay, masks, injection/deepfake). Plan for independent testing (ISO/IEC 30107-3 style) before marketing it.

Legal: identify applicable regimes for each market (data-protection law, AML/KYC rules, biometric rules, cross-border transfer limits; GDPR if EU residents are verified). Get legal review before launch. This file is not legal advice.

### Security risks and limitations found today

1. No backend: nothing is protected because nothing is stored. Any real PII added to the static site would be public. **Never put real identity data or real keys in this repo or in the static bundle.**
2. `ApiKeys.tsx` generates keys client-side. It is a UI demo only; do not reuse the pattern.
3. Demo faces in `public/faces` come from user-supplied images; confirm usage rights before public launch.
4. Landing claims overstate capabilities (section 3.6).
5. No CSP / security headers (static host; configure headers on Render or a CDN).
6. No dependency auditing, no CI, no tests, no secret scanning in the pipeline.
7. `next/font/google` makes builds depend on external network.
8. The build output uses `output: "export"`; any future need for server-side session handling must live in the FastAPI service, not Next.

---

## 9. AI / ML components and licensing

Rule: verify the license of **code, model weights and training data** separately. "Open source code" does not imply "weights usable commercially".

| Component | Purpose | License note (verify before use) |
|---|---|---|
| OpenCV.js (`@techstark/opencv-js` 4.10, vendored in `public/vendor`) | Client-side card detection | Apache-2.0 (OpenCV >= 4.5). License file shipped as `public/vendor/opencv.LICENSE.txt`; keep it with the binary. ~10 MB (≈3.4 MB gzip), loaded lazily only on `/verify` |
| MediaPipe Tasks Vision `@mediapipe/tasks-vision` 1.2.3 (npm dependency; runtime vendored in `public/vendor/mediapipe`) + `face_landmarker.task` | Client-side face detection and head pose | Library/runtime: Apache-2.0 (package.json). **Model weights license NOT confirmed** (official model card was unreachable here): verify the Face Landmarker model card terms before commercial production use. ~15 MB wasm (≈4 MB gzip) + 3.7 MB model, loaded lazily only for the selfie step |
| PaddleOCR | OCR, MRZ text | Apache-2.0 (code and models) — confirm per model |
| OpenCV | image processing | Apache-2.0 |
| DeepFace | face verification wrapper | Wrapper is MIT, but each backend model's weights (VGG-Face, Facenet, ArcFace…) have their own terms; some are research/non-commercial. **Verify.** |
| InsightFace / ArcFace weights | face recognition | Commonly non-commercial for pre-trained weights. **Verify; likely needs a commercial license or own training.** |
| Anti-spoofing / liveness models | PAD | No mature, free, commercially safe, certified option assumed. Research + testing required. |
| Sanctions data (OFAC SDN, UN, EU lists) | AML | Official lists are generally public but each publisher has terms; use official feeds. |
| OpenSanctions and similar aggregators | AML | Often free only for non-commercial use; commercial use needs a paid license. **Do not assume.** |
| PEP data | AML | No high-quality free commercial source assumed; likely a licensing cost. |
| Training / test datasets | evaluation | Many face datasets are non-commercial. Never train or ship on them without verified terms. |

---

## 10. Cost strategy

Goal: **$0 software budget** for development, without sacrificing security, accuracy or compliance.

| Category | Examples |
|---|---|
| Free in development | Local Docker, PostgreSQL, Redis, MinIO, Python/Node tooling, open-source libraries, local models |
| Free open-source in production | FastAPI, PostgreSQL, OpenCV, PaddleOCR (subject to license checks) |
| Infrastructure costs (not free) | Servers (CPU/GPU), object storage, backups, monitoring, bandwidth, domain/TLS, email/SMS for OTP |
| Commercial data licensing | PEP data, aggregated sanctions/watchlists with commercial terms, company registries, possibly face models |
| Needs professional testing/services | Liveness/PAD evaluation, penetration test, security audit, legal/privacy review, compliance advice |

Never make a paid external KYC API a **mandatory** dependency; keep provider interfaces pluggable.

---

## 11. Gap analysis — spec vs. current frontend

Dashboard sections requested: Overview, Verifications, Customers, Organizations, Developers, API Keys, Webhooks, Analytics, Settings.

| Section | Today |
|---|---|
| Overview | UI mock ✔ |
| Verifications | UI mock ✔ (list, filters, detail, media viewer, approve/reject) |
| Customers | **missing** (could merge with Verifications or be the business's end-customer directory) |
| Organizations | **missing** (Businesses page is KYB subjects, not tenants) |
| Developers | **missing** (docs, test documents, SDK downloads) |
| API Keys | UI mock ✔ |
| Webhooks | **missing** page (only a URL field in Settings) |
| Analytics | **missing** (Overview chart only) |
| Settings | UI mock ✔ |
| Logs, Support | UI mock ✔ (extra, not in spec) |
| White label | UI mock ✔ (`/dashboard/white-label`): brand, colors, theme, button shape, language (EN/FR/HT), texts, accepted documents, redirect URL, custom domain, hide "Powered by", live phone preview |
| Hosted verification flow (end user) | **UI live at `/verify` in demo mode (no upload, no result)**, automatic scanner with OpenCV.js card detection, and a desktop → QR-code hand-off (desktop detection by user agent + touch; QR encodes the current page URL — in production it must encode a one-time session link, never data); also a clickable preview inside White label. Still missing: session tokens, upload to storage, OCR/face/liveness, result and webhook. Previously described as: **mock only** — clickable 5-step preview inside White label (welcome with language picker and 2-step stepper, issuing-country picker with search, document type, selfie, done). The real mobile-first page (camera, uploads, session token) is not built |
| Login / signup / MFA / password recovery | **missing** |
| Landing | done visually; copy needs claim review |

---

### White-label requirements (target, for the backend phase)

- Store per-organization branding as a validated theme record (name, logo key in object storage, color, theme, shape, language, texts, allowed documents, redirect URL, support email, custom domain, `hide_powered_by`).
- Treat every branding field as untrusted input: length limits, hex-color validation, **no HTML** in texts (render as text), logos restricted to PNG/JPG/WebP and sanitized SVG (or reject SVG), size limit, virus/type check, served from a separate asset origin.
- Redirect URLs: HTTPS only, allow-list per organization, never open redirects.
- Custom domains: DNS ownership verification (CNAME/TXT), automatic TLS issuance and renewal, protection against subdomain takeover, per-domain tenant routing.
- Always show required consent/privacy text and legal notices even when white-labelled; do not let branding remove them.
- "Hide Powered by Freda Verify" is a commercial/plan decision (open, D10).
- The hosted page reads the theme by session token and must never expose the organization's secret keys.

---

## 12. Development rules

1. Inspect existing files before modifying anything.
2. Never overwrite working code without understanding it.
3. Modular, maintainable architecture.
4. TypeScript types (strict) and Python type hints.
5. Reusable components.
6. Validate all API inputs.
7. Meaningful error handling.
8. Tests for critical functionality (none exist yet; start with backend and decision logic).
9. Document every important endpoint.
10. Use database migrations (Alembic).
11. Never hard-code credentials.
12. Secrets only in environment variables / secret store.
13. Never use fake verification results in production.
14. Clearly label mock implementations (keep "Sample data" / "Demo" notices).
15. Never claim a feature is production-ready without adequate testing.
16. Update this CLAUDE.md when architecture or state changes.

Repo habits: small commits, develop on the assigned branch, run `npx tsc --noEmit` and `npm run build` before pushing, verify UI in a headless browser, no PR unless requested.

### Commands

```bash
npm install            # install
npm run dev            # dev server at http://localhost:3000
npm run build          # type-check + static export to out/
npx tsc --noEmit       # type-check only
npx serve out          # preview the static export (next start is not supported)
```

---

## 13. Roadmap

### Phase 0 — Finish and de-risk the frontend (current)
Priority order:
1. Decide D1–D4 (section 14).
2. Review landing claims (section 3.6) and the pricing placeholders.
3. Add missing UI sections: Webhooks, Developers, Analytics, Organizations/Customers, login/signup, and the **hosted verification flow** (consent → document → selfie → result), all clearly mocked.
4. Add basic frontend tests and a CI workflow (type-check + build).
5. Decide branch/merge strategy and wire Render auto-deploy.
Exit: UI complete and honest about being mocked; API contract frozen (OpenAPI draft) so backend and frontend can be built against it.

### Phase 1 — Foundation
Backend scaffold, Docker Compose (Postgres, Redis, MinIO), Alembic, auth (register/login/reset/MFA), organizations, RBAC, API-key issuing (hashed), request logging, audit log, CI.
Exit: a user can sign up, create an organization and a test API key; tenant isolation tests pass.

### Phase 2 — Document engine
Upload to private storage, image-quality checks, PaddleOCR, document classification, MRZ parsing (checksum validation), expiry and consistency checks, tamper heuristics (clearly labeled heuristic).
Exit: measured accuracy on a lawfully obtained test set; results stored encrypted.

### Phase 3 — Biometric engine
Selfie capture, face detection, comparison with a **license-cleared** model, liveness/anti-spoofing evaluation against a documented attack set.
Exit: documented error rates (FAR/FRR), and an explicit statement of what liveness does and does not protect against.

### Phase 4 — Risk and AML
Risk scoring, decision engine with manual-review queue, sanctions screening from licensed/official sources, PEP source decision, name + DOB fuzzy matching, screening history.
Exit: configurable thresholds, reason codes, reviewer workflow.

### Phase 5 — SaaS dashboard (real data)
Connect the existing screens to the API: verifications, analytics, organizations, team, audit logs; remove mocks page by page.

### Phase 6 — Developer platform
Public REST API, test/live environments, webhooks with signatures and retries, sandbox with test documents, docs site, JS/React/React Native SDKs, PHP/Python/Node examples.

### Phase 7 — Production readiness
Security audit and pen test, load testing, privacy/DPIA review, monitoring and alerting, backups and restore drills, deployment, production verification tests, incident process.

---

## 14. Decisions requiring approval

| # | Decision | Recommendation |
|---|---|---|
| D1 | Frontend framework: keep **Next.js (static export)** or switch to a plain React SPA (Vite)? | Keep Next.js for now (already built; still React + TS + Tailwind). Revisit if SSR is never needed. |
| D2 | Repo layout: add `backend/` and `infra/` beside the current app, or restructure into a monorepo (`apps/web`) now? | Add beside now; restructure later. |
| D3 | API auth style and path: `Authorization: Bearer` + `/api/v1/verifications` (spec) vs the `x-api-key` + `/v1/sessions` shown in the UI. | Follow the spec; update UI/copy. Support Bearer with `fv_test_` / `fv_live_` prefixes. |
| D4 | Public-copy honesty: remove or soften unimplemented claims on the landing page now? | Yes, before sharing the site publicly. |
| D5 | Branch/merge: merge to `main` and deploy from `main`? | Yes (needs an explicit go-ahead to open a PR). |
| D6 | Hosting for backend and AI (CPU vs GPU, region, provider) and data-residency choice. | Decide after Phase 1; drives cost and legal. |
| D7 | Face model and liveness approach given weight licensing. | Run a license review before Phase 3. |
| D8 | AML data sources (official lists vs licensed commercial feeds; PEP source). | Decide before Phase 4; expect a licensing cost. |
| D9 | Launch markets and legal review (Haiti and others), consent and retention policy. | Engage legal/compliance early. |
| D10 | Pricing model (current $0 / $0.40 / custom are placeholders). | Decide after cost per verification is measured. |

---

## 15. Changelog

- 2026-11-19 — Selfie scanner with MediaPipe face detection and a random LEFT/RIGHT head-turn challenge with an animated pointing finger (`FaceScanner.tsx`, `faceDetect.ts`). Basic active challenge only (not certified liveness); tested with synthetic frames, not real devices.
- 2026-11-19 — OpenCV.js card-edge detection in the document scanner (perspective-corrected crop, "move closer/back/center" guidance), and desktop detection with a QR-code hand-off to the phone on `/verify` (`qrcode-generator`, MIT). Face detection for the selfie is still missing.
- 2026-11-19 — Scanner page with automatic capture on `/verify` (document front/back and selfie), auto-advance and countdown. Quality heuristics only, no real document/face detection yet.
- 2026-11-19 — Added the public hosted verification page `/verify` (demo mode): real camera/upload, local image-quality check, issuing-country and document steps, review, 3 languages, brand params from the URL. Nothing is uploaded and no verification result is produced. Country search made accent-insensitive.
- 2026-11-19 — Redesigned the hosted verification preview (Didit-style welcome, issuing-country step with search, document cards, selfie, done; phone chrome; "Secured by Freda Verify"). No social sign-in by decision.
- 2026-11-19 — Added White label page (branding form + live preview of the hosted verification page, mock only) and documented white-label requirements.
- 2026-11-19 — Initial CLAUDE.md. Frontend prototype documented: landing, brand identity, dashboard (Overview, Verifications with media viewer, Businesses, API Keys, Logs, Settings, Support). No backend yet.
