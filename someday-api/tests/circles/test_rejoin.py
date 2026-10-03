"""Joining by invite against a real Postgres: rejoin after leaving, join twice.

Reuses the throwaway database fixture from tests/account (skips without
SOMEDAY_TEST_DATABASE_URL).
"""

from app_util.db_util import DBUtil
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
