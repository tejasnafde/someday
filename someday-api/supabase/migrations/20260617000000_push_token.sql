-- One push token per user (ponytail: multi-device when someone asks)
ALTER TABLE public.users ADD COLUMN IF NOT EXISTS push_token text;
CREATE INDEX IF NOT EXISTS idx_users_push_token
  ON public.users(push_token) WHERE push_token IS NOT NULL;
