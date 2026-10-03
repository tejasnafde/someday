"""Every column that references public.users must be handled by account deletion.

Static, like test_rls_coverage: it parses the migrations, so it runs in CI
with no database. A new table or column holding a user id fails here until
account_queries.py either touches it with `<column> = :user_id` in a query on
that table, or lists it in RETAINED_USER_COLUMNS as content that stays.
"""

import re
from pathlib import Path

from modules.account import account_queries

MIGRATIONS = Path(__file__).resolve().parents[2] / "supabase" / "migrations"
REF = "REFERENCES public.users"


def columns_referencing_users() -> set[str]:
    sql = "\n".join(p.read_text() for p in sorted(MIGRATIONS.glob("*.sql")))
    columns = set()
    for match in re.finditer(r"CREATE TABLE IF NOT EXISTS public\.(\w+)\s*\((.*?)\n\);", sql, re.S):
        for line in match.group(2).splitlines():
            if REF in line:
                columns.add(f"{match.group(1)}.{line.split()[0]}")
    for match in re.finditer(rf"ALTER TABLE (?:IF EXISTS )?public\.(\w+)\s+ADD COLUMN (?:IF NOT EXISTS )?(\w+)[^;]*{REF}", sql):
        columns.add(f"{match.group(1)}.{match.group(2)}")
    return columns


def is_handled(column: str, queries: list[str]) -> bool:
    table, col = column.split(".")
    touches = re.compile(rf"\b(?:\w+\.)?{col} = :user_id\b")
    return any(f"public.{table} " in qs and touches.search(qs) for qs in queries)


def test_parser_sees_known_columns():
    assert {
        "circles.owner_id", "intents.created_by", "notifications.actor_id", "moment_posts.user_id",
    } <= columns_referencing_users()


def test_every_user_column_is_handled_by_deletion():
    queries = [v for k, v in vars(account_queries).items() if k.isupper() and isinstance(v, str)]
    missing = {
        c for c in columns_referencing_users()
        if c not in account_queries.RETAINED_USER_COLUMNS and not is_handled(c, queries)
    }
    assert not missing, f"account deletion ignores {sorted(missing)} - handle it in account_queries.py"


def test_retained_columns_are_real():
    assert set(account_queries.RETAINED_USER_COLUMNS) <= columns_referencing_users()
