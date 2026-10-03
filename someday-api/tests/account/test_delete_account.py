"""DELETE /auth/me against a real Postgres built from the migrations.

Mocks cannot prove that a dozen UPDATEs hit the right rows and only those, so
this runs the real SQL. CI provides a Postgres service and sets
SOMEDAY_TEST_DATABASE_URL; without it the module skips. The database name must
end in _test because the fixture drops and rebuilds every schema in it.

Supabase owns the auth and storage schemas, so the fixture stubs the two
objects the migrations touch: auth.users (+ auth.uid()) and storage.buckets.
"""

import os
import uuid
from pathlib import Path

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.engine import make_url

from app_util.db_util import DBUtil
from config.settings import settings
from modules.account import account_helper

DB_URL = os.environ.get("SOMEDAY_TEST_DATABASE_URL")
pytestmark = pytest.mark.skipif(not DB_URL, reason="SOMEDAY_TEST_DATABASE_URL not set")

MIGRATIONS = Path(__file__).resolve().parents[2] / "supabase" / "migrations"
STUBS = """
    DROP SCHEMA IF EXISTS public, auth, storage CASCADE;
    CREATE SCHEMA public;
    CREATE SCHEMA auth;
    CREATE SCHEMA storage;
    CREATE TABLE auth.users (id uuid PRIMARY KEY);
    CREATE FUNCTION auth.uid() RETURNS uuid LANGUAGE sql AS 'SELECT NULL::uuid';
    CREATE TABLE storage.buckets (id text PRIMARY KEY, name text, public boolean);
"""
TABLES = [
    "reactions", "intent_boosts", "notifications", "moment_pings", "moment_posts",
    "circle_moments", "intents", "web_push_subscriptions", "circle_members", "circles", "users",
]
STORAGE = f"{settings.SUPABASE_URL}/storage/v1/object/public"


@pytest.fixture(scope="module")
def engine():
    assert make_url(DB_URL).database.endswith("_test"), "refusing to rebuild a database not named *_test"
    eng = create_engine(DB_URL)
    with eng.begin() as conn:
        conn.exec_driver_sql(STUBS)
        for path in sorted(MIGRATIONS.glob("*.sql")):
            conn.exec_driver_sql(path.read_text())
    previous, DBUtil.engine = DBUtil.engine, eng
    yield eng
    DBUtil.engine = previous
    eng.dispose()


@pytest.fixture
def db(engine, monkeypatch):
    with engine.begin() as conn:
        conn.exec_driver_sql(f"TRUNCATE {', '.join('public.' + t for t in TABLES)}, auth.users CASCADE")
    auth_calls, file_calls = [], []
    monkeypatch.setattr(account_helper, "delete_auth_user", lambda uid: auth_calls.append(uid) or True)
    monkeypatch.setattr(account_helper, "delete_objects", lambda b, p: file_calls.append((b, sorted(p))) or True)
    return Seeder(engine, auth_calls, file_calls)


class Seeder:
    def __init__(self, engine, auth_calls, file_calls):
        self.engine, self.auth_calls, self.file_calls = engine, auth_calls, file_calls

    def run(self, sql: str, **params):
        with self.engine.begin() as conn:
            result = conn.execute(text(sql), params)
            return result.fetchall() if result.returns_rows else []

    def one(self, sql: str, **params):
        return self.run(sql, **params)[0]

    def user(self, name: str) -> str:
        uid = str(uuid.uuid4())
        self.run("INSERT INTO auth.users (id) VALUES (:id)", id=uid)
        self.run(
            "INSERT INTO public.users (id, email, display_name, avatar_url, city, push_token) "
            "VALUES (:id, :email, :name, :avatar, 'Pune', 'ExponentPushToken[x]')",
            id=uid, email=f"{name}@example.com", name=name, avatar=f"{STORAGE}/avatars/{uid}.webp?v=1",
        )
        return uid

    def circle(self, owner: str, *members: tuple[str, str]) -> str:
        cid = str(self.one(
            "INSERT INTO public.circles (name, owner_id) VALUES ('C', :owner) RETURNING id", owner=owner
        )[0])
        self.member(cid, owner, "owner", "2026-01-01")
        for uid, joined in members:
            self.member(cid, uid, "member", joined)
        return cid

    def member(self, cid: str, uid: str, role: str, joined: str):
        self.run(
            "INSERT INTO public.circle_members (circle_id, user_id, role, joined_at) "
            "VALUES (:cid, :uid, :role, CAST(:joined AS timestamptz))",
            cid=cid, uid=uid, role=role, joined=joined,
        )

    def intent(self, cid: str, uid: str, photo: str | None = None) -> str:
        photos = f'["{STORAGE}/memories/{photo}"]' if photo else "[]"
        return str(self.one(
            "INSERT INTO public.intents (circle_id, created_by, title, done_photos) "
            "VALUES (:cid, :uid, 'T', CAST(:photos AS jsonb)) RETURNING id",
            cid=cid, uid=uid, photos=photos,
        )[0])

    def moment_post(self, cid: str, uid: str, photo: str) -> str:
        mid = self.one(
            "INSERT INTO public.circle_moments (circle_id, moment_date) VALUES (:cid, CURRENT_DATE) "
            "ON CONFLICT (circle_id, moment_date) DO UPDATE SET status = circle_moments.status RETURNING id",
            cid=cid,
        )[0]
        self.run(
            "INSERT INTO public.moment_pings (moment_id, user_id, ping_at) VALUES (:mid, :uid, now())",
            mid=mid, uid=uid,
        )
        return str(self.one(
            "INSERT INTO public.moment_posts (moment_id, user_id, photo_url, tz) "
            "VALUES (:mid, :uid, :url, 'UTC') RETURNING id",
            mid=mid, uid=uid, url=f"{STORAGE}/moments/{photo}",
        )[0])

    def status(self, table: str, row_id: str) -> int:
        return self.one(f"SELECT status FROM public.{table} WHERE id = :id", id=row_id)[0]


@pytest.fixture
def as_user(mock_jwt):
    def set_user(uid: str):
        mock_jwt["sub"] = uid
    return set_user


async def test_sole_member_circle_is_deleted_with_its_content(client, db, as_user):
    me = db.user("asha")
    cid = db.circle(me)
    iid = db.intent(cid, me, photo="i1/a.webp")
    rid = str(db.one("INSERT INTO public.reactions (intent_id, user_id) VALUES (:i, :u) RETURNING id", i=iid, u=me)[0])
    bid = str(db.one("INSERT INTO public.intent_boosts (intent_id, user_id) VALUES (:i, :u) RETURNING id", i=iid, u=me)[0])
    pid = db.moment_post(cid, me, photo=f"m1/{me}/p.webp")

    as_user(me)
    resp = await client.delete("/auth/me")

    assert resp.status_code == 200
    assert db.status("circles", cid) == -1
    for table, row in [("intents", iid), ("reactions", rid), ("intent_boosts", bid), ("moment_posts", pid)]:
        assert db.status(table, row) == -1, table
    assert db.one("SELECT count(*) FROM public.circle_moments WHERE circle_id = :c AND status = 1", c=cid)[0] == 0
    assert db.one("SELECT count(*) FROM public.moment_pings WHERE status = 1")[0] == 0
    assert db.one("SELECT count(*) FROM public.circle_members WHERE circle_id = :c AND status = 1", c=cid)[0] == 0
    files = dict(db.file_calls)
    assert files["memories"] == ["i1/a.webp"]
    assert files["moments"] == [f"m1/{me}/p.webp"]
    assert files["circle-photos"] == [cid]
    assert files["avatars"] == sorted([f"{me}.webp", f"{me}.jpg", f"{me}.png"])


async def test_ownership_moves_to_longest_standing_member(client, db, as_user):
    me, early, late = db.user("asha"), db.user("bina"), db.user("chen")
    cid = db.circle(me, (late, "2026-03-01"), (early, "2026-02-01"))

    as_user(me)
    assert (await client.delete("/auth/me")).status_code == 200

    owner, status = db.one("SELECT owner_id, status FROM public.circles WHERE id = :c", c=cid)
    assert (str(owner), status) == (early, 1)
    roles = dict(db.run(
        "SELECT CAST(user_id AS text), role FROM public.circle_members WHERE circle_id = :c AND status = 1", c=cid
    ))
    assert roles == {early: "owner", late: "member"}
    assert "circle-photos" not in dict(db.file_calls)


async def test_users_row_is_scrubbed_and_auth_user_deleted(client, db, as_user):
    me = db.user("asha")
    db.run(
        "INSERT INTO public.web_push_subscriptions (user_id, endpoint, p256dh, auth) VALUES (:u, 'e', 'p', 'a')", u=me
    )

    as_user(me)
    assert (await client.delete("/auth/me")).status_code == 200

    row = db.one(
        "SELECT status, email, display_name, avatar_url, city, push_token FROM public.users WHERE id = :u", u=me
    )
    assert tuple(row) == (-1, f"deleted-{me}@deleted.invalid", None, None, None, None)
    assert db.auth_calls == [me]
    assert db.one("SELECT count(*) FROM public.web_push_subscriptions WHERE status = 1")[0] == 0

    # A JWT that outlives the deletion can neither re-verify nor delete again.
    resp = await client.post("/auth/verify")
    assert resp.status_code == 410
    assert db.one("SELECT email FROM public.users WHERE id = :u", u=me)[0] == f"deleted-{me}@deleted.invalid"
    assert (await client.delete("/auth/me")).status_code == 404


async def test_shared_circle_content_stays_and_personal_signals_go(client, db, as_user):
    me, friend = db.user("asha"), db.user("bina")
    cid = db.circle(friend, (me, "2026-02-01"))
    mine, theirs = db.intent(cid, me, photo="mine.webp"), db.intent(cid, friend, photo="theirs.webp")
    their_reaction_on_mine = str(db.one(
        "INSERT INTO public.reactions (intent_id, user_id) VALUES (:i, :u) RETURNING id", i=mine, u=friend
    )[0])
    my_reaction_on_theirs = str(db.one(
        "INSERT INTO public.reactions (intent_id, user_id) VALUES (:i, :u) RETURNING id", i=theirs, u=me
    )[0])
    my_boost_on_theirs = str(db.one(
        "INSERT INTO public.intent_boosts (intent_id, user_id) VALUES (:i, :u) RETURNING id", i=theirs, u=me
    )[0])
    their_post, my_post = db.moment_post(cid, friend, "f.webp"), db.moment_post(cid, me, "m.webp")
    notif_about_me, notif_unrelated = (
        str(db.one(
            "INSERT INTO public.notifications (user_id, actor_id, type, body) "
            "VALUES (:to, :by, 'x', 'b') RETURNING id", to=friend, by=by,
        )[0])
        for by in (me, friend)
    )

    as_user(me)
    assert (await client.delete("/auth/me")).status_code == 200

    assert db.status("circles", cid) == 1
    for table, row in [
        ("intents", mine), ("intents", theirs), ("moment_posts", my_post), ("moment_posts", their_post),
        ("reactions", their_reaction_on_mine), ("notifications", notif_unrelated), ("users", friend),
    ]:
        assert db.status(table, row) == 1, table
    for table, row in [
        ("reactions", my_reaction_on_theirs), ("intent_boosts", my_boost_on_theirs),
        ("notifications", notif_about_me),
    ]:
        assert db.status(table, row) == -1, table
    # Photos of content that stays are kept; only the avatar goes.
    assert set(dict(db.file_calls)) == {"avatars"}

    # The friend still sees it all, credited to "Deleted user", never the scrubbed email.
    as_user(friend)
    intents = (await client.get(f"/circles/{cid}/intents")).json()["items"]
    assert {i["id"] for i in intents} >= {mine, theirs}
    mid = db.one("SELECT CAST(moment_id AS text) FROM public.moment_posts WHERE id = :p", p=my_post)[0]
    moment = (await client.get(f"/moments/{mid}")).json()
    authors = {p["id"]: (p["display_name"], p["avatar_url"]) for p in moment["posts"]}
    assert authors[my_post] == ("Deleted user", None)
    assert authors[their_post][0] == "bina"
    assert (await client.post(f"/moments/posts/{my_post}/someday")).json()["note"].startswith(
        "From Deleted user's"
    )

    scrubbed = f"deleted-{me}@deleted.invalid"
    for path in [
        "/circles", f"/circles/{cid}", f"/circles/{cid}/intents", f"/intents/{mine}",
        f"/circles/{cid}/moments", f"/moments/{mid}", "/notifications",
    ]:
        resp = await client.get(path)
        assert resp.status_code == 200, path
        assert scrubbed not in resp.text and "deleted.invalid" not in resp.text, path


async def test_cleanup_failure_does_not_fail_the_request(client, db, as_user, monkeypatch):
    me = db.user("asha")
    monkeypatch.setattr(account_helper, "delete_auth_user", lambda uid: False)
    as_user(me)
    assert (await client.delete("/auth/me")).status_code == 200
    assert db.one("SELECT status FROM public.users WHERE id = :u", u=me)[0] == -1
