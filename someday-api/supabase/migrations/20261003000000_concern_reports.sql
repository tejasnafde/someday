-- Report a concern: Settings > Report a concern. Google Play's child safety
-- standards require an in-app way to report, and tn07.dev/child-safety/ points
-- users here. Rows are kept when the reporter deletes their account, because a
-- report may be evidence (see RETAINED_USER_COLUMNS in account_queries.py).

CREATE TABLE IF NOT EXISTS public.concern_reports (
    id         uuid        PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id    uuid        NOT NULL REFERENCES public.users(id),
    category   text        NOT NULL CHECK (category IN ('child_safety', 'abuse', 'other')),
    subject    text,
    body       text        NOT NULL,
    status     integer     NOT NULL DEFAULT 1,
    created_at timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_concern_reports_created
    ON public.concern_reports (created_at DESC);

-- No policies: only the backend (postgres role, bypasses RLS) reads or writes.
ALTER TABLE public.concern_reports ENABLE ROW LEVEL SECURITY;
