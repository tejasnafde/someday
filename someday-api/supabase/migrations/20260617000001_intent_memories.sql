-- Memory capture: note + photos attached when marking an intent done
ALTER TABLE public.intents
  ADD COLUMN IF NOT EXISTS done_note   text,
  ADD COLUMN IF NOT EXISTS done_photos jsonb DEFAULT '[]'::jsonb;

-- Storage bucket for memory photos (public, no RLS needed)
INSERT INTO storage.buckets (id, name, public)
VALUES ('memories', 'memories', true)
ON CONFLICT DO NOTHING;
