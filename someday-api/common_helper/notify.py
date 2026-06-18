"""Push notification fan-out and in-app notification storage for social events."""

import json

from pywebpush import WebPushException, webpush

from app_util.db_util import DBUtil
from app_util.log_util import errorlogger, infologger
from common_helper.push_helper import send_push
from config.settings import settings
from modules.notifications.notifications_queries import INSERT_NOTIFICATION
from modules.push.push_queries import DELETE_STALE_ENDPOINT, GET_WEB_PUSH_FOR_USERS

# All circle members except the actor — includes users with and without push tokens.
CIRCLE_ALL_RECIPIENTS = """
    WITH actor AS (
        SELECT display_name FROM public.users WHERE id = :actor_id AND status = 1
    )
    SELECT
        u.id::text     AS user_id,
        u.push_token,
        actor.display_name AS actor_name,
        c.name             AS circle_name,
        i.title            AS intent_title
    FROM public.intents i
    JOIN public.circles c         ON c.id = i.circle_id AND c.status = 1
    JOIN public.circle_members cm ON cm.circle_id = i.circle_id
                                  AND cm.status = 1
                                  AND cm.user_id != :actor_id
    JOIN public.users u           ON u.id = cm.user_id AND u.status = 1
    CROSS JOIN actor
    WHERE i.id = :intent_id AND i.status = 1
"""

ALL_PUSH_TOKENS = """
    SELECT push_token FROM public.users WHERE status = 1 AND push_token IS NOT NULL
"""

# Intent creator (if different from actor) — includes even without push token.
CREATOR_RECIPIENT = """
    WITH actor AS (
        SELECT display_name FROM public.users WHERE id = :actor_id AND status = 1
    )
    SELECT
        u.id::text     AS user_id,
        u.push_token,
        actor.display_name AS actor_name,
        c.name             AS circle_name,
        i.title            AS intent_title
    FROM public.intents i
    JOIN public.circles c ON c.id = i.circle_id AND c.status = 1
    JOIN public.users u   ON u.id = i.created_by AND u.status = 1
    CROSS JOIN actor
    WHERE i.id = :intent_id AND i.status = 1 AND i.created_by != :actor_id
"""


class Notify(DBUtil):
    """Fire-and-forget push fan-out + in-app notification storage for social events."""

    def send_web_push(self, user_ids: list[str], title: str, body: str, path: str) -> None:
        if not user_ids:
            return
        rows = self.execute_query_with_value(GET_WEB_PUSH_FOR_USERS, {"user_ids": user_ids})
        for row in rows:
            try:
                webpush(
                    subscription_info={"endpoint": row["endpoint"], "keys": {"p256dh": row["p256dh"], "auth": row["auth"]}},
                    data=json.dumps({"title": title, "body": body, "url": path}),
                    vapid_private_key=settings.VAPID_PRIVATE_KEY,
                    vapid_claims={"sub": f"mailto:{settings.VAPID_CONTACT_EMAIL}"},
                )
            except WebPushException as exc:
                errorlogger.error(f"Notify.send_web_push | endpoint={row['endpoint'][:40]}… | {exc}")
                if getattr(exc, "response", None) and exc.response.status_code == 410:
                    self.execute_query_with_value_without_output(DELETE_STALE_ENDPOINT, {"endpoint": row["endpoint"]})

    def store_notification(self, user_id: str, actor_id: str, intent_id: str, notif_type: str, body: str) -> None:
        try:
            self.execute_query_with_value_without_output(
                INSERT_NOTIFICATION,
                {"user_id": user_id, "actor_id": actor_id, "intent_id": intent_id, "type": notif_type, "body": body},
            )
        except Exception as exc:
            errorlogger.error(f"Notify.store_notification | failed | user_id={user_id} | {exc}", exc_info=True)

    def intent_created(self, intent_id: str, actor_id: str) -> None:
        infologger.info(f"Notify.intent_created | intent_id={intent_id} actor_id={actor_id}")
        rows = self.execute_query_with_value(CIRCLE_ALL_RECIPIENTS, {"intent_id": intent_id, "actor_id": actor_id})
        if not rows:
            return
        r = rows[0]
        actor, title, circle = r["actor_name"], r["intent_title"], r["circle_name"]
        body = f"{actor} saved '{title}'"
        tokens = [row["push_token"] for row in rows if row.get("push_token")]
        if tokens:
            send_push(self, tokens, circle, body, f"/intents/{intent_id}")
        user_ids = [row["user_id"] for row in rows]
        self.send_web_push(user_ids, circle, body, f"/intents/{intent_id}")
        for row in rows:
            self.store_notification(row["user_id"], actor_id, intent_id, "intent_created", body)

    def reaction_added(self, intent_id: str, actor_id: str) -> None:
        infologger.info(f"Notify.reaction_added | intent_id={intent_id} actor_id={actor_id}")
        rows = self.execute_query_with_value(CREATOR_RECIPIENT, {"intent_id": intent_id, "actor_id": actor_id})
        if not rows:
            return
        r = rows[0]
        actor, title, circle = r["actor_name"], r["intent_title"], r["circle_name"]
        body = f"{actor} likes '{title}'"
        if r.get("push_token"):
            send_push(self, [r["push_token"]], circle, body, f"/intents/{intent_id}")
        self.send_web_push([r["user_id"]], circle, body, f"/intents/{intent_id}")
        self.store_notification(r["user_id"], actor_id, intent_id, "reaction_added", body)

    def boost_added(self, intent_id: str, actor_id: str) -> None:
        infologger.info(f"Notify.boost_added | intent_id={intent_id} actor_id={actor_id}")
        rows = self.execute_query_with_value(CIRCLE_ALL_RECIPIENTS, {"intent_id": intent_id, "actor_id": actor_id})
        if not rows:
            return
        r = rows[0]
        actor, title, circle = r["actor_name"], r["intent_title"], r["circle_name"]
        body = f"{actor} boosted '{title}'"
        tokens = [row["push_token"] for row in rows if row.get("push_token")]
        if tokens:
            send_push(self, tokens, circle, body, f"/intents/{intent_id}")
        user_ids = [row["user_id"] for row in rows]
        self.send_web_push(user_ids, circle, body, f"/intents/{intent_id}")
        for row in rows:
            self.store_notification(row["user_id"], actor_id, intent_id, "boost_added", body)

    def update_released(self, version: str) -> None:
        infologger.info(f"Notify.update_released | version={version}")
        rows = self.execute_query_with_value(ALL_PUSH_TOKENS, {})
        if not rows:
            return
        tokens = [r["push_token"] for r in rows]
        send_push(self, tokens, f"Someday v{version} is ready", "Quick install, no link needed.", "/")
