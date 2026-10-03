"""Joining by invite against a real Postgres: rejoin after leaving, join twice,
and a removed member is refused until an admin allows them back.

Reuses the throwaway database fixture from tests/account (skips without
SOMEDAY_TEST_DATABASE_URL).
"""

from app_util.db_util import DBUtil
from handler.circles_handler import CirclesHandler
from modules.circles import circles_helper as h
from tests.account.test_delete_account import Seeder, engine, pytestmark  # noqa: F401 - fixtures

MEMBERSHIP = "SELECT role, status FROM public.circle_members WHERE circle_id = :cid AND user_id = :uid ORDER BY joined_at"


def setup(engine):
    with engine.begin() as conn:
        conn.exec_driver_sql("TRUNCATE public.circle_members, public.circles, public.users, auth.users CASCADE")
    seed = Seeder(engine, [], [])
    owner, guest = seed.user("owner"), seed.user("guest")
    cid = seed.circle(owner)
    token = seed.one("SELECT invite_token FROM public.circles WHERE id = :cid", cid=cid)[0]
    return seed, cid, guest, token


def owner_of(seed, cid):
    return seed.one("SELECT owner_id FROM public.circles WHERE id = :cid", cid=cid)[0]


def test_leave_then_rejoin_reactivates_one_row(engine):
    seed, cid, guest, token = setup(engine)
    db = DBUtil()
    h.join_circle_by_token(db, token, guest)
    seed.run("UPDATE public.circle_members SET role = 'admin' WHERE circle_id = :cid AND user_id = :uid", cid=cid, uid=guest)
    h.leave_circle(db, cid, guest)
    assert h.get_circle_with_members(db, cid, guest) is None

    assert h.join_circle_by_token(db, token, guest)
    assert h.get_circle_with_members(db, cid, guest) is not None
    assert [tuple(r) for r in seed.run(MEMBERSHIP, cid=cid, uid=guest)] == [("member", 1)]


def test_join_twice_stays_one_row(engine):
    seed, cid, guest, token = setup(engine)
    db = DBUtil()
    h.join_circle_by_token(db, token, guest)
    h.join_circle_by_token(db, token, guest)
    assert [tuple(r) for r in seed.run(MEMBERSHIP, cid=cid, uid=guest)] == [("member", 1)]


def test_removed_member_cannot_rejoin(engine):
    seed, cid, guest, token = setup(engine)
    handler = CirclesHandler()
    handler.join_circle(token, guest)
    assert handler.remove_member(cid, owner_of(seed, cid), guest) == (200, "Member removed")

    assert handler.join_circle(token, guest) == (
        403, "You were removed from this circle. Ask an admin to add you back."
    )
    assert h.get_circle_with_members(handler, cid, guest) is None
    assert [tuple(r) for r in seed.run(MEMBERSHIP, cid=cid, uid=guest)] == [("member", 0)]


def test_left_member_is_not_listed_as_removed(engine):
    seed, cid, guest, token = setup(engine)
    handler = CirclesHandler()
    handler.join_circle(token, guest)
    handler.leave_circle(cid, guest)
    status, circle = handler.get_circle(cid, owner_of(seed, cid))
    assert status == 200 and circle["removed"] == []
    assert handler.join_circle(token, guest)[0] == 200


def test_admin_allows_removed_member_back(engine):
    seed, cid, guest, token = setup(engine)
    handler = CirclesHandler()
    owner = owner_of(seed, cid)
    handler.join_circle(token, guest)
    handler.remove_member(cid, owner, guest)
    status, circle = handler.get_circle(cid, owner)
    assert [str(r["user_id"]) for r in circle["removed"]] == [str(guest)]

    # A non-member cannot clear the removal.
    assert handler.allow_member_back(cid, guest, guest)[0] == 403
    assert handler.allow_member_back(cid, owner, guest) == (200, "Allowed back")
    assert handler.allow_member_back(cid, owner, guest)[0] == 404

    assert handler.join_circle(token, guest)[0] == 200
    assert [tuple(r) for r in seed.run(MEMBERSHIP, cid=cid, uid=guest)] == [("member", 1)]
    assert handler.get_circle(cid, owner)[1]["removed"] == []
