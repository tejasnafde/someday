import json

import httpx

from app_util.log_util import infologger
from config.settings import settings

EVENT_SURFACES = {
    "auth_account_verified": "auth",
    "circle_created": "circles",
    "item_created": "items",
    "activation_milestone_reached": "items",
}


def track_product_event(event: str, surface: str) -> None:
    if settings.APP_ENV != "production":
        return
    if EVENT_SURFACES.get(event) != surface:
        infologger.warning(
            f"product analytics rejected unknown event | event={event} surface={surface}"
        )
        return
    payload = {
        "event": event,
        "event_version": 1,
        "product": "someday",
        "surface": surface,
        "environment": "production",
        "authority": "server",
        "platform": "server",
        "properties": {},
    }
    try:
        httpx.post(
            "https://analytics.tn07.dev/v1/events",
            headers={
                "Content-Type": "application/json",
                "Origin": "https://someday.tn07.dev",
            },
            content=json.dumps(payload),
            timeout=3,
        )
    except httpx.HTTPError as exc:
        infologger.warning(
            f"product analytics delivery failed | event={event} error={type(exc).__name__}"
        )
