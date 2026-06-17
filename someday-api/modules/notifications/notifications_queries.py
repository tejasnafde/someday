GET_NOTIFICATIONS = """
    SELECT
        n.id::text,
        n.type,
        n.body,
        n.seen,
        n.intent_id::text,
        n.created_at::text
    FROM public.notifications n
    WHERE n.user_id = :user_id AND n.status = 1
    ORDER BY n.created_at DESC
    LIMIT 30
"""

GET_UNSEEN_COUNT = """
    SELECT COUNT(*) AS unseen
    FROM public.notifications
    WHERE user_id = :user_id AND seen = false AND status = 1
"""

INSERT_NOTIFICATION = """
    INSERT INTO public.notifications (user_id, actor_id, intent_id, type, body)
    VALUES (:user_id, :actor_id, :intent_id, :type, :body)
"""

MARK_ALL_SEEN = """
    UPDATE public.notifications
    SET seen = true
    WHERE user_id = :user_id AND status = 1
"""
