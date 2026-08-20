import asyncio
import json

import httpx
import pytest

from common_helper import discord_alert


def test_error_embed_is_actionable_without_exposing_the_bearer_token():
    token = "eyJhbGciOiJFUzI1NiJ9.secret.signature"

    embed = discord_alert.build_error_embed(
        status=401,
        method="GET",
        path="/circles",
        error_message=f"Invalid Bearer {token}",
        duration_ms=23.4,
        request_id="trace-123",
        client="native/1.15.0",
        user_agent="okhttp/5",
        auth_context={
            "reason": "expired",
            "fingerprint": "sha256:abc123",
            "token_length": len(token),
            "segments": 3,
            "subject": "user-123",
            "expires_at": "2026-08-19T10:00:00+00:00",
        },
    )

    rendered = json.dumps(embed)
    assert embed["title"] == "🟡 DEV `401` GET /circles"
    assert "Invalid Bearer [REDACTED]" in rendered
    assert "expired" in rendered
    assert "sha256:abc123" in rendered
    assert "native/1.15.0" in rendered
    assert "trace-123" in rendered
    assert token not in rendered


def test_error_embed_bounds_untrusted_values_and_redacts_bare_jwts():
    token = "eyJhbGciOiJFUzI1NiJ9.eyJzdWIiOiJ1c2VyLTEyMyJ9.signature"

    embed = discord_alert.build_error_embed(
        status=500,
        method="POST",
        path="/unfurl",
        error_message=f"@everyone failed with {token} " + "x" * 3000,
        auth_context={"reason": "@here " + "y" * 2000},
    )

    rendered = json.dumps(embed)
    assert token not in rendered
    assert "[JWT REDACTED]" in rendered
    assert all(len(field["name"]) <= 256 for field in embed["fields"])
    assert all(len(field["value"]) <= 1024 for field in embed["fields"])


@pytest.mark.anyio
async def test_alert_schedules_the_structured_embed(monkeypatch):
    delivered = []

    async def capture(embed):
        delivered.append(embed)

    monkeypatch.setattr(discord_alert.settings, "DISCORD_WEBHOOK_URL", "https://example.test/hook")
    monkeypatch.setattr(discord_alert, "_post", capture)

    discord_alert.alert(
        status=422,
        method="POST",
        path="/circles",
        error_message="name is required",
        duration_ms=4.2,
        client="web",
    )
    await asyncio.sleep(0)

    assert len(delivered) == 1
    assert delivered[0]["title"] == "🟡 DEV `422` POST /circles"
    assert delivered[0]["fields"][0]["value"] == "name is required"


@pytest.mark.anyio
async def test_discord_delivery_disables_mentions_and_logs_rejected_payloads(monkeypatch):
    requests = []
    errors = []
    real_client = httpx.AsyncClient

    def handle(request: httpx.Request) -> httpx.Response:
        requests.append(json.loads(request.content))
        return httpx.Response(400, text="invalid embed")

    def client_factory(*_args, **_kwargs):
        return real_client(transport=httpx.MockTransport(handle))

    monkeypatch.setattr(discord_alert.httpx, "AsyncClient", client_factory)
    monkeypatch.setattr(discord_alert.settings, "DISCORD_WEBHOOK_URL", "https://example.test/hook")
    monkeypatch.setattr(discord_alert.errorlogger, "error", errors.append)

    await discord_alert._post({"title": "@everyone"})

    assert requests[0]["allowed_mentions"] == {"parse": []}
    assert len(errors) == 1
    assert "400" in errors[0]
    assert "https://example.test/hook" not in errors[0]


def test_error_embed_stays_within_discords_total_size_limit():
    embed = discord_alert.build_error_embed(
        status=500,
        method="POST",
        path="/" + "path" * 500,
        error_message="e" * 5000,
        duration_ms=1.0,
        request_id="r" * 2000,
        client="c" * 2000,
        user_agent="u" * 2000,
        auth_context={"reason": "a" * 3000},
        exc=RuntimeError("trace" * 2000),
    )

    size = len(embed["title"]) + len(embed["description"])
    size += sum(len(field["name"]) + len(field["value"]) for field in embed["fields"])
    assert len(embed["title"]) <= 256
    assert len(embed["description"]) <= 4096
    assert size <= 6000


def test_error_embed_redacts_common_secret_shapes():
    embed = discord_alert.build_error_embed(
        status=500,
        method="GET",
        path="/circles",
        error_message=(
            "password=hunter2 api_key=sk_live_secret "
            "postgresql://dbuser:dbpass@example.test/someday"
        ),
    )

    rendered = json.dumps(embed)
    assert "hunter2" not in rendered
    assert "sk_live_secret" not in rendered
    assert "dbpass" not in rendered
    assert rendered.count("[REDACTED]") >= 3


def test_error_embed_preserves_intentional_traceback_and_auth_line_breaks():
    try:
        raise RuntimeError("multi-line diagnostic")
    except RuntimeError as exc:
        embed = discord_alert.build_error_embed(
            status=500,
            method="POST",
            path="/webhooks/eas-build",
            auth_context={"verification": "failed", "reason": "malformed"},
            exc=exc,
        )

    assert embed["description"].count("\n") > 2
    auth = next(field["value"] for field in embed["fields"] if field["name"] == "auth")
    assert auth == "verification: failed\nreason: malformed"
