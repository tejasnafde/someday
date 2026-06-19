import json

from app_util.log_util import infologger, errorlogger
from modules.intents import intents_queries as q

DEFAULT_PAGE_SIZE = 50


def list_intents(
    db,
    circle_id: str,
    user_id: str,
    task_status: str | None = None,
    category: str | None = None,
    tag: str | None = None,
    shortlist: bool = False,
    cursor: str | None = None,
    limit: int = DEFAULT_PAGE_SIZE,
) -> dict:
    """Returns {items: [...], next_cursor: str | None}."""
    infologger.info(
        f"intents_helper.list_intents | circle_id={circle_id} "
        f"task_status={task_status} category={category} tag={tag} "
        f"shortlist={shortlist} cursor={cursor!r} limit={limit}"
    )
    params = {"circle_id": circle_id, "user_id": user_id, "cursor": cursor, "limit": limit}
    if shortlist:
        items = db.execute_query_with_value(q.LIST_INTENTS_SHORTLIST, params)
    else:
        items = db.execute_query_with_value(
            q.LIST_INTENTS,
            {**params, "task_status": task_status, "category": category, "tag": tag},
        )
    next_cursor = items[-1]["created_at"] if len(items) == limit else None
    return {"items": items, "next_cursor": next_cursor}


def get_intent(db, intent_id: str, user_id: str) -> dict | None:
    """Returns the intent if found AND the user is a member of its circle, else None."""
    infologger.info(f"intents_helper.get_intent | intent_id={intent_id}")
    rows = db.execute_query_with_value(q.GET_INTENT_BY_ID, {"intent_id": intent_id, "user_id": user_id})
    if not rows:
        infologger.warning(f"intents_helper.get_intent | not found or not a member | intent_id={intent_id}")
        return None
    return rows[0]


def create_intent(
    db,
    circle_id: str,
    user_id: str,
    title: str,
    url: str | None,
    note: str | None,
    category: str | None,
    tags: list[str],
    link_meta: dict | None,
) -> dict | None:
    infologger.info(
        f"intents_helper.create_intent | circle_id={circle_id} "
        f"user_id={user_id} title={title!r}"
    )
    row = db.execute_query_with_value_returning(
        q.INSERT_INTENT,
        {
            "circle_id":  circle_id,
            "created_by": user_id,
            "title":      title,
            "url":        url,
            "note":       note,
            "category":   category,
            "tags":       tags,
            "link_meta":  json.dumps(link_meta) if link_meta else None,
        },
    )
    if not row:
        # Membership gate in INSERT_INTENT returned nothing — caller is not a member
        infologger.warning(f"intents_helper.create_intent | not a member | circle_id={circle_id} user_id={user_id}")
        return None
    reacted = db.execute_query_with_value_returning(
        q.AUTO_REACT_IF_COUPLE,
        {"intent_id": row["id"], "user_id": user_id, "circle_id": circle_id},
    )
    row["reaction_count"] = 1 if reacted else 0
    row["boosted_by_me"]  = False
    row["reacted_by_me"]  = bool(reacted)
    if reacted:
        infologger.info(f"intents_helper.create_intent | auto-hearted (couple circle) | intent_id={row['id']}")
    infologger.info(f"intents_helper.create_intent | created intent_id={row['id']}")
    return row


def update_intent(db, intent_id: str, updates: dict) -> dict | None:
    infologger.info(f"intents_helper.update_intent | intent_id={intent_id} fields={list(updates)}")
    # Serialize done_photos list → JSON string for CAST(:done_photos AS jsonb)
    if isinstance(updates.get("done_photos"), list):
        updates = {**updates, "done_photos": json.dumps(updates["done_photos"])}
    # SQLAlchemy text() requires every named param present even when NULL.
    # COALESCE(NULL, col) = existing value, so missing fields are preserved.
    params = {
        "intent_id":   intent_id,
        "title":       None,
        "url":         None,
        "note":        None,
        "category":    None,
        "tags":        None,
        "task_status": None,
        "planned_for": None,
        "done_note":   None,
        "done_photos": None,
        **updates,
    }
    row = db.execute_query_with_value_returning(q.UPDATE_INTENT, params)
    if not row:
        infologger.warning(f"intents_helper.update_intent | not found | intent_id={intent_id}")
    return row or None


def delete_intent(db, intent_id: str) -> None:
    infologger.info(f"intents_helper.delete_intent | intent_id={intent_id}")
    db.execute_query_with_value_without_output(q.SOFT_DELETE_INTENT, {"intent_id": intent_id})


def toggle_reaction(db, intent_id: str, user_id: str, kind: str = "interested") -> bool:
    """Returns True if reaction was added, False if removed."""
    infologger.info(f"intents_helper.toggle_reaction | intent_id={intent_id} user_id={user_id} kind={kind}")
    existing = db.execute_query_with_value(
        q.GET_REACTION, {"intent_id": intent_id, "user_id": user_id, "kind": kind}
    )
    if existing:
        db.execute_query_with_value_without_output(
            q.REMOVE_REACTION, {"intent_id": intent_id, "user_id": user_id, "kind": kind}
        )
        infologger.info(f"intents_helper.toggle_reaction | removed | intent_id={intent_id}")
        return False
    db.execute_query_with_value_without_output(
        q.INSERT_REACTION, {"intent_id": intent_id, "user_id": user_id, "kind": kind}
    )
    infologger.info(f"intents_helper.toggle_reaction | added | intent_id={intent_id}")
    return True


def toggle_boost(db, intent_id: str, user_id: str) -> bool:
    """Returns True if boost was added, False if removed."""
    infologger.info(f"intents_helper.toggle_boost | intent_id={intent_id} user_id={user_id}")
    existing = db.execute_query_with_value(
        q.GET_BOOST, {"intent_id": intent_id, "user_id": user_id}
    )
    if existing:
        db.execute_query_with_value_without_output(
            q.REMOVE_BOOST, {"intent_id": intent_id, "user_id": user_id}
        )
        infologger.info(f"intents_helper.toggle_boost | removed | intent_id={intent_id}")
        return False
    db.execute_query_with_value_without_output(
        q.INSERT_BOOST, {"intent_id": intent_id, "user_id": user_id}
    )
    infologger.info(f"intents_helper.toggle_boost | added | intent_id={intent_id}")
    return True


def refresh_preview(db, intent_id: str, fetch_meta) -> dict | None:
    """Re-run unfurl for an existing intent's URL and store the result."""
    infologger.info(f"intents_helper.refresh_preview | intent_id={intent_id}")
    rows = db.execute_query_with_value(q.GET_INTENT_URL, {"intent_id": intent_id})
    if not rows or not rows[0].get("url"):
        infologger.warning(f"intents_helper.refresh_preview | no url | intent_id={intent_id}")
        return None
    meta = fetch_meta(rows[0]["url"])
    if not meta:
        return None
    return db.execute_query_with_value_returning(
        q.UPDATE_INTENT_META,
        {"intent_id": intent_id, "link_meta": json.dumps(meta)},
    )
