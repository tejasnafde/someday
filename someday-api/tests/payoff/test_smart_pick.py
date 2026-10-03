"""GET /circles/:id/payoff/smart - an empty shortlist is 200, not a 404 alert."""

from app_util.db_util import DBUtil
from modules.circles import circles_queries as cq


def fake_db(member: bool, rows: list):
    def run(self, query, params):
        if query == cq.GET_MEMBER_ROLE:
            return [{"role": "member"}] if member else []
        return rows
    return run


async def test_empty_shortlist_is_200_with_reason(client, mock_jwt, monkeypatch):
    monkeypatch.setattr(DBUtil, "execute_query_with_value", fake_db(True, []))
    resp = await client.get("/circles/c1/payoff/smart")
    assert resp.status_code == 200
    assert resp.json()["pick"] is None
    assert resp.json()["reason"].startswith("Nothing to pick")


async def test_not_a_member_is_404(client, mock_jwt, monkeypatch):
    monkeypatch.setattr(DBUtil, "execute_query_with_value", fake_db(False, []))
    resp = await client.get("/circles/c1/payoff/smart")
    assert resp.status_code == 404


async def test_pick_is_nested(client, mock_jwt, monkeypatch):
    row = {"intent_id": "i1", "title": "Dune", "link_meta": None, "score": 60, "mutual_ratio": 1,
           "reaction_count": 2, "days_saved": 0, "has_boost": 0}
    monkeypatch.setattr(DBUtil, "execute_query_with_value", fake_db(True, [row]))
    resp = await client.get("/circles/c1/payoff/smart")
    assert resp.status_code == 200
    assert resp.json()["pick"]["title"] == "Dune"
    assert resp.json()["reason"] is None
