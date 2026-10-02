"""Every table that references public.users must be handled by account deletion.

Static, like test_rls_coverage: it parses the migrations, so it runs in CI
with no database. A new table holding a user_id fails here until
account_queries.py soft-deletes (or deliberately handles) its rows.
"""

import re
from pathlib import Path

from modules.account import account_queries

MIGRATIONS = Path(__file__).resolve().parents[2] / "supabase" / "migrations"


def tables_referencing_users() -> set[str]:
    sql = "\n".join(p.read_text() for p in sorted(MIGRATIONS.glob("*.sql")))
    tables = set()
    for match in re.finditer(r"CREATE TABLE IF NOT EXISTS public\.(\w+)\s*\((.*?)\n\);", sql, re.S):
        if "REFERENCES public.users" in match.group(2):
            tables.add(match.group(1))
    return tables


def test_parser_sees_known_tables():
    assert {"circles", "intents", "notifications", "moment_posts"} <= tables_referencing_users()


def test_every_user_table_is_covered_by_deletion():
    queries = "\n".join(v for k, v in vars(account_queries).items() if k.isupper())
    missing = {t for t in tables_referencing_users() if f"public.{t} " not in queries}
    assert not missing, f"account deletion ignores {sorted(missing)} - add it to account_queries.py"
