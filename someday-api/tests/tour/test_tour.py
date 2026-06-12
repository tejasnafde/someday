"""Tour endpoints — seen-step merge, reset, and tour_state exposure on /auth/me."""

import json

from app_util.db_util import DBUtil

# ---------- pure merge logic ----------

def test_merge_seen_dedups_and_preserves_order():
    from modules.tour.tour_helper import merge_seen

    assert merge_seen(["a", "b"], ["b", "c", "a", "d"]) == ["a", "b", "c", "d"]


def test_merge_seen_handles_empty_current():
    from modules.tour.tour_helper import merge_seen

    assert merge_seen([], ["x", "x", "y"]) == ["x", "y"]


# ---------- POST /tour/seen ----------

async def test_seen_merges_into_tour_state(client, mock_jwt, monkeypatch):
    captured = {}

    def fake_select(self, query, params):
        return [{"tour_state": {"seen": ["dash.welcome"]}}]

    def fake_update(self, query, params):
        captured["params"] = params
        return {"tour_state": json.loads(params["tour_state"])}

    monkeypatch.setattr(DBUtil, "execute_query_with_value", fake_select)
    monkeypatch.setattr(DBUtil, "execute_query_with_value_returning", fake_update)

    resp = await client.post(
        "/tour/seen",
        json={"step_ids": ["circle.payoff", "dash.welcome"]},
        headers={"Authorization": "Bearer t"},
    )

    assert resp.status_code == 200
    assert resp.json()["tour_state"]["seen"] == ["dash.welcome", "circle.payoff"]
    assert captured["params"]["user_id"] == mock_jwt["sub"]


async def test_seen_404_when_user_missing(client, mock_jwt, monkeypatch):
    monkeypatch.setattr(DBUtil, "execute_query_with_value", lambda self, q, p: [])

    resp = await client.post(
        "/tour/seen",
        json={"step_ids": ["dash.welcome"]},
        headers={"Authorization": "Bearer t"},
    )

    assert resp.status_code == 404


async def test_seen_rejects_empty_step_ids(client, mock_jwt):
    resp = await client.post(
        "/tour/seen",
        json={"step_ids": []},
        headers={"Authorization": "Bearer t"},
    )

    assert resp.status_code == 422


async def test_seen_requires_auth(client):
    resp = await client.post("/tour/seen", json={"step_ids": ["dash.welcome"]})

    assert resp.status_code in (401, 403)


# ---------- POST /tour/reset ----------

async def test_reset_clears_seen(client, mock_jwt, monkeypatch):
    def fake_update(self, query, params):
        return {"tour_state": {"seen": []}}

    monkeypatch.setattr(DBUtil, "execute_query_with_value_returning", fake_update)

    resp = await client.post("/tour/reset", headers={"Authorization": "Bearer t"})

    assert resp.status_code == 200
    assert resp.json()["tour_state"]["seen"] == []


async def test_reset_404_when_user_missing(client, mock_jwt, monkeypatch):
    monkeypatch.setattr(DBUtil, "execute_query_with_value_returning", lambda self, q, p: {})

    resp = await client.post("/tour/reset", headers={"Authorization": "Bearer t"})

    assert resp.status_code == 404


# ---------- GET /auth/me exposes tour_state ----------

async def test_me_includes_tour_state(client, mock_jwt, monkeypatch):
    user_row = {
        "id": mock_jwt["sub"],
        "email": "test@example.com",
        "display_name": "test",
        "avatar_url": None,
        "tour_state": {"seen": ["dash.welcome"]},
    }
    monkeypatch.setattr(DBUtil, "execute_query_with_value", lambda self, q, p: [user_row])
    import handler.auth_handler as ah
    monkeypatch.setattr(ah.ch, "get_my_circles", lambda db, user_id: [])

    resp = await client.get("/auth/me", headers={"Authorization": "Bearer t"})

    assert resp.status_code == 200
    assert resp.json()["user"]["tour_state"] == {"seen": ["dash.welcome"]}
