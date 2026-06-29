"""Fire-and-forget Discord alerts for 4xx/5xx errors."""

import asyncio
import traceback
from datetime import datetime, timezone

import httpx

from app_util.log_util import errorlogger
from config.settings import settings


async def _post(embed: dict) -> None:
    try:
        async with httpx.AsyncClient(timeout=5) as client:
            await client.post(
                settings.DISCORD_WEBHOOK_URL,
                json={"username": "Someday API", "embeds": [embed]},
            )
    except Exception as exc:
        errorlogger.error(f"discord_alert | delivery failed | {exc}")


async def send_build_alert(build_id: str, status: str, log_url: str, commit: str) -> None:
    """Alert on a failed Cloud Build deploy. A failed revision does not migrate traffic,
    so without this a bad deploy silently sits behind the previous (stale) revision."""
    if not settings.DISCORD_WEBHOOK_URL:
        return
    env_label = "🔴 PROD" if settings.APP_ENV == "production" else "🟡 DEV"
    embed = {
        "title": f"{env_label} Cloud Build {status} - someday-api",
        "description": (
            f"Build [`{build_id[:12]}`]({log_url}) ended `{status}`.\n"
            f"commit `{(commit or 'n/a')[:8]}` - **the deploy did NOT go live; "
            f"traffic stays on the previous revision.**"
        ),
        "color": 0xE53E3E,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
    await _post(embed)


def alert(
    status: int,
    method: str,
    path: str,
    user_hint: str,
    exc: BaseException | None = None,
) -> None:
    """Schedule a Discord alert. Safe to call from async context; no-op if webhook not configured."""
    if not settings.DISCORD_WEBHOOK_URL:
        return

    description = ""
    if exc:
        tb = "".join(traceback.format_exception(type(exc), exc, exc.__traceback__))
        description = f"```\n{tb[-3800:]}\n```"

    env_label = "🔴 PROD" if settings.APP_ENV == "production" else "🟡 DEV"
    embed = {
        "title": f"{env_label} `{status}` {method} {path}",
        "description": description,
        "color": 0xE53E3E if status >= 500 else 0xDD6B20,
        "fields": [
            {"name": "user", "value": user_hint, "inline": True},
        ],
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }

    try:
        asyncio.get_running_loop().create_task(_post(embed))
    except RuntimeError:
        errorlogger.error("discord_alert | no running loop - alert dropped")
