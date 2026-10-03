# Account deletion. Every write here runs inside ONE transaction
# (account_helper.delete_account_rows). status = -1 marks user-initiated removal.
#
# Deleting an account does not delete content shared with others: in circles
# that keep other members, the user's intents (and their memory photos) and
# Meanwhile posts stay at status = 1 and point at the scrubbed users row.
# Author lookups show that row as "Deleted user". Only personal signals go.

# Columns referencing public.users that deletion leaves in place on purpose.
# tests/account/test_deletion_coverage.py fails on any other unhandled column.
RETAINED_USER_COLUMNS = {
    "intents.created_by": "shared content, author shown as Deleted user",
    "moment_posts.user_id": "shared content, author shown as Deleted user",
    # A report may be evidence of harm (Google Play child safety), so it outlives
    # the reporter's account. Only the backend can read it (RLS, no policies).
    "concern_reports.user_id": "safety report, kept as possible evidence",
}

# Row lock: a second concurrent delete waits here, then finds status = -1.
LOCK_USER = """
    SELECT id FROM public.users
    WHERE id = :user_id AND status = 1
    FOR UPDATE
"""

# Circles the user owns, each with its successor: the longest-standing other
# active member. successor_id is NULL when the user is the only member.
LIST_OWNED_CIRCLES = """
    SELECT c.id AS circle_id,
           (SELECT cm.user_id
            FROM public.circle_members cm
            JOIN public.users u ON u.id = cm.user_id AND u.status = 1
            WHERE cm.circle_id = c.id AND cm.user_id <> :user_id AND cm.status = 1
            ORDER BY cm.joined_at, cm.id
            LIMIT 1) AS successor_id
    FROM public.circles c
    WHERE c.owner_id = :user_id AND c.status = 1
    FOR UPDATE OF c
"""

# ── Content of a circle that dies with its only member ──────────────────────

DELETE_CIRCLE_REACTIONS = """
    UPDATE public.reactions r SET status = -1
    FROM public.intents i
    WHERE r.intent_id = i.id AND i.circle_id = :circle_id AND r.status = 1
"""

DELETE_CIRCLE_BOOSTS = """
    UPDATE public.intent_boosts b SET status = -1
    FROM public.intents i
    WHERE b.intent_id = i.id AND i.circle_id = :circle_id AND b.status = 1
"""

DELETE_CIRCLE_NOTIFICATIONS = """
    UPDATE public.notifications n SET status = -1
    FROM public.intents i
    WHERE n.intent_id = i.id AND i.circle_id = :circle_id AND n.status = 1
"""

DELETE_CIRCLE_INTENTS = """
    UPDATE public.intents SET status = -1
    WHERE circle_id = :circle_id AND status = 1
    RETURNING done_photos
"""

DELETE_CIRCLE_MOMENT_PINGS = """
    UPDATE public.moment_pings p SET status = -1
    FROM public.circle_moments m
    WHERE p.moment_id = m.id AND m.circle_id = :circle_id AND p.status = 1
"""

DELETE_CIRCLE_MOMENT_POSTS = """
    UPDATE public.moment_posts p SET status = -1
    FROM public.circle_moments m
    WHERE p.moment_id = m.id AND m.circle_id = :circle_id AND p.status = 1
    RETURNING p.photo_url
"""

DELETE_CIRCLE_MOMENTS = """
    UPDATE public.circle_moments SET status = -1
    WHERE circle_id = :circle_id AND status = 1
"""

DELETE_CIRCLE_MEMBERS = """
    UPDATE public.circle_members SET status = -1
    WHERE circle_id = :circle_id AND status = 1
"""

DELETE_CIRCLE = """
    UPDATE public.circles SET status = -1
    WHERE id = :circle_id AND status = 1
"""

# ── The user's personal signals, in any circle ──────────────────────────────

DELETE_USER_REACTIONS = """
    UPDATE public.reactions SET status = -1
    WHERE user_id = :user_id AND status = 1
"""

DELETE_USER_BOOSTS = """
    UPDATE public.intent_boosts SET status = -1
    WHERE user_id = :user_id AND status = 1
"""

DELETE_USER_MOMENT_PINGS = """
    UPDATE public.moment_pings SET status = -1
    WHERE user_id = :user_id AND status = 1
"""

DELETE_USER_WEB_PUSH = """
    UPDATE public.web_push_subscriptions SET status = -1
    WHERE user_id = :user_id AND status = 1
"""

# Notifications FOR the user, and notifications ABOUT the user in other feeds:
# their body text carries the user's display name.
DELETE_USER_NOTIFICATIONS = """
    UPDATE public.notifications SET status = -1
    WHERE (user_id = :user_id OR actor_id = :user_id) AND status = 1
"""

DELETE_USER_MEMBERSHIPS = """
    UPDATE public.circle_members SET status = -1
    WHERE user_id = :user_id AND status = 1
"""

# email is UNIQUE NOT NULL, so it gets a per-row placeholder on a reserved TLD.
SCRUB_USER = """
    UPDATE public.users
    SET status       = -1,
        email        = 'deleted-' || CAST(id AS text) || '@deleted.invalid',
        display_name = NULL,
        avatar_url   = NULL,
        city         = NULL,
        push_token   = NULL,
        timezone     = 'UTC',
        tour_state   = '{"seen": []}'
    WHERE id = :user_id AND status = 1
"""

# Deliberately matches status = -1: guards sign-in paths against a deleted
# account whose JWT has not expired yet.
IS_DELETED_USER = """
    SELECT 1 FROM public.users WHERE id = :user_id AND status = -1
"""
