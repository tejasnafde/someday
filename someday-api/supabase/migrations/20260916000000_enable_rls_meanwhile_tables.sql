-- Enable RLS on the three Meanwhile tables. They were added by
-- 20260907000000_meanwhile.sql and missed it, so Supabase's security advisor
-- flagged them on 2026-09-13 and it was exploitable, not theoretical.
--
-- The anon key is published on purpose: someday-app/app.json ships it and the
-- web bundle contains it. Verified against production before this fix, a plain
-- PostgREST call with that key returned real rows from all three tables, while
-- the same call against notifications and users correctly returned []. anon
-- also held INSERT, UPDATE, DELETE and TRUNCATE on all three, so the advisor's
-- wording was accurate: read, edit and delete, not just read.
--
-- No policies are created, deliberately. Nothing client-side queries these
-- tables through supabase-js - there is no supabase.from(...) call anywhere in
-- someday-web or someday-app. All access goes through the FastAPI backend,
-- which connects as the `postgres` role (rolbypassrls = true) and is therefore
-- unaffected by RLS. RLS enabled with zero policies denies anon and
-- authenticated everything, which is exactly the intent.
--
-- This is the SECOND time new tables shipped without RLS; 20260729000000 fixed
-- notifications and web_push_subscriptions for the same reason. A comment
-- asking the next author to remember has now failed once. See the RLS coverage
-- test that accompanies this migration - that is the part meant to stop a third
-- occurrence.
--
-- If a client ever needs direct access, add a policy here rather than turning
-- RLS back off.

ALTER TABLE public.circle_moments ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.moment_pings   ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.moment_posts   ENABLE ROW LEVEL SECURITY;
