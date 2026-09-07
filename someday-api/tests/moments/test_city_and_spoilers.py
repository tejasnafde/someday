from datetime import datetime, timezone

from common_helper.geo_util import pick_city, reverse_geocode_city
from modules.moments import moments_queries as q
from modules.moments.moments_helper import list_moments


def test_pick_city_prefers_most_specific():
    assert pick_city({"city": "Bengaluru", "state": "Karnataka"}) == "Bengaluru"
    assert pick_city({"town": "Alibag", "state": "Maharashtra"}) == "Alibag"
    assert pick_city({"state": "Goa"}) == "Goa"
    assert pick_city({}) is None


def test_pick_city_caps_length():
    assert len(pick_city({"city": "x" * 100})) == 40


def test_reverse_geocode_rejects_out_of_range():
    assert reverse_geocode_city(91.0, 0.0) is None
    assert reverse_geocode_city(0.0, 181.0) is None


class SpoilerStubDB:
    """Dispatches on query identity so list_moments runs without Postgres."""

    def __init__(self, moments, posts, ping_rows):
        self.moments = moments
        self.posts = posts
        self.ping_rows = ping_rows
        self.max_date_param = None

    def execute_query_with_value(self, query, params):
        if query is q.GET_USER_TIMEZONE:
            return [{"timezone": "Asia/Kolkata", "city": None}]
        if query is q.LIST_MOMENTS_FOR_CIRCLE:
            self.max_date_param = params["max_date"]
            return self.moments
        if query is q.LIST_POSTS_FOR_MOMENTS:
            return self.posts
        if query is q.GET_MY_PING:
            return self.ping_rows
        raise AssertionError(f"unexpected query: {query[:40]}")


# 12:00 UTC on Sept 7 is 17:30 in Kolkata - viewer_today is Sept 7.
NOW = datetime(2026, 9, 7, 12, 0, tzinfo=timezone.utc)


def test_todays_moment_hidden_before_ping_fires():
    db = SpoilerStubDB(
        moments=[{"id": "m1", "circle_id": "c1", "moment_date": "2026-09-07", "created_at": "x"}],
        posts=[],
        ping_rows=[{"ping_at": "2026-09-07 15:00:00+00"}],  # 20:30 IST - later
    )
    page = list_moments(db, "c1", "viewer", None, 20, NOW)
    assert page["items"] == []
    assert db.max_date_param == "2026-09-07"  # future days excluded in SQL


def test_todays_moment_visible_after_ping_fires():
    db = SpoilerStubDB(
        moments=[{"id": "m1", "circle_id": "c1", "moment_date": "2026-09-07", "created_at": "x"}],
        posts=[],
        ping_rows=[{"ping_at": "2026-09-07 08:00:00+00"}],  # already fired
    )
    page = list_moments(db, "c1", "viewer", None, 20, NOW)
    assert len(page["items"]) == 1


def test_todays_moment_visible_once_a_friend_posted():
    db = SpoilerStubDB(
        moments=[{"id": "m1", "circle_id": "c1", "moment_date": "2026-09-07", "created_at": "x"}],
        posts=[{
            "id": "p1", "moment_id": "m1", "user_id": "friend", "display_name": "Asha",
            "avatar_url": None, "photo_url": "u", "caption": None, "tz": "Asia/Kolkata",
            "city": "Bengaluru", "late": False, "created_at": "2026-09-07 10:00:00+00",
        }],
        ping_rows=[],  # viewer's ping has not even fired
    )
    page = list_moments(db, "c1", "viewer", None, 20, NOW)
    assert len(page["items"]) == 1
    # Not revealed (viewer has not posted, day not over) - proof of life only.
    entry = page["items"][0]
    assert not entry["revealed"]
    assert entry["posts"][0]["photo_url"] is None
    assert entry["posts"][0]["city"] == "Bengaluru"


def test_past_moment_always_listed_and_revealed():
    db = SpoilerStubDB(
        moments=[{"id": "m0", "circle_id": "c1", "moment_date": "2026-09-05", "created_at": "x"}],
        posts=[],
        ping_rows=[],
    )
    page = list_moments(db, "c1", "viewer", None, 20, NOW)
    assert len(page["items"]) == 1
    assert page["items"][0]["revealed"]
