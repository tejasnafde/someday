"""Expo push fan-out. One HTTP call per batch, dead tokens cleaned up inline."""

import httpx

from app_util.log_util import errorlogger, infologger

EXPO_PUSH = "https://exp.host/--/api/v2/push/send"

CLEAR_DEAD_TOKEN = """
    UPDATE public.users SET push_token = NULL WHERE push_token = :t
"""


def send_push(db, tokens: list[str], title: str, body: str, path: str) -> None:
    """Fire push to a batch. Removes any token Expo reports as DeviceNotRegistered."""
    if not tokens:
        return
    msgs = [{"to": t, "title": title, "body": body, "data": {"path": path}, "sound": "default"} for t in tokens]
    try:
        r = httpx.post(EXPO_PUSH, json=msgs, timeout=10)
        r.raise_for_status()
        for token, item in zip(tokens, r.json().get("data", [])):
            if item.get("status") == "error" and item.get("details", {}).get("error") == "DeviceNotRegistered":
                db.execute_query_with_value_without_output(CLEAR_DEAD_TOKEN, {"t": token})
                infologger.warning(f"push.cleanup | dead token removed | {token[:18]}…")
        infologger.info(f"push.send | {len(tokens)} sent | {title!r} | {body[:60]!r}")
    except Exception as exc:
        errorlogger.error(f"push.send | failed | {exc}", exc_info=True)
