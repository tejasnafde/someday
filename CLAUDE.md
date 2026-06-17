# Someday — Agent Instructions

## Design System

**Before writing any UI code, read `docs/style-guide.md` in full.**

The style guide is the single source of truth for colours, typography, spacing, buttons, icons, and glass surfaces. Violating it produces visual inconsistency that requires a full review pass to fix. It is faster to check first.

### Hard UI rules (no exceptions)

- **Colours via tokens only.** Never hardcode a hex value in a component. Use `var(--acc)`, `var(--cp)`, etc.
- **One button gradient.** Every filled CTA uses `linear-gradient(135deg, var(--acc), var(--acc-m))`. No green "success" buttons, no red "danger" buttons, no one-off colours.
- **No emoji in UI chrome.** Icons, buttons, labels, badges, tabs, and navigation must use the SVG sprite system (`<svg class="icon"><use href="#i-name"/></svg>`). Emoji are user content only.
- **Dark mode = charcoal only.** Dark backgrounds and glass surfaces must be neutral grey. Zero blue, purple, or colour tints in `--bg-*`, `--glass*`, or `--brd*` dark tokens.
- **Circle identity colours (`--cp`, `--cg`, `--cb`) in three places only:** left-border stripe, icon background, count badge. Nowhere else.
- **`--r` and `--rs` for all border-radius.** No custom values.

---

## Backend (FastAPI)

### Project structure

Mirrors `geoiq_broker_app_v2`. Every new module follows this exact layering:

```
routers/<module>_router.py      ← HTTP only: Pydantic validation, Depends(jwt_required), calls create_response()
handler/<module>_handler.py     ← Extends DBUtil, returns (status_code, result) tuples
modules/<module>/
  <module>_helper.py            ← Business logic, orchestration
  <module>_queries.py           ← Raw SQL strings only (sqlalchemy.text + :named params)
schemas/<module>_schema.py      ← Pydantic BaseModels for request/response
```

### Hard backend rules

- **No `SELECT *`.** Always name every column.
- **`status = 1` filter on every query.** All tables have a `status` integer column. Active = 1, soft-deleted = 0, user-deleted = -1. Never `DELETE` rows.
- **Intent workflow state is `task_status`.** The column `status` is the soft-delete flag on every table. The workflow (saved/interested/planned/done/archived) is `task_status` on the `intents` table.
- **Raw SQL via `sql_text()`.** Import as `from sqlalchemy import text as sql_text`. Query strings live in `_queries.py` as plain Python strings; `sql_text()` is applied in `db_util.py` at execution time, never in the query files themselves.
- **Named params only.** Use `:param_name` syntax. No f-strings or string interpolation in SQL.
- **No `::type` PostgreSQL casts in parameterised queries.** The `::` operator after a named param (e.g. `:tags::text[]`) conflicts with SQLAlchemy's param parser. Use ANSI `CAST(:param AS type)` instead, or rely on psycopg2's automatic Python→Postgres type coercion (lists → `text[]`, JSON strings → `jsonb`).
- **No `os.environ`.** Always `from config.settings import settings`.
- **No `print()`.** Always `infologger` or `errorlogger` from `app_util/log_util.py`.
- **Handlers return `(status_code, result)` tuples.** Routers wrap with `create_response()`.
- **No `_` prefix on anything.** There is no private convention in this codebase. Never name a function, method, variable, or module-level constant with a leading underscore. Dunder methods (`__init__`, `__str__`, etc.) are fine — single-underscore names are not. If you think something should be "private", just don't expose it — the underscore prefix adds noise without enforcement.

---

## Logging — non-negotiable

Set up `log_util.py` and decorators **before any feature code**. Every endpoint, always.

- `@log_timing("ENDPOINT_NAME")` on every router function — logs request start with payload, end with duration.
- `@log_payload` logs the Pydantic-validated body at INFO before calling the handler.
- `DBUtil` logs every query + params (DEBUG) and result row count (DEBUG) automatically.
- Every handler method logs its entry point with key identifiers (`user_id`, `circle_id`, etc.).
- `WARNING` for every fallback or degraded path (unfurl failed, invite token not found, etc.).
- `ERROR` + full exception in every `except` block.
- Never remove logs to silence noise — tune `LOG_LEVEL` env var instead (DEBUG in dev, INFO in prod).
- Abundant logs are correct. The rule is: if you're testing a new endpoint, you should never need to go back and add logs after the fact.

---

## Database

- **Supabase Postgres** for both dev and prod. Two separate Supabase projects.
- Load connection string from `settings.py` via `APP_ENV` → `.env.dev` or `.env.production`.
- All migrations are plain SQL files in `someday-api/supabase/migrations/` (Supabase CLI format: `YYYYMMDDHHMMSS_name.sql`). Run `supabase db push` to apply. No ORM migration tooling.
- Soft deletes only. `status = 0` hides from UI. `status = -1` for user-initiated removal.

---

## Environments

| Env | Backend | DB |
|---|---|---|
| dev | local `uvicorn` (`python run.py`) | Supabase project `someday-dev` (ydjqonpciulspgzzxepw) |
| production | GCP Cloud Run `someday-api` (project `teejayproject`, asia-south1), auto-deployed by Cloud Build on push to main touching `someday-api/**` | Supabase project `someday` (hltpqcmmpddjhijqeeko) |

`APP_ENV` env var selects the environment. Default is `dev`.

---

## Tours — non-negotiable

Every new user-facing feature ships with a coachmark tour step. No exceptions.

**Checklist before merging any UI change:**

1. Add `data-tour="<anchor>"` to the feature's target element.
2. Append a `TourStep` to `TOUR_REGISTRY` in `someday-web/lib/tour/registry.ts` with a **stable, never-reused** id (format: `<page>.<feature>`). IDs are permanent — users' seen state lives server-side against these ids.
3. If the page doesn't already have `<Tour page="..."/>`, add it and extend `TourPage` in `registry.ts`.
4. Tour copy follows the same voice as the rest of the app: short, second-person, no filler. One sentence is enough.

**Anchor naming convention:** `<page>-<feature>` e.g. `circle-tags`, `intent-planned`, `members-roles`.

---

## Git

- **main is protected — no direct pushes, even for admins.** All changes go through a feature branch + PR: `git checkout -b <branch>` → push → `gh pr create` → `gh pr merge --merge`. Zero approvals required, so you can merge your own PR immediately.
- **Always merge, never rebase.** If a push is rejected for being behind, `git pull` (merge) then push.
- Commit messages: short imperative subject line + body explaining the *why*, not the *what*.
- Co-author line: `Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>`
