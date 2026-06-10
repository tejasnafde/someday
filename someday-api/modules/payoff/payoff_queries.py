"""
Raw SQL for the payoff domain.

SMART_PICK score formula (100 pts max):
  mutual_ratio  = (interested reactions / member count) × 40
  save_age      = min(days_since_saved / 30, 1.0)       × 20
  boost_bonus   = any active boost exists?               × 40

Tiebreaker: most recently reacted to.
Only shortlisted intents (≥ 2 interested reactions) are eligible.
Membership gate + member count are inlined — one round trip per endpoint.
"""

SMART_PICK = """
    WITH mc AS (
        SELECT COUNT(*)::float AS n
        FROM public.circle_members
        WHERE circle_id = :circle_id AND status = 1
    )
    SELECT
        i.id                                                             AS intent_id,
        i.title,
        i.link_meta,
        COUNT(DISTINCT r.user_id)  FILTER (WHERE r.status = 1)          AS reaction_count,
        COUNT(DISTINCT r.user_id)::float / NULLIF((SELECT n FROM mc), 0) AS mutual_ratio,
        EXTRACT(EPOCH FROM (now() - i.created_at)) / 86400.0            AS days_saved,
        MAX(CASE WHEN b.status = 1 THEN 1 ELSE 0 END)                   AS has_boost,

        (COUNT(DISTINCT r.user_id)::float / NULLIF((SELECT n FROM mc), 0) * 40.0)
        + (LEAST(EXTRACT(EPOCH FROM (now() - i.created_at)) / 86400.0 / 30.0, 1.0) * 20.0)
        + (MAX(CASE WHEN b.status = 1 THEN 1 ELSE 0 END) * 40.0)        AS score,

        MAX(r.created_at)                                                AS last_reacted_at

    FROM public.intents i
    LEFT JOIN public.reactions r
           ON r.intent_id = i.id AND r.kind = 'interested' AND r.status = 1
    LEFT JOIN public.intent_boosts b
           ON b.intent_id = i.id AND b.status = 1
    WHERE i.circle_id   = :circle_id
      AND i.status      = 1
      AND i.task_status NOT IN ('done', 'archived')
      AND EXISTS (
          SELECT 1 FROM public.circle_members cm
          WHERE cm.circle_id = :circle_id AND cm.user_id = :user_id AND cm.status = 1
      )
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
      AND EXISTS (
          SELECT 1 FROM public.circle_members cm
          WHERE cm.circle_id = :circle_id AND cm.user_id = :user_id AND cm.status = 1
      )
    GROUP BY i.id
    HAVING COUNT(DISTINCT r.user_id) FILTER (WHERE r.status = 1) >= 2
"""
