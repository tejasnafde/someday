-- Meanwhile: synchronized circle moments for long-distance circles.
-- A cron draws N random moment days per circle per week; each member gets a
-- push at a random minute inside their local waking hours on that day. Posts
-- reveal to a member once they post, and to everyone after the day ends.

ALTER TABLE public.users
    ADD COLUMN IF NOT EXISTS timezone text NOT NULL DEFAULT 'UTC';

-- Existing circles stay off (0) - the feature is opt-in for them.
-- New circles default to 2 moments a week.
ALTER TABLE public.circles
    ADD COLUMN IF NOT EXISTS moments_cadence integer NOT NULL DEFAULT 0;
ALTER TABLE public.circles
    ALTER COLUMN moments_cadence SET DEFAULT 2;

CREATE TABLE IF NOT EXISTS public.circle_moments (
    id          uuid        PRIMARY KEY DEFAULT gen_random_uuid(),
    circle_id   uuid        NOT NULL REFERENCES public.circles(id),
    moment_date date        NOT NULL,
    status      integer     NOT NULL DEFAULT 1,
    created_at  timestamptz NOT NULL DEFAULT now()
);
CREATE UNIQUE INDEX IF NOT EXISTS idx_circle_moments_unique
    ON public.circle_moments (circle_id, moment_date);
CREATE INDEX IF NOT EXISTS idx_circle_moments_list
    ON public.circle_moments (circle_id, moment_date DESC);

CREATE TABLE IF NOT EXISTS public.moment_pings (
    id         uuid        PRIMARY KEY DEFAULT gen_random_uuid(),
    moment_id  uuid        NOT NULL REFERENCES public.circle_moments(id),
    user_id    uuid        NOT NULL REFERENCES public.users(id),
    ping_at    timestamptz NOT NULL,
    sent       integer     NOT NULL DEFAULT 0,
    status     integer     NOT NULL DEFAULT 1,
    created_at timestamptz NOT NULL DEFAULT now()
);
CREATE UNIQUE INDEX IF NOT EXISTS idx_moment_pings_unique
    ON public.moment_pings (moment_id, user_id);
CREATE INDEX IF NOT EXISTS idx_moment_pings_due
    ON public.moment_pings (ping_at) WHERE sent = 0 AND status = 1;

CREATE TABLE IF NOT EXISTS public.moment_posts (
    id         uuid        PRIMARY KEY DEFAULT gen_random_uuid(),
    moment_id  uuid        NOT NULL REFERENCES public.circle_moments(id),
    user_id    uuid        NOT NULL REFERENCES public.users(id),
    photo_url  text        NOT NULL,
    caption    text,
    tz         text        NOT NULL,
    late       boolean     NOT NULL DEFAULT false,
    status     integer     NOT NULL DEFAULT 1,
    created_at timestamptz NOT NULL DEFAULT now()
);
CREATE UNIQUE INDEX IF NOT EXISTS idx_moment_posts_unique
    ON public.moment_posts (moment_id, user_id);

-- Moment photos. Public bucket, uploads via service key - same as memories.
INSERT INTO storage.buckets (id, name, public)
VALUES ('moments', 'moments', true)
ON CONFLICT DO NOTHING;
