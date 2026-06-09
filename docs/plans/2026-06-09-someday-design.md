# Someday — Full Product Design
**Date:** 2026-06-09  
**Status:** Approved

---

## 1. What We're Building

**Someday** is a shared memory layer for friendships. Instead of saving things for yourself, you save them *for a relationship*. Every circle becomes a living backlog of experiences waiting to happen.

The core inversion: most tools are organized Me → Things. Someday is organized Me → People → Things.

**Name:** Someday (the app). **Circles** = the feature name for a shared group/relationship space within the app.

---

## 2. Architecture Overview

```
┌─────────────────────┐     ┌──────────────────────────┐
│  Next.js (Vercel)   │────▶│  FastAPI (Railway)        │
│  Responsive Web App │     │  routers → handlers →     │
└─────────────────────┘     │  modules → db_util        │
                            └────────────┬─────────────┘
┌─────────────────────┐                  │
│  Expo Android App   │────▶             │
│  (share-sheet only) │     ┌────────────▼─────────────┐
└─────────────────────┘     │  Supabase                 │
                            │  Postgres + Auth           │
                            │  (magic link JWTs)         │
                            └──────────────────────────┘
```

**Auth flow:** Supabase Auth issues JWTs on magic link verify → web and Android send JWT on every request → FastAPI middleware validates against Supabase's public JWKS keys → handlers receive `current_user` via `Depends()`.

**Unfurl:** FastAPI fetches OG metadata server-side (httpx + opengraph-py3) when a URL is saved. Returns `{title, image, site}` from Open Graph meta tags.

**Environments:** `.env.dev` (Supabase dev project) and `.env.production` (Supabase prod project). Railway has separate dev/prod services with env vars per environment. `APP_ENV` env var selects which file to load via pydantic-settings.

---

## 3. Tech Stack

| Layer | Choice |
|---|---|
| App name | Someday |
| Groups | Circles (renameable) |
| Backend | FastAPI on Railway |
| DB + Auth | Supabase (Postgres + magic link) |
| Web | Next.js + Tailwind on Vercel |
| Android | Expo (share-sheet only) |
| Unfurl | httpx + opengraph-py3 |
| Tests | pytest + httpx |

---

## 4. Backend Structure

Mirrors `geoiq_broker_app_v2` layering exactly.

```
someday-api/
├── main.py                      # FastAPI app, CORS, middleware, router registration
├── run.py                       # Uvicorn entry point
├── pyproject.toml
├── .env.dev
├── .env.production
├── .env.example                 # committed, no secrets
│
├── routers/                     # HTTP layer only — Pydantic validation, Depends(jwt_required)
│   ├── auth_router.py           # POST /auth/verify
│   ├── circles_router.py
│   ├── intents_router.py
│   ├── payoff_router.py         # Smart pick + spin
│   └── unfurl_router.py
│
├── handler/                     # Extends DBUtil, returns (status_code, result) tuples
│   ├── circles_handler.py
│   ├── intents_handler.py
│   ├── payoff_handler.py        # Scoring algorithm lives here
│   └── unfurl_handler.py
│
├── modules/
│   ├── circles/
│   │   ├── circles_helper.py
│   │   └── circles_queries.py
│   ├── intents/
│   │   ├── intents_helper.py
│   │   └── intents_queries.py
│   └── payoff/
│       ├── payoff_helper.py     # Score computation helpers
│       └── payoff_queries.py    # Scoring SQL
│
├── schemas/                     # Pydantic BaseModels (request + response)
│   ├── circles_schema.py
│   ├── intents_schema.py
│   └── payoff_schema.py
│
├── app_util/
│   ├── db_util.py               # DBUtil base class (SQLAlchemy 2.0, Supabase Postgres)
│   └── log_util.py              # infologger + errorlogger setup
│
├── common_helper/
│   ├── auth_helper.py           # Supabase JWT verification via PyJWT + JWKS
│   └── decorators.py            # @log_timing, @log_payload
│
├── config/
│   └── settings.py              # pydantic-settings, reads APP_ENV → .env.{env}
│
└── tests/
    ├── conftest.py
    ├── circles/
    ├── intents/
    └── payoff/
```

**Request flow:** HTTP Request → `main.py` middleware → `routers/` (Pydantic validation + `Depends(jwt_required)`) → `handler/` (extends DBUtil, returns `(status_code, result)`) → `modules/` (helpers + SQL) → `db_util.py`

**Hard rules (same as reference project):**
- No `SELECT *`
- No `os.environ` — always `from config.settings import settings`
- No `print()` — always `infologger` / `errorlogger`
- Handlers return `(status, result)` tuples; routers wrap with `create_response()`
- All SQL uses `:param` named params with `sqlalchemy.text()`
- Soft deletes only — never `DELETE` from DB
- All queries filter `status = 1`

---

## 5. Logging Architecture

Logging is infrastructure, not an afterthought. Set up before any feature code is written.

### Log levels

| Level | When to use |
|---|---|
| `DEBUG` | DB query string + bound params, DB result row count, helper inputs/outputs |
| `INFO` | Request received + payload, business logic milestones, response + duration |
| `WARNING` | Unexpected but handled paths (unfurl failed, token not found, etc.) |
| `ERROR` | Any caught exception, failed DB op, auth failure |

### Components

**`app_util/log_util.py`**
- Sets up two named loggers: `infologger` (INFO+) and `errorlogger` (ERROR+)
- Dev: colored, human-readable, shows module + line number
- Prod: structured JSON → Railway log viewer can filter/search
- Log level tuned via `LOG_LEVEL` env var (DEBUG in dev, INFO in prod)

**`common_helper/decorators.py`**
- `@log_timing("ENDPOINT_NAME")` — logs REQUEST_START with payload, REQUEST_END with duration_ms. Applied to every router endpoint.
- `@log_payload` — logs Pydantic-validated request body at INFO before calling handler.

**`app_util/db_util.py`**  
Every query method logs automatically — handlers never log SQL manually:
```
DEBUG  DB_QUERY  | SELECT id, name FROM circles WHERE owner_id = :owner_id AND status = 1
DEBUG  DB_PARAMS | {'owner_id': 'abc-123'}
DEBUG  DB_RESULT | 3 rows | 4.2ms
```

**`main.py` middleware**
```
INFO  REQUEST  | POST /circles/:id/intents | user=tejas@geoiq.io
INFO  RESPONSE | 201 | 267ms
```

### Full request lifecycle in logs

```
INFO  middleware        REQUEST | POST /circles/:id/intents | user=tejas@geoiq.io
INFO  intents_router    PAYLOAD | {title: "Dune 2", url: "https://...", circle_id: "..."}
INFO  intents_handler   CREATE_INTENT_START | circle_id=abc user_id=xyz
DEBUG db_util           DB_QUERY | INSERT INTO intents ...
DEBUG db_util           DB_PARAMS | {id: "new-uuid", circle_id: "abc", ...}
DEBUG db_util           DB_RESULT | 1 row | 3.1ms
INFO  unfurl_handler    UNFURL_START | url=https://youtube.com/...
INFO  unfurl_handler    UNFURL_SUCCESS | title="Dune: Part Two" site="YouTube" | 210ms
INFO  intents_handler   CREATE_INTENT_END | intent_id=new-uuid
INFO  middleware        RESPONSE | 201 | 267ms
```

### CLAUDE.md rules (enforced)
- Every handler method logs entry with key identifiers (user_id, circle_id, etc.)
- Every router endpoint uses `@log_timing` and `@log_payload` decorators
- DBUtil logs all queries automatically — never log SQL manually in handlers/modules
- `WARNING` for every fallback or degraded path
- `ERROR` + full exception in every `except` block
- Never `print()` — always `infologger` / `errorlogger`
- Abundant logs are correct — silence with LOG_LEVEL, never by removing them

---

## 6. Data Model

### Status convention (universal — every table)

| Value | Meaning |
|---|---|
| `1` | Active — default, included in all queries |
| `0` | Soft deleted / hidden from UI |
| `-1` | User-initiated delete / deactivated |
| Other | Case by case (e.g. `2` = pending on circle_members) |

**All queries always filter `WHERE status = 1`.**  
The intent workflow field is named `task_status` (not `status`) to avoid collision.

### Schema

```sql
-- mirrors supabase auth.users
CREATE TABLE public.users (
  id            uuid PRIMARY KEY REFERENCES auth.users(id),
  email         text UNIQUE NOT NULL,
  display_name  text,
  avatar_url    text,
  status        integer NOT NULL DEFAULT 1,
  created_at    timestamptz DEFAULT now()
);

CREATE TABLE public.circles (
  id            uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  name          text NOT NULL,
  emoji         text,
  owner_id      uuid NOT NULL REFERENCES users(id),
  invite_token  text UNIQUE NOT NULL DEFAULT encode(gen_random_bytes(16), 'hex'),
  status        integer NOT NULL DEFAULT 1,
  created_at    timestamptz DEFAULT now()
);

CREATE TABLE public.circle_members (
  id            uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  circle_id     uuid NOT NULL REFERENCES circles(id) ON DELETE CASCADE,
  user_id       uuid NOT NULL REFERENCES users(id),
  role          text NOT NULL DEFAULT 'member',  -- 'owner' | 'member'
  status        integer NOT NULL DEFAULT 1,
  joined_at     timestamptz DEFAULT now()
  -- UNIQUE(circle_id, user_id) enforced at app layer (re-join after leave sets status=1)
);

CREATE TABLE public.intents (
  id            uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  circle_id     uuid NOT NULL REFERENCES circles(id) ON DELETE CASCADE,
  created_by    uuid NOT NULL REFERENCES users(id),
  title         text NOT NULL,
  url           text,
  note          text,
  category      text,         -- 'watch'|'eat'|'visit'|'read'|'play'|'trip'|'other'
  tags          text[] DEFAULT '{}',
  task_status   text NOT NULL DEFAULT 'saved',
                -- 'saved'|'interested'|'planned'|'done'|'archived'
  link_meta     jsonb,        -- {title, image, site} from unfurl
  planned_for   text,         -- loose free-text date (P1)
  status        integer NOT NULL DEFAULT 1,
  created_at    timestamptz DEFAULT now(),
  updated_at    timestamptz DEFAULT now()
);

CREATE OR REPLACE FUNCTION update_updated_at()
RETURNS TRIGGER AS $$
BEGIN NEW.updated_at = now(); RETURN NEW; END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER intents_updated_at
  BEFORE UPDATE ON intents
  FOR EACH ROW EXECUTE FUNCTION update_updated_at();

CREATE TABLE public.reactions (
  id            uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  intent_id     uuid NOT NULL REFERENCES intents(id) ON DELETE CASCADE,
  user_id       uuid NOT NULL REFERENCES users(id),
  kind          text NOT NULL DEFAULT 'interested',
  status        integer NOT NULL DEFAULT 1,
  created_at    timestamptz DEFAULT now(),
  UNIQUE(intent_id, user_id, kind)
);

-- "I really want this today" boost signal
CREATE TABLE public.intent_boosts (
  id            uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  intent_id     uuid NOT NULL REFERENCES intents(id) ON DELETE CASCADE,
  user_id       uuid NOT NULL REFERENCES users(id),
  status        integer NOT NULL DEFAULT 1,
  created_at    timestamptz DEFAULT now(),
  UNIQUE(intent_id, user_id)   -- one per member, toggleable
);
```

### Indexes

```sql
CREATE INDEX ON circles(owner_id) WHERE status = 1;
CREATE INDEX ON circle_members(user_id) WHERE status = 1;
CREATE INDEX ON circle_members(circle_id) WHERE status = 1;
CREATE INDEX ON intents(circle_id, task_status) WHERE status = 1;
CREATE INDEX ON reactions(intent_id) WHERE status = 1;
CREATE INDEX ON intent_boosts(intent_id) WHERE status = 1;
CREATE INDEX ON intents(created_at);
```

---

## 7. API Surface

```
AUTH
POST  /auth/verify                 Validate Supabase JWT, upsert user row, return profile

USER
GET   /me                          Current user + their circles

CIRCLES
POST  /circles                     Create circle (auto-generates invite_token)
GET   /circles/:id                 Circle detail + members
PATCH /circles/:id                 Rename / set emoji
DELETE /circles/:id                Soft delete (status=0), owner only
POST  /circles/join/:token         Join via invite link
POST  /circles/:id/leave           Set circle_members.status=0 for current user

INTENTS
GET   /circles/:id/intents         List (filters: task_status, category, tag, shortlist=true)
POST  /circles/:id/intents         Create intent; triggers unfurl if URL present
PATCH /intents/:id                 Edit fields / change task_status
DELETE /intents/:id                Soft delete (status=0)
POST  /intents/:id/react           Toggle 'interested' reaction
POST  /intents/:id/boost           Toggle boost for current user

PAYOFF
GET   /circles/:id/payoff/smart    Top-scored intent + score breakdown
GET   /circles/:id/payoff/spin     Full shortlist shuffled (frontend animates the wheel)

UNFURL
POST  /unfurl                      {url} → {title, image, site}
```

---

## 8. Payoff Feature

### Two modes

**Smart pick** — algorithmic, reveals top-scored intent with a reason card:
> "3 of 4 interested · saved 6 weeks ago · 2 boosts"

**Spin for fun** — backend returns full shortlist in random order, frontend runs the wheel/slot animation. Pure random, no weighting.

### Scoring algorithm (smart pick)

```
score =
  (reaction_count / member_count)  × 40   -- mutual interest ratio
  + min(days_saved / 30, 1.0)      × 20   -- save age bonus (caps at 1 month)
  + has_any_boost                  × 40   -- boost signal (binary)
```

Tiebreaker: most recently reacted to.

### Scoring query

```sql
SELECT
  i.id,
  i.title,
  i.link_meta,
  COUNT(DISTINCT r.user_id)                                     AS reaction_count,
  COUNT(DISTINCT r.user_id)::float / :member_count              AS mutual_ratio,
  EXTRACT(EPOCH FROM (now() - i.created_at)) / 86400            AS days_saved,
  MAX(CASE WHEN b.id IS NOT NULL THEN 1 ELSE 0 END)             AS has_boost,
  (COUNT(DISTINCT r.user_id)::float / :member_count * 40)
  + (LEAST(EXTRACT(EPOCH FROM (now() - i.created_at))/86400 / 30, 1) * 20)
  + (MAX(CASE WHEN b.id IS NOT NULL THEN 1 ELSE 0 END) * 40)   AS score
FROM intents i
LEFT JOIN reactions r      ON r.intent_id = i.id AND r.kind = 'interested' AND r.status = 1
LEFT JOIN intent_boosts b  ON b.intent_id = i.id AND b.status = 1
WHERE i.circle_id   = :circle_id
  AND i.status      = 1
  AND i.task_status NOT IN ('done', 'archived')
  AND (
    SELECT COUNT(DISTINCT r2.user_id)
    FROM reactions r2
    WHERE r2.intent_id = i.id AND r2.status = 1
  ) >= 2
GROUP BY i.id
ORDER BY score DESC
LIMIT 1;
```

### Boost UX

- ⚡ toggle button on every intent card — tap any time to signal "I really want this today"
- When opening the Payoff screen with no active boosts: gentle prompt "Feeling anything in particular right now?" — quick-tap shortlisted items to boost before revealing the pick

---

## 9. Screens

| Screen | Route | Key elements |
|---|---|---|
| Auth | `/login` | Email input → magic link → `/verify?token=` |
| Home | `/` | Grid of circle cards — emoji, member avatars, open intent count. + New circle |
| Circle detail | `/circles/:id` | Tabs: All · Shortlist · Done. Filter chips. Intent cards with ⚡ boost. FAB: + Add |
| Add / Edit intent | `/circles/:id/intents/new` | Title, URL (live unfurl preview), note, category picker, tags |
| Intent detail | `/intents/:id` | Link preview card, who's interested, task_status switcher, react + boost |
| Payoff | `/circles/:id/payoff` | Two buttons — 🎯 Best Pick / 🎡 Spin. Boost prompt if nothing boosted |
| Smart pick reveal | (modal) | Winning intent + reason: "3 of 4 interested · 6 weeks · 2 boosts" |
| Spin reveal | (modal) | Animated wheel/slot → lands on random shortlisted intent |
| Invite | `/circles/:id/invite` | Shareable link + copy |
| Settings | `/settings` | Display name, avatar, sign out |

### Visual direction

- Tone: warm, calm, personal — not productivity-grey, not loud-social
- Palette: soft violet/indigo accent (`#5B4B8A`) on warm off-white; per-circle emoji/color as personality
- Type: friendly geometric sans (Inter, General Sans, or Satoshi); generous spacing; large tappable cards
- Feel: each circle reads like a shared scrapbook of future plans, not a task tracker

### Microcopy principles

- "Save to circle" not "Add task"
- Empty state: "Nothing saved yet — drop in the first thing you two should do."
- Shortlist header: "When you meet, do these."
- Payoff screen: "What are you doing today?"

---

## 10. Android Share-Sheet (Expo)

Minimal Expo app — registers as Android share target only. All other functionality is the web app.

**Flow:** User in Instagram/YouTube/browser → Share → picks "Someday" → Expo app receives URL → calls `/unfurl` → shows preview → user picks circle → calls `POST /circles/:id/intents` → intent saved. Done.

No navigation, no auth UI, no full app — just the capture flow. Web app handles everything else.

---

## 11. Build Order

```
PHASE 1 — FOUNDATION
1.  Monorepo setup: someday-api/ + someday-web/
2.  log_util.py + decorators (@log_timing, @log_payload) — before any feature code
3.  CLAUDE.md written — logging rules, status convention, SQL rules
4.  Supabase projects (dev + prod) — schema migration, RLS policies
5.  FastAPI skeleton — db_util, settings, main.py, health check endpoint
6.  Auth — Supabase magic link → POST /auth/verify → JWT middleware → GET /me

PHASE 2 — CORE LOOP
7.  Circles CRUD + invite/join + leave
8.  Intents CRUD + task_status transitions
9.  URL unfurl (httpx + opengraph-py3) wired into intent creation
10. Reactions toggle (interested)

PHASE 3 — PAYOFF
11. intent_boosts table + toggle endpoint
12. Smart pick algorithm + GET /circles/:id/payoff/smart
13. Spin endpoint + GET /circles/:id/payoff/spin

PHASE 4 — WEB FRONTEND
14. Next.js setup + Tailwind + Supabase auth client
15. Auth screens (login → magic link → verify)
16. Home + circle cards
17. Circle detail — intent list, filters, shortlist tab
18. Add/edit intent + live unfurl preview
19. Intent detail + react + boost
20. Payoff screen — smart pick reveal + spin animation

PHASE 5 — ANDROID + POLISH
21. Expo share-sheet — receive URL → pick circle → save
22. Empty states, error states, brand polish
23. End-to-end acceptance criteria run
```

---

## 12. Acceptance Criteria

1. New user can sign in via email magic link on web and Android.
2. User can create a circle and another user can join via invite link.
3. User can add an intent with a URL and see an auto-fetched link preview.
4. On Android, sharing a URL from another app opens Someday with the URL prefilled.
5. Members see the same intents; task_status changes and reactions sync across members.
6. Shortlist correctly shows only intents with ≥2 interested reactions.
7. Smart pick returns the highest-scored intent with a breakdown.
8. Spin returns a random shortlisted intent.
9. Boost toggles correctly influence smart pick scoring.
10. Filtering by task_status, category, and tag works.
11. Data persists across sessions and devices.
12. All endpoints log full request lifecycle — no silent paths.
