# AutoJob AI — UI & Workflow Rebuild Plan

Status: draft for review · 2026-11-08

## 1. Goals

1. Split the product into two distinct surfaces that link to each other:
   - **Landing site** (`/`) — public marketing page, cinematic, GSAP-driven.
   - **Dashboard app** (`/app/*`) — authenticated operator console, dense and fast.
2. Replace the hardcoded PIN (`7878` in `src/server.py`) with real **role-based access control** (RBAC).
3. Add **demo login** so visitors can try the dashboard without touching real data or real browser automation.
4. Adopt the supplied industrial dark-mode design language ("Combined HTML Collection") as the shared design system for both surfaces.
5. Use **GSAP** for orchestrated motion; keep the reference's CSS `@keyframes` for small looping loaders.

## 2. Current state (what we are replacing)

| Area | Today | Problem |
|---|---|---|
| UI | One page `ui/index.html` (714 lines) + `app.js` (1356) + `styles.css` (1407); landing and dashboard are tabs of the same page | Landing and app are not separable; files exceed the 800-line ceiling |
| Auth | `POST /api/auth/verify` compares PIN to literal `"7878"`, returns a fixed token; token never checked server-side | **Every `/api/*` endpoint is unauthenticated**, including `POST /api/contact` which rewrites `config/profile.json` and `POST /api/browser/prefill` which launches Chromium |
| Backend | `src/server.py` 551 lines, module-level mutable globals (`live_process_state`, `agent_running`) | Hard to test, no routers, no role checks |
| Agent telemetry | Step 4 log hardcodes "Pritam Biswas" | Should read from profile |
| Theme | Light default with toggle | Reference design is dark-only |

## 3. Information architecture & connected flow

```
 /                Landing (public)
 ├─ Hero (fog canvas + 3D parallax "agent core")
 ├─ How it works (5-phase pipeline, scroll-pinned)
 ├─ Live stats teaser  ← GET /api/public/stats (aggregate counts only)
 ├─ Feature grid / reels
 └─ CTA: "Try live demo"  ·  "Sign in"
        │
        ▼
 /login           Sign in + 3 demo cards (Admin / Operator / Viewer)
        │  (session cookie set)
        ▼
 /app             Dashboard shell (sidebar + topbar, "← Back to site" link)
 ├─ /app/overview        KPIs + AXIS charts
 ├─ /app/pipeline        Live 5-phase agent run (start/stop/step)
 ├─ /app/opportunities   Jobs table + proposal drawer + prefill/apply
 ├─ /app/inbox           Conversations + responder simulator
 ├─ /app/profile         Dossier / contact + rates (Onyx form components)
 ├─ /app/console         Raw runtime console (admin)
 └─ /app/users           Users & roles (admin)
```

How the two surfaces stay connected:
- Same design tokens, fonts, icon sprite and noise/grid background (shared files in `ui/shared/`).
- Landing nav button reads session state: shows **"Open Console"** if logged in, **"Sign in"** otherwise.
- Landing stats teaser pulls real aggregate numbers from the backend.
- Dashboard topbar has **"Back to site"**; logout returns to `/`.
- Cross-page transition: GSAP exit timeline on landing CTA → `/login` entry timeline (with native View Transitions API where supported).

## 4. Frontend architecture

No build step. Static files served by FastAPI.

```
ui/
  shared/
    tokens.css          # CSS vars: #000 void, #222 borders, #ccff00 acid, #ff3300 accent, zinc text
    tailwind.config.js  # colors + all reference @keyframes (radar, ring-dash, upload-arrow, morph, shake, float, reveal-sec12...)
    sprite.svg          # 50+ <symbol> icons copied verbatim from reference
    motion.js           # GSAP setup, gsap.matchMedia() for prefers-reduced-motion, shared eases
    api.js              # fetch wrapper: credentials, CSRF header, 401 → /login, 403 → toast
    session.js          # GET /api/auth/me, role helpers (can(permission))
  landing/
    index.html
    landing.js          # fog canvas, parallax, ScrollTrigger sections
  login/
    index.html
    login.js
  app/
    index.html          # shell; views loaded as <template>s, hash/History routing
    router.js
    charts.js           # AXIS ChartRenderer (custom SVG engine, no chart lib)
    views/overview.js  pipeline.js  opportunities.js  inbox.js  profile.js  console.js  users.js
```

Libraries (CDN, pinned versions): Tailwind CDN, GSAP 3.13 core + ScrollTrigger + SplitText + Flip (all free since 2025). Nothing else.

Note: Tailwind CDN is fine for local/dev. If this ever ships publicly, swap to the Tailwind standalone CLI binary (still no Node needed).

### Mapping the reference sections onto AutoJob

| Reference section | Where it lands |
|---|---|
| §1 SaaS icon system (sprite, acid hover) | Shared sprite: sidebar nav, action buttons, status chips |
| §2 AXIS data vis (`ChartRenderer`) | Overview: line (applications/day), bar (jobs per platform), donut (status split), gauge (avg match score), radar (skill coverage), treemap (tags), area (inbound volume). Custom `#tooltip` on mousemove |
| §3 Kinetic interactions | Agent status loaders (Pulse = running, Hourglass = waiting for human), Success/Error micro-feedback on save/apply, Download button = CSV export of jobs/applications |
| §4 Onyx decorative assets | Landing section dividers (Organic Wave, Hard Tilt, Digital Steps), morph blobs behind hero, pattern fills (Circuit/Hive) on cards |
| §5 Onyx UI components | Kinetic Arrow = primary CTAs; Success Morph = "Mark applied"; SVG checkbox, Mechanical Toggle = agent on/off + settings; Drop Zone = résumé/profile JSON import |
| §6 Nexus Pro landing | Landing hero: fog canvas + mouse-tracked `rotateX/rotateY` parallax on a hero visual, blurred nav, floating glass card |

Deviation to confirm: the reference's controller artwork, "Nexus Pro" copy and "Combined HTML Collection" footer title belong to the template, not AutoJob. Plan uses the same hero mechanics and SVG technique but with an AutoJob visual (agent core / pipeline glyph) and AutoJob copy. If you want the template content reproduced verbatim instead, say so.

**Blocker:** exact SVG path data, sprite symbols and keyframe timings must come from the reference HTML source. Drop the file at `design/reference/combined.html` before Phase 2.

### GSAP motion plan

| Surface | Motion |
|---|---|
| Landing hero | SplitText char reveal on headline, staggered nav fade, parallax via `gsap.quickTo` (smooth, no layout thrash) |
| Landing "How it works" | ScrollTrigger pin; 5 phases advance with scroll, SVG connector stroke draws |
| Landing dividers/blobs | Scrub-linked y-offset; blobs keep CSS `animate-morph` |
| Login | Card entrance, demo-card hover tilt, success → exit timeline then navigate |
| Dashboard shell | One-shot entrance (sidebar slide, KPI count-up), not on every route change |
| Pipeline view | Master timeline driven by polled `active_step`; node pulse, connector fill, log lines slide in |
| Opportunities | `Flip` on filter/sort so rows reorder smoothly; proposal drawer slide |
| Charts | Bar `scaleY`, line `strokeDashoffset` draw, donut arc sweep on first view |
| Everywhere | `gsap.matchMedia('(prefers-reduced-motion: reduce)')` → instant states |

Rule: dashboard motion stays under ~300 ms and never blocks input; landing can be cinematic.

## 5. Backend: auth + RBAC

### Data model (SQLite, added to `src/db.py`)

```sql
users    (id, email UNIQUE, password_hash, role, is_demo INTEGER, created_at, disabled INTEGER)
sessions (token_hash PRIMARY KEY, user_id, created_at, expires_at, csrf_token)
audit_log(id, user_id, action, target, created_at)
```

- Password hashing: stdlib `hashlib.scrypt` with per-user salt — no new dependency.
- Session: random `secrets.token_urlsafe(32)`, stored **hashed**; cookie `HttpOnly; SameSite=Strict; Secure` (Secure when not localhost); 12 h expiry.
- CSRF: per-session token returned by `/api/auth/me`, required in `X-CSRF-Token` header on all mutating requests.
- Login rate limit: in-memory per-IP counter (5 attempts / 5 min). `# ponytail:` note — single-process only; move to DB if multi-worker.
- First admin created from env `AUTOJOB_ADMIN_EMAIL` / `AUTOJOB_ADMIN_PASSWORD` on startup; startup fails loudly if neither an admin exists nor env is set.

### Roles & permissions

| Permission | Admin | Operator | Viewer |
|---|:-:|:-:|:-:|
| View overview, jobs, applications, inbox | ✓ | ✓ | ✓ |
| Run scout / generate proposal / responder sim | ✓ | ✓ | — |
| Start/stop agent loop, trigger steps | ✓ | ✓ | — |
| Browser prefill (launches Chromium) | ✓ | ✓ | — |
| Record application | ✓ | ✓ | — |
| Edit profile / contact / rates | ✓ | — | — |
| Runtime console | ✓ | — | — |
| Manage users & roles, view audit log | ✓ | — | — |

Implemented as one FastAPI dependency: `Depends(require("jobs:run"))`, permissions in a single dict `ROLE_PERMISSIONS`. Frontend hides controls via the same permission names from `/api/auth/me`, but the **server is the only enforcement point**.

### Demo login

- Enabled only when `AUTOJOB_DEMO=1`.
- `POST /api/auth/demo {role}` creates a session for a seeded `is_demo` user of that role; login page shows three demo cards.
- Demo sessions read from a separate seeded DB file (`data/demo.db`) so real jobs/profile are never shown or modified.
- Side-effect endpoints are simulated for demo sessions: browser prefill returns a canned result (no Chromium), profile writes go to the demo copy, Gemini calls use the existing offline/fallback templates.
- Demo DB reset on startup and every 30 minutes.
- Banner in dashboard: "Demo mode — data resets every 30 min".

### Backend restructure

```
src/
  server.py            # app factory, mounts routers + static pages only
  auth/
    security.py        # hashing, session create/verify, CSRF
    rbac.py            # ROLE_PERMISSIONS, require()
    routes.py          # /api/auth/login, logout, me, demo
  api/
    agent.py           # status/start/stop/live-process/run
    jobs.py            # jobs, applications, proposals, prefill, apply
    inbox.py           # conversations
    profile.py         # contact/profile
    users.py           # admin user management
    public.py          # /api/public/stats (aggregate counts, no PII)
  agent_state.py       # AgentController class replacing module globals
```

Also fix: Step 4 telemetry reads name from profile; `POST /api/contact` validates email/URL formats with Pydantic (`EmailStr`, `HttpUrl`); all endpoints return consistent error envelopes.

Page routes: `/` → landing, `/login` → login, `/app/{path}` → app shell. `/app/*` HTML is public (static), all data behind the API is protected — unauthenticated `/api/*` → 401, frontend redirects to `/login?next=…`.

## 6. Phases

| # | Phase | Output | Skills / agents |
|---|---|---|---|
| 0 | Reference intake | `design/reference/combined.html` checked in; tokens, sprite, keyframes extracted into `ui/shared/` | `design-system` |
| 1 | Auth + RBAC backend (TDD) | `src/auth/*`, users/sessions tables, routers split, every `/api/*` protected, PIN removed | `fastapi-patterns`, `api-design`, `python-testing`, `app-security-hardening`; `ecc:tdd-guide`, `ecc:security-reviewer` |
| 2 | Shared design system | `tokens.css`, `tailwind.config.js`, `sprite.svg`, `motion.js`, `api.js`, `session.js` | `frontend-design`, `taste-skill`, `motion-foundations` |
| 3 | Landing page | `ui/landing/*` with fog canvas, parallax, ScrollTrigger pipeline, dividers, CTA → login | `motion-advanced`, `motion-patterns`, `frontend-design` |
| 4 | Login + demo | `ui/login/*`, demo cards, `demo.db` seeding/reset | `app-security-hardening` |
| 5 | Dashboard shell + views | Router, sidebar, all 7 views ported from current `app.js` logic, role-gated controls | `frontend-patterns`, `make-interfaces-feel-better` |
| 6 | AXIS charts | `charts.js` ChartRenderer, 7 chart types on Overview, tooltip | `dataviz` |
| 7 | Hardening & QA | a11y pass, reduced-motion, mobile widths, E2E flows, security review, delete old `ui/index.html`/`app.js`/`styles.css` | `accessibility`, `browser-qa`, `e2e-testing`; `ecc:code-reviewer`, `ecc:security-reviewer` |

Phases 1 and 2 are independent and can run in parallel; 3–6 depend on 2; 4–5 depend on 1.

## 7. Testing

- **pytest** (`tests/`): RBAC matrix test — every route × every role → expected 200/401/403 (one parametrized test, catches any unprotected endpoint); login/logout/session expiry; CSRF rejection; login rate limit; demo sessions never touch `data/autojob.db` and never launch Chromium.
- **Playwright E2E** (already a dependency): landing → "Try demo (Operator)" → dashboard loads → run scout → viewer cannot see "Start agent" → logout returns to landing.
- Target 80% coverage on `src/auth` and `src/api`.

## 8. Risks

- **Reference fidelity**: without the source HTML we cannot match exact paths/timings. Blocking for Phase 2.
- **Tailwind CDN in production**: runtime JIT, not for public deployment; swap to standalone CLI if deployed.
- **Single-process state**: agent controller and rate limiter are in-memory; fine for `uvicorn` single worker, documented with `ponytail:` notes.
- **GSAP + polling**: pipeline timeline must be idempotent on repeated identical `active_step` polls (only tween on change).

## 9. Open questions

1. Can you add the reference HTML source file to `design/reference/`?
2. Keep the template's "Nexus Pro" controller/copy literally, or adapt the hero to AutoJob (plan assumes adapt)?
3. Is this single-user local tool or will multiple real users log in? (affects whether the Users admin page is needed now)
4. Dark-only OK, dropping the current light theme toggle?
