CREATE TABLE public.web_push_subscriptions (
    id         uuid        DEFAULT gen_random_uuid() PRIMARY KEY,
    user_id    uuid        NOT NULL REFERENCES public.users(id),
    endpoint   text        NOT NULL,
    p256dh     text        NOT NULL,
    auth       text        NOT NULL,
    status     integer     NOT NULL DEFAULT 1,
    created_at timestamptz DEFAULT now()
);

CREATE UNIQUE INDEX web_push_subs_user_endpoint
    ON public.web_push_subscriptions(user_id, endpoint)
    WHERE status = 1;

CREATE INDEX web_push_subs_user_id
    ON public.web_push_subscriptions(user_id)
    WHERE status = 1;
