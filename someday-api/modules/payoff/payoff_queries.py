"""
Smart-pick scoring query.

Score formula (100 pts max):
  mutual_ratio  = (interested reactions / member count) × 40
  save_age      = min(days_since_saved / 30, 1.0)       × 20
  boost_bonus   = any active boost exists?               × 40

Tiebreaker: most recently reacted to.
Only shortlisted intents (≥ 2 interested reactions) are eligible.
"""

SMART_PICK = """
    SELECT
        i.id                                                             AS intent_id,
        i.title,
        i.link_meta,
        COUNT(DISTINCT r.user_id)  FILTER (WHERE r.status = 1)          AS reaction_count,
        COUNT(DISTINCT r.user_id)::float
            / NULLIF(:member_count, 0)                                   AS mutual_ratio,
        EXTRACT(EPOCH FROM (now() - i.created_at)) / 86400.0            AS days_saved,
        MAX(CASE WHEN b.status = 1 THEN 1 ELSE 0 END)                   AS has_boost,

        -- final score
        (COUNT(DISTINCT r.user_id)::float / NULLIF(:member_count, 0) * 40.0)
        + (LEAST(EXTRACT(EPOCH FROM (now() - i.created_at)) / 86400.0 / 30.0, 1.0) * 20.0)
        + (MAX(CASE WHEN b.status = 1 THEN 1 ELSE 0 END) * 40.0)        AS score,

        -- tiebreaker: most recent reaction timestamp
        MAX(r.created_at)                                                AS last_reacted_at

    FROM public.intents i
    LEFT JOIN public.reactions r
           ON r.intent_id = i.id AND r.kind = 'interested' AND r.status = 1
    LEFT JOIN public.intent_boosts b
           ON b.intent_id = i.id AND b.status = 1
    WHERE i.circle_id   = :circle_id
      AND i.status      = 1
      AND i.task_status NOT IN ('done', 'archived')
    GROUP BY i.id, i.title, i.link_meta, i.created_at
    HAVING COUNT(DISTINCT r.user_id) FILTER (WHERE r.status = 1) >= 2
    ORDER BY score DESC, last_reacted_at DESC NULLS LAST
    LIMIT 1
"""

SHORTLIST_FOR_SPIN = """
    SELECT
        i.id,
        i.title,
        i.link_meta,
        i.category,
        COUNT(DISTINCT r.user_id) FILTER (WHERE r.status = 1) AS reaction_count
    FROM public.intents i
    LEFT JOIN public.reactions r
           ON r.intent_id = i.id AND r.kind = 'interested' AND r.status = 1
    WHERE i.circle_id   = :circle_id
      AND i.status      = 1
      AND i.task_status NOT IN ('done', 'archived')
    GROUP BY i.id
    HAVING COUNT(DISTINCT r.user_id) FILTER (WHERE r.status = 1) >= 2
"""

GET_MEMBER_COUNT = """
    SELECT COUNT(*) AS cnt
    FROM public.circle_members
    WHERE circle_id = :circle_id AND status = 1
"""
