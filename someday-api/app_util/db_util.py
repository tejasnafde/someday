"""
DBUtil — base class for all handlers.

Every handler extends DBUtil and calls its query methods.
Query methods log automatically — handlers must never log SQL manually.

Logging contract (see CLAUDE.md):
    DEBUG  DB_QUERY   — SQL string before execution
    DEBUG  DB_PARAMS  — bound parameter dict
    DEBUG  DB_RESULT  — row count + duration
    ERROR  DB_ERROR   — exception + truncated query string

Connection:
    Single Supabase Postgres engine with connection pooling.
    Call DBUtil.init_engine() once at startup (see main.py).
"""

import time

from sqlalchemy import create_engine, text
from sqlalchemy.pool import QueuePool

from app_util.log_util import errorlogger, infologger
from config.settings import settings


class DBUtil:
    _engine = None

    # ── Lifecycle ────────────────────────────────────────────────────────────

    @classmethod
    def init_engine(cls) -> None:
        if cls._engine is not None:
            return
        cls._engine = create_engine(
            settings.DATABASE_URL,
            poolclass=QueuePool,
            pool_size=5,
            max_overflow=10,
            pool_pre_ping=True,
            pool_recycle=3600,
            echo=False,
        )
        infologger.info("DB_ENGINE_INIT | Connection pool created")

    def get_connection(self):
        if DBUtil._engine is None:
            DBUtil.init_engine()
        return DBUtil._engine.connect()

    # ── Query helpers ─────────────────────────────────────────────────────────

    def execute_query_with_value(self, query: str, params: dict) -> list[dict]:
        """
        Execute a SELECT query. Returns list of row dicts.
        Always filters status = 1 in the SQL itself — not enforced here.
        """
        infologger.debug(f"DB_QUERY | {query.strip()}")
        infologger.debug(f"DB_PARAMS | {params}")
        t0 = time.perf_counter()
        try:
            with self.get_connection() as conn:
                result = conn.execute(text(query), params)
                rows = [dict(row._mapping) for row in result]
            ms = (time.perf_counter() - t0) * 1000
            infologger.debug(f"DB_RESULT | {len(rows)} rows | {ms:.1f}ms")
            return rows
        except Exception as exc:
            errorlogger.error(
                f"DB_ERROR | {exc} | query={query.strip()[:200]}",
                exc_info=True,
            )
            raise

    def execute_query_with_value_without_output(self, query: str, params: dict) -> None:
        """
        Execute INSERT / UPDATE / DELETE with no return value.
        Commits automatically.
        """
        infologger.debug(f"DB_QUERY | {query.strip()}")
        infologger.debug(f"DB_PARAMS | {params}")
        t0 = time.perf_counter()
        try:
            with self.get_connection() as conn:
                conn.execute(text(query), params)
                conn.commit()
            ms = (time.perf_counter() - t0) * 1000
            infologger.debug(f"DB_EXEC_DONE | {ms:.1f}ms")
        except Exception as exc:
            errorlogger.error(
                f"DB_ERROR | {exc} | query={query.strip()[:200]}",
                exc_info=True,
            )
            raise

    def execute_query_with_value_returning(self, query: str, params: dict) -> dict:
        """
        Execute INSERT ... RETURNING or UPDATE ... RETURNING.
        Returns the first row as a dict, or {} if nothing returned.
        Commits automatically.
        """
        infologger.debug(f"DB_QUERY | {query.strip()}")
        infologger.debug(f"DB_PARAMS | {params}")
        t0 = time.perf_counter()
        try:
            with self.get_connection() as conn:
                result = conn.execute(text(query), params)
                conn.commit()
                row = result.fetchone()
            ms = (time.perf_counter() - t0) * 1000
            infologger.debug(f"DB_RESULT | {'1 row' if row else '0 rows'} returned | {ms:.1f}ms")
            return dict(row._mapping) if row else {}
        except Exception as exc:
            errorlogger.error(
                f"DB_ERROR | {exc} | query={query.strip()[:200]}",
                exc_info=True,
            )
            raise
