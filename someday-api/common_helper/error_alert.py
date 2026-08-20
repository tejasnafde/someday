"""ASGI middleware that turns failed API responses into structured alerts."""

import json
import time

from starlette.types import ASGIApp, Message, Receive, Scope, Send

from common_helper.discord_alert import alert as discord_alert

MAX_ERROR_BODY_BYTES = 16_384


def _headers(scope: Scope) -> dict[str, str]:
    return {
        key.decode("latin-1").lower(): value.decode("latin-1")
        for key, value in scope.get("headers", [])
    }


def _error_message(body: bytes) -> str:
    if not body:
        return ""
    decoded = body.decode("utf-8", errors="replace")
    try:
        payload = json.loads(decoded)
    except json.JSONDecodeError:
        return decoded
    if isinstance(payload, dict):
        value = payload.get("detail", payload.get("message", payload))
    else:
        value = payload
    if isinstance(value, str):
        return value
    return json.dumps(value, ensure_ascii=False)


def _auth_context(scope: Scope, headers: dict[str, str], status: int) -> dict | None:
    context = scope.get("state", {}).get("auth_alert")
    if context or status != 401:
        return context
    authorization = headers.get("authorization", "")
    if not authorization:
        return {"reason": "missing_credentials"}
    if not authorization.startswith("Bearer "):
        return {"reason": "invalid_authorization_scheme"}
    return {"reason": "unclassified_auth_failure"}


def _route_path(scope: Scope) -> str:
    route = scope.get("route")
    return getattr(route, "path", None) or "<unmatched route>"


class StructuredErrorAlertMiddleware:
    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        started_at = time.perf_counter()
        status = 0
        body = bytearray()

        async def observe(message: Message) -> None:
            nonlocal status
            if message["type"] == "http.response.start":
                status = message["status"]
            elif message["type"] == "http.response.body" and status >= 400:
                remaining = MAX_ERROR_BODY_BYTES - len(body)
                if remaining > 0:
                    body.extend(message.get("body", b"")[:remaining])
            await send(message)

        try:
            await self.app(scope, receive, observe)
        except Exception as exc:
            headers = _headers(scope)
            trace = headers.get("x-cloud-trace-context", "").split("/", 1)[0]
            discord_alert(
                status=500,
                method=scope.get("method", ""),
                path=_route_path(scope),
                error_message=str(exc),
                duration_ms=(time.perf_counter() - started_at) * 1000,
                request_id=headers.get("x-request-id", trace),
                client=headers.get("x-someday-client", ""),
                user_agent=headers.get("user-agent", ""),
                auth_context=_auth_context(scope, headers, 500),
                exc=exc,
            )
            raise

        if status < 400:
            return

        headers = _headers(scope)
        trace = headers.get("x-cloud-trace-context", "").split("/", 1)[0]
        discord_alert(
            status=status,
            method=scope.get("method", ""),
            path=_route_path(scope),
            error_message=_error_message(bytes(body)),
            duration_ms=(time.perf_counter() - started_at) * 1000,
            request_id=headers.get("x-request-id", trace),
            client=headers.get("x-someday-client", ""),
            user_agent=headers.get("user-agent", ""),
            auth_context=_auth_context(scope, headers, status),
        )
