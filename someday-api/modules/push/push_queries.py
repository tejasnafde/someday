UPSERT_WEB_PUSH_SUBSCRIPTION = """
    INSERT INTO public.web_push_subscriptions (user_id, endpoint, p256dh, auth)
    VALUES (:user_id, :endpoint, :p256dh, :auth)
    ON CONFLICT (user_id, endpoint) WHERE status = 1
    DO UPDATE SET p256dh = EXCLUDED.p256dh, auth = EXCLUDED.auth
"""

DELETE_WEB_PUSH_SUBSCRIPTION = """
    UPDATE public.web_push_subscriptions
    SET status = 0
    WHERE user_id = :user_id AND endpoint = :endpoint AND status = 1
"""

GET_WEB_PUSH_FOR_USERS = """
    SELECT user_id::text, endpoint, p256dh, auth
    FROM public.web_push_subscriptions
    WHERE user_id = ANY(CAST(:user_ids AS uuid[]))
    AND status = 1
"""

DELETE_STALE_ENDPOINT = """
    UPDATE public.web_push_subscriptions SET status = 0 WHERE endpoint = :endpoint
"""
