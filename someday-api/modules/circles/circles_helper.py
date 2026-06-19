from app_util.log_util import infologger, errorlogger
from modules.circles import circles_queries as q


def get_my_circles(db, user_id: str) -> list[dict]:
    infologger.info(f"circles_helper.get_my_circles | user_id={user_id}")
    return db.execute_query_with_value(q.GET_MY_CIRCLES, {"user_id": user_id})


def get_circle_with_members(db, circle_id: str, user_id: str) -> dict | None:
    infologger.info(f"circles_helper.get_circle_with_members | circle_id={circle_id} user_id={user_id}")
    rows = db.execute_query_with_value(q.GET_CIRCLE_BY_ID, {"circle_id": circle_id, "user_id": user_id})
    if not rows:
        infologger.warning(f"circles_helper.get_circle_with_members | not found or not a member | circle_id={circle_id}")
        return None
    circle = rows[0]
    circle["members"] = db.execute_query_with_value(q.GET_CIRCLE_MEMBERS, {"circle_id": circle_id})
    return circle


def create_circle(db, name: str, emoji: str | None, owner_id: str) -> dict:
    """Create a circle and add the owner as a member in a single transaction."""
    infologger.info(f"circles_helper.create_circle | owner_id={owner_id} name={name!r}")
    with db.transaction() as conn:
        circle = db.tx_exec_returning(
            conn, q.INSERT_CIRCLE,
            {"name": name, "emoji": emoji, "owner_id": owner_id},
        )
        db.tx_exec(
            conn, q.INSERT_CIRCLE_MEMBER,
            {"circle_id": circle["id"], "user_id": owner_id, "role": "owner"},
        )
    circle["member_count"] = 1
    circle["open_intent_count"] = 0
    infologger.info(f"circles_helper.create_circle | created circle_id={circle['id']}")
    return circle


def update_circle(db, circle_id: str, user_id: str, name: str | None, emoji: str | None) -> dict | None:
    infologger.info(f"circles_helper.update_circle | circle_id={circle_id} user_id={user_id}")
    row = db.execute_query_with_value_returning(
        q.UPDATE_CIRCLE,
        {"circle_id": circle_id, "user_id": user_id, "name": name, "emoji": emoji},
    )
    if not row:
        infologger.warning(f"circles_helper.update_circle | not found or not owner | circle_id={circle_id}")
    return row or None


def delete_circle(db, circle_id: str, user_id: str) -> bool:
    infologger.info(f"circles_helper.delete_circle | circle_id={circle_id} user_id={user_id}")
    db.execute_query_with_value_without_output(
        q.SOFT_DELETE_CIRCLE,
        {"circle_id": circle_id, "user_id": user_id},
    )
    return True


def join_circle_by_token(db, token: str, user_id: str) -> dict | None:
    infologger.info(f"circles_helper.join_circle_by_token | user_id={user_id} token={token[:8]}…")
    rows = db.execute_query_with_value(q.GET_CIRCLE_BY_INVITE_TOKEN, {"token": token})
    if not rows:
        infologger.warning(f"circles_helper.join_circle_by_token | invalid token")
        return None
    circle = rows[0]
    db.execute_query_with_value_without_output(
        q.INSERT_CIRCLE_MEMBER,
        {"circle_id": circle["id"], "user_id": user_id, "role": "member"},
    )
    infologger.info(f"circles_helper.join_circle_by_token | joined circle_id={circle['id']}")
    return circle


def leave_circle(db, circle_id: str, user_id: str) -> None:
    infologger.info(f"circles_helper.leave_circle | circle_id={circle_id} user_id={user_id}")
    db.execute_query_with_value_without_output(
        q.LEAVE_CIRCLE,
        {"circle_id": circle_id, "user_id": user_id},
    )


def assert_member(db, circle_id: str, user_id: str) -> bool:
    """Returns True if user is an active member; raises ValueError otherwise."""
    rows = db.execute_query_with_value(q.IS_MEMBER, {"circle_id": circle_id, "user_id": user_id})
    if not rows:
        raise ValueError(f"user {user_id} is not a member of circle {circle_id}")
    return True


def get_member_role(db, circle_id: str, user_id: str) -> str | None:
    rows = db.execute_query_with_value(q.GET_MEMBER_ROLE, {"circle_id": circle_id, "user_id": user_id})
    return rows[0]["role"] if rows else None


def can_manage_members(role: str | None) -> bool:
    return role in {"owner", "admin"}


def set_member_role(db, circle_id: str, target_user_id: str, role: str) -> dict | None:
    infologger.info(f"circles_helper.set_member_role | circle_id={circle_id} target={target_user_id} role={role}")
    return db.execute_query_with_value_returning(
        q.SET_MEMBER_ROLE, {"circle_id": circle_id, "target_user_id": target_user_id, "role": role}
    ) or None


def transfer_ownership(db, circle_id: str, actor_id: str, target_id: str) -> None:
    """Transfer ownership atomically: update circle.owner_id + both member roles in one transaction."""
    infologger.info(f"circles_helper.transfer_ownership | circle_id={circle_id} actor={actor_id} target={target_id}")
    with db.transaction() as conn:
        db.tx_exec(conn, q.SET_CIRCLE_OWNER, {"circle_id": circle_id, "new_owner_id": target_id})
        db.tx_exec(conn, q.SET_MEMBER_ROLE, {"circle_id": circle_id, "target_user_id": target_id, "role": "owner"})
        db.tx_exec(conn, q.SET_MEMBER_ROLE, {"circle_id": circle_id, "target_user_id": actor_id, "role": "admin"})


def remove_member(db, circle_id: str, target_user_id: str) -> None:
    infologger.info(f"circles_helper.remove_member | circle_id={circle_id} target={target_user_id}")
    db.execute_query_with_value_without_output(
        q.REMOVE_MEMBER, {"circle_id": circle_id, "target_user_id": target_user_id}
    )


def set_owner(db, circle_id: str, new_owner_id: str) -> None:
    infologger.info(f"circles_helper.set_owner | circle_id={circle_id} new_owner={new_owner_id}")
    db.execute_query_with_value_without_output(
        q.SET_CIRCLE_OWNER, {"circle_id": circle_id, "new_owner_id": new_owner_id}
    )


def list_tags(db, circle_id: str) -> list[str]:
    rows = db.execute_query_with_value(q.LIST_CIRCLE_TAGS, {"circle_id": circle_id})
    return [r["tag"] for r in rows]


def rotate_invite_token(db, circle_id: str, user_id: str) -> dict | None:
    """Generate a new invite token (owner-only). Returns {id, invite_token} or None."""
    infologger.info(f"circles_helper.rotate_invite_token | circle_id={circle_id} user_id={user_id}")
    row = db.execute_query_with_value_returning(
        q.ROTATE_INVITE_TOKEN, {"circle_id": circle_id, "user_id": user_id}
    )
    if not row:
        infologger.warning(f"circles_helper.rotate_invite_token | not owner or not found | circle_id={circle_id}")
    return row or None
