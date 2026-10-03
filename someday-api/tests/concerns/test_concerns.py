"""POST /concerns - store first, alert after, Child safety marked urgent."""

import asyncio

from app_util.db_util import DBUtil
from common_helper import discord_alert
from routers import concerns_router

AUTH = {"Authorization": "Bearer t"}
ROW = {"id": "r-1", "category": "child_safety", "created_at": "2026-10-03T00:00:00+00:00"}


def capture_alerts(monkeypatch):
    sent = []

    async def fake_alert(*args):
        sent.append(args)

    monkeypatch.setattr(concerns_router, "send_concern_alert", fake_alert)
    return sent


async def test_report_is_stored_then_alerted(client, mock_jwt, monkeypatch):
    stored = {}

    def fake_insert(self, query, params):
        stored.update(params)
        return ROW

    monkeypatch.setattr(DBUtil, "execute_query_with_value_returning", fake_insert)
    sent = capture_alerts(monkeypatch)

    resp = await client.post(
        "/concerns",
        json={"category": "child_safety", "subject": "  Weekend circle ", "body": " Details here "},
        headers=AUTH,
    )

    assert resp.status_code == 201
    assert resp.json()["id"] == "r-1"
    assert stored == {
        "user_id": mock_jwt["sub"], "category": "child_safety", "subject": "Weekend circle", "body": "Details here",
    }
    assert sent == [("r-1", mock_jwt["sub"], "child_safety", "Weekend circle", "Details here")]


async def test_unknown_user_gets_404_and_no_alert(client, mock_jwt, monkeypatch):
    monkeypatch.setattr(DBUtil, "execute_query_with_value_returning", lambda self, q, p: {})
    sent = capture_alerts(monkeypatch)

    resp = await client.post("/concerns", json={"category": "other", "body": "x"}, headers=AUTH)

    assert resp.status_code == 404
    assert sent == []


async def test_rejects_bad_input(client, mock_jwt):
    for payload in (
        {"category": "spam", "body": "x"},
        {"category": "other", "body": "   "},
        {"category": "other", "body": "x" * 4001},
        {"category": "other", "subject": "s" * 201, "body": "x"},
    ):
        resp = await client.post("/concerns", json=payload, headers=AUTH)
        assert resp.status_code == 422, payload


async def test_requires_auth(client):
    resp = await client.post("/concerns", json={"category": "other", "body": "x"})
    assert resp.status_code in (401, 403)


def test_child_safety_alert_is_urgent_and_others_are_not(monkeypatch):
    posted = []

    async def capture(embed):
        posted.append(embed)

    monkeypatch.setattr(discord_alert.settings, "DISCORD_WEBHOOK_URL", "https://example.test/hook")
    monkeypatch.setattr(discord_alert, "_post", capture)

    asyncio.run(discord_alert.send_concern_alert("r-1", "u-1", "child_safety", "Circle X", "help @everyone"))
    asyncio.run(discord_alert.send_concern_alert("r-2", "u-1", "abuse", None, "rude"))

    assert "URGENT" in posted[0]["title"] and "Child safety" in posted[0]["title"]
    assert "@everyone" not in posted[0]["description"]
    assert "URGENT" not in posted[1]["title"]


def test_failed_alert_logs_error_and_does_not_raise(monkeypatch):
    errors = []

    class Boom:
        def __init__(self, *a, **k):
            pass

        async def __aenter__(self):
            raise RuntimeError("discord down")

        async def __aexit__(self, *a):
            return False

    monkeypatch.setattr(discord_alert.settings, "DISCORD_WEBHOOK_URL", "https://example.test/hook")
    monkeypatch.setattr(discord_alert.httpx, "AsyncClient", Boom)
    monkeypatch.setattr(discord_alert.errorlogger, "error", errors.append)

    asyncio.run(discord_alert.send_concern_alert("r-1", "u-1", "other", None, "x"))

    assert errors and "delivery failed" in errors[0]
