-- Auto-tagging provenance: which of an intent's tags were machine-generated.
-- auto_tags is always a subset of tags. The web UI renders these as
-- "suggested" chips until the user edits tags (any manual tag edit clears
-- auto_tags - the user has taken ownership of the tag list).
ALTER TABLE public.intents
    ADD COLUMN IF NOT EXISTS auto_tags text[] NOT NULL DEFAULT '{}';
