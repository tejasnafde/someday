from app_util.log_util import infologger
from modules.notifications import notifications_queries as q


def get_notifications(db, user_id: str) -> dict:
    infologger.info(f"notifications_helper.get_notifications | user_id={user_id}")
    items = db.execute_query_with_value(q.GET_NOTIFICATIONS, {"user_id": user_id})
    count_rows = db.execute_query_with_value(q.GET_UNSEEN_COUNT, {"user_id": user_id})
    unseen = int(count_rows[0]["unseen"]) if count_rows else 0
    return {"unseen": unseen, "items": items}


def mark_all_seen(db, user_id: str) -> None:
    infologger.info(f"notifications_helper.mark_all_seen | user_id={user_id}")
    db.execute_query_with_value_without_output(q.MARK_ALL_SEEN, {"user_id": user_id})
