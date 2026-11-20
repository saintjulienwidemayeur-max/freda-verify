# CLAUDE.md — FREDA VERIFY

Permanent technical reference and development guide for **Freda Verify**.
Last updated: 2026-11-19. Keep this file in sync with the code (rule 16, section 12).

> **Read this first:** the repository holds (1) a **frontend prototype** (landing site + sample dashboard + a demo hosted verification page) and (2) a **Phase 1 backend foundation** in `backend/` (accounts, organizations, roles, API keys, audit log, MRZ check-digit validator).
> There is still **no verification engine**: no OCR, no face matching, no liveness server-side, no AML, no result/webhook. Login/sign-up and the **API Keys, Logs, Settings (workspace, team, two-step verification)** pages and the usage card on Overview are **connected to the backend**; Overview charts, Verifications, Businesses, White label and the hosted page are not (sample data / local state). See sections 3.5 (mock inventory), 3.8 (backend) and 3.9 (Supabase + Render).
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
| Fonts | **Self-hosted** with `next/font/local` from npm packages `@fontsource-variable/inter`, `@fontsource-variable/plus-jakarta-sans`, `@fontsource/ibm-plex-mono` (latin subset, SIL OFL); the build no longer needs Google Fonts. |
| Output | **Static export** (`output: "export"` in `next.config.mjs`) → `out/` |
| Hosting | Render **Static Site**: build `npm install && npm run build`, publish dir `out` |
| Backend | **Phase 1 only** (`backend/`, see 3.8): FastAPI + PostgreSQL + Alembic, auth, organizations, API keys, audit/request logs, MRZ validator. Connected to the frontend for auth, API keys, logs, team and MFA (see 3.9) |
| Frontend tests / CI | CI workflow `.github/workflows/ci.yml` (frontend type-check + build, backend lint + migrations + tests); **no frontend tests** |
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
  login/ signup/ forgot-password/ reset-password/   auth pages (components/AuthUI.tsx) talking to the backend
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
lib/
  api.ts                        API client (typed errors, 401 → refresh once, cross-tab refresh lock, safeNext), token storage
  auth.tsx                      AuthProvider/useAuth (login, MFA step, register, logout, organization switch), role helpers `can.*`
components/
  AuthUI.tsx                    Login / sign-up / forgot / reset forms + split-screen layout
  LiveUsage.tsx                 Real usage card on Overview
  DashShell.tsx                 Sidebar (collapsible) + top bar + **session guard** (redirects to /login?next=…), user/org card, organization switcher, sign out; `sample` prop controls the Sample/Live badge
  OverviewChart.tsx             Interactive bar chart
  EmptyState.tsx                Honest empty state used by Verifications and Businesses
  Scanner.tsx                   DOCUMENT scanner with automatic capture: OpenCV.js card-edge detection, shape must match the chosen document, strict validation of the flattened crop (docValidate.ts); fails closed if OpenCV/MediaPipe cannot load
  docValidate.ts                Strict document checks: passport page = shape + face photo on the left + two MRZ text lines; ID/licence front = shape + face photo; back = shape. Also validates uploaded photos
  FaceScanner.tsx               Selfie scanner: MediaPipe face detection + ACTIVE two-step challenge (turn LEFT/RIGHT at random, then turn the OTHER way; blink only with ?blink=1), animated SVG pointing hand + chevrons + label. Fails closed if MediaPipe cannot load
  faceDetect.ts                 MediaPipe Face Landmarker loader + detectFace (478 landmarks, face box, head yaw from the facial transformation matrix + nose/cheek ratio fallback)
  cardDetect.ts                 OpenCV.js loader (lazy, /vendor/opencv.js) + detectCard (Canny + contours + 4-corner/aspect/angle filter) + rectify (perspective warp)
  HostedPage.tsx                Real end-user flow at /verify: consent, country, document, camera/upload, local quality check, review, demo finish. Config via URL params
  HostedPreview.tsx             Mock of the end-user hosted verification page (welcome, country, document, selfie, done), driven by the white-label config
  WhiteLabel.tsx                Branding form (name, logo, colors, theme, shape, language, texts, docs, domain, redirect) + phone preview
  ApiKeys.tsx, Logs.tsx, Settings.tsx, Support.tsx
  FaceMatch.tsx                 Landing animation (document photo vs selfie)
  Sections.tsx                  Landing sections (Platform, Developers, AML, services, FAQ...)
  AmlCard.tsx, ApiHub.tsx       Landing animations
public/ faces/*.webp, hero.png, logo*.{svg,png}
scripts/copy-vendor.mjs  copies the big binaries from node_modules into public/vendor before every build/dev (prebuild/predev); they are git-ignored
public/vendor/ opencv.js (OpenCV 4.10 via npm `@techstark/opencv-js`, Apache-2.0, ~10 MB) — GIT-IGNORED, copied at build; opencv.LICENSE.txt is committed
public/vendor/mediapipe/ wasm/vision_wasm_internal.{js,wasm} (npm `@mediapipe/tasks-vision` 1.2.3, Apache-2.0, ~15 MB) — GIT-IGNORED, copied at build; face_landmarker.task (3.7 MB model), NOTICE.txt and LICENSE-Apache-2.0.txt are committed
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
| `components/ApiKeys.tsx` | **Real** (backend): list/create/revoke through `/organizations/{id}/api-keys`; the secret is shown once and never stored in the browser. (Old client-side key generation was removed.) |
| `components/Logs.tsx` | **Real** (backend): request log (route template, status, latency, key prefix) and audit trail. Empty until the API is used. |
| `components/Settings.tsx` | **Real** (backend): rename organization, team (add existing user, change role, remove), TOTP two-step verification with recovery codes. Webhook URL and notification toggles were removed (no backend yet). |
| `components/HostedPage.tsx` (`/verify`) | **Public page. Real UI; backend only for the session (branding, logo, consent). With a session link (`/verify#s=fvs_…`) it loads the organization's saved branding/logo and records consent; an invalid or expired link shows an error page; the QR hand-off keeps the token. Without a token it is the URL-parameter demo. In session mode each accepted photo is uploaded (PUT `/session/media/...`) BEFORE it is shown as captured, and "finish" calls `/session/complete`; the done screen then says the verification was submitted. Without a token nothing is uploaded (demo). The capture/scan behaviour below is otherwise unchanged. Browser-tested: welcome, consent, no demo banner; the upload endpoints were exercised with the API, NOT through the real scanner (needs a real camera/document).** The scanner opens the camera automatically on each capture step and **captures automatically** (`components/Scanner.tsx`): it analyses the frame area every 140 ms (brightness, glare, sharpness via Laplacian variance, frame-to-frame stability) and captures after ~1.3 s of good frames (selfie: ~3 s with a visible 3-2-1 countdown); a manual "Capture now" appears after 9 s and an upload fallback exists. **Documents now use OpenCV.js card-edge detection** (`cardDetect.ts`): it finds a convex 4-corner shape with a card/passport-page aspect ratio (1.2–1.9) and 65–115° corners, checks fit ("Move closer / back / center"), corner stability, exposure, glare and sharpness, then captures a perspective-corrected, upright crop (~1000 px wide). Limits: it detects a card-SHAPED rectangle, not a genuine document (a credit card, a card-shaped object or a screen can pass); low contrast against the background can miss the edges; no OCR, no document-type classification, no tamper checks. If OpenCV (or MediaPipe, needed for the face-photo check) cannot load, the document scanner **fails closed**: it shows an error with a "Try again" button and accepts nothing. **Selfie (`FaceScanner.tsx`)**: MediaPipe Face Landmarker (self-hosted, in-browser) requires exactly one face, centered in the oval, big enough and frontal (yaw within ±9°) for ~0.8 s, takes the still photo, then **asks the user to turn their head LEFT or RIGHT (random)** showing an animated pointing finger (👈/👉) with chevrons and a direction label. Success = head yaw ≥ 20° in the requested direction for 2 consecutive frames (≈ nose/cheek ratio 0.17 as fallback); the wrong direction shows "Other way"; after 12 s the direction flips ("Let's try again"). Sign convention (verified): yaw > 0 = user's LEFT, < 0 = user's RIGHT, from `atan2(m[8], m[10])` of the facial transformation matrix; the preview is mirrored so the finger points to the same side the user sees. **Limits: this is a basic active challenge, NOT certified liveness.** A replayed video, a deep-fake or a 3D mask can pass; no PAD, no texture/depth analysis, no server-side re-check, no face matching against the document. It was tested only with synthetic perspective-warped frames (≈5° effective yaw) using a test-only build flag `NEXT_PUBLIC_TURN_DEG` (**never set it in production**; default 20°) and never with real head turns on real phones: thresholds must be tuned on real devices. If MediaPipe cannot load, the selfie scanner **fails closed** (error + "Try again"); there is no weaker fallback. Document authenticity, face matching and certified liveness belong to Phases 2–3. Camera (`getUserMedia`) and file input work; a local quality check (brightness, glare, blur via canvas) runs in the browser. In demo mode (no session link) photos live only in memory (`blob:` URLs), are never uploaded (no network request is made), and are deleted on submit/restart; the final screen says "Demo complete — no verification was performed" and **never shows a verdict**. In session mode they are uploaded (see 3.8, "Photos"). Branding comes from URL params (`name,color,theme,shape,lang,docs,title,subtitle,support`), validated and rendered as text; `redirect` and logo are deliberately NOT accepted from the URL (open-redirect / untrusted-image risk). Upload is wired only in session mode, after consent, with encrypted storage and a retention period (see 3.8). |
| `components/WhiteLabel.tsx` | **Settings are real** (backend `GET/PUT /organizations/{id}/branding`, table `branding`, validated server-side; owners/admins write, every member reads; audit `branding.updated`). **Logo is real:** stored in PostgreSQL (table `branding_logos`, bytea, PNG/JPEG/WebP only, ≤ 512 KB, magic-byte check, SVG refused, served `nosniff` + sandbox CSP, `PUT|GET|DELETE /organizations/{id}/branding/logo`, members read / owners-admins write, audited); it is served to authenticated members and, through a verification session token, to the hosted page (`GET /session/logo`). **Still mock:** the custom domain and redirect URL are saved but never verified or used; the hosted page reads the saved settings (and logo) **only when opened with a session link** (`#s=…`); without a token `/verify` stays the URL-parameter demo (the "Open the live page" link in White label uses that demo path). The phone preview (`HostedPreview.tsx`) is a clickable mock: country list is a fixed sample of 24 ISO codes; Kreyòl falls back to French country names. |
| `components/Verifications.tsx` | **Real** (backend): create a link, list (status, photo count, expiry), review panel with the decrypted photos (owners/admins), manual Approve/Reject, delete photos now. Statuses: PENDING, MANUAL_REVIEW, APPROVED, REJECTED, EXPIRED. The decisions are HUMAN decisions; no automated check exists. |
| `app/dashboard/businesses` | **Empty state** (`components/EmptyState.tsx`): the 8 fake companies were deleted (2026-11-20); KYB does not exist. |
| `components/Overview.tsx`, `OverviewChart.tsx` | **Real** (backend): requests/errors (30 days), active API keys, team members, per-day chart from `/usage`, recent API activity from request-logs. The "Verifications" card is an honest empty state (no engine yet). All invented numbers were removed (2026-11-20). |
| `components/FaceMatch.tsx` | Marketing animation; scores 98 % / 34 % are scripted. |
| `components/Support.tsx` | "All systems operational" is static text. |

Every dashboard page shows a "Sample data" badge and/or a "Demo:" note. Keep these until the page is backed by real data (rule 14).

### 3.7 Hosted page `/verify`: scanner and validation details (current behaviour)

- **Default branding:** if the client has not filled the white label (no `name` param), the hosted page uses the **Freda Verify name and logo mark** ("Verification for Freda Verify"); with a name but no logo it shows an initial tile in the brand color. The White label form leaves the name empty (placeholder "Freda Verify (default)") and the live link only carries `name` when it is filled.
- **Flow:** QR hand-off on desktop → welcome (consent) → issuing country → document type → document front (and back for ID/licence; passport = photo page only) → selfie → "Demo complete". There is **no review screen**; each captured document shows a short "Captured!" preview and advances automatically; the selfie finishes the flow.
- **Passport is strict.** A passport page is accepted only if the flattened crop has (1) a passport-page aspect ratio (1.30–1.56; ID-1 cards are 1.45–1.75, so an ID card is refused as a passport and vice versa), (2) a face photo of printed size (20–85 % of page height) on the left half (MediaPipe face detector) and (3) the two dense full-width text lines of the MRZ in the bottom ~30 % (OpenCV adaptive threshold + row/column analysis). ID/licence front needs shape + face photo; back needs shape. Uploaded photos go through the same pipeline and are stored as the flattened crop. Rejections explain why (shape / photo / MRZ / cannot check).
- **Tested only with synthetic documents** drawn with PIL (a valid passport page, one without MRZ, one without photo, an ID card, a plain face, an upload of each). It was never tested with real passports, real lighting, glare, worn documents or different national passport layouts; the MRZ and face thresholds will need tuning on real samples. **The checks do not prove a document is genuine** (a printed or on-screen copy of a real page with the right layout passes); MRZ check digits are not verified, no OCR, no tamper detection.
- **Selfie challenge:** one face, centered, looking straight → still photo taken; then task 1 = turn LEFT or RIGHT (random) and task 2 = turn the OTHER way (random content, user must look straight between tasks, 14 s per task with the turn threshold relaxed to 75 % after 6 s, 20° yaw by default measured relative to the user's own straight pose). Blink is implemented with baseline-relative blendshape thresholds but is **opt-in (`?blink=1`)**: with a synthetic closed-eye image the model scored only 0.34–0.39 and the open-eye baseline of the test portrait was already 0.28, so it could not be validated; do not enable it for users before testing on real faces/devices.
- **First real-device test (iPhone, Safari, 2026-11-19, user screenshots):** MediaPipe ran on the GPU delegate at 9–10 fps; the two-step challenge (right then left) completed with "Parfait !"; head yaw reached 38.6° (ratio 0.60) on a turn and ~1–3° when looking straight (baseline 1.5°), so the 20° threshold is comfortable; open-eye blink scores were 0.03–0.33 (varies with lighting/angle, which is why blink stays opt-in); the animated hand + chevrons + label were legible. One device only: still test Android, low-end phones, other lighting.
- **Debug overlay:** open `/verify?...&debug=1` on a phone to see live values (delegate/fps, number of faces, head yaw in degrees, nose/cheek ratio, blink scores, document ratio/fill/sharpness). Use it to tune thresholds on real devices.
- **Still NOT certified liveness.** A replayed video, a deep fake or a 3D mask can pass; random multi-step content only makes pre-recorded replay harder. There is no face match between selfie and document photo (needs a license-cleared face-recognition model, D7) and no server-side verification.
- Engines are preloaded when the user reaches the document step (OpenCV ~10 MB, MediaPipe ~15 MB wasm + 3.7 MB model).

### 3.6 Landing-page claims (corrected 2026-11-20)

The landing page (`app/page.tsx`, `components/Sections.tsx`) was rewritten so it only claims what exists: accounts/teams/roles, API keys, request + audit logs, white-label settings, and **demo** capture pages. Everything else is labelled "prévu" / "démo" / "illustration":

- hero says the engine is under construction; no "automated in seconds", no "no manual review queue", no "catches deepfakes";
- services list: document and face = "démo" (browser capture only, nothing uploaded, not certified liveness); address, AML, KYB, Video KYC = "prévu";
- API example is the real `GET /api/v1/usage` with `Authorization: Bearer` (the fake `api.freda.dev/v1/sessions` + `x-api-key` was removed, closing D3 for the landing copy); docs, sandbox, SDKs, MCP are stated as not existing;
- security section lists only what is implemented (argon2id, TOTP, hashed keys, append-only audit, tenant isolation) and names the missing items (document encryption, retention, regions, on-prem, external audit);
- pricing shows "À définir" (no invented prices); FAQ rewritten; the placeholder `mailto:contact@example.com` was replaced by a sign-up link; footer no longer shows dead "Docs · Status · Privacy" items;
- still illustrative by design: the face-match animation (scripted scores), the AML card, the audit JSON sample (`case_20817`), each labelled as illustration.

Re-check this list whenever a feature ships or a claim is added (rule 15). Legal review before public launch is still required (D4/D9).

## 3.8 Backend (Phase 1 foundation)

Location `backend/` (Python, FastAPI, SQLAlchemy 2, Alembic, PostgreSQL). Local infra in `infra/docker-compose.yml`. CI in `.github/workflows/ci.yml`.

```
backend/
  app/main.py                  app factory, CORS, /health, /health/ready, routers under /api/v1
  app/core/                    config (env FV_*), security (argon2id, JWT, API keys, Fernet), deps (auth + RBAC), errors, middleware, ratelimit, net
  app/models.py                users, organizations, memberships, refresh_sessions, password_reset_tokens, recovery_codes, api_keys, branding, branding_logos, verifications, verification_media, verification_checks, audit_logs, request_logs
  app/api/v1/                  auth.py, orgs.py (orgs, members, api keys, audit logs, usage), tools.py (MRZ check)
  app/services/                audit.py, mrz.py (ICAO 9303 TD1/TD2/TD3 parser + check digits)
  alembic/versions/0001_*.py   initial schema in the dedicated PostgreSQL schema `freda_verify` (+ trigger that makes audit_logs append-only)
  alembic/versions/0002_*.py   lock-down: row level security on every table + revoke from Supabase `anon`/`authenticated`
  tests/                       118 tests against a real PostgreSQL (runs the real migrations)
  docker-entrypoint.sh         applies the migrations at container start (tables are created automatically), then starts uvicorn
infra/docker-compose.yml       postgres 16, redis 7, minio, backend; every secret required from infra/.env (see infra/.env.example)
```

**Endpoints** (`/api/v1`): `POST /auth/register|login|refresh|logout|mfa/verify|mfa/setup|mfa/enable|mfa/disable|password/forgot|password/reset`, `GET /auth/me`; `GET|POST /organizations`, `GET|PATCH /organizations/{id}`, `GET|POST /organizations/{id}/members`, `PATCH|DELETE /organizations/{id}/members/{user_id}`, `GET|POST /organizations/{id}/api-keys`, `DELETE /organizations/{id}/api-keys/{key_id}`, `GET /organizations/{id}/audit-logs`, `GET /organizations/{id}/request-logs`, `GET|PUT /organizations/{id}/branding`, `PUT|GET|DELETE /organizations/{id}/branding/logo`; **verification sessions** `POST|GET /verifications`, `GET /verifications/{id}` (API key, or dashboard user with `organization_id`; viewers read only) and the **hosted-page endpoints** `GET /session`, `GET /session/logo`, `POST /session/consent` (authenticated ONLY by the `fvs_…` session token); `GET /usage` (API key or `?organization_id=`); `POST /tools/mrz/check`. OpenAPI at `/docs` (disabled when `FV_APP_ENV=prod`). **Not built yet** (spec endpoints): `/verifications/{id}/result` and `/webhooks`. The spec's `documents|selfie|complete` upload paths are implemented as session-token endpoints instead (below).

**Photos (2026-11-20).** Session endpoints `PUT /session/media/{document_front|document_back|selfie}?doc_type=id|passport|license&country=XX` (raw JPEG/PNG/WebP, magic-byte check, ≤ `FV_MEDIA_MAX_BYTES` = 2 MB, streamed cap, requires consent and a PENDING non-expired session, replaces a previous photo of that kind) and `POST /session/complete` (needs document front + selfie, plus back for ID/licence; sets **MANUAL_REVIEW**, locks the session). Storage: table `verification_media`, bytes **Fernet-encrypted** with `FV_ENCRYPTION_KEY` (key never in the database), SHA-256 of the plain image, **Photos are KEPT until a person deletes them** (owner decision 2026-11-20: `FV_MEDIA_RETENTION_DAYS` defaults to 0 = no automatic deletion, `purge_after` is NULL). If you set it > 0, `purge_after` = upload + N days and the purge runs at startup and on every upload (no scheduler). Keeping biometric photos indefinitely needs a legal basis and a retention policy (D9): review before real customers. Reviewer endpoints (dashboard users, by organization): `GET .../verifications/{id}/media` (metadata, all roles), `GET .../media/{kind}` (decrypted image, **owner/admin only, every view audited**, `no-store`), `DELETE .../media` (owner/admin, audited; the record stays), `POST .../decision` (owner/admin, APPROVED/REJECTED only from MANUAL_REVIEW, with optional note, audited). **MRZ reading (OCR):** after `/session/complete` a background task (`run_mrz_check`) reads the machine-readable zone of the document photos with **Tesseract** (`app/services/ocr.py`: bottom crop, upscale, contrast, character whitelist, two crops × two preprocessings, candidates for TD1/TD2/TD3 with ±3-char padding) and validates it with the ICAO 9303 parser (`app/services/mrz.py`); the best reading (most check digits passed) is stored in `verification_checks`, Fernet-encrypted (it holds names, birth date, document number). Reviewers (owner/admin, audited) see it via `GET .../verifications/{id}/checks` and can re-run it with `POST .../checks/mrz`. One reading at a time per process (semaphore). The Docker image installs `tesseract-ocr` and the OCR-B model (CI too, plus `fonts-ocr-b` for the tests). **Accuracy (measured 2026-11-20 with `python -m tools.ocr_eval --synthetic --n 24 --seed 7`, 312 generated pages = 13 degradations × TD1/TD2/TD3, real OCR-B font, ground truth known; the code was tuned on seed 1 and measured on fresh seed 7): MRZ found 97.4 %; every check digit valid 94.6 %; all identity fields (document number, dates, nationality, issuing country, sex) exactly right 91.3 %; names exactly right 95.8 %; 'confirmed' (two independent readings agree) 88.1 %. Wrong readings that still pass the check digits: 10/312 (3.2 %), of which 4 were 'confirmed'; almost all are document-number errors (O/0, I/1, B/8 and compensating pairs): ONE check digit is one digit, a wrong text passes it about 1 time in 10, so a valid check is NOT proof of a correct reading. Good: clean, JPEG q35, downscale, noise, ±2/5° rotation, perspective, low contrast, 'phone' combination (≈ 95–100 % fields). Weak: heavy blur (σ=3: 67 %), glare over the MRZ (54 %). The score depends on the Tesseract model: with the generic `eng` model the same test gave 19 % check-digit-valid on clean pages; the pinned OCR-B model (`ocrb.traineddata`, Shreeshrii/tessdata_ocrb, Apache-2.0, SHA-256 pinned in the Dockerfile and CI, falls back to `eng` if missing) is essential.** **These are SYNTHETIC pages: the OCR-B model was trained on OCR-B fonts that overlap with the font used to render the test, so the numbers are optimistic. Real printing, laminate/holograms, wear, national layouts and phone photos of real passports (incl. ID cards of Haiti/diaspora) have NOT been measured: use `python -m tools.ocr_eval --dir <your lawful photos> [--labels labels.json]` (never commit photos). No real document was available in the build sandbox (no network access to specimen archives).** Reading strategy: two crops × two preprocessings, then ±2/4/6° rotations if not confirmed; candidates must match a TD1/TD2/TD3 layout (±3 chars padded with '<'); repairs decided by the check digits (optional-data filler misread as K/X; O↔0 in the document number); a reading counts as a vote only if all check digits pass, `agreeing` = number of independent readings giving the same fields (stored and shown to reviewers: 'N readings agree' vs 'single reading: verify on the photo'). Latency ≈ 1–5 s per photo on one core (set `OMP_THREAD_LIMIT=1`, done in the Dockerfile; without it parallel runs slowed to >10 s per call). Passing check digits shows the text is internally consistent, not that the document is genuine; the result is advice for a human and never decides. **Still no** face match, liveness, document authenticity or AML; a person decides. Costs/limits: Tesseract needs RAM (~100–300 MB peak) on a 512 MB free Render instance and may be slow; photos live in PostgreSQL (Supabase free tier = 500 MB; ~3 photos × ≤2 MB per verification); move to encrypted object storage before volume. Not done: per-organization retention setting, scheduled purge, OCR accuracy measurement on real documents, PaddleOCR (heavier, not installed), MRZ cross-check against the printed text/selfie, e-mail/webhook on submission, malware scanning, EXIF stripping, image re-encoding, Row-level audit of every API-key read.

**Verification sessions (2026-11-20).** `POST /verifications` returns the session token once (`fvs_…`, only its SHA-256 stored, 24 h default, 5 min–7 days) and a link `{FV_HOSTED_URL}/verify#s=<token>`; the token is in the URL **fragment** so it never reaches a server log or Referer, and the page sends it only as a Bearer header to `/session*`. Session endpoints: rate limit per token, 401 for unknown tokens (keys/JWTs do not open sessions and the token opens nothing else), 410 when expired, they expose only the public branding (name, colors, theme, shape, language, texts, accepted documents, support e-mail, hide_powered, has_logo): never the redirect URL, domain or any key. Status is PENDING and stays PENDING (EXPIRED is derived from `expires_at`); no state machine beyond that exists yet. Consent is recorded once (`consent_at`) with an audit entry. Env (`test`/`live`) comes from the key; dashboard-created links are `test`. Settings: `FV_HOSTED_URL` (default the static site URL), `FV_SESSION_TTL_MINUTES`, `FV_SESSION_RATE_LIMIT`.

**Security decisions implemented and tested:**
- Passwords: argon2id, min 10 chars, rejects common/repetitive passwords and ones containing the e-mail name; constant-time-ish login (dummy hash for unknown e-mails); same error for unknown e-mail and wrong password; lockout after 5 failures (15 min) shown as a generic 429; per-IP and per-e-mail rate limits on credential endpoints (Redis when `FV_REDIS_URL` is set, otherwise in-process).
- Sessions: 15-min JWT access token (HS256, `typ` claim so MFA/refresh tokens can never be used as access tokens); opaque refresh tokens stored only as SHA-256, **rotated on every use**, and **reuse of a rotated token revokes every session of that user**; password reset revokes all sessions.
- MFA: TOTP (pyotp), secret encrypted at rest (Fernet), replay of a TOTP step refused, 8 single-use recovery codes stored hashed.
- API keys: `fv_test_…` / `fv_live_…`, secret returned **once**, only SHA-256 + prefix + last 4 stored, revocation, per-key rate limit, `last_used_at`.
- Tenant isolation: every query is scoped by `organization_id`; non-members get **404** (not 403) so organizations cannot be enumerated; keys/ids of another tenant are "not found" even through your own org path; API keys cannot call dashboard routes.
- RBAC: owner / admin / member / viewer with a permission map in `core/deps.py`; last-owner protection; only owners can create/remove owners.
- Audit log (who/what/when/IP, no secrets) is append-only at the database level (trigger rejects UPDATE/DELETE). Request log stores method, route template, status, latency, org and key id only: **no bodies, headers, query strings or IPs**.
- Errors are structured (`{"error": {code, message, request_id, details}}`), validation errors never echo submitted values, 500s never leak internals; `X-Request-ID` is accepted/generated; security headers on every response; CORS allow-list from env (wildcard refused in prod); in `prod` the app refuses to start without `FV_SECRET_KEY` (≥ 32 chars) and `FV_ENCRYPTION_KEY`.

**MRZ validator (`app/services/mrz.py`)**: parses TD3 (passport), TD2 and TD1 (ID card) MRZ text and verifies the ICAO 9303 check digits (document number, birth date, expiry date, optional data, composite) with weights 7-3-1, parses names/dates/sex/expiry and flags impossible dates and expired documents; optional correction of common OCR confusions (O/0, I/1, B/8, S/5, Z/2) only where the grammar requires digits/letters (the number of corrections is reported). Tested with the ICAO specimen TD3 and TD1 and a generated TD2, tampered digits, wrong layouts and forbidden characters. **It validates the internal consistency of text you already have; it does not read the MRZ from an image (no OCR yet) and does not prove a document is genuine.** The hosted page does not use it yet (it needs OCR; Phase 2: PaddleOCR on the server).

**Known gaps in Phase 1 (do not hide them):** the registration form does not verify e-mail addresses and the reset page cannot receive a link (no e-mail provider); no e-mail verification at sign-up (anyone can register any address); no e-mail provider, so password-reset links are only logged in `dev` (never in prod) and nothing is sent; members can be added only if they already have an account (no invitation e-mails); no `Idempotency-Key` handling yet; request logs are written synchronously; the in-process rate limiter is per worker (use Redis in prod); no backups, no monitoring, no pen test; platform-admin features absent; the Docker image and the compose stack were validated only with `docker compose config` (no Docker daemon in the build sandbox), not built or run; tests ran on Python 3.13 / PostgreSQL 16.15 locally while the Docker image and CI use Python 3.12 (the CI workflow had not run when this was written).

**Run locally:**
```bash
cd backend && python -m venv .venv && . .venv/bin/activate && pip install -r requirements-dev.txt
cp .env.example .env            # fill FV_DATABASE_URL (and generate FV_SECRET_KEY / FV_ENCRYPTION_KEY)
alembic upgrade head && uvicorn app.main:app --reload
FV_TEST_DATABASE_URL=postgresql+psycopg://USER:PASS@localhost:5432/freda_test python -m pytest   # database name must end in _test (it is wiped)
ruff check .
```

## 3.9 Supabase + Render: how the database, backend and frontend connect

**Architecture.** Static site (Render) → HTTPS → FastAPI container (Render web service) → PostgreSQL (Supabase). Supabase is used **only as managed PostgreSQL**; authentication, MFA, roles and API keys are Freda Verify's own (backend). We do not use Supabase Auth, PostgREST or the anon key: the browser never talks to the database.

**Tables create themselves.** The container runs `alembic upgrade head` at every start (`docker-entrypoint.sh`, `FV_AUTO_MIGRATE=true`). It creates the schema `freda_verify` and every table; later versions add only what is missing; a PostgreSQL advisory lock makes two containers starting together safe. Alternative without a server: `alembic upgrade head --sql` prints the SQL to paste in the Supabase SQL editor.

**Isolation (important).** All tables live in the schema **`freda_verify`**, never in `public`. This was introduced after finding that the existing Supabase project "Freda Workspace" already hosts another application (`public.users`, `public.api_keys`, orders, domains…) whose names would have collided. **Never point Freda Verify at a database that holds another application's data unless you accept this schema isolation; the owner of that project chose a separate project instead.** Migration 0002 enables row level security (no policies) on every table and revokes `anon`/`authenticated` privileges, so even if the schema is later exposed to the Supabase API nothing is readable. After the first deploy run the Supabase security advisors and fix anything reported.

**Connection string.** Use the **Session pooler** string (Supabase dashboard → Connect), it works over IPv4 and keeps prepared statements: `postgresql://postgres.<project-ref>:<DB-PASSWORD>@aws-0-<region>.pooler.supabase.com:5432/postgres`. The backend accepts `postgres://` / `postgresql://` and adds `sslmode=require` for remote hosts. The transaction pooler (port 6543) is supported (`prepare_threshold=None`) but is not recommended for migrations. The direct connection (`db.<ref>.supabase.co`) is IPv6-only on the free tier and may not be reachable from the host. Hardening (recommended): create a dedicated database role for the app instead of the `postgres` role.

**Runbook.**
1. Supabase: create the new project (not "Freda Workspace"), set a strong DB password, copy the **Session pooler** URI.
2. Render: *New → Blueprint* on this repo (`render.yaml`: service `freda-verify-api` (Docker, `backend/`) + static site `freda-verify`). Secrets are typed in the Render dashboard, never in git: `FV_DATABASE_URL` (the URI above), `FV_CORS_ORIGINS` (JSON list with the static site URL, e.g. `["https://freda-verify.onrender.com"]`). `FV_SECRET_KEY` and `FV_ENCRYPTION_KEY` are generated by Render (`generateValue`); keep them stable (changing `FV_SECRET_KEY` signs everyone out; changing `FV_ENCRYPTION_KEY` makes stored TOTP secrets unreadable).
3. Static site env var `NEXT_PUBLIC_API_URL` = the API service URL (e.g. `https://freda-verify-api.onrender.com`). It is inlined at build time: redeploy the static site after changing it.
4. Open `/signup`. First start: check the API logs for `Running upgrade -> 0001`, then `GET /health/ready`.

**Frontend session handling (decision).** Access token (15 min) lives in memory only. The refresh token is stored in `localStorage` when "Keep me signed in" is ticked, otherwise in `sessionStorage`. Trade-off: JavaScript-readable storage is exposed to XSS (no CSP is configured yet; the site loads no third-party scripts). Mitigations in place: refresh tokens rotate on every use and reuse revokes all sessions; short access tokens. Refreshes are serialised across tabs with the Web Locks API (without it, two tabs refreshing the same token would look like theft and sign the user out everywhere). **Move to an httpOnly, Secure, SameSite cookie once the API and the app share a registrable domain** (custom domain, e.g. `app.example.com` + `api.example.com`; with both on `onrender.com` browsers treat them as different sites and block such cookies). The route guard in `DashShell` is UX only; the API refuses every request without a valid session.

**Deployed (2026-11-20):** Render web service `freda-verify-api` in workspace "freda word" (URL https://freda-verify-api.onrender.com), branch `claude/eloquent-thompson-o5zagp`, auto-deploy on commit; Supabase project "Freda verify" (ref `uewiqzlcncwuzfjzwzqy`, us-west-2). First boot created all tables; `request_logs` rows prove the API writes to Supabase. Still to do by hand: set the Render health check path to `/health`; set `NEXT_PUBLIC_API_URL` on the static site; the free plan sleeps after ~15 min idle.

**Verified end-to-end locally** (Playwright against uvicorn + PostgreSQL 16 + the static build, 20 checks): guard redirect with `?next=`, weak-password message, sign-up, real user/org in the sidebar, key creation (secret shown once, gone after reload), the key authenticating against the API, request log and audit trail, revocation (401), organization rename, MFA enrolment + recovery codes, session surviving reload, sign out, MFA sign-in with a recovery code, two tabs loading at once, generic forgot-password answer. **Not verified:** the Supabase connection itself (no project/password available to the build sandbox), the Render Blueprint, a real browser on Safari/Android, e-mail sending (none exists).

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
| A | Authentication | register, login, reset, MFA, RBAC, sessions | **Phase 1 done in backend** (register, login, refresh rotation + reuse detection, logout, password reset, TOTP MFA + recovery codes, lockout, rate limit). Missing: e-mail verification, e-mail sending, frontend pages |
| B | Organizations | multi-tenant isolation, team, permissions, settings | **Phase 1 done in backend** (orgs, memberships, roles owner/admin/member/viewer, tenant isolation tests). Missing: e-mail invitations, org deletion, settings |
| C | Document engine | upload, quality, OCR, classification, MRZ, expiry, consistency, tamper hints | **Started**: upload + encrypted storage; server-side MRZ reading (Tesseract) with ICAO check digits and expiry flag. Missing: accuracy measurement on real documents, classification, text OCR of other fields, tamper hints |
| D | Biometric engine | selfie, face detect/compare, liveness, anti-spoofing, confidence | not started |
| E | AML engine | PEP, sanctions, watchlists, name/DOB matching, history | not started |
| F | Risk engine | document/biometric/AML risk, indicators, thresholds | not started |
| G | Decision engine | APPROVED / REJECTED / PENDING / MANUAL_REVIEW / EXPIRED | not started |
| H | Verification management | sessions, links, progress, storage, manual review, reports | **Partial**: sessions, links, consent, expiry, encrypted photo storage, retention, manual review real; no results API/webhooks/review queue filters |
| I | Developer platform | API keys, test/live, docs, webhooks, logs, usage, SDK docs | **Partial**: API keys (test/live, hashed, revoke), request logs, `/usage`, MRZ tool endpoint exist in backend. Missing: webhooks, sandbox, docs, SDKs; UI still mock |
| J | Administration | platform admins, monitoring, fraud, audit, config | **Partial**: append-only audit log (DB trigger) + per-org audit endpoint. Missing: platform admin endpoints/UI, monitoring |

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
7. (fixed 2026-11-20) fonts used to come from Google at build time and made CI fail intermittently; they are now self-hosted.
8. The build output uses `output: "export"`; any future need for server-side session handling must live in the FastAPI service, not Next.

---

## 9. AI / ML components and licensing

Rule: verify the license of **code, model weights and training data** separately. "Open source code" does not imply "weights usable commercially".

| Component | Purpose | License note (verify before use) |
|---|---|---|
| OpenCV.js (`@techstark/opencv-js` 4.10, vendored in `public/vendor`) | Client-side card detection | Apache-2.0 (OpenCV >= 4.5). License file shipped as `public/vendor/opencv.LICENSE.txt`; keep it with the binary. ~10 MB (≈3.4 MB gzip), loaded lazily only on `/verify` |
| MediaPipe Tasks Vision `@mediapipe/tasks-vision` 1.2.3 (npm dependency; runtime copied to `public/vendor/mediapipe` at build) + `face_landmarker.task` (face detector = BlazeFace short-range, landmarks = Face Mesh V2, blendshapes V2) | Client-side face detection, head pose, blinks | **License confirmed:** the official model cards (Face Mesh V2, BlazeFace Short Range, Blendshape V2; downloaded 2026-11-19 from storage.googleapis.com/mediapipe-assets) all state "Licensed under Apache License, Version 2.0"; the library is Apache-2.0. **Cautions from the same cards:** intended use is AR/entertainment, "not intended for human life-critical decisions", and the models provide no face recognition or identification; BlazeFace needs faces ≥ 20 % of the image sides; its recall varies by skin tone (94.7 %–100 %) and region (92.5 %–100 %) — **test on the real target population (Haiti/diaspora, varied skin tones) before relying on it**. Not a face-matching model. ~15 MB wasm (≈4 MB gzip) + 3.7 MB model, loaded lazily |
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
| Overview | **Real data** (usage, keys, members, recent API activity); verification stats absent until the engine exists |
| Verifications | Real: links, uploads, encrypted photos, manual review; no automated engine, no results API, no webhooks |
| Customers | **missing** (could merge with Verifications or be the business's end-customer directory) |
| Organizations | **missing** (Businesses page is KYB subjects, not tenants) |
| Developers | **missing** (docs, test documents, SDK downloads) |
| API Keys | UI mock ✔ |
| Webhooks | **missing** page (only a URL field in Settings) |
| Analytics | **missing** (Overview chart only) |
| Settings | UI mock ✔ |
| Logs, Support | UI mock ✔ (extra, not in spec) |
| White label | Settings saved in the backend; logo/domain/redirect not functional (`/dashboard/white-label`): brand, colors, theme, button shape, language (EN/FR/HT), texts, accepted documents, redirect URL, custom domain, hide "Powered by", live phone preview |
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

Backend commands: see section 3.8.

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
**Status (2026-11-19): exit criteria met in the backend** (register → org → API key, 54 tests including tenant isolation; smoke-tested with uvicorn + PostgreSQL + Redis). Still open for Phase 1: e-mail verification and sending, org invitations, idempotency keys, frontend login/sign-up wired to the API, backups, deployment, CI run.

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
| D2 | Repo layout: add `backend/` and `infra/` beside the current app, or restructure into a monorepo (`apps/web`) now? | **Decided & done**: `backend/` and `infra/` sit beside the Next.js app. |
| D3 | API auth style and path: `Authorization: Bearer` + `/api/v1/verifications` (spec) vs the `x-api-key` + `/v1/sessions` shown in the UI. | **Backend follows the spec**: `Authorization: Bearer` (JWT for dashboard users, `fv_test_`/`fv_live_` keys for the API) under `/api/v1`. UI/landing copy still show `x-api-key` and `/v1/sessions`: update them. |
| D4 | Public-copy honesty: remove or soften unimplemented claims on the landing page now? | **Done 2026-11-20** (section 3.6); still needs legal review before public launch. |
| D5 | Branch/merge: merge to `main` and deploy from `main`? | Yes (needs an explicit go-ahead to open a PR). |
| D6 | Hosting for backend and AI (CPU vs GPU, region, provider) and data-residency choice. | Decide after Phase 1; drives cost and legal. |
| D7 | Face model and liveness approach given weight licensing. | Run a license review before Phase 3. |
| D8 | AML data sources (official lists vs licensed commercial feeds; PEP source). | Decide before Phase 4; expect a licensing cost. |
| D9 | Launch markets and legal review (Haiti and others), consent and retention policy. | Engage legal/compliance early. |
| D10 | Pricing model (current $0 / $0.40 / custom are placeholders). | Decide after cost per verification is measured. |

---

## 15. Changelog

- 2026-11-20 — OCR accuracy measured on generated OCR-B pages (`backend/tools/ocr_eval.py`, 13 degradations): the generic `eng` model was poor (19 % valid), so the pinned OCR-B Tesseract model is now installed (Dockerfile, CI); added filler/O-0 repairs guided by check digits, deskew, and multi-reading agreement (`agreeing`, shown in the review panel); fresh-seed result 91 % of pages with all identity fields right, 3.2 % wrong-but-check-digit-valid. Findings and limits in 3.8. Not measured on real documents (none available offline).
- 2026-11-20 — CI backend failure fixed: `alembic check` found that the indexes on `verification_media` / `verification_checks` were named differently in the models (`index=True` → schema-prefixed name) than in migrations 0007/0008. Models now declare the same explicit index names as the migrations (no new migration needed, nothing changes in deployed databases). Lesson: run `alembic upgrade head && alembic check` locally before pushing a migration.
- 2026-11-20 — Server-side MRZ reading: `app/services/ocr.py` (Tesseract + ICAO validator), table `verification_checks` (migration 0008, encrypted), background run after submission, reviewer endpoints (`GET .../checks`, `POST .../checks/mrz`) and a review-panel section; Dockerfile and CI install tesseract; 8 new tests (116 total) + browser check. Retention decision: photos are now kept until a person deletes them (default `FV_MEDIA_RETENTION_DAYS=0`, migration 0008 clears existing `purge_after`); the hosted-page notice no longer claims automatic deletion. NOT validated on real documents.
- 2026-11-20 — Document and selfie upload (session mode): migration 0007 (`verification_media`, submission/decision columns), encrypted storage, retention purge, `PUT /session/media/{kind}`, `POST /session/complete` → MANUAL_REVIEW, reviewer endpoints (list/view/delete photos, decision) with RBAC and audit; hosted page uploads in session mode; dashboard review panel. 8 new tests (108 total) + browser check (consent, API upload, decrypted photos in the review panel, approve, delete, closed session). NOT browser-tested: the real scanner → upload path. No automated verification exists; legal/privacy review of retention, consent text and biometric handling (D9) is required before real customers use it.
- 2026-11-20 — CI frontend job failed intermittently because `next/font/google` could not load Plus Jakarta Sans at build time (runs 7 and 11; the same code passed in other runs). Fonts are now self-hosted via `next/font/local` + @fontsource packages.
- 2026-11-20 — Verification API started (sessions only): table `verifications` (migration 0006, RLS), `POST|GET /verifications`, public session endpoints (`/session`, `/session/logo`, `/session/consent`) with a hashed token carried in the URL fragment, expiry (410), per-token rate limit, tenant isolation, audit; hosted page `/verify` now serves the organization's saved branding and logo through the session; dashboard Verifications page is real (create link, list). 14 new backend tests (100 total) and a browser check (branding+logo → link → branded page, consent, invalid link). NOT built: document/selfie upload, engine, results, webhooks, `Idempotency-Key`, completion state.
- 2026-11-20 — Logo storage: migration 0005 (`branding_logos`, RLS), raw-body upload/download/delete endpoints with strict validation (type, magic bytes, 512 KB streamed limit, SVG refused), frontend upload/remove/reload; 8 new tests (86 total) and a browser check (upload, reload, decode, SVG refused, remove). Stored in PostgreSQL rather than object storage: fine for small logos; move to S3/Supabase Storage + a separate public asset origin when `/verify` must serve it to end users.
- 2026-11-20 — Landing copy corrected to match reality (see 3.6): unimplemented claims removed or labelled prévu/démo/illustration, fake API example replaced by the real `/usage` call, invented prices removed, placeholder contact e-mail removed.
- 2026-11-20 — White label connected to the backend: table `branding` (migration 0004, RLS), `GET/PUT /organizations/{id}/branding` with strict validation, role checks, audit entry, tenant isolation; CORS now allows PUT (a missing method would have blocked saving from the browser); 20 new backend tests, browser check of save + reload. Domain verification and serving the saved branding to `/verify` are NOT done.
- 2026-11-20 — Removed the fake Verifications (10 people), Businesses (8 companies) and media viewer; both pages are honest empty states. White label preview and landing animations remain demo/mock.
- 2026-11-20 — Overview now shows only real backend data (new `Overview.tsx`, data-driven `OverviewChart`); fake stat cards, chart, recent verifications and activity removed; `LiveUsage.tsx` merged into it.
- 2026-11-20 — Backend deployed as a Render **Web Service** (`freda-verify-api`, Docker, free plan, Oregon) against the new Supabase project "Freda verify"; migrations 0001–0002 ran automatically (10 tables in `freda_verify`). Supabase advisor findings addressed by migration 0003 (RLS on `alembic_version`, pinned `search_path` of the audit trigger function). Open finding that is NOT ours: `public.rls_auto_enable()` (SECURITY DEFINER, executable by `anon`/`authenticated`) exists in the Supabase project; revoke EXECUTE if it is not needed.
- 2026-11-19 — Frontend connected to the backend: login, sign-up, forgot/reset password, session guard, user/org card + organization switcher, real API Keys / Logs / Settings (team, MFA) pages and live usage card; backend moved to the dedicated schema `freda_verify` (RLS + revoke migration), tables created automatically at container start, DSN normalisation for Supabase, `/request-logs` endpoint, `render.yaml`; 20 browser end-to-end checks, 58 backend tests. Supabase/Render deployment not performed.
- 2026-11-19 — Backend Phase 1 foundation (`backend/`, `infra/`, CI): FastAPI + PostgreSQL + Alembic, auth (argon2id, JWT, refresh rotation, TOTP MFA, lockout, rate limit), organizations + RBAC + tenant isolation, hashed API keys, append-only audit log, request logs, structured errors; ICAO 9303 MRZ check-digit validator + `/tools/mrz/check`; 54 tests. Frontend not connected yet.
- 2026-11-19 — Hosted page and its preview default to the Freda Verify name and logo when the white label is not filled.
- 2026-11-19 — Hardening of `/verify`: removed the review screen; strict passport/ID validation (shape + face photo + MRZ) for live scans and uploads; scanners fail closed instead of falling back to weak heuristics; selfie challenge is now two random steps (turn, then the other way; blink opt-in); SVG animated hand + chevrons instead of emoji; `?debug=1` overlay for real-device tuning; engines preloaded; large binaries (OpenCV, MediaPipe wasm) are no longer committed (copied from node_modules by `scripts/copy-vendor.mjs`); MediaPipe model license confirmed from the official model cards.
- 2026-11-19 — Selfie scanner with MediaPipe face detection and a random LEFT/RIGHT head-turn challenge with an animated pointing finger (`FaceScanner.tsx`, `faceDetect.ts`). Basic active challenge only (not certified liveness); tested with synthetic frames, not real devices.
- 2026-11-19 — OpenCV.js card-edge detection in the document scanner (perspective-corrected crop, "move closer/back/center" guidance), and desktop detection with a QR-code hand-off to the phone on `/verify` (`qrcode-generator`, MIT). Face detection for the selfie is still missing.
- 2026-11-19 — Scanner page with automatic capture on `/verify` (document front/back and selfie), auto-advance and countdown. Quality heuristics only, no real document/face detection yet.
- 2026-11-19 — Added the public hosted verification page `/verify` (demo mode): real camera/upload, local image-quality check, issuing-country and document steps, review, 3 languages, brand params from the URL. Nothing is uploaded and no verification result is produced. Country search made accent-insensitive.
- 2026-11-19 — Redesigned the hosted verification preview (Didit-style welcome, issuing-country step with search, document cards, selfie, done; phone chrome; "Secured by Freda Verify"). No social sign-in by decision.
- 2026-11-19 — Added White label page (branding form + live preview of the hosted verification page, mock only) and documented white-label requirements.
- 2026-11-19 — Initial CLAUDE.md. Frontend prototype documented: landing, brand identity, dashboard (Overview, Verifications with media viewer, Businesses, API Keys, Logs, Settings, Support). No backend yet.
