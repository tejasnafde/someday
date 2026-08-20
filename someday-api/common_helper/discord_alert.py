"""Fire-and-forget Discord alerts for 4xx/5xx errors."""

import asyncio
import re
import traceback
from datetime import UTC, datetime

import httpx

from app_util.log_util import errorlogger
from config.settings import settings

BEARER_RE = re.compile(r"(?i)(\bBearer\s+)[A-Za-z0-9._~+/=-]+")
JWT_RE = re.compile(r"\b[A-Za-z0-9_-]{8,}\.[A-Za-z0-9_-]{2,}\.[A-Za-z0-9_-]{6,}\b")
CREDENTIAL_URL_RE = re.compile(r"(\b[a-z][a-z0-9+.-]*://[^:/\s]+:)[^@\s]+(@)", re.IGNORECASE)
NAMED_SECRET_RE = re.compile(
    r"\b(password|passwd|secret|api[_-]?key|access[_-]?token|refresh[_-]?token|authorization|cookie)"
    r"(\s*[:=]\s*)([^\s,;]+)",
    re.IGNORECASE,
)


def safe_alert_text(
    value: object,
    limit: int = 1024,
    *,
    preserve_newlines: bool = False,
) -> str:
    safe = BEARER_RE.sub(r"\1[REDACTED]", str(value))
    safe = JWT_RE.sub("[JWT REDACTED]", safe)
    safe = CREDENTIAL_URL_RE.sub(r"\1[REDACTED]\2", safe)
    safe = NAMED_SECRET_RE.sub(r"\1\2[REDACTED]", safe)
    if preserve_newlines:
        safe = re.sub(r"\r\n?|\x85|\u2028|\u2029", "\n", safe)
        safe = re.sub(r"[\x00-\x08\x0b-\x1f\x7f]+", " ", safe)
    else:
        safe = re.sub(r"[\x00-\x1f\x7f\x85\u2028\u2029]+", " ", safe)
    safe = safe.replace("@everyone", "@\u200beveryone").replace("@here", "@\u200bhere")
    return safe if len(safe) <= limit else f"{safe[: limit - 1]}…"


def build_error_embed(
    status: int,
    method: str,
    path: str,
    *,
    error_message: str = "",
    duration_ms: float | None = None,
    request_id: str = "",
    client: str = "",
    user_agent: str = "",
    auth_context: dict | None = None,
    exc: BaseException | None = None,
) -> dict:
    """Build a secret-safe Discord embed with actionable request context."""
    env_label = "🔴 PROD" if settings.APP_ENV == "production" else "🟡 DEV"
    fields = []

    if error_message:
        fields.append(
            {"name": "error", "value": safe_alert_text(error_message, 1000), "inline": False}
        )

    request_parts = []
    if duration_ms is not None:
        request_parts.append(f"{duration_ms:.1f} ms")
    if request_id:
        request_parts.append(safe_alert_text(request_id))
    if request_parts:
        fields.append(
            {
                "name": "request",
                "value": safe_alert_text(" · ".join(request_parts), 500),
                "inline": True,
            }
        )

    client_parts = [part for part in (client, user_agent) if part]
    if client_parts:
        client_value = " · ".join(map(safe_alert_text, client_parts))
        fields.append(
            {"name": "client", "value": safe_alert_text(client_value, 750), "inline": True}
        )

    if auth_context:
        auth_value = "\n".join(
            f"{key}: {safe_alert_text(value)}" for key, value in auth_context.items()
        )
        fields.append(
            {
                "name": "auth",
                "value": safe_alert_text(auth_value, 1000, preserve_newlines=True),
                "inline": False,
            }
        )

    description = ""
    if exc:
        tb = "".join(traceback.format_exception(type(exc), exc, exc.__traceback__))
        description = (
            f"```\n{safe_alert_text(tb[-2000:], 2000, preserve_newlines=True)}\n```"
        )

    return {
        "title": safe_alert_text(f"{env_label} `{status}` {method} {path}", 256),
        "description": description,
        "color": 0xE53E3E if status >= 500 else 0xDD6B20,
        "fields": fields,
        "timestamp": datetime.now(UTC).isoformat(),
    }


async def _post(embed: dict) -> None:
    try:
        async with httpx.AsyncClient(timeout=5) as client:
            response = await client.post(
                settings.DISCORD_WEBHOOK_URL,
                json={
                    "username": "Someday API",
                    "embeds": [embed],
                    "allowed_mentions": {"parse": []},
                },
            )
            response.raise_for_status()
    except Exception as exc:
        status = getattr(getattr(exc, "response", None), "status_code", None)
        status_hint = f" | status={status}" if status is not None else ""
        errorlogger.error(
            f"discord_alert | delivery failed | type={type(exc).__name__}{status_hint}"
        )


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
        "timestamp": datetime.now(UTC).isoformat(),
    }
    await _post(embed)


def alert(
    status: int,
    method: str,
    path: str,
    *,
    error_message: str = "",
    duration_ms: float | None = None,
    request_id: str = "",
    client: str = "",
    user_agent: str = "",
    auth_context: dict | None = None,
    exc: BaseException | None = None,
) -> None:
    """Schedule a Discord alert. Safe to call from async context; no-op if webhook not configured."""
    if not settings.DISCORD_WEBHOOK_URL:
        return

    embed = build_error_embed(
        status=status,
        method=method,
        path=path,
        error_message=error_message,
        duration_ms=duration_ms,
        request_id=request_id,
        client=client,
        user_agent=user_agent,
        auth_context=auth_context,
        exc=exc,
    )

    try:
        asyncio.get_running_loop().create_task(_post(embed))
    except RuntimeError:
        errorlogger.error("discord_alert | no running loop - alert dropped")
