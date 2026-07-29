-- Enable RLS on the two tables that were added after the initial schema and
-- missed it. Supabase's security advisor flagged both as publicly accessible,
-- and it was exploitable: the anon key is published in someday-app/app.json and
-- in the web bundle, and a plain PostgREST call with it could read every row of
-- notifications and web_push_subscriptions, and insert into them.
--
-- No policies are created, deliberately. Nothing client-side ever queries these
-- tables through supabase-js - all access goes through the FastAPI backend,
-- which connects as the `postgres` role (rolbypassrls = true) and is therefore
-- unaffected by RLS. RLS enabled with zero policies means anon and
-- authenticated are denied everything, which is exactly the intent.
--
-- If a client ever needs direct access, add a policy here rather than turning
-- RLS back off.

ALTER TABLE public.notifications           ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.web_push_subscriptions  ENABLE ROW LEVEL SECURITY;
