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
        i.auto_tags,
        i.task_status,
        i.link_meta,
        i.planned_for,
        i.done_note,
        i.done_photos,
        i.created_at::text,
        i.updated_at::text,
        COUNT(DISTINCT r.user_id) FILTER (WHERE r.status = 1) AS reaction_count,
        MAX(CASE WHEN b.user_id = :user_id AND b.status = 1 THEN 1 ELSE 0 END) AS boosted_by_me,
        MAX(CASE WHEN r.user_id = :user_id AND r.status = 1 THEN 1 ELSE 0 END) AS reacted_by_me
    FROM public.intents i
    LEFT JOIN public.reactions r ON r.intent_id = i.id
    LEFT JOIN public.intent_boosts b ON b.intent_id = i.id
    WHERE i.circle_id = :circle_id
      AND i.status = 1
      AND (:task_status  IS NULL OR i.task_status = :task_status)
      AND (:category     IS NULL OR i.category    = :category)
      AND (:tag          IS NULL OR :tag = ANY(i.tags))
      AND (:cursor       IS NULL OR i.created_at < CAST(:cursor AS timestamptz))
    GROUP BY i.id
    ORDER BY i.created_at DESC
    LIMIT :limit
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
        i.auto_tags,
        i.task_status,
        i.link_meta,
        i.planned_for,
        i.done_note,
        i.done_photos,
        i.created_at::text,
        i.updated_at::text,
        COUNT(DISTINCT r.user_id) FILTER (WHERE r.status = 1) AS reaction_count,
        MAX(CASE WHEN b.user_id = :user_id AND b.status = 1 THEN 1 ELSE 0 END) AS boosted_by_me,
        MAX(CASE WHEN r.user_id = :user_id AND r.status = 1 THEN 1 ELSE 0 END) AS reacted_by_me
    FROM public.intents i
    LEFT JOIN public.reactions r ON r.intent_id = i.id AND r.kind = 'interested' AND r.status = 1
    LEFT JOIN public.intent_boosts b ON b.intent_id = i.id
    WHERE i.circle_id   = :circle_id
      AND i.status      = 1
      AND i.task_status NOT IN ('done', 'archived')
      AND (:cursor       IS NULL OR i.created_at < CAST(:cursor AS timestamptz))
    GROUP BY i.id
    HAVING COUNT(DISTINCT r.user_id) FILTER (WHERE r.status = 1) >= 2
    ORDER BY i.created_at DESC
    LIMIT :limit
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
        i.auto_tags,
        i.task_status,
        i.link_meta,
        i.planned_for,
        i.done_note,
        i.done_photos,
        i.created_at::text,
        i.updated_at::text,
        COUNT(DISTINCT r.user_id) FILTER (WHERE r.status = 1) AS reaction_count,
        MAX(CASE WHEN b.user_id = :user_id AND b.status = 1 THEN 1 ELSE 0 END) AS boosted_by_me,
        MAX(CASE WHEN r.user_id = :user_id AND r.status = 1 THEN 1 ELSE 0 END) AS reacted_by_me
    FROM public.intents i
    LEFT JOIN public.reactions r ON r.intent_id = i.id
    LEFT JOIN public.intent_boosts b ON b.intent_id = i.id
    WHERE i.id = :intent_id AND i.status = 1
      AND EXISTS (
          SELECT 1 FROM public.circle_members cm
          WHERE cm.circle_id = i.circle_id AND cm.user_id = :user_id AND cm.status = 1
      )
    GROUP BY i.id
"""

INSERT_INTENT = """
    INSERT INTO public.intents
        (circle_id, created_by, title, url, note, category, tags, link_meta, status)
    SELECT :circle_id, :created_by, :title, :url, :note, :category, :tags, CAST(:link_meta AS jsonb), 1
    WHERE EXISTS (
        SELECT 1 FROM public.circle_members cm
        WHERE cm.circle_id = :circle_id AND cm.user_id = :created_by AND cm.status = 1
    )
    RETURNING
        id, circle_id, created_by, title, url, note, category, tags, auto_tags,
        task_status, link_meta, planned_for, done_note, done_photos,
        created_at::text, updated_at::text
"""

UPDATE_INTENT = """
    UPDATE public.intents SET
        title       = COALESCE(:title,       title),
        url         = COALESCE(:url,         url),
        note        = COALESCE(:note,        note),
        category    = COALESCE(:category,    category),
        tags        = COALESCE(:tags, tags),
        -- A manual tag edit takes ownership: suggestions still present in the
        -- new list count as accepted, so provenance is cleared either way.
        auto_tags   = CASE WHEN :tags IS NULL THEN auto_tags ELSE '{}' END,
        task_status  = COALESCE(:task_status, task_status),
        planned_for  = COALESCE(:planned_for, planned_for),
        done_note    = COALESCE(:done_note, done_note),
        done_photos  = COALESCE(CAST(:done_photos AS jsonb), done_photos)
    WHERE id = :intent_id AND status = 1
    RETURNING
        id, circle_id, created_by, title, url, note, category, tags, auto_tags,
        task_status, link_meta, planned_for, done_note, done_photos,
        created_at::text, updated_at::text
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

GET_INTENT_URL = """
    SELECT id, url FROM public.intents
    WHERE id = :intent_id AND status = 1
"""

UPDATE_INTENT_META = """
    UPDATE public.intents
    SET link_meta = CAST(:link_meta AS jsonb)
    WHERE id = :intent_id AND status = 1
    RETURNING id, link_meta
"""

# One-off backfill: active intents whose preview image is still a remote URL
# (not yet re-hosted into our own storage).
SELECT_INTENTS_WITH_REMOTE_PREVIEW = """
    SELECT id, url, link_meta
    FROM public.intents
    WHERE status = 1
      AND link_meta IS NOT NULL
      AND link_meta->>'image' IS NOT NULL
      AND link_meta->>'image' NOT LIKE :rehosted_prefix
    ORDER BY created_at DESC
"""

# In two-person circles the adder auto-hearts their own save -
# the other member's single heart is then enough to shortlist it.
AUTO_REACT_IF_COUPLE = """
    INSERT INTO public.reactions (intent_id, user_id, kind, status)
    SELECT :intent_id, :user_id, 'interested', 1
    WHERE (
        SELECT COUNT(*) FROM public.circle_members
        WHERE circle_id = :circle_id AND status = 1
    ) <= 2
    ON CONFLICT DO NOTHING
    RETURNING id
"""
