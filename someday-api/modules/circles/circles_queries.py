"""Raw SQL for the circles domain."""

GET_MY_CIRCLES = """
    SELECT
        c.id,
        c.name,
        c.emoji,
        c.owner_id,
        c.invite_token,
        c.created_at::text,
        COUNT(DISTINCT all_cm.user_id)                            AS member_count,
        COUNT(DISTINCT i.id)       FILTER (WHERE i.status = 1
                                           AND i.task_status NOT IN ('done','archived'))
                                                                  AS open_intent_count
    FROM public.circles c
    JOIN public.circle_members cm ON cm.circle_id = c.id
         AND cm.user_id = :user_id AND cm.status = 1
    LEFT JOIN public.circle_members all_cm ON all_cm.circle_id = c.id AND all_cm.status = 1
    LEFT JOIN public.intents i ON i.circle_id = c.id
    WHERE c.status = 1
    GROUP BY c.id
    ORDER BY c.created_at DESC
"""

GET_CIRCLE_BY_ID = """
    SELECT
        c.id,
        c.name,
        c.emoji,
        c.owner_id,
        c.invite_token,
        c.created_at::text,
        COUNT(DISTINCT cm_all.user_id) FILTER (WHERE cm_all.status = 1) AS member_count,
        COUNT(DISTINCT i.id) FILTER (WHERE i.status = 1
                                     AND i.task_status NOT IN ('done','archived'))
                                                                         AS open_intent_count
    FROM public.circles c
    JOIN public.circle_members cm_me  ON cm_me.circle_id = c.id
         AND cm_me.user_id = :user_id AND cm_me.status = 1
    LEFT JOIN public.circle_members cm_all ON cm_all.circle_id = c.id
    LEFT JOIN public.intents i ON i.circle_id = c.id
    WHERE c.id = :circle_id AND c.status = 1
    GROUP BY c.id
"""

GET_CIRCLE_MEMBERS = """
    SELECT
        cm.user_id,
        cm.role,
        cm.joined_at::text,
        u.email,
        u.display_name,
        u.avatar_url
    FROM public.circle_members cm
    JOIN public.users u ON u.id = cm.user_id AND u.status = 1
    WHERE cm.circle_id = :circle_id AND cm.status = 1
    ORDER BY cm.joined_at
"""

INSERT_CIRCLE = """
    INSERT INTO public.circles (id, name, emoji, owner_id, invite_token, status)
    VALUES (gen_random_uuid(), :name, :emoji, :owner_id,
            encode(gen_random_bytes(16), 'hex'), 1)
    RETURNING id, name, emoji, owner_id, invite_token, created_at::text
"""

INSERT_CIRCLE_MEMBER = """
    INSERT INTO public.circle_members (circle_id, user_id, role, status)
    VALUES (:circle_id, :user_id, :role, 1)
    ON CONFLICT DO NOTHING
"""

UPDATE_CIRCLE = """
    UPDATE public.circles
    SET name  = COALESCE(:name,  name),
        emoji = COALESCE(:emoji, emoji)
    WHERE id = :circle_id AND owner_id = :user_id AND status = 1
    RETURNING id, name, emoji, owner_id, invite_token, created_at::text
"""

SOFT_DELETE_CIRCLE = """
    UPDATE public.circles
    SET status = 0
    WHERE id = :circle_id AND owner_id = :user_id AND status = 1
"""

GET_CIRCLE_BY_INVITE_TOKEN = """
    SELECT id, name, emoji, owner_id, status
    FROM public.circles
    WHERE invite_token = :token AND status = 1
"""

LEAVE_CIRCLE = """
    UPDATE public.circle_members
    SET status = 0
    WHERE circle_id = :circle_id AND user_id = :user_id AND status = 1
"""

IS_MEMBER = """
    SELECT 1
    FROM public.circle_members
    WHERE circle_id = :circle_id AND user_id = :user_id AND status = 1
"""

# ── Member management (admin role + remove + transfer ownership) ────────────

GET_MEMBER_ROLE = """
    SELECT role FROM public.circle_members
    WHERE circle_id = :circle_id AND user_id = :user_id AND status = 1
"""

SET_MEMBER_ROLE = """
    UPDATE public.circle_members
    SET role = :role
    WHERE circle_id = :circle_id AND user_id = :target_user_id AND status = 1
    RETURNING user_id, role
"""

REMOVE_MEMBER = """
    UPDATE public.circle_members
    SET status = 0
    WHERE circle_id = :circle_id AND user_id = :target_user_id AND status = 1
"""

SET_CIRCLE_OWNER = """
    UPDATE public.circles
    SET owner_id = :new_owner_id
    WHERE id = :circle_id AND status = 1
"""

# Tag chips for the circle filter: unique tags across all active intents.
LIST_CIRCLE_TAGS = """
    SELECT DISTINCT unnest(tags) AS tag
    FROM public.intents
    WHERE circle_id = :circle_id AND status = 1 AND array_length(tags, 1) > 0
    ORDER BY tag
"""

# Rotate the invite token - owner-only, returns new token.
ROTATE_INVITE_TOKEN = """
    UPDATE public.circles
    SET invite_token = encode(gen_random_bytes(16), 'hex')
    WHERE id = :circle_id AND owner_id = :user_id AND status = 1
    RETURNING id, invite_token
"""
