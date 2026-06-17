"""Push notification fan-out for social events."""

from app_util.db_util import DBUtil
from app_util.log_util import infologger
from common_helper.push_helper import send_push

# Everyone in the intent's circle except the actor, plus actor name / circle name / intent title.
CIRCLE_PUSH_TARGETS = """
    WITH actor AS (
        SELECT display_name FROM public.users WHERE id = :actor_id AND status = 1
    )
    SELECT
        u.push_token,
        actor.display_name AS actor_name,
        c.name             AS circle_name,
        i.title            AS intent_title
    FROM public.intents i
    JOIN public.circles c         ON c.id = i.circle_id AND c.status = 1
    JOIN public.circle_members cm ON cm.circle_id = i.circle_id
                                  AND cm.status = 1
                                  AND cm.user_id != :actor_id
    JOIN public.users u           ON u.id = cm.user_id
                                  AND u.status = 1
                                  AND u.push_token IS NOT NULL
    CROSS JOIN actor
    WHERE i.id = :intent_id AND i.status = 1
"""

# Just the intent creator (if different from actor).
CREATOR_PUSH_TARGET = """
    WITH actor AS (
        SELECT display_name FROM public.users WHERE id = :actor_id AND status = 1
    )
    SELECT
        u.push_token,
        actor.display_name AS actor_name,
        c.name             AS circle_name,
        i.title            AS intent_title
    FROM public.intents i
    JOIN public.circles c ON c.id = i.circle_id AND c.status = 1
    JOIN public.users u   ON u.id = i.created_by
                          AND u.status = 1
                          AND u.push_token IS NOT NULL
    CROSS JOIN actor
    WHERE i.id = :intent_id AND i.status = 1 AND i.created_by != :actor_id
"""


class Notify(DBUtil):
    """Fire-and-forget push fan-out. Methods are designed for FastAPI BackgroundTasks."""

    def intent_created(self, intent_id: str, actor_id: str) -> None:
        infologger.info(f"Notify.intent_created | intent_id={intent_id} actor_id={actor_id}")
        rows = self.execute_query_with_value(CIRCLE_PUSH_TARGETS, {"intent_id": intent_id, "actor_id": actor_id})
        if not rows:
            return
        r = rows[0]
        actor, title, circle = r["actor_name"], r["intent_title"], r["circle_name"]
        tokens = [row["push_token"] for row in rows]
        send_push(self, tokens, circle, f"{actor} saved '{title}'", f"/intents/{intent_id}")

    def reaction_added(self, intent_id: str, actor_id: str) -> None:
        infologger.info(f"Notify.reaction_added | intent_id={intent_id} actor_id={actor_id}")
        rows = self.execute_query_with_value(CREATOR_PUSH_TARGET, {"intent_id": intent_id, "actor_id": actor_id})
        if not rows:
            return
        r = rows[0]
        actor, title, circle = r["actor_name"], r["intent_title"], r["circle_name"]
        send_push(self, [r["push_token"]], circle, f"{actor} likes '{title}'", f"/intents/{intent_id}")

    def boost_added(self, intent_id: str, actor_id: str) -> None:
        infologger.info(f"Notify.boost_added | intent_id={intent_id} actor_id={actor_id}")
        rows = self.execute_query_with_value(CIRCLE_PUSH_TARGETS, {"intent_id": intent_id, "actor_id": actor_id})
        if not rows:
            return
        r = rows[0]
        actor, title, circle = r["actor_name"], r["intent_title"], r["circle_name"]
        tokens = [row["push_token"] for row in rows]
        send_push(self, tokens, circle, f"{actor} boosted '{title}'", f"/intents/{intent_id}")
