"""Every table in the public schema must have RLS enabled by some migration.

This exists because the same mistake shipped twice. Tables added after the
initial schema missed ENABLE ROW LEVEL SECURITY, and both times Supabase's
security advisor found it rather than we did:

  2026-07-29  notifications, web_push_subscriptions
  2026-09-16  circle_moments, moment_pings, moment_posts

The second time was verified exploitable against production. The anon key is
published on purpose (someday-app/app.json and the web bundle both carry it),
and a plain PostgREST call with it returned real rows. anon also held INSERT,
UPDATE, DELETE and TRUNCATE on those tables.

The fix after the first occurrence was a comment asking the next author to
remember. That failed, so this is a check instead.

It is deliberately STATIC - it parses the migration SQL and needs no database.
CI runs pytest with DATABASE_URL pointing at a throwaway localhost, so a test
that queried the real schema could not run there, and a check that only runs
on someone's laptop is the kind that stops running.

RLS with zero policies is the correct end state for this project. Nothing
client-side queries these tables through supabase-js; the FastAPI backend
connects as `postgres`, which has rolbypassrls = true and is unaffected. So
this test asserts RLS is enabled, and says nothing about policies.
"""

import re
from pathlib import Path

MIGRATIONS = Path(__file__).resolve().parent.parent / "supabase" / "migrations"

CREATE_TABLE = re.compile(
    r"CREATE\s+TABLE\s+(?:IF\s+NOT\s+EXISTS\s+)?public\.(\w+)", re.IGNORECASE
)
ENABLE_RLS = re.compile(
    r"ALTER\s+TABLE\s+public\.(\w+)\s+ENABLE\s+ROW\s+LEVEL\s+SECURITY", re.IGNORECASE
)


def strip_sql_comments(sql: str) -> str:
    """Drop -- line comments so prose in a migration header cannot match.

    The RLS migrations explain themselves at length and name tables while doing
    it, so without this a comment mentioning a table would satisfy the check.
    """
    return re.sub(r"--[^\n]*", "", sql)


def read_migrations() -> str:
    files = sorted(MIGRATIONS.glob("*.sql"))
    assert files, f"no migrations found in {MIGRATIONS}"
    return strip_sql_comments("\n".join(f.read_text() for f in files))


def test_every_public_table_enables_rls():
    sql = read_migrations()
    created = set(CREATE_TABLE.findall(sql))
    protected = set(ENABLE_RLS.findall(sql))

    unprotected = sorted(created - protected)
    assert not unprotected, (
        "These public tables are created by a migration but never get "
        f"ENABLE ROW LEVEL SECURITY: {unprotected}. "
        "Anyone holding the published anon key can read and write them through "
        "PostgREST. Add 'ALTER TABLE public.<name> ENABLE ROW LEVEL SECURITY;' "
        "to the migration that creates the table."
    )


def test_rls_statements_reference_real_tables():
    """Guard the guard: a typo in a table name would silently protect nothing."""
    sql = read_migrations()
    created = set(CREATE_TABLE.findall(sql))
    protected = set(ENABLE_RLS.findall(sql))

    unknown = sorted(protected - created)
    assert not unknown, (
        f"ENABLE ROW LEVEL SECURITY names tables no migration creates: {unknown}. "
        "Check for a typo - the statement would apply to nothing."
    )
