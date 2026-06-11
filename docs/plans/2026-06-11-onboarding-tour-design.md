# Onboarding Tour — Design

**Date:** 2026-06-11
**Status:** Approved
**Scope:** someday-web (UI), someday-api (state), automatically visible in someday-app webview.

## Goal

A first-login product tour using spotlight coachmarks, plus an extensible registry so
that shipping a new feature later means appending registry entries — returning users
then get a mini-tour of just the unseen features.

## Decisions

| Question | Decision |
|---|---|
| Tour form | Spotlight coachmarks: dimmed scrim, cut-out spotlight over real UI, glass tooltip card |
| Scope | Two-stage: dashboard steps on first login; circle steps auto-trigger on first circle visit |
| Extensibility | Feature-keyed registry; per-user seen step-ids stored server-side |
| Skip/replay | Skip marks the whole current run seen; "Replay tour" row in /settings resets state |
| Existing users at launch | Get the full tour once (empty `seen`); no backfill |

## Frontend (someday-web)

### Registry — `lib/tour/registry.ts`

```ts
export type TourStep = {
  id: string;            // stable forever, e.g. "circle.payoff"
  page: 'dashboard' | 'circle';
  anchor: string;        // matches data-tour="..." on the target element
  title: string;
  body: string;
  placement?: 'top' | 'bottom' | 'left' | 'right';
};
```

Launch set (array order = play order):

| id | page | anchor |
|---|---|---|
| `dash.welcome` | dashboard | logo (centered intro card) |
| `dash.create` | dashboard | create-circle |
| `dash.settings` | dashboard | settings |
| `circle.add` | circle | add-intent |
| `circle.status` | circle | status-tabs (saved → interested → planned → done) |
| `circle.payoff` | circle | payoff (smart-pick + spin) |
| `circle.reactions` | circle | intent-card (reactions + boosts) |
| `circle.invite` | circle | invite |

Adding a feature tour later = one registry entry + one `data-tour` attribute in the
feature's UI PR. No version math anywhere.

### Components

- **`TourProvider`** (client, root layout): after auth, reads `tour_state` from
  `api.me()`, computes `unseen = REGISTRY for current page − seen`, starts a run if
  non-empty. Exposes `useTour()`.
- **`TourOverlay`**: fixed scrim with SVG-mask spotlight over the anchor's
  `getBoundingClientRect` (recomputed on resize/scroll), glass tooltip card with
  title, body, step dots, Next / Skip tour. Style-guide compliant: token colours
  only, single CTA gradient, sprite icons, `--r`/`--rs` radii, charcoal dark mode.
  CSS transitions only (no GSAP in v1). Anchor scrolled into view per step.
- **Settings**: "Replay tour" row calls reset endpoint and restarts the current
  page's run.

### Behavior

- Stage 2 needs no special casing: first visit to `/circles/[id]` finds `circle.*`
  steps unseen and runs them. New-feature mini-tours fall out of the same logic.
- Finish or Skip → step ids merged into seen (optimistic local + one `POST /tour/seen`).
- Skip marks all steps in the current run seen.
- Missing anchor in DOM → step silently skipped.
- Max one run per page-load; never interrupt an in-progress run.

## Backend (someday-api)

### Migration — `supabase/migrations/<ts>_add_tour_state.sql`

```sql
ALTER TABLE public.users
  ADD COLUMN tour_state jsonb NOT NULL DEFAULT '{"seen": []}';
```

### New `tour` module (standard layering)

- `routers/tour_router.py` — `@log_timing` + `@log_payload`, `Depends(jwt_required)`,
  wraps handler with `create_response()`.
- `handler/tour_handler.py` — extends `DBUtil`, returns `(status_code, result)`,
  logs entry with `user_id`, WARNING on no-row-updated.
- `modules/tour/tour_helper.py`, `modules/tour/tour_queries.py` — named params,
  `status = 1` filter, no `::` casts.
- `schemas/tour_schema.py` — request/response models.

Endpoints:

- `POST /tour/seen` — `{"step_ids": [...]}` → set-union merge into
  `tour_state.seen`, returns updated `tour_state`.
- `POST /tour/reset` — resets to `{"seen": []}`.
- `GET /auth/me` — gains `tour_state` in its column list (only change outside the
  new module).

## Data flow

```
login → api.me() (includes tour_state)
  → TourProvider: unseen = page registry − seen
  → coachmark run → finish/skip → optimistic merge + POST /tour/seen
```

## Failure handling

- `POST /tour/seen` fails (offline webview, API hiccup): pending ids parked in
  localStorage, merged into the next run computation, retried on next load. A step
  is never replayed because a server write lagged.
- `tour_state` absent from `me()` (stale deploy ordering): tour does not run —
  fail-quiet beats re-nagging.

## Testing

- Backend: merge/reset verified against dev (pytest if harness exists, else curl).
- Web: scripted pass via the `ui-test.mjs` pattern — fresh user → tour → skip →
  reload → no tour → settings replay → tour again — plus manual verify with
  screenshots, including a narrow viewport to simulate the APK webview.

## Delivery

Branch `feat/onboarding-tour` → PR. No overlap with concurrent native-app work
(`someday-app`); this touches `someday-web` and one new API module.
