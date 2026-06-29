-- ─────────────────────────────────────────────────────────────────────────────
-- Someday - initial schema
-- Run in Supabase SQL editor (dev project first, then prod).
--
-- Status convention (every table):
--   1  = active (all queries filter WHERE status = 1)
--   0  = soft-deleted / hidden from UI
--  -1  = user-initiated deletion
--
-- Intent workflow state is task_status on the intents table.
-- The column `status` is always the soft-delete flag.
-- ─────────────────────────────────────────────────────────────────────────────

-- Extensions
CREATE EXTENSION IF NOT EXISTS "pgcrypto";


-- ── users ────────────────────────────────────────────────────────────────────
-- Mirrors auth.users - extended with display name / avatar.
CREATE TABLE IF NOT EXISTS public.users (
    id           uuid        PRIMARY KEY REFERENCES auth.users(id) ON DELETE CASCADE,
    email        text        UNIQUE NOT NULL,
    display_name text,
    avatar_url   text,
    status       integer     NOT NULL DEFAULT 1,
    created_at   timestamptz NOT NULL DEFAULT now()
);


-- ── circles ──────────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS public.circles (
    id           uuid        PRIMARY KEY DEFAULT gen_random_uuid(),
    name         text        NOT NULL,
    emoji        text,
    owner_id     uuid        NOT NULL REFERENCES public.users(id),
    invite_token text        UNIQUE NOT NULL DEFAULT encode(gen_random_bytes(16), 'hex'),
    status       integer     NOT NULL DEFAULT 1,
    created_at   timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_circles_owner
    ON public.circles(owner_id) WHERE status = 1;


-- ── circle_members ────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS public.circle_members (
    id         uuid        PRIMARY KEY DEFAULT gen_random_uuid(),
    circle_id  uuid        NOT NULL REFERENCES public.circles(id) ON DELETE CASCADE,
    user_id    uuid        NOT NULL REFERENCES public.users(id),
    role       text        NOT NULL DEFAULT 'member',  -- 'owner' | 'member'
    status     integer     NOT NULL DEFAULT 1,
    joined_at  timestamptz NOT NULL DEFAULT now()
);

-- Enforce one active membership per user per circle at DB level
CREATE UNIQUE INDEX IF NOT EXISTS idx_circle_members_unique
    ON public.circle_members(circle_id, user_id) WHERE status = 1;

CREATE INDEX IF NOT EXISTS idx_circle_members_user
    ON public.circle_members(user_id) WHERE status = 1;

CREATE INDEX IF NOT EXISTS idx_circle_members_circle
    ON public.circle_members(circle_id) WHERE status = 1;


-- ── intents ───────────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS public.intents (
    id           uuid        PRIMARY KEY DEFAULT gen_random_uuid(),
    circle_id    uuid        NOT NULL REFERENCES public.circles(id) ON DELETE CASCADE,
    created_by   uuid        NOT NULL REFERENCES public.users(id),
    title        text        NOT NULL,
    url          text,
    note         text,
    category     text,        -- watch|eat|visit|read|play|trip|other
    tags         text[]      NOT NULL DEFAULT '{}',
    task_status  text        NOT NULL DEFAULT 'saved',
                              -- saved|interested|planned|done|archived
    link_meta    jsonb,       -- {title, image, site} from unfurl
    planned_for  text,        -- loose free-text date (optional)
    status       integer     NOT NULL DEFAULT 1,
    created_at   timestamptz NOT NULL DEFAULT now(),
    updated_at   timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_intents_circle_status
    ON public.intents(circle_id, task_status) WHERE status = 1;

CREATE INDEX IF NOT EXISTS idx_intents_created_at
    ON public.intents(created_at);

-- Auto-update updated_at on any row change
CREATE OR REPLACE FUNCTION public.set_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = now();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS intents_set_updated_at ON public.intents;
CREATE TRIGGER intents_set_updated_at
    BEFORE UPDATE ON public.intents
    FOR EACH ROW EXECUTE FUNCTION public.set_updated_at();


-- ── reactions ─────────────────────────────────────────────────────────────────
-- Shortlist = intents with ≥ 2 distinct 'interested' reactions (status = 1).
CREATE TABLE IF NOT EXISTS public.reactions (
    id         uuid        PRIMARY KEY DEFAULT gen_random_uuid(),
    intent_id  uuid        NOT NULL REFERENCES public.intents(id) ON DELETE CASCADE,
    user_id    uuid        NOT NULL REFERENCES public.users(id),
    kind       text        NOT NULL DEFAULT 'interested',
    status     integer     NOT NULL DEFAULT 1,
    created_at timestamptz NOT NULL DEFAULT now()
);

CREATE UNIQUE INDEX IF NOT EXISTS idx_reactions_unique
    ON public.reactions(intent_id, user_id, kind) WHERE status = 1;

CREATE INDEX IF NOT EXISTS idx_reactions_intent
    ON public.reactions(intent_id) WHERE status = 1;


-- ── intent_boosts ─────────────────────────────────────────────────────────────
-- "I really want this today" signal. Toggleable, one per member per intent.
-- Feeds into smart-pick algorithm (+40 points if any boost exists).
CREATE TABLE IF NOT EXISTS public.intent_boosts (
    id         uuid        PRIMARY KEY DEFAULT gen_random_uuid(),
    intent_id  uuid        NOT NULL REFERENCES public.intents(id) ON DELETE CASCADE,
    user_id    uuid        NOT NULL REFERENCES public.users(id),
    status     integer     NOT NULL DEFAULT 1,
    created_at timestamptz NOT NULL DEFAULT now()
);

CREATE UNIQUE INDEX IF NOT EXISTS idx_boosts_unique
    ON public.intent_boosts(intent_id, user_id) WHERE status = 1;

CREATE INDEX IF NOT EXISTS idx_boosts_intent
    ON public.intent_boosts(intent_id) WHERE status = 1;


-- ─────────────────────────────────────────────────────────────────────────────
-- Row Level Security
-- FastAPI handles authorisation - RLS is a defence-in-depth layer only.
-- All tables: authenticated users can only read rows they have membership for.
-- ─────────────────────────────────────────────────────────────────────────────

ALTER TABLE public.users          ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.circles        ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.circle_members ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.intents        ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.reactions      ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.intent_boosts  ENABLE ROW LEVEL SECURITY;

-- Service role bypasses RLS (FastAPI uses service role key for all DB ops)
-- These policies are a fallback for direct dashboard queries / future client use.

CREATE POLICY "users: read own row"
    ON public.users FOR SELECT
    USING (auth.uid() = id);

CREATE POLICY "users: insert own row"
    ON public.users FOR INSERT
    WITH CHECK (auth.uid() = id);

CREATE POLICY "users: update own row"
    ON public.users FOR UPDATE
    USING (auth.uid() = id);

CREATE POLICY "circles: members can read"
    ON public.circles FOR SELECT
    USING (
        status = 1 AND
        EXISTS (
            SELECT 1 FROM public.circle_members cm
            WHERE cm.circle_id = id AND cm.user_id = auth.uid() AND cm.status = 1
        )
    );

CREATE POLICY "circle_members: members can read"
    ON public.circle_members FOR SELECT
    USING (
        status = 1 AND
        EXISTS (
            SELECT 1 FROM public.circle_members cm2
            WHERE cm2.circle_id = circle_id AND cm2.user_id = auth.uid() AND cm2.status = 1
        )
    );

CREATE POLICY "intents: circle members can read"
    ON public.intents FOR SELECT
    USING (
        status = 1 AND
        EXISTS (
            SELECT 1 FROM public.circle_members cm
            WHERE cm.circle_id = intents.circle_id AND cm.user_id = auth.uid() AND cm.status = 1
        )
    );

CREATE POLICY "reactions: circle members can read"
    ON public.reactions FOR SELECT
    USING (
        status = 1 AND
        EXISTS (
            SELECT 1 FROM public.intents i
            JOIN public.circle_members cm ON cm.circle_id = i.circle_id
            WHERE i.id = reactions.intent_id AND cm.user_id = auth.uid() AND cm.status = 1
        )
    );

CREATE POLICY "intent_boosts: circle members can read"
    ON public.intent_boosts FOR SELECT
    USING (
        status = 1 AND
        EXISTS (
            SELECT 1 FROM public.intents i
            JOIN public.circle_members cm ON cm.circle_id = i.circle_id
            WHERE i.id = intent_boosts.intent_id AND cm.user_id = auth.uid() AND cm.status = 1
        )
    );
