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
  tests/                       134 tests against a real PostgreSQL (runs the real migrations)
  docker-entrypoint.sh         applies the migrations at container start (tables are created automatically), then starts uvicorn
infra/docker-compose.yml       postgres 16, redis 7, minio, backend; every secret required from infra/.env (see infra/.env.example)
```

**Endpoints** (`/api/v1`): `POST /auth/register|login|refresh|logout|mfa/verify|mfa/setup|mfa/enable|mfa/disable|password/forgot|password/reset`, `GET /auth/me`; `GET|POST /organizations`, `GET|PATCH /organizations/{id}`, `GET|POST /organizations/{id}/members`, `PATCH|DELETE /organizations/{id}/members/{user_id}`, `GET|POST /organizations/{id}/api-keys`, `DELETE /organizations/{id}/api-keys/{key_id}`, `GET /organizations/{id}/audit-logs`, `GET /organizations/{id}/request-logs`, `GET|PUT /organizations/{id}/branding`, `PUT|GET|DELETE /organizations/{id}/branding/logo`; **verification sessions** `POST|GET /verifications`, `GET /verifications/{id}` (API key, or dashboard user with `organization_id`; viewers read only) and the **hosted-page endpoints** `GET /session`, `GET /session/logo`, `POST /session/consent` (authenticated ONLY by the `fvs_…` session token); `GET /usage` (API key or `?organization_id=`); `POST /tools/mrz/check`. OpenAPI at `/docs` (disabled when `FV_APP_ENV=prod`). **Webhooks and `/verifications/{id}/result` exist since 2026-11-20 (see changelog); org-scoped, not the spec's `/webhooks` path.** Still not built: `Idempotency-Key`, retry scheduler. The spec's `documents|selfie|complete` upload paths are implemented as session-token endpoints instead (below).

**Photos (2026-11-20).** Session endpoints `PUT /session/media/{document_front|document_back|selfie}?doc_type=id|passport|license&country=XX` (raw JPEG/PNG/WebP, magic-byte check, ≤ `FV_MEDIA_MAX_BYTES` = 2 MB, streamed cap, requires consent and a PENDING non-expired session, replaces a previous photo of that kind) and `POST /session/complete` (needs document front + selfie, plus back for ID/licence; sets **MANUAL_REVIEW**, locks the session). Storage: table `verification_media`, bytes **Fernet-encrypted** with `FV_ENCRYPTION_KEY` (key never in the database), SHA-256 of the plain image, **Photos are KEPT until a person deletes them** (owner decision 2026-11-20: `FV_MEDIA_RETENTION_DAYS` defaults to 0 = no automatic deletion, `purge_after` is NULL). If you set it > 0, `purge_after` = upload + N days and the purge runs at startup and on every upload (no scheduler). Keeping biometric photos indefinitely needs a legal basis and a retention policy (D9): review before real customers. Reviewer endpoints (dashboard users, by organization): `GET .../verifications/{id}/media` (metadata, all roles), `GET .../media/{kind}` (decrypted image, **owner/admin only, every view audited**, `no-store`), `DELETE .../media` (owner/admin, audited; the record stays), `POST .../decision` (owner/admin, APPROVED/REJECTED only from MANUAL_REVIEW, with optional note, audited). **MRZ reading (OCR):** after `/session/complete` a background task (`run_mrz_check`) reads the machine-readable zone of the document photos with **Tesseract** (`app/services/ocr.py`: bottom crop, upscale, contrast, character whitelist, two crops × two preprocessings, candidates for TD1/TD2/TD3 with ±3-char padding) and validates it with the ICAO 9303 parser (`app/services/mrz.py`); the best reading (most check digits passed) is stored in `verification_checks`, Fernet-encrypted (it holds names, birth date, document number). Reviewers (owner/admin, audited) see it via `GET .../verifications/{id}/checks` and can re-run it with `POST .../checks/mrz`. One reading at a time per process (semaphore). The Docker image installs `tesseract-ocr` and the OCR-B model (CI too, plus `fonts-ocr-b` for the tests). **Accuracy (measured 2026-11-20 with `python -m tools.ocr_eval --synthetic --n 24 --seed 7`, 312 generated pages = 13 degradations × TD1/TD2/TD3, real OCR-B font, ground truth known; the code was tuned on seed 1 and measured on fresh seed 7): MRZ found 97.4 %; every check digit valid 94.6 %; all identity fields (document number, dates, nationality, issuing country, sex) exactly right 91.3 %; names exactly right 95.8 %; 'confirmed' (two independent readings agree) 88.1 %. Wrong readings that still pass the check digits: 10/312 (3.2 %), of which 4 were 'confirmed'; almost all are document-number errors (O/0, I/1, B/8 and compensating pairs): ONE check digit is one digit, a wrong text passes it about 1 time in 10, so a valid check is NOT proof of a correct reading. Good: clean, JPEG q35, downscale, noise, ±2/5° rotation, perspective, low contrast, 'phone' combination (≈ 95–100 % fields). Weak: heavy blur (σ=3: 67 %), glare over the MRZ (54 %). The score depends on the Tesseract model: with the generic `eng` model the same test gave 19 % check-digit-valid on clean pages; the pinned OCR-B model (`ocrb.traineddata`, Shreeshrii/tessdata_ocrb, Apache-2.0, SHA-256 pinned in the Dockerfile and CI, falls back to `eng` if missing) is essential.** **These are SYNTHETIC pages: the OCR-B model was trained on OCR-B fonts that overlap with the font used to render the test, so the numbers are optimistic. Real printing, laminate/holograms, wear, national layouts and phone photos of real passports (incl. ID cards of Haiti/diaspora) have NOT been measured: use `python -m tools.ocr_eval --dir <your lawful photos> [--labels labels.json]` (never commit photos). **First real documents (2026-11-20, supplied by the owner, deleted from the sandbox after the test, never committed; n = 2, so this is an anecdote, not a measurement):** (1) a flat scan of a Haitian passport data page (1524×2191 JPEG, with the holder's MRZ both at the bottom and in a small copy at the top): MRZ found, ALL five check digits valid, 2 independent readings agree, every field matched the printed page (document number, nationality, birth date, sex, expiry), 3.5 s; (2) a phone photo of a Haitian national ID card (CIN) FRONT: correctly `unreadable` because that side has no MRZ. Generic Tesseract on the CIN printed fields is NOT reliable (it misread the birth date day and the card number's 0/O while getting the national ID number right) and the CIN has no check digits, so CIN fields cannot be machine-read safely today; they need a human reviewer, or a dedicated model trained on real CIN samples (needs many lawful samples). **In-browser scanner on the real passport (headless Chromium, upload path, session mode, 2026-11-20): the flat scan of the WHOLE page (data page + facing page) was refused (`face`: the portrait is only ~14 % of the image height, correct behaviour); a tight crop of the data page WITHOUT a visible outline was first refused as `shape` because the card detector needs a convex quad outline. Fix: for uploads only, when no outline is found and the image itself has a passport-page aspect ratio, the image is used as the page (face + MRZ-line checks still apply). With that fix the real data-page crop passed the in-browser checks (real face detector + MRZ lines), was uploaded (`PUT /session/media/document_front?doc_type=passport&country=HT`) and the server read it: all 5 check digits valid, 2 readings agree.** **Live camera scanner (owner's phone test, 2026-11-20): it did NOT detect the real passport and gave no useful feedback.** Cause: the live path needs the card detector to find a convex page outline (ratio 1.3–1.56); with the passport held open, on a busy surface or in a sleeve no outline is found and the hint stayed on the generic 'place the document' text. Fix (`Scanner.tsx`): PASSPORT-only fallback: when no valid outline is found, every ~1.3 s the area inside the on-screen frame is validated directly (photo on the left + MRZ lines, same checks as uploads) and captured after 2 consecutive passes; guidance text now says what to do ('fit the photo page in the frame…', 'checking…', or the specific missing element). Never used for ID cards (their back has no content check). **Found while testing it with a simulated camera (headless Chromium with a fake video feed built from the owner's documents): the in-browser MRZ-line heuristic accepted a Haitian national ID card (CIN, no MRZ) as a passport page, so it is NOT a reliable gate on real images (it was only validated on synthetic documents).** Fix: server-side gate: `PUT /session/media/document_front?doc_type=passport` runs a quick Tesseract read (`read_mrz(quick=True)`, 1 crop × 2 preprocessings, ≤ ~2 s) and answers 422 `mrz_not_found` when no MRZ-shaped text can be read (check digits are not required there); the page shows the 'two lines of characters are not visible' message. Re-test with the simulated camera: CIN → 422 refused, real passport page → 204 accepted and the flow moves to the selfie. ID cards are not gated. If tesseract is not installed the gate is skipped. Cost: ~1–3 s and Tesseract CPU per passport-front upload attempt on the API instance. **Second phone test (owner, same day): nothing happened, in the camera AND in the upload path. Render API logs for the owner's two sessions show `GET /session` 200 and `POST /session/consent` 204 but NO `PUT /session/media` at all: the page never produced a photo to upload (client-side).** Likely causes found/guessed: (a) quality gates blocked everything on a pale page: with a bright page the scanner flagged 'glare' (mean brightness > 225) and disabled capture (reproduced with a simulated camera; thresholds relaxed: only clipped pixels count, mean > 250); (b) engine loading (OpenCV 10 MB / MediaPipe 15 MB) hanging on a phone with no message (the face loader had no timeout; now 45 s, OpenCV already 30 s); (c) no manual way out. Changes: always-visible diagnostics line under the hint (placement, frame-check result, dark/bright/blurry), a manual 'Capture now' button after 5 s (crops the on-screen frame; the server still gates passports by MRZ text), frame-check progress decays instead of resetting. Verified with a simulated camera only (manual button → `PUT 204` → review screen). **Still not tested: a real phone camera after these changes; if it still fails, the diagnostics line (bottom of the scanner) or a `?debug=1` screenshot is the next data point.** Still not tested: the real phone camera after these fixes (the simulated feed is a still image: no motion blur, no hand shake, no auto-exposure), other passport layouts, the CIN back.** Reading strategy: two crops × two preprocessings, then ±2/4/6° rotations if not confirmed; candidates must match a TD1/TD2/TD3 layout (±3 chars padded with '<'); repairs decided by the check digits (optional-data filler misread as K/X; O↔0 in the document number); a reading counts as a vote only if all check digits pass, `agreeing` = number of independent readings giving the same fields (stored and shown to reviewers: 'N readings agree' vs 'single reading: verify on the photo'). Latency ≈ 1–5 s per photo on one core (set `OMP_THREAD_LIMIT=1`, done in the Dockerfile; without it parallel runs slowed to >10 s per call). Passing check digits shows the text is internally consistent, not that the document is genuine; the result is advice for a human and never decides. **Still no** face match, liveness, document authenticity or AML; a person decides. Costs/limits: Tesseract needs RAM (~100–300 MB peak) on a 512 MB free Render instance and may be slow; photos live in PostgreSQL (Supabase free tier = 500 MB; ~3 photos × ≤2 MB per verification); move to encrypted object storage before volume. Not done: per-organization retention setting, scheduled purge, OCR accuracy measurement on real documents, PaddleOCR (heavier, not installed), MRZ cross-check against the printed text/selfie, e-mail/webhook on submission, malware scanning, EXIF stripping, image re-encoding, Row-level audit of every API-key read.

**Face comparison, advisory (2026-11-20).** After submission a background task (`run_face_check`, `app/services/face.py`) compares the portrait on `document_front` with the `selfie` using OpenCV only: **YuNet** face detector (MIT) + **SFace** recognizer (Apache-2.0 model files from the OpenCV Zoo, pinned by SHA-256 in the Dockerfile and CI, in `/opt/face-models`, override `FV_FACE_MODEL_DIR`); the cosine similarity of the two aligned faces is stored (Fernet-encrypted JSON in `verification_checks`, kind `face`) with a band: `high` ≥ 0.50, `possible` ≥ 0.363 (the threshold published with the model, NOT calibrated on our population), `low` below. **No embedding is stored, only the number.** Reviewers (owner/admin) see it in the review panel (`GET .../checks` now returns `face`; `POST .../checks/face` re-runs it), always with an 'advisory, a person decides' notice; it never changes the status. Measured so far: the repo's demo portraits (same person pair 0.91, different people 0.04–0.08) and ONE real pair (the owner's passport photo vs the owner's national ID card photo, same person: 0.67 'high'; the same photos against other people: 0.04–0.05). **That is an anecdote, not a measurement: no FAR/FRR, nothing measured on Haitian/diaspora faces, and darker skin tones and small printed passport photos are known to be harder.** **Open licence question (D7, not closed):** the model files are Apache-2.0, but the dataset SFace was trained on (a public web-collected face dataset) has an unclear licence/consent status; dlib's ResNet (CC0) is another candidate with the same kind of dataset question. Do not describe this as 'certified' or 'license-cleared'. **Evaluation tool:** `python -m tools.face_eval <photos-folder> [--meta meta.json]` (folder per person: `doc*.jpg` + `selfie*.jpg`, never committed) computes genuine/impostor score distributions, FRR/FAR per threshold with 95 % Wilson intervals, the threshold for FAR ≤ 1 % / 0.1 % when enough impostor pairs exist, optional per-group results (labels the owner assigns with consent) and the weakest genuine pairs; it warns when there are fewer than ~30 people. **First real result (owner's phone flow): selfie vs passport photo scored 0.32 (below 0.363) while passport vs national ID card scored 0.67 for the same person: a false non-match; the threshold was NOT changed from one sample; the UI says 'Low similarity' with a warning.** **First real evaluation (2026-11-20, owner-supplied zips of 21 merchant onboarding files: official ID/passport photo or PDF + a 'selfie holding the ID'; extracted, anonymised to p01…, evaluated with `tools.face_eval`, then DELETED from the sandbox; only aggregates are recorded here; nothing was committed).** 21 files → 17 usable people (4 skipped: no face found on 3 document images and in 1 selfie = 19 % detection failures to handle in the product). 17 genuine pairs, 272 impostor pairs. Genuine scores: median 0.49, mean 0.49, range 0.04–0.69 (far below the 0.91 of the demo portraits: real phone selfies vs printed ID photos). Impostor scores: median 0.13, max 0.40, 95th percentile ≈ 0.3. At the published threshold 0.363: **FRR 2/17 = 11.8 % (95 % interval 3–34 %), FAR 1/272 = 0.37 % (0.06–2.1 %)**; at 0.30 FAR 5 %; at 0.50 FRR 53 %, so the 'Strong' band (≥ 0.50) is rarely reached by the same person and 'Moderate' (0.363–0.50) is normal. AUC 0.95. **n = 17 people is INDICATIVE only (the intervals are wide) and the sample is not demographically documented.** Tried simple pre-processing on the document photo (2× upscale, CLAHE, both): none helped (AUC 0.95 → 0.89–0.95), so the pipeline is unchanged. One genuine pair scored 0.04 (as low as impostors): possibly a real mismatch or a bad document photo; not investigated further. **Second, larger evaluation (2026-11-20, same owner-supplied merchant files, now 49 zips-worth reduced to 44 unique people; 39 usable, 5 skipped because no face was found in the document photo (4) or the selfie (1) = 11 % detection failures; data deleted, aggregates only).** 39 genuine pairs, 1482 impostor pairs. Genuine: median 0.55, mean 0.53, a few near 0.04-0.20 (3 pairs below 0.30). Impostor: median 0.14, max 0.50. At the published threshold 0.363: **FRR 5/39 = 12.8 % (5.6-26.7 %), FAR 20/1482 = 1.35 % (0.88-2.08 %)**; at 0.383 FAR = 1 % with FRR 15.4 %; at 0.40 FAR 0.67 % / FRR 17.9 %; at 0.50 FAR 0 % but FRR 46 %. Conclusion: 0.363 is roughly right for an advisory flag but gives ~1 % false matches on this sample, so it must stay advisory; n = 39 is still small and the sample is not demographically documented. Threshold NOT changed.

**Selfie-with-ID finding:** 9 of 17 selfies contain two faces (the person + the portrait on the ID held in hand; the person's face is 16–90× larger). The ID portrait in the selfie matches the document photo very strongly (0.71–0.93) because it is the same card, so scoring 'any/largest-by-luck face' would let someone holding a stolen ID score ~0.9. Guard added: if the selfie has ≥ 2 faces and the largest is not ≥ 4× the area of the second, no score is computed (`ambiguous`) and the reviewer is told to look at the photos. Threshold NOT changed; UI band names are now descriptive ('Strong / Moderate / Low similarity') with the observed typical range shown. Possible future signal (not built): the ID portrait visible in the selfie matching the document photo shows the person holds the same document. **Privacy note:** these files are real customers' identity data collected for onboarding; using them for model evaluation should have a documented legal basis (D9); they were processed only in memory/temp files and removed. Costs: `opencv-python-headless` (+ numpy) and ~39 MB of models in the image; ~0.1–0.5 s per comparison on one core.

**E-mail through Brevo (2026-11-20).** `app/services/mailer.py` sends transactional e-mail with Brevo's HTTP API (`POST https://api.brevo.com/v3/smtp/email`, header `api-key`). Settings (env): `FV_BREVO_API_KEY` (**secret, set only in the Render dashboard, never in git or chat**; without it mail is disabled and nothing is sent), `FV_MAIL_FROM_EMAIL` (default `no-reply@fredaverify.com`, must be a sender/domain validated in Brevo), `FV_MAIL_FROM_NAME`, `FV_NOTIFY_ON_SUBMIT` (default true). Two uses: (1) when a customer submits a verification, owners and admins get 'A verification is ready for your review' with the business's own reference and a dashboard link — **no personal data in the message**; an audit row `verification.notified` records how many were sent; (2) password reset: `POST /auth/password/forgot` now e-mails the single-use 30-minute link (`{FV_HOSTED_URL}/reset-password?token=…`) from a background task, so the response and its timing are identical for unknown accounts. Sending never raises and never blocks a request; only the HTTP status is logged. **Not verified against the real Brevo API from the build sandbox (no key, egress restricted): the code is tested with a mocked transport (payload shape, header, de-duplication, HTML escaping, failure handling, who is notified, no identity data in the body).** Owner steps: Brevo → SMTP & API → create an API key → Render env `FV_BREVO_API_KEY`; Brevo → Senders, Domains & Dedicated IPs → add and authenticate `fredaverify.com` (Brevo shows the DKIM / brevo-code TXT records and a DMARC suggestion; SPF must include Brevo) in the same DNS zone as the site; then send a test (forgot-password on a real account). Not built: e-mail verification at sign-up, invitations, e-mail to the end customer, bounce/unsubscribe handling, templates per language.

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

**Known gaps in Phase 1 (do not hide them):** the registration form does not verify e-mail addresses; no e-mail verification at sign-up (anyone can register any address); password-reset links are e-mailed only when `FV_BREVO_API_KEY` is set (otherwise logged in `dev` only, nothing in prod); members can be added only if they already have an account (no invitation e-mails); no `Idempotency-Key` handling yet; request logs are written synchronously; the in-process rate limiter is per worker (use Redis in prod); no backups, no monitoring, no pen test; platform-admin features absent; the Docker image and the compose stack were validated only with `docker compose config` (no Docker daemon in the build sandbox), not built or run; tests ran on Python 3.13 / PostgreSQL 16.15 locally while the Docker image and CI use Python 3.12 (the CI workflow had not run when this was written).

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

**Custom domain `fredaverify.com` (LIVE 2026-11-20: the owner confirmed the site and `https://api.fredaverify.com/health` → `{"status":"ok"}`; Render env switched by the assistant: static site `NEXT_PUBLIC_API_URL=https://api.fredaverify.com`, API `FV_HOSTED_URL=https://fredaverify.com`; the onrender.com URLs stay allowed in `FV_CORS_ORIGINS`; browser sessions do not carry over from the onrender.com origin, users sign in again).** Original plan and steps (kept for reference): Plan: `fredaverify.com` + `www.fredaverify.com` → static site `freda-verify` (Render); `api.fredaverify.com` → API `freda-verify-api`. Same registrable domain for app and API, so the httpOnly-cookie session migration (above) becomes possible later. Done by the assistant: `FV_CORS_ORIGINS` on the API already allows `https://fredaverify.com` and `https://www.fredaverify.com` (plus the onrender.com URL); `render.yaml` lists the domains; `metadataBase` set in `app/layout.tsx`. **To be done by the owner (needs the registrar and the Render dashboard):** (1) Render → static site → Settings → Custom Domains → add `fredaverify.com` and `www.fredaverify.com`; Render → API → add `api.fredaverify.com`; Render shows the exact DNS values; (2) at the registrar: apex `fredaverify.com` → A record (or ALIAS/ANAME) with the value Render displays, `www` → CNAME `freda-verify.onrender.com`, `api` → CNAME `freda-verify-api.onrender.com`; remove conflicting AAAA/old A records; (3) wait for "Verified" + certificate issued (minutes to hours). **Only AFTER the domain answers over HTTPS**, switch these (do NOT earlier, it would break the live site): static site env `NEXT_PUBLIC_API_URL=https://api.fredaverify.com` (then redeploy the static site, it is inlined at build time); API env `FV_HOSTED_URL=https://fredaverify.com` (verification links); landing curl example → `api.fredaverify.com`. Optional: redirect `www` ↔ apex in Render. E-mail (SPF/DKIM/DMARC) is a separate DNS task for when an e-mail provider is chosen.

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
| Anti-spoofing / liveness models | PAD | **In use experimentally (2026-11-20): Minivision MiniFASNetV2 + V1SE ONNX.** Code Apache-2.0, but no licence or training-data statement for the WEIGHTS: unverified for commercial use (D7). No certified option assumed; measurement with `tools/pad_eval.py` required. |
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
| D7 | Face model and liveness approach given weight licensing. | **Partly done 2026-11-20:** advisory comparison with YuNet (MIT) + SFace (Apache-2.0 files) is running for reviewers; the training-data licence question and measured error rates on our population are still OPEN, liveness is still not certified. Keep the 'advisory' framing. |
| D8 | AML data sources (official lists vs licensed commercial feeds; PEP source). | Decide before Phase 4; expect a licensing cost. |
| D9 | Launch markets and legal review (Haiti and others), consent and retention policy. | Engage legal/compliance early. |
| D11 | External AI/LLM (DeepSeek, Claude, GPT, Gemini…) to read documents? | **Decided 2026-11-20 by the owner: NO.** Document and selfie reading stays self-hosted and deterministic (Tesseract + ICAO check digits, later open-weights models on our own servers if needed). No identity photo is ever sent to a third-party AI API. Revisit only with a legal review (D9) and a DPA. |
| D10 | Pricing model (current $0 / $0.40 / custom are placeholders). | Decide after cost per verification is measured. |

---

## 15. Changelog

- 2026-11-20 — **Volunteer photo collection for PAD testing** (migration 0010: `pad_campaigns`, `pad_contributions`, `pad_samples`, RLS; `app/api/v1/collect.py`). The owner/admin creates a collection on the new dashboard page `/dashboard/collection` and gets ONE link `{FV_HOSTED_URL}/contribute#c=fvc_…` (token in the fragment, stored encrypted so it can be copied again) to send to volunteers. The public page `/contribute` (Kreyòl / Français / English, browser-language default) shows a DRAFT consent (lawyer review required, D9; version `draft-1`), refuses to start without the checkbox, then collects 3 live selfies (with a lighting label each), optionally 2 photos of a printed photo and 2 of a screen, taken through the front camera (file picker fallback). Each volunteer gets a code (p001, …) and a personal token; photos are Fernet-encrypted (≤ 2 MB, JPEG/PNG/WebP magic bytes, ≤ 4 slots per kind); the volunteer can erase everything from the page, the owner can close or delete a whole collection, and `GET …/pad-campaigns/{id}/export` returns a ZIP in the `tools.pad_eval` layout (`genuine/`, `attack_print/`, `attack_replay/`, `attack_mask/`, `p001_<light>_<slot>.jpg`, `people.csv`) for owners/admins only, audited, `no-store`. Campaign and volunteer tokens open nothing else (tested). Verified: 158 backend tests, `alembic check` clean, and an 8-check headless-browser run (create link, open in French, consent gate, 3 live + 1 print upload via fake camera and file picker, no token in any request URL, counts on the dashboard, ZIP download, volunteer erase). NOT tested on real phones/browsers (Safari camera permissions especially). Nothing here trains or decides anything. Stored in PostgreSQL (500 MB Supabase free tier ≈ a few hundred photos): export and delete after each pilot. Retention is manual.
- 2026-11-20 — `tools/pad_eval.py --protocol` (OULU-NPU style): files named `<person>_…`, people split deterministically into DEVELOPMENT and TEST halves (never the same person in both), threshold chosen on development at EER (BPCER = pooled APCER), then BPCER, APCER per attack type, worst-type APCER and ACER reported on TEST only, with 'indicative only' warnings (< ~100 genuine / 50 per attack on the test half) and a 'not enough people' guard. Unit-tested with synthetic scores (152 tests); smoke-run with the real models on 4 stock images only (no meaning). `docs/pad-collection-protocol.md` now asks for person codes in file names. Still no real attack set, so no APCER exists.
- 2026-11-20 — **GitHub / web search for a licence-clean PAD model: nothing found; plan to train our own.** Read `facenox/face-antispoof-onnx` (the `johnraivenolazo` URL shows the same repo): Apache-2.0 code (copyright 'John Raiven Olazo'), MiniFASNetV2-SE 128x128, includes training and ONNX export scripts, but NO licence statement for the weights and NO training data named; its '70k+ samples' are the CelebA-Spoof TEST set it is evaluated on (accuracy / ROC-AUC only, no APCER/BPCER), so its weights were probably trained on a non-commercial-reputation dataset. Other hits: ChaLearn challenge code (MIT, weights on Google Drive, challenge-dataset terms), a CelebA-Spoof evaluation repo, a YOLOv8 detector under AGPL-3.0 (avoid). Also read the OULU-NPU paper (55 subjects, 6 phones, 3 lights, 2 printers, 2 displays, 4 generalisation protocols, APCER/BPCER/ACER with the threshold set on a dev split; mostly East-Asian / North-African / European subjects, no dark skin; access terms unverified). `docs/pad-training-plan.md` records the plan: use the Apache-2.0 architecture and scripts, never the existing weights, train on our own consented data (>= 150 people, ~3,000 live + ~3,000 print + ~3,000 replay, person-disjoint train/dev/test, held-out phone and lighting), acceptance criteria decided before training, deepfake / virtual-camera / mask limits stated. Nothing was trained or run; no data exists yet.
- 2026-11-20 — **PAD probe on AI-generated collages (NOT a measurement).** The owner had ChatGPT generate 5 collages of synthetic faces, including AI-RENDERED pictures of a printed photo, a phone screen and a laptop screen (4 distinct images, 1 duplicate; images not stored). Each face was cropped and scored with MiniFASNetV2 + V1SE. 21 'attack renders' (print / phone / laptop): 10 scored ≥ 0.7 and 12 ≥ 0.5; 26 plain synthetic portraits: 16 scored ≥ 0.7. The model therefore did not separate the renders from plain faces (48 % vs 62 % above 0.7), and the two models often disagreed (e.g. V2 0.00 vs V1SE 0.98 on the same tile). **These renders are not real captures** (no real print texture, moiré, screen glare or camera noise; everything went through one image generator), so this says nothing reliable about APCER on real print/replay attacks; it only shows the score is erratic on synthetic imagery, which also means a fully synthetic face injected through a virtual camera would not be caught. Real attack photos (printed, then photographed with a phone on `/verify`) are still required.
- 2026-11-20 — **First real PAD measurement, GENUINE side only (owner-supplied merchant onboarding files, same 'selfie holding the ID' photos as the face evaluation; 44 unique people, 43 with a usable face; data deleted afterwards, aggregates only).** MiniFASNetV2 + V1SE ensemble, real-probability of 'live': median 0.95, mean 0.80, p10 0.34, p25 0.72, min 0.04. With the current bands: 33 high (≥ 0.7), 7 uncertain, 3 low (< 0.3). **BPCER (real people refused): 7.0 % at threshold 0.3 (2.4–18.6), 20.9 % at 0.5 (11.4–35.2), 23.3 % at 0.7 (13.2–37.7), 41.9 % at 0.9.** Per model, below 0.5: V2 9/43, V1SE 5/43. Synthetic stress at 0.5: darker ×0.6 → 11.9 %, darker ×0.35 → 26.8 % (face lost on 3 images), blur → 16.3 %, JPEG q25 → 18.6 %; the 'dark + noise' line showed 0 % only because the face detector lost 14 of 44 images (not a good result). **Reading:** on real phone selfies of the target population roughly 1 in 5 live people would be refused or called uncertain at the usual thresholds, so this model must NOT be used to reject or to gate anything; the 0.7 'high' band is not calibrated. **Not measured: APCER (no attack photos exist), so these numbers say nothing about how well attacks are caught.** Caveats: these photos show a person holding an ID, taken outside `/verify` (different framing and capture quality), the sample is not demographically documented, n = 43 gives wide intervals, and using customers' onboarding files for evaluation needs a documented legal basis (D9). 149 tests unchanged.
- 2026-11-20 — **PAD follow-up (the owner asked to address the four limits).** (1) *Single frame → several frames:* the selfie scanner now also captures up to two extra FRONTAL frames (mid-stability and when the user looks straight again between the two turn tasks) and uploads them best-effort as `selfie_2`/`selfie_3`; the server scores every selfie frame and aggregates (`pad.aggregate`: mean, worst frame kept, a good mean with one bad frame is downgraded to 'uncertain'); the face comparison still uses `selfie` only. The review panel shows 'n/m frames, worst x %'. Not tested on a real phone (only the API path and unit tests: 149 tests). Expectation to verify: this makes a flickering screen replay a bit easier to catch, it does not make the check robust to a good replay. (2) *Masks, deepfakes, virtual camera:* NOT tested and cannot be by photos; `docs/pad-collection-protocol.md` describes how to test the pipeline attacks (virtual camera feeding a recorded video and a deepfake) and the physical ones (masks, cut-outs), and says what must be measured before any claim. (3) *APCER/BPCER on our users:* nothing could be collected here (needs consenting volunteers); the protocol gives consent template, quotas (≥ 100 genuine, ≥ 50 per attack type, ≥ 10 volunteers), capture rules (through the real `/verify` page) and decision rules; `tools/pad_eval.py` now also reports GROUP results from sub-folders (skin tone, lighting, phone) and the worst attack type. (4) *Dark skin / low light:* `pad_eval --stress` adds a SYNTHETIC sensitivity probe (darkening, noise, blur, JPEG q25) as a quick signal only; the protocol requires real dark-skin and low-light groups. Measured with the real models on 2 stock selfies (no meaning): the tool runs end to end; no accuracy claim is made.
- 2026-11-20 — **MiniFASNet integrated as an EXPERIMENTAL, advisory presentation-attack check (owner's decision, after a ChatGPT suggestion).** `app/services/pad.py` runs Minivision MiniFASNetV2 (crop 2.7) + MiniFASNetV1SE (crop 4.0), ONNX conversions from `yakhyo/face-anti-spoofing` releases, with OpenCV DNN (no new dependency), on the SELFIE only; mean real-probability with bands high ≥ 0.7 / uncertain / low < 0.3 (NOT calibrated). Separate from face comparison on purpose (own module, own check kind `liveness`, own review-panel section, own endpoint `POST .../checks/pad`; `GET .../checks` returns `pad`, `pad_available`). Runs in the background after submission; stored encrypted; audit `verification.pad_scored`. The result API only says `advisory.liveness: experimental_not_certified` when a score exists (never the score, never a verdict); the review panel labels it 'Live capture check (experimental, selfie only)' and states the limits. Models are NOT in git: the Dockerfile downloads them into `/opt/pad-models` pinned by SHA-256 (V2 `b32929ad…`, V1SE `ebab7f90…`), skippable with `--build-arg INSTALL_PAD=0`; without them the check reports `unavailable`. **Verified for real in the sandbox:** the models load and run through the DNN path (both score the demo selfies 0.74–1.00 and the demo document photos 0.04–0.25, which is an anecdote on 4 stock images, NOT a measurement). **Licence correction to the ChatGPT claim 'Apache 2.0, commercial use allowed':** read from the repos (2026-11-20): the Minivision code is Apache-2.0 (copyright 2020 Minivision) and the yakhyo repo shows Apache-2.0, but NEITHER README states a licence for the pretrained weights, NOR the training data; Minivision says its high-precision model is NOT open-sourced and sells its own commercial SDK. So the weights' commercial status is UNVERIFIED (D7 stays open): get a lawyer's reading, or ask Minivision, before real customers rely on it. **Known limits:** single still image, 2D attacks only; not tested on masks, deepfakes or a virtual camera; no APCER/BPCER on our population (use `tools/pad_eval.py` with a consented genuine + attack set); the model was trained for face crops from a phone camera, and darker skin tones / low light are unmeasured. 147 tests (1 more, plus a model-dependent test that is skipped when the models are absent).
- 2026-11-20 — **Liveness: model shortlist and plug-in, no model shipped.** Licence research (web, secondary sources only; nothing downloaded or run): (a) Minivision *Silent-Face-Anti-Spoofing* (MiniFASNetV2 / V1SE): code reported as Apache-2.0, but the training data of the released weights is not disclosed and a third-party weights catalogue warns against commercial use of this family: **NOT cleared**; (b) OpenVINO `anti-spoof-mn3`: a forum answer says MIT, trained on CelebA-Spoof, whose terms are reported as non-commercial: **NOT cleared**; (c) CelebA-Spoof / CASIA-SURF data: licence terms not verified: do not train or evaluate on them for the product without reading the agreements; (d) the remaining routes are an own model trained on consented data (needs a large attack/genuine collection), or a commercial PAD SDK certified under ISO/IEC 30107-3 (iBeta), behind the same pluggable interface (never a mandatory dependency). Recommendation: do (d) in parallel with collecting an evaluation set, and do not ship (a)/(b) before a lawyer reads the weights' terms. Built: `app/services/pad.py` (optional ONNX plug-in via OpenCV DNN, disabled unless `FV_PAD_MODEL_PATH`, advisory only, never decides; defaults follow the MiniFASNet convention) and `python -m tools.pad_eval <set>` (BPCER on `genuine/`, APCER per `attack_*/` folder with Wilson 95 % intervals and an 'indicative only' warning under ~100 genuine / 50 per attack type). The pad.py DNN path was NOT run against any real model (none was available or licensed), only the evaluation maths and the 'disabled' behaviour are tested (146 tests). It is not wired into the review panel or the result API (`liveness` stays `not_performed`) until APCER/BPCER are measured.
- 2026-11-20 — **Webhooks + result API** (migration 0009, tables `webhook_endpoints`, `webhook_deliveries`, RLS): `POST|GET /organizations/{id}/webhooks`, `DELETE .../{wid}`, `POST .../{wid}/test`, `GET .../{wid}/deliveries`, `POST .../deliveries/{did}/resend` (owner/admin); events `verification.submitted|approved|rejected` (+ `webhook.test`) sent after submission and after a human decision. HTTPS only, host resolved and refused if private/loopback/link-local (at save AND at each delivery; DNS-rebinding between the check and the request is a known residual risk), no redirects, 8 s timeout, secret `whsec_…` shown once and stored encrypted, header `Freda-Signature: t=<unix>,v1=<HMAC-SHA256 of "<t>.<raw body>">` (receiver must refuse > 5 min), payload = ids/reference/status/timestamps only (no personal data, no reviewer notes), 3 attempts (1 s, 4 s) in a background task, failures visible and resendable from the new dashboard page `/dashboard/webhooks`; NO retry after a process restart (no scheduler). `GET /verifications/{id}/result` (API key or dashboard user) returns status, `decision` (set only after a PERSON approved/rejected), timestamps and `advisory` {document_checks: valid|partial|invalid|expired|unreadable|pending, face_similarity: high|possible|low|status, liveness: not_performed, aml: not_performed}: no names, numbers or scores. 142 tests (7 new), `alembic check` clean. Tested with a faked HTTP client only: never against a real receiver.
- 2026-11-20 — Passport capture in the browser now also requires that both MRZ lines are COMPLETE: each must span > 78 % of the page width with a margin (> 1.2 %) on both sides and the two lines must end at about the same place; otherwise the reject message asks to keep the whole page flat with some space left and right. Type-checked/built only: NOT tested with real passports or a real phone, so it may reject good captures (thresholds are guesses) and needs a real-device test.
- 2026-11-20 — **Liveness: not built, on purpose.** A real presentation-attack-detection (PAD) layer needs (1) a model whose weights and training data are licence-cleared for commercial use, (2) an attack set (printed photo, screen replay, 3D/silicone mask, injection/virtual camera, deepfake) and a genuine set across skin tones/devices, (3) measured APCER/BPCER per ISO/IEC 30107-3 ideally by an independent lab, (4) server-side checking, not browser-only. None of these exist yet, so the product keeps saying `liveness: not_performed` (result API) and "basic active challenge, not certified liveness" (UI/docs). Next concrete steps: shortlist PAD models and check licences (D7), collect a consented attack/genuine set, write `tools/pad_eval.py` to compute APCER/BPCER, and only then wire a score into the review panel as advisory.
- 2026-11-20 — Review panel shows a **recommendation** banner (pass / needs review / do NOT approve) derived in the browser from the MRZ and face checks (expired document → 'do not approve'; low face similarity or imperfect MRZ → 'needs review'; everything consistent → 'you can approve'). It is advice for the reviewer only: no automatic decision, no verdict shown to the end customer, and the banner states that liveness, document authenticity and AML are NOT covered. The thresholds behind it are the unmeasured ones (face 0.363/0.50).
- 2026-11-20 — Follow-up on the cut-off MRZ lines: white margin around the OCR crop (Tesseract drops characters touching the border; synthetic result: no regression, 'confirmed' 85.8 → 86.7 %), two new `ocr_eval` scenarios ('tight crop', 'tight crop + tilt 3°'), and the review panel now shows an amber 'Main fields valid · overall check failed (end of line probably cut off)' badge instead of red when document number, birth and expiry check digits pass but the composite fails. Measured honestly: 'tight crop' reads 100 %, but 'tight crop + tilt 3°' only 54 % all-digits-valid because the test itself rotates pixels out of the frame (real information is lost); the real passport failure is NOT reproduced or proven fixed.
- 2026-11-20 — A real passport photographed by the owner on a phone was read as TD2 (36 chars) instead of TD3 (44): document number, birth and expiry check digits valid but the composite failed, so the badge said 'Check digits do NOT match'. Parsed by hand, the full printed MRZ passes all 5 TD3 checks, so the OCR reading had lost the end of the lines (photo edge, tilt or glare). `parse_mrz` now warns when a 'P' document is read in a non-44 layout ('end of the lines may have been cut off'); the test uses the public ICAO specimen; 135 tests. The capture/OCR is NOT fixed: a tilted, hand-held passport can still lose the line ends; next step is wider crops or TD3 candidates from the full line width.
- 2026-11-20 — Review panel polls `.../checks` every 4 s (max ~2 min) after a submission until the MRZ and face results exist (owner saw 'Not read yet' because the background tasks had not finished). Type-check + build pass; not browser-tested against a live submission.
- 2026-11-20 — Brevo e-mails redesigned (`mailer.render_html`): branded table layout with the logo (`{FV_HOSTED_URL}/logo.png`), title, button + copy-paste link, footer; all dynamic text escaped; checked in a headless browser render only, NOT in real mail clients (Gmail/Outlook). Real sending hit HTTP 401 first (wrong Brevo key type); the owner replaced the key.
- 2026-11-20 — Face evaluation enlarged to 39 usable people: FRR 12.8 % and FAR 1.35 % at 0.363 (details in 3.8); threshold unchanged; data deleted.
- 2026-11-20 — First real face-comparison evaluation on 17 people (owner-supplied merchant onboarding files, deleted afterwards): at threshold 0.363 FRR 11.8 % (3–34 %), FAR 0.37 % (0.06–2.1 %), AUC 0.95; 19 % of files had no detectable face; 'selfie holding the ID' contains the ID portrait which would match trivially, so a dominance guard (`ambiguous` status, 134 tests) was added; band labels made descriptive. Details in 3.8.
- 2026-11-20 — `backend/tools/face_eval.py` (+ `face.embed/cosine` helpers, 2 tests, 133 total) to measure genuine/impostor face-comparison error rates on consented photos; sample-size guidance in the final message of this session (≈30 people for a first useful picture, ≥100 genuine pairs to bound FRR).
- 2026-11-20 — Custom domain switched on after the owner confirmed it works (`NEXT_PUBLIC_API_URL`, `FV_HOSTED_URL`, landing example). First real face-comparison result from the owner's phone flow: selfie vs passport photo scored 0.32 (below the 0.363 threshold) for what should be the same person, while the passport photo vs the national ID card photo scored 0.67: a false non-match caused by the printed-photo/selfie gap (quality, lighting, angle). The UI label 'Different' was softened to 'Low similarity' with an explicit warning. Threshold NOT changed (one sample proves nothing). Next step for a real answer: measure genuine and impostor pairs with consenting people.
- 2026-11-20 — Owner phone feedback: the camera showed 'Capture now' after a delay instead of capturing by itself. Passport scanner now auto-captures after ~3 s of a steady, sharp, non-dark frame when no page outline is confirmed (brightness no longer blocks; the server still refuses a photo without readable MRZ text). Verified with a simulated camera (auto capture, no click, `PUT 204`); not re-verified on a real phone. Also added: advisory face comparison (YuNet + SFace, 3.8), e-mail through Brevo for submission notifications and password reset (3.8, tested with a mocked transport only), 131 tests.
- 2026-11-20 — Third owner phone test SUCCEEDED end to end: the real passport was captured on the phone, uploaded, and the dashboard review panel showed the MRZ with all 5 check digits valid, 2 readings agreeing, and every field matching the printed page (1 OCR confusion auto-corrected; the hyphen of the surname appears as a space, as MRZ encodes it). Which of the two capture paths (camera / upload) succeeded was not recorded. Review-panel disclaimer updated (generated pages + two real documents).
- 2026-11-20 — Second owner phone test failed (no photo ever uploaded, confirmed by Render API logs). Scanner: relaxed brightness gate, always-visible diagnostics, manual 'Capture now' after 5 s, decaying frame-check progress, face-engine load timeout. Not verified on a real phone.
- 2026-11-20 — Owner's phone test: the camera scanner did not detect the real passport. Added the passport 'frame' fallback (validate the area inside the on-screen frame when no outline is found) and clearer guidance; a simulated-camera test then showed the in-browser MRZ heuristic accepts a real Haitian ID card as a passport → added a server-side MRZ gate on passport front uploads (`422 mrz_not_found`, tests updated, 119 tests). Details in 3.8.
- 2026-11-20 — Custom domain `fredaverify.com` prepared: API `FV_CORS_ORIGINS` extended (Render env, redeploy triggered), `render.yaml` domains, `metadataBase`, `.env.example`; DNS + Render domain verification are owner steps, and `NEXT_PUBLIC_API_URL` / `FV_HOSTED_URL` / landing example are switched only after the domain is live (see 3.9).
- 2026-11-20 — Tested the in-browser upload validation + session upload on the owner's real passport: whole two-page scan refused (face too small), tight data-page crop initially refused (no outline for the card detector) → upload-only fallback in `docValidate.ts` (use the image as the page when no outline is found and its aspect ratio fits); then accepted, uploaded and read by the server (all check digits valid). Photos deleted from the sandbox.
- 2026-11-20 — First real-document check of the MRZ reader (owner-supplied Haitian passport scan: all check digits valid, fields correct; Haitian CIN front: no MRZ, unreadable as expected, printed-field OCR unreliable). Findings in 3.8. Test files removed from the sandbox.
- 2026-11-20 — Decision D11: no external AI/LLM API for reading identity documents or selfies (privacy, cross-border biometric transfer, hallucination risk, no mandatory paid dependency). Improvements to document reading stay self-hosted.
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
