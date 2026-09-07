-- City is user-declared, never derived. Deriving it from the IANA timezone
-- labeled every Indian user "Calcutta" (India is one timezone). Optional
-- profile field, snapshotted onto each moment post at post time.
ALTER TABLE public.users
    ADD COLUMN IF NOT EXISTS city text;
ALTER TABLE public.moment_posts
    ADD COLUMN IF NOT EXISTS city text;
