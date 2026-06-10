"""Raw SQL for the intents domain."""

LIST_INTENTS = """
    SELECT
        i.id,
        i.circle_id,
        i.created_by,
        i.title,
        i.url,
        i.note,
        i.category,
        i.tags,
        i.task_status,
        i.link_meta,
        i.planned_for,
        i.created_at::text,
        i.updated_at::text,
        COUNT(DISTINCT r.user_id) FILTER (WHERE r.status = 1) AS reaction_count,
        MAX(CASE WHEN b.user_id = :user_id AND b.status = 1 THEN 1 ELSE 0 END) AS boosted_by_me
    FROM public.intents i
    LEFT JOIN public.reactions r ON r.intent_id = i.id
    LEFT JOIN public.intent_boosts b ON b.intent_id = i.id
    WHERE i.circle_id = :circle_id
      AND i.status = 1
      AND (:task_status  IS NULL OR i.task_status = :task_status)
      AND (:category     IS NULL OR i.category    = :category)
    GROUP BY i.id
    ORDER BY i.created_at DESC
"""

# Shortlist: intents with ≥ 2 distinct interested reactions
LIST_INTENTS_SHORTLIST = """
    SELECT
        i.id,
        i.circle_id,
        i.created_by,
        i.title,
        i.url,
        i.note,
        i.category,
        i.tags,
        i.task_status,
        i.link_meta,
        i.planned_for,
        i.created_at::text,
        i.updated_at::text,
        COUNT(DISTINCT r.user_id) FILTER (WHERE r.status = 1) AS reaction_count,
        MAX(CASE WHEN b.user_id = :user_id AND b.status = 1 THEN 1 ELSE 0 END) AS boosted_by_me
    FROM public.intents i
    LEFT JOIN public.reactions r ON r.intent_id = i.id AND r.kind = 'interested' AND r.status = 1
    LEFT JOIN public.intent_boosts b ON b.intent_id = i.id
    WHERE i.circle_id   = :circle_id
      AND i.status      = 1
      AND i.task_status NOT IN ('done', 'archived')
    GROUP BY i.id
    HAVING COUNT(DISTINCT r.user_id) FILTER (WHERE r.status = 1) >= 2
    ORDER BY i.created_at DESC
"""

GET_INTENT_BY_ID = """
    SELECT
        i.id,
        i.circle_id,
        i.created_by,
        i.title,
        i.url,
        i.note,
        i.category,
        i.tags,
        i.task_status,
        i.link_meta,
        i.planned_for,
        i.created_at::text,
        i.updated_at::text,
        COUNT(DISTINCT r.user_id) FILTER (WHERE r.status = 1) AS reaction_count,
        MAX(CASE WHEN b.user_id = :user_id AND b.status = 1 THEN 1 ELSE 0 END) AS boosted_by_me
    FROM public.intents i
    LEFT JOIN public.reactions r ON r.intent_id = i.id
    LEFT JOIN public.intent_boosts b ON b.intent_id = i.id
    WHERE i.id = :intent_id AND i.status = 1
    GROUP BY i.id
"""

INSERT_INTENT = """
    INSERT INTO public.intents
        (circle_id, created_by, title, url, note, category, tags, link_meta, status)
    VALUES
        (:circle_id, :created_by, :title, :url, :note, :category, :tags::text[], :link_meta::jsonb, 1)
    RETURNING
        id, circle_id, created_by, title, url, note, category, tags,
        task_status, link_meta, planned_for, created_at::text, updated_at::text
"""

UPDATE_INTENT = """
    UPDATE public.intents SET
        title       = COALESCE(:title,       title),
        url         = COALESCE(:url,         url),
        note        = COALESCE(:note,        note),
        category    = COALESCE(:category,    category),
        tags        = COALESCE(:tags::text[], tags),
        task_status = COALESCE(:task_status, task_status),
        planned_for = COALESCE(:planned_for, planned_for)
    WHERE id = :intent_id AND status = 1
    RETURNING
        id, circle_id, created_by, title, url, note, category, tags,
        task_status, link_meta, planned_for, created_at::text, updated_at::text
"""

SOFT_DELETE_INTENT = """
    UPDATE public.intents
    SET status = 0
    WHERE id = :intent_id AND status = 1
"""

# Reactions: toggle (upsert / soft-delete)
GET_REACTION = """
    SELECT id FROM public.reactions
    WHERE intent_id = :intent_id AND user_id = :user_id AND kind = :kind AND status = 1
"""

INSERT_REACTION = """
    INSERT INTO public.reactions (intent_id, user_id, kind, status)
    VALUES (:intent_id, :user_id, :kind, 1)
    ON CONFLICT DO NOTHING
"""

REMOVE_REACTION = """
    UPDATE public.reactions
    SET status = 0
    WHERE intent_id = :intent_id AND user_id = :user_id AND kind = :kind AND status = 1
"""

# Boosts: toggle (upsert / soft-delete)
GET_BOOST = """
    SELECT id FROM public.intent_boosts
    WHERE intent_id = :intent_id AND user_id = :user_id AND status = 1
"""

INSERT_BOOST = """
    INSERT INTO public.intent_boosts (intent_id, user_id, status)
    VALUES (:intent_id, :user_id, 1)
    ON CONFLICT DO NOTHING
"""

REMOVE_BOOST = """
    UPDATE public.intent_boosts
    SET status = 0
    WHERE intent_id = :intent_id AND user_id = :user_id AND status = 1
"""
