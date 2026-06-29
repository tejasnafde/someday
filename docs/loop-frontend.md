# /loop prompt - build the Someday frontend until done

Build, test, and deploy the Someday Next.js frontend until every acceptance
criterion below passes against the real backend. Work autonomously; iterate
without asking for permission. Commit + push after every meaningful unit of
work with proper messages.

## Context

- Repo: ~/Desktop/projects/someday (CLAUDE.md + docs/style-guide.md are law)
- Backend: someday-api/ (FastAPI) - fully working, 24/24 smoke tests pass.
  Run locally: `cd someday-api && source .venv/bin/activate && python3 run.py` (port 8000)
- Design: mocks/mock-combined.html is the visual spec - Lora + DM Sans,
  glass cards, per-circle colours, charcoal dark mode, SVG sprite icons,
  light/dark toggle. Replicate it faithfully.
- Design doc: docs/plans/2026-06-09-someday-design.md (screens, API, payoff)
- Supabase: project ref hltpqcmmpddjhijqeeko, magic-link auth, ES256 JWKS

## Test auth autonomously

Use SUPABASE_SERVICE_ROLE_KEY from someday-api/.env.dev to mint sessions:
1. POST {SUPABASE_URL}/auth/v1/admin/generate_link {"type":"magiclink","email":"test@someday.dev"} with service-role apikey header
2. Exchange: POST {SUPABASE_URL}/auth/v1/verify {"type":"magiclink","token_hash":...} → access_token
Never ask the user for tokens. Create test users as needed (test1@someday.dev etc. - needed for multi-member shortlist/payoff testing).

## Build (in someday-web/)

Next.js 16 App Router + TypeScript + Tailwind v4. Minimal deps:
@supabase/supabase-js for auth only; plain fetch wrapper for the API.

Screens (routes from design doc):
1. /login - email → magic link; /auth/callback handles the token fragment, calls POST /auth/verify
2. / - home: circle cards (colour identity, member dots, idea count), new-circle modal
3. /circles/[id] - tabs All·Shortlist·Done, filter chips, intent cards with react+boost, payoff CTA
4. /circles/[id]/add - URL input with live unfurl preview, category picker, tags, note
5. /intents/[id] - detail: link preview, who's interested, task_status stepper, react + boost
6. /circles/[id]/payoff - Best Pick (reveal card with score chips) + Spin (wheel animation over shortlist)
7. /circles/[id]/invite - share link copy
8. /circles/[id]/members - member list, promote/remove, invite link
9. /join/[token] - accept invite
10. /notifications - in-app activity feed (reactions, boosts, saves)
11. /settings - display name, avatar, sign out

Code standards - hard rules:
- Minimal code. No speculative abstractions, no unused exports, no boilerplate comments, no defensive try/catch on trusted paths. If a file reads like a tutorial, rewrite it.
- Style guide tokens exactly: CSS variables from mock-combined.html, both themes, prefers-color-scheme + manual toggle.
- No emoji in UI chrome - port the SVG sprite from the mock.
- One API client module (lib/api.ts): typed fetch wrapper that attaches the Supabase access token, base URL from NEXT_PUBLIC_API_URL.
- Loading/empty/error states on every screen (empty states use the microcopy from the design doc).

## Test loop (every iteration)

1. Backend on :8000, frontend dev server on :3000
2. Mint a token, exercise the changed flow end-to-end with curl/node against the running frontend (SSR HTML) and API
3. `npm run build` must pass clean (type errors = broken)
4. For UI verification use Playwright (npx playwright) headless: screenshot each screen in light+dark, check console errors
5. Fix everything you find; never leave an iteration red

## Acceptance criteria (the loop exits when ALL pass)

1. Magic-link login works end-to-end on the deployed web app
2. Create circle → invite link → second test user joins via /join/[token]
3. Add intent with URL → unfurl preview renders before save → saved card shows link preview
4. React/boost toggle and sync between the two test users
5. Shortlist tab shows only ≥2-interested intents
6. Best Pick returns top-scored intent with score-breakdown chips rendered
7. Spin animates and lands on a shortlisted intent
8. task_status stepper moves saved→interested→planned→done; Done tab shows done items
9. Filters (task_status, category, tag) work
10. Light/dark toggle works, dark is pure charcoal, zero hex literals in components (tokens only)
11. npm run build clean; no console errors on any screen
12. Deployed: backend on GCP Cloud Run (auto-deployed via Cloud Build on push to main), frontend on Vercel (vercel --prod from someday-web/, NEXT_PUBLIC_* set), Supabase auth redirect URLs updated to the Vercel domain, full flow re-tested on production URLs

## Deployment notes

- API: GCP Cloud Run (`someday-api`, project `teejayproject`, asia-south1) - auto-deployed by Cloud Build on pushes to main touching `someday-api/**` (`cloudbuild-production.yaml`). Env vars: APP_ENV=production + SUPABASE_URL + SUPABASE_ANON_KEY + DATABASE_URL + LOG_LEVEL=INFO + ALLOWED_ORIGINS=(vercel domain).
- Vercel: project someday-web, NEXT_PUBLIC_API_URL=(Cloud Run service URL), NEXT_PUBLIC_SUPABASE_URL, NEXT_PUBLIC_SUPABASE_ANON_KEY
- Supabase dashboard → Auth → URL configuration: add Vercel domain to redirect allowlist (if dashboard-only, pause and ask - this is the ONLY allowed pause besides CLI re-auth)

## Pause rules

Only stop for: railway/vercel CLI auth expiry, missing secrets, or
dashboard-only configuration. For everything else: decide, build, test, ship.
When pausing, state exactly what you need and what command/value unblocks you.
