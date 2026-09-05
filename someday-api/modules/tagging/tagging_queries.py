"""Raw SQL for the auto-tagging domain."""

GET_INTENT_FOR_TAGGING = """
    SELECT id, circle_id, title, url, note, category, tags, link_meta
    FROM public.intents
    WHERE id = :intent_id AND status = 1
"""

# Existing tags in the circle feed the closed vocabulary so suggestions match
# what the members already use.
LIST_CIRCLE_TAG_VOCAB = """
    SELECT DISTINCT unnest(tags) AS tag
    FROM public.intents
    WHERE circle_id = :circle_id AND status = 1
    ORDER BY tag
    LIMIT 60
"""

# Guarded write: only lands if the intent still has no tags, so a user who
# edited tags while the background task ran always wins the race.
SET_AUTO_TAGS = """
    UPDATE public.intents
    SET tags = :tags, auto_tags = :tags
    WHERE id = :intent_id AND status = 1
      AND cardinality(tags) = 0
    RETURNING id, tags
"""

# Backfill driver: active intents that never got any tags.
SELECT_UNTAGGED_INTENTS = """
    SELECT id
    FROM public.intents
    WHERE status = 1
      AND cardinality(tags) = 0
    ORDER BY created_at DESC
    LIMIT :limit
"""
