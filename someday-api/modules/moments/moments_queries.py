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
      -- Never list future moments: the week is drawn upfront and listing
      -- them would publish the schedule, killing the surprise.
      AND m.moment_date <= CAST(:max_date AS date)
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
        p.city,
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
    INSERT INTO public.moment_posts (moment_id, user_id, photo_url, caption, tz, city, late, status)
    VALUES (:moment_id, :user_id, :photo_url, :caption, :tz, :city, :late, 1)
    ON CONFLICT DO NOTHING
    RETURNING id, moment_id, user_id, photo_url, caption, tz, city, late, created_at::text
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
    SELECT timezone, city FROM public.users WHERE id = :user_id AND status = 1
"""

# Pending pings whose window was computed with the user's OLD timezone. Fetched
# on timezone change so each can be re-windowed in the new zone.
LIST_UNSENT_PINGS_FOR_USER = """
    SELECT p.id, m.moment_date::text
    FROM public.moment_pings p
    JOIN public.circle_moments m ON m.id = p.moment_id AND m.status = 1
    WHERE p.user_id = :user_id
      AND p.sent = 0
      AND p.status = 1
      AND m.moment_date >= CAST(:min_date AS date)
"""

UPDATE_PING_TIME = """
    UPDATE public.moment_pings
    SET ping_at = CAST(:ping_at AS timestamptz)
    WHERE id = :ping_id AND sent = 0 AND status = 1
"""

UPDATE_USER_CITY = """
    UPDATE public.users
    SET city = :city
    WHERE id = :user_id AND status = 1
"""

UPDATE_USER_TIMEZONE = """
    UPDATE public.users
    SET timezone = :timezone
    WHERE id = :user_id AND status = 1
    RETURNING id, timezone
"""
