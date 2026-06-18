-- Per-user onboarding tour progress. seen = flat array of tour step ids;
-- the web client's tour registry decides which steps are new.
ALTER TABLE public.users
  ADD COLUMN IF NOT EXISTS tour_state jsonb NOT NULL DEFAULT '{"seen": []}';
