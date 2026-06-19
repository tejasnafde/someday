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
- **No top-level imports inside functions.** All imports belong at the top of the file. The only exception is circular-import avoidance, which must be documented with a comment.
- **All config values in `settings.py`.** No hardcoded strings that could vary between environments (repo names, URLs, tokens). If a constant is used in more than one place or could ever change, put it in `settings.py`.

### Authorization on mutations (non-negotiable)

Every endpoint that mutates or reads a resource gated to circle membership **must verify membership before acting**. The pattern:

```python
# In the handler method — always the first thing:
existing = h.get_intent(self, intent_id, user_id)   # enforces membership via EXISTS subquery
if not existing:
    return 404, "Intent not found"
# ... proceed with mutation
```

- Never trust that a resource belongs to the caller without checking. The SQL query (`GET_INTENT_BY_ID`, etc.) enforces membership via an `EXISTS` subquery — this is the authoritative check, not application logic.
- If you add a new mutation endpoint, add the membership `EXISTS` clause to the lookup query before anything else.

### Transactions for multi-step writes

Any operation that touches more than one table (or more than one row that must stay consistent) **must use `db.transaction()`**:

```python
with db.transaction() as conn:
    row = db.tx_exec_returning(conn, QUERY_A, params_a)
    db.tx_exec(conn, QUERY_B, {**params_b, "id": row["id"]})
# commit happens automatically on exit; rollback on exception
```

- Never call `execute_query_with_value_without_output` multiple times for logically atomic operations. A half-applied state (circle created but owner not added as member, ownership transferred but old role not demoted) is worse than an error.
- `db.tx_exec(conn, query, params)` — execute on existing connection, no commit.
- `db.tx_exec_returning(conn, query, params)` — execute RETURNING on existing connection, returns the row dict.

### Cursor-based pagination on all list endpoints

Every endpoint that returns a list of rows **must support cursor pagination**. No offset/page-number pagination (it drifts under concurrent inserts).

```sql
AND (:cursor IS NULL OR created_at < CAST(:cursor AS timestamptz))
ORDER BY created_at DESC
LIMIT :limit
```

- Router: `cursor: str | None = Query(default=None)`, `limit: int = Query(default=50, ge=1, le=200)`.
- Handler/helper: pass through to query; return `{"items": [...], "next_cursor": str | None}`.
- `next_cursor = items[-1]["created_at"] if len(items) == limit else None`
- Client: pass `next_cursor` as `cursor` on the next call to load more. A null cursor means there are no more pages.

### SSRF protection on all outbound HTTP

Any code that makes an outbound HTTP call with a URL from user input (unfurl, image re-host, webhook, etc.) **must call `common_helper.url_util.validate_url(url)` before the request**:

```python
from common_helper.url_util import validate_url
validate_url(url)  # raises ValueError on private IPs, file://, metadata hosts
```

- `validate_url` blocks: non-http/https schemes, IP literals in private/loopback/link-local ranges, known cloud metadata hostnames (169.254.169.254, etc.).
- Catch `ValueError` and log at ERROR level; return `None` or 400 to the caller.
- After following redirects (e.g. shortlink resolution), validate the final URL too.
- Note: full DNS-rebinding protection requires infra-level egress controls and is out of scope for application code.

### Pinned dependencies

`requirements.txt` uses `==` for every package. When adding a new dependency:
1. Find the latest stable version.
2. Pin it: `newpackage==x.y.z`.
3. Update `cloudbuild-production.yaml` if the build step caches layers that need to be busted.

Never use `>=`, `~=`, or unpinned versions in `requirements.txt`.

---

## Auth — read the doc first

**Before touching anything auth-related (app, web, or backend), read `docs/auth-architecture.md` in full.**

Sign-in is not a normal native flow. The mobile app is a **native auth shell wrapping a WebView**, and a signed-in device holds **two independent Supabase sessions** — a native one (`AsyncStorage`) and a separately-minted WebView one (web `localStorage`), bridged via `POST /auth/webview-session` and an implicit-grant URL fragment. They are kept separate on purpose (refresh-token rotation reuse-detection would otherwise revoke both). The doc covers the full flow plus the load-bearing gotchas: PKCE `flowType`, the Android `someday:` scheme (no `//`), single-exchange guarding, and the mandatory `expires_in` in the bridge fragment. Client-side auth failures have no server log — instrument with `api.clientError()` → Discord.

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

### Hard migration rules (no exceptions)

- **All migrations must be idempotent.** Every statement must be safe to run more than once against a database that already has it applied. No exceptions — this is enforced, not advisory.
  - Tables: `CREATE TABLE IF NOT EXISTS`
  - Indexes: `CREATE INDEX IF NOT EXISTS` / `CREATE UNIQUE INDEX IF NOT EXISTS`
  - Columns: `ALTER TABLE ... ADD COLUMN IF NOT EXISTS`
  - Functions: `CREATE OR REPLACE FUNCTION`
  - Triggers: `DROP TRIGGER IF EXISTS` before `CREATE TRIGGER`
  - Policies: `CREATE POLICY` has no `IF NOT EXISTS` — wrap in a DO block checking `pg_policies`:
    ```sql
    DO $$ BEGIN
      IF NOT EXISTS (SELECT 1 FROM pg_policies WHERE schemaname = 'public' AND tablename = 'x' AND policyname = 'y') THEN
        CREATE POLICY "y" ON public.x ...;
      END IF;
    END $$;
    ```
  - Inserts: `ON CONFLICT DO NOTHING`
- **Apply migrations via Supabase CLI, never the SQL editor.** Run `supabase db push --linked` (switch projects with `supabase link --project-ref <ref>`). If a migration was accidentally run via the editor and is missing from CLI tracking, use `supabase migration repair --status applied <version>` to sync the state, then push.

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

## Mobile App (Expo / React Native)

### Secure token storage

Auth tokens are stored in the device secure enclave via `expo-secure-store`, **not** `AsyncStorage`. This was a deliberate security fix — do not revert.

- `someday-app/lib/supabase.ts` uses `SecureStore.getItemAsync / setItemAsync / deleteItemAsync` as the Supabase auth storage adapter.
- The session inactivity timer in `App.tsx` uses `AsyncStorage` only for the `last_active_timestamp` value (not sensitive) — this is intentional. Supabase tokens stay in SecureStore.

### Crash reporting

`App.tsx` installs `ErrorUtils.setGlobalHandler` at module load time. It forwards fatal and non-fatal JS errors to `POST /auth/client-error` via `api.clientError()` (fire-and-forget, never throws).

- `ErrorUtils` is a React Native runtime global — not exported by the `react-native` package. Declare it with a local `declare const ErrorUtils` in the file that uses it.
- Do not wrap `api.clientError()` in a try/catch — it is already fire-and-forget by design.

### setTimeout safety in auth flows

Any `setTimeout` that refs state or clears a spinner **must be stored in a `useRef<ReturnType<typeof setTimeout> | null>` and cancelled in the cleanup function** returned from `useEffect`. Bare `setTimeout(() => setState(x), N)` after an async operation leaks into unmounted components and can clobber valid state (e.g. clearing a spinner after a successful sign-in).

Pattern:
```tsx
const timerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
useEffect(() => () => { if (timerRef.current) clearTimeout(timerRef.current); }, []);
// ...
timerRef.current = setTimeout(() => setBusy(false), 4000);
// Cancel when the real result arrives:
if (timerRef.current) { clearTimeout(timerRef.current); timerRef.current = null; }
```

---

## Web (Next.js)

### Error boundaries

Every Next.js App Router page directory **must have an `error.tsx`** that:
1. Uses `"use client"` (required by Next.js).
2. Calls `api.clientError("web_error", error.message, error.digest)` in a `useEffect` so errors are visible in Discord.
3. Shows a minimal "Something went wrong / Try again" UI.

The root `app/error.tsx` exists and handles the top-level boundary. Do not remove it.

### API call error handling

Every `async` form submit or button handler that calls `api.*()` **must use try/catch/finally**:

```tsx
async function create(e: React.FormEvent) {
  e.preventDefault();
  setBusy(true);
  setError("");
  try {
    await api.createSomething(...);
    // success path
  } catch (err: unknown) {
    setError(err instanceof Error ? err.message : "Something went wrong.");
  } finally {
    setBusy(false);  // always resets, even on error
  }
}
```

Letting `await api.call()` throw unhandled leaves the spinner stuck. `finally { setBusy(false) }` is the fix — not `setBusy(false)` after `await`.

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
