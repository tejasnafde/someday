import random
from datetime import date, datetime, timezone
from zoneinfo import ZoneInfo

import pytest
from pydantic import ValidationError

from modules.moments.moments_helper import rewindow_pending_pings
from routers.moments_router import TimezoneRequest


def test_accepts_legacy_alias_android_sends():
    # Android Chrome/WebView reports Asia/Calcutta, not Asia/Kolkata. The
    # container must resolve it too - the tzdata pin in requirements.txt
    # provides the full IANA db on python:slim images.
    assert TimezoneRequest(timezone="Asia/Calcutta").timezone == "Asia/Calcutta"
    assert TimezoneRequest(timezone="Asia/Kolkata").timezone == "Asia/Kolkata"


def test_rejects_garbage_timezone():
    with pytest.raises(ValidationError):
        TimezoneRequest(timezone="Not/AZone")


class RewindowStubDB:
    def __init__(self, rows):
        self.rows = rows
        self.updates = []

    def execute_query_with_value(self, query, params):
        return self.rows

    def execute_query_with_value_without_output(self, query, params):
        self.updates.append(params)


def test_rewindow_moves_pending_pings_into_new_zone():
    rows = [
        {"id": "p1", "moment_date": "2026-09-08"},
        {"id": "p2", "moment_date": "2026-09-09"},
    ]
    db = RewindowStubDB(rows)
    now = datetime(2026, 9, 7, 12, 0, tzinfo=timezone.utc)
    n = rewindow_pending_pings(db, "u1", "Asia/Calcutta", random.Random(1), now)
    assert n == 2
    assert len(db.updates) == 2
    for update, row in zip(db.updates, rows):
        assert update["ping_id"] == row["id"]
        local = datetime.fromisoformat(update["ping_at"]).astimezone(ZoneInfo("Asia/Calcutta"))
        assert local.date() == date.fromisoformat(row["moment_date"])
        assert 9 <= local.hour < 22


def test_rewindow_no_pending_pings():
    db = RewindowStubDB([])
    assert rewindow_pending_pings(db, "u1", "Asia/Kolkata") == 0
    assert db.updates == []
