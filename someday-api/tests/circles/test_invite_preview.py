"""GET /circles/invite/:token - public preview leaks only name + first name."""

from app_util.db_util import DBUtil


async def test_preview_returns_only_name_and_first_name(client, monkeypatch):
    monkeypatch.setattr(
        DBUtil, "execute_query_with_value",
        lambda self, q, p: [{"name": "Goa Gang", "display_name": "Asha Rao"}],
    )
    resp = await client.get("/circles/invite/abc123")
    assert resp.status_code == 200
    assert resp.json() == {"circle_name": "Goa Gang", "inviter_name": "Asha"}


async def test_preview_without_display_name(client, monkeypatch):
    monkeypatch.setattr(
        DBUtil, "execute_query_with_value",
        lambda self, q, p: [{"name": "Goa Gang", "display_name": None}],
    )
    resp = await client.get("/circles/invite/abc123")
    assert resp.json()["inviter_name"] is None


async def test_preview_invalid_token_404(client, monkeypatch):
    monkeypatch.setattr(DBUtil, "execute_query_with_value", lambda self, q, p: [])
    resp = await client.get("/circles/invite/nope")
    assert resp.status_code == 404
    assert resp.json() == {"message": "Invalid or expired invite link"}
