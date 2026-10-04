import json
import time
from collections import defaultdict

import httpx
import jwt

from app_util.log_util import errorlogger, infologger
from common_helper.storage_helper import delete_objects, storage_path
from common_helper.url_util import safe_client
from config.settings import settings
from modules.account import account_queries as q
from modules.circles import circles_queries as cq

AVATAR_EXTENSIONS = ("webp", "jpg", "png")


def photo_urls(rows: list[dict], key: str) -> list[str]:
    """Flatten photo URLs out of RETURNING rows (done_photos is a jsonb list, photo_url a string)."""
    urls = []
    for row in rows:
        value = row.get(key)
        if isinstance(value, list):
            urls.extend(value)
        elif value:
            urls.append(value)
    return urls


def delete_account_rows(db, user_id: str) -> dict | None:
    """Soft-delete the account in ONE transaction. Content shared in circles
    that keep other members stays. Returns what to clean up
    after commit ({"files": {bucket: [paths]}, ...}), or None if the user is
    not active."""
    infologger.info(f"account_helper.delete_account_rows | user_id={user_id}")
    p = {"user_id": user_id}
    urls: list[str] = []
    files: dict[str, list[str]] = defaultdict(list)
    transferred, deleted_circles = [], []

    with db.transaction() as conn:
        if not db.tx_query(conn, q.LOCK_USER, p):
            infologger.warning(f"account_helper.delete_account_rows | no active user | user_id={user_id}")
            return None

        for circle in db.tx_query(conn, q.LIST_OWNED_CIRCLES, p):
            circle_id, successor_id = circle["circle_id"], circle["successor_id"]
            c = {"circle_id": circle_id}
            if successor_id:
                infologger.info(
                    f"account_helper.delete_account_rows | transfer | circle_id={circle_id} new_owner={successor_id}"
                )
                db.tx_exec(conn, cq.SET_CIRCLE_OWNER, {**c, "new_owner_id": successor_id})
                db.tx_exec(conn, cq.SET_MEMBER_ROLE, {**c, "target_user_id": successor_id, "role": "owner"})
                transferred.append(circle_id)
                continue
            infologger.info(f"account_helper.delete_account_rows | sole member, deleting circle | circle_id={circle_id}")
            db.tx_exec(conn, q.DELETE_CIRCLE_REACTIONS, c)
            db.tx_exec(conn, q.DELETE_CIRCLE_BOOSTS, c)
            db.tx_exec(conn, q.DELETE_CIRCLE_NOTIFICATIONS, c)
            urls += photo_urls(db.tx_query(conn, q.DELETE_CIRCLE_INTENTS, c), "done_photos")
            db.tx_exec(conn, q.DELETE_CIRCLE_MOMENT_PINGS, c)
            urls += photo_urls(db.tx_query(conn, q.DELETE_CIRCLE_MOMENT_POSTS, c), "photo_url")
            db.tx_exec(conn, q.DELETE_CIRCLE_MOMENTS, c)
            db.tx_exec(conn, q.DELETE_CIRCLE_MEMBERS, c)
            db.tx_exec(conn, q.DELETE_CIRCLE, c)
            files["circle-photos"].append(circle_id)
            deleted_circles.append(circle_id)

        # Intents and Meanwhile posts in circles that live on stay, and so do their photos.
        db.tx_exec(conn, q.DELETE_USER_REACTIONS, p)
        db.tx_exec(conn, q.DELETE_USER_BOOSTS, p)
        db.tx_exec(conn, q.DELETE_USER_MOMENT_PINGS, p)
        db.tx_exec(conn, q.DELETE_USER_WEB_PUSH, p)
        db.tx_exec(conn, q.DELETE_USER_NOTIFICATIONS, p)
        db.tx_exec(conn, q.DELETE_USER_MEMBERSHIPS, p)
        db.tx_exec(conn, q.SCRUB_USER, p)

    for url in urls:
        parsed = storage_path(url)
        if parsed:
            files[parsed[0]].append(parsed[1])
    # Upload paths are deterministic per user; deleting all three covers any extension.
    files["avatars"] += [f"{user_id}.{ext}" for ext in AVATAR_EXTENSIONS]
    infologger.info(
        f"account_helper.delete_account_rows | committed | user_id={user_id} "
        f"transferred={len(transferred)} deleted_circles={len(deleted_circles)} "
        f"files={sum(len(v) for v in files.values())}"
    )
    return {"files": dict(files), "transferred": transferred, "deleted_circles": deleted_circles}


def delete_auth_user(user_id: str) -> bool:
    """Soft-delete the Supabase auth user so the person cannot sign in again.

    Soft, not hard: public.users.id references auth.users ON DELETE CASCADE,
    and the soft-deleted rows that still reference public.users (intents,
    circle_members, ...) would block that cascade. A GoTrue soft delete
    obfuscates the email, removes identities and revokes sessions.

    Apple token revocation is separate, see revoke_apple_tokens."""
    if not settings.SUPABASE_SERVICE_ROLE_KEY:
        errorlogger.error(f"account_helper.delete_auth_user | SUPABASE_SERVICE_ROLE_KEY not configured | user_id={user_id}")
        return False
    try:
        resp = httpx.request(
            "DELETE",
            f"{settings.SUPABASE_URL}/auth/v1/admin/users/{user_id}",
            headers={
                "apikey": settings.SUPABASE_SERVICE_ROLE_KEY,
                "Authorization": f"Bearer {settings.SUPABASE_SERVICE_ROLE_KEY}",
            },
            json={"should_soft_delete": True},
            timeout=15,
        )
        resp.raise_for_status()
        infologger.info(f"account_helper.delete_auth_user | ok | user_id={user_id}")
        return True
    except httpx.HTTPError as exc:
        errorlogger.error(f"account_helper.delete_auth_user | failed | user_id={user_id} | {exc}", exc_info=True)
        return False


def is_apple_user(claims: dict) -> bool:
    """True when Supabase lists Apple among the user's sign-in providers. Read
    from the verified JWT's app_metadata, which Supabase writes, never from a
    client claim."""
    providers = (claims.get("app_metadata") or {}).get("providers") or []
    return "apple" in providers


def apple_client_secret(key: dict, now: int | None = None) -> str:
    """The short-lived ES256 client_secret JWT Apple's token and revoke endpoints require."""
    now = int(time.time()) if now is None else now
    return jwt.encode(
        {
            "iss": key["team_id"],
            "iat": now,
            "exp": now + settings.APPLE_CLIENT_SECRET_TTL_SECONDS,
            "aud": settings.APPLE_AUDIENCE,
            "sub": key["client_id"],
        },
        key["p8"],
        algorithm="ES256",
        headers={"kid": key["key_id"]},
    )


def revoke_apple_tokens(user_id: str, authorization_code: str) -> bool:
    """Exchange a fresh Sign in with Apple authorizationCode for a refresh
    token, then revoke it. Apple requires this on account deletion. Supabase
    keeps no Apple token for a native sign-in, hence the fresh code. Logs and
    returns False on any failure: the caller must not block deletion on it."""
    infologger.info(f"account_helper.revoke_apple_tokens | user_id={user_id}")
    if not settings.SOMEDAY_SIWA_KEY:
        errorlogger.error(f"account_helper.revoke_apple_tokens | SOMEDAY_SIWA_KEY not configured | user_id={user_id}")
        return False
    try:
        key = json.loads(settings.SOMEDAY_SIWA_KEY)
        form = {"client_id": key["client_id"], "client_secret": apple_client_secret(key)}
        # Fixed Apple URLs from settings, not user input; the safe client is still the house rule.
        with safe_client(timeout=10) as client:
            resp = client.post(
                settings.APPLE_TOKEN_URL,
                data={**form, "code": authorization_code, "grant_type": "authorization_code"},
            )
            resp.raise_for_status()
            refresh_token = resp.json()["refresh_token"]
            resp = client.post(
                settings.APPLE_REVOKE_URL,
                data={**form, "token": refresh_token, "token_type_hint": "refresh_token"},
            )
            resp.raise_for_status()
        infologger.info(f"account_helper.revoke_apple_tokens | ok | user_id={user_id}")
        return True
    except httpx.HTTPStatusError as exc:
        # Apple's body names the cause (invalid_grant, invalid_client); the status alone does not.
        errorlogger.error(
            f"account_helper.revoke_apple_tokens | failed | user_id={user_id} | {exc} | {exc.response.text[:300]}"
        )
        return False
    except Exception as exc:
        errorlogger.error(f"account_helper.revoke_apple_tokens | failed | user_id={user_id} | {exc}", exc_info=True)
        return False


def delete_files(user_id: str, files: dict[str, list[str]]) -> None:
    infologger.info(f"account_helper.delete_files | user_id={user_id} buckets={sorted(files)}")
    for bucket, paths in files.items():
        delete_objects(bucket, paths)


def is_deleted_user(db, user_id: str) -> bool:
    return bool(db.execute_query_with_value(q.IS_DELETED_USER, {"user_id": user_id}))
