-- In-app notification history: social events stored per-recipient
CREATE TABLE IF NOT EXISTS public.notifications (
    id          uuid        DEFAULT gen_random_uuid() PRIMARY KEY,
    user_id     uuid        REFERENCES public.users(id),
    actor_id    uuid        REFERENCES public.users(id),
    intent_id   uuid        REFERENCES public.intents(id),
    type        text        NOT NULL,
    body        text        NOT NULL,
    seen        boolean     DEFAULT false,
    created_at  timestamptz DEFAULT now(),
    status      integer     DEFAULT 1
);

CREATE INDEX IF NOT EXISTS idx_notifications_user
    ON public.notifications(user_id, created_at DESC)
    WHERE status = 1;
