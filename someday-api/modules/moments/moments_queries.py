"""Raw SQL for the Meanwhile moments domain."""

LIST_CIRCLES_WITH_CADENCE = """
    SELECT id, moments_cadence
    FROM public.circles
    WHERE status = 1 AND moments_cadence > 0
"""

LIST_WEEK_MOMENT_DATES = """
    SELECT moment_date
    FROM public.circle_moments
    WHERE circle_id = :circle_id
      AND status = 1
      AND moment_date >= CAST(:week_start AS date)
      AND moment_date <= CAST(:week_end AS date)
"""

INSERT_MOMENT = """
    INSERT INTO public.circle_moments (circle_id, moment_date, status)
    VALUES (:circle_id, CAST(:moment_date AS date), 1)
    ON CONFLICT DO NOTHING
    RETURNING id
"""

LIST_MOMENTS_NEEDING_PINGS = """
    SELECT m.id, m.circle_id, m.moment_date
    FROM public.circle_moments m
    WHERE m.status = 1
      AND m.moment_date >= CAST(:min_date AS date)
      AND m.moment_date <= CAST(:max_date AS date)
"""

LIST_MEMBER_TIMEZONES = """
    SELECT cm.user_id, u.timezone
    FROM public.circle_members cm
    JOIN public.users u ON u.id = cm.user_id AND u.status = 1
    WHERE cm.circle_id = :circle_id AND cm.status = 1
"""

LIST_MOMENT_PING_USER_IDS = """
    SELECT user_id
    FROM public.moment_pings
    WHERE moment_id = :moment_id AND status = 1
"""

INSERT_PING = """
    INSERT INTO public.moment_pings (moment_id, user_id, ping_at, sent, status)
    VALUES (:moment_id, :user_id, CAST(:ping_at AS timestamptz), 0, 1)
    ON CONFLICT DO NOTHING
"""

LIST_DUE_PINGS = """
    SELECT
        p.id,
        p.user_id,
        p.moment_id,
        m.circle_id,
        c.name  AS circle_name,
        u.push_token
    FROM public.moment_pings p
    JOIN public.circle_moments m ON m.id = p.moment_id AND m.status = 1
    JOIN public.circles c        ON c.id = m.circle_id AND c.status = 1
    JOIN public.users u          ON u.id = p.user_id AND u.status = 1
    WHERE p.sent = 0 AND p.status = 1 AND p.ping_at <= now()
    LIMIT 500
"""

MARK_PINGS_SENT = """
    UPDATE public.moment_pings
    SET sent = 1
    WHERE id = ANY(CAST(:ping_ids AS uuid[]))
"""

GET_MOMENT_FOR_MEMBER = """
    SELECT m.id, m.circle_id, m.moment_date::text, c.name AS circle_name
    FROM public.circle_moments m
    JOIN public.circles c ON c.id = m.circle_id AND c.status = 1
    WHERE m.id = :moment_id AND m.status = 1
      AND EXISTS (
          SELECT 1 FROM public.circle_members cm
          WHERE cm.circle_id = m.circle_id AND cm.user_id = :user_id AND cm.status = 1
      )
"""

LIST_MOMENTS_FOR_CIRCLE = """
    SELECT m.id, m.circle_id, m.moment_date::text, m.created_at::text
    FROM public.circle_moments m
    WHERE m.circle_id = :circle_id
      AND m.status = 1
      AND EXISTS (
          SELECT 1 FROM public.circle_members cm
          WHERE cm.circle_id = m.circle_id AND cm.user_id = :user_id AND cm.status = 1
      )
      AND (:cursor IS NULL OR m.moment_date < CAST(:cursor AS date))
    ORDER BY m.moment_date DESC
    LIMIT :limit
"""

LIST_POSTS_FOR_MOMENTS = """
    SELECT
        p.id,
        p.moment_id,
        p.user_id,
        u.display_name,
        u.avatar_url,
        p.photo_url,
        p.caption,
        p.tz,
        p.late,
        p.created_at::text
    FROM public.moment_posts p
    JOIN public.users u ON u.id = p.user_id AND u.status = 1
    WHERE p.moment_id = ANY(CAST(:moment_ids AS uuid[]))
      AND p.status = 1
    ORDER BY p.created_at
"""

GET_MY_PING = """
    SELECT ping_at::text
    FROM public.moment_pings
    WHERE moment_id = :moment_id AND user_id = :user_id AND status = 1
"""

INSERT_POST = """
    INSERT INTO public.moment_posts (moment_id, user_id, photo_url, caption, tz, late, status)
    VALUES (:moment_id, :user_id, :photo_url, :caption, :tz, :late, 1)
    ON CONFLICT DO NOTHING
    RETURNING id, moment_id, user_id, photo_url, caption, tz, late, created_at::text
"""

GET_POST_FOR_MEMBER = """
    SELECT
        p.id,
        p.moment_id,
        p.user_id,
        p.photo_url,
        p.caption,
        u.display_name AS author_name,
        m.circle_id,
        m.moment_date::text
    FROM public.moment_posts p
    JOIN public.circle_moments m ON m.id = p.moment_id AND m.status = 1
    JOIN public.users u          ON u.id = p.user_id AND u.status = 1
    WHERE p.id = :post_id AND p.status = 1
      AND EXISTS (
          SELECT 1 FROM public.circle_members cm
          WHERE cm.circle_id = m.circle_id AND cm.user_id = :viewer_id AND cm.status = 1
      )
"""

GET_USER_TIMEZONE = """
    SELECT timezone FROM public.users WHERE id = :user_id AND status = 1
"""

UPDATE_USER_TIMEZONE = """
    UPDATE public.users
    SET timezone = :timezone
    WHERE id = :user_id AND status = 1
    RETURNING id, timezone
"""
