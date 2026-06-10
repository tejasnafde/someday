"""DBUtil — base class for all handlers."""

import time
import uuid
from datetime import datetime

from sqlalchemy import create_engine
from sqlalchemy import text as sql_text
from sqlalchemy.pool import QueuePool

from app_util.log_util import errorlogger, infologger
from config.settings import settings


def serialize_row(row) -> dict:
    """Convert a SQLAlchemy row to a JSON-safe dict.

    SQLAlchemy returns uuid.UUID and datetime objects for Postgres uuid/timestamptz
    columns. JSONResponse can't serialize those — convert them to str here once
    rather than in every handler.
    """
    result = {}
    for k, v in row._mapping.items():
        if isinstance(v, uuid.UUID):
            result[k] = str(v)
        elif isinstance(v, datetime):
            result[k] = v.isoformat()
        else:
            result[k] = v
    return result


class DBUtil:
    engine = None

    # ── Lifecycle ────────────────────────────────────────────────────────────

    @classmethod
    def init_engine(cls) -> None:
        if cls.engine is not None:
            return
        cls.engine = create_engine(
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
        if DBUtil.engine is None:
            DBUtil.init_engine()
        return DBUtil.engine.connect()

    # ── Query helpers ─────────────────────────────────────────────────────────

    def execute_query_with_value(self, query: str, params: dict) -> list[dict]:
        infologger.debug(f"DB_QUERY | {query.strip()}")
        infologger.debug(f"DB_PARAMS | {params}")
        t0 = time.perf_counter()
        try:
            with self.get_connection() as conn:
                result = conn.execute(sql_text(query), params)
                rows = [serialize_row(row) for row in result]
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
        infologger.debug(f"DB_QUERY | {query.strip()}")
        infologger.debug(f"DB_PARAMS | {params}")
        t0 = time.perf_counter()
        try:
            with self.get_connection() as conn:
                conn.execute(sql_text(query), params)
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
        infologger.debug(f"DB_QUERY | {query.strip()}")
        infologger.debug(f"DB_PARAMS | {params}")
        t0 = time.perf_counter()
        try:
            with self.get_connection() as conn:
                result = conn.execute(sql_text(query), params)
                conn.commit()
                row = result.fetchone()
            ms = (time.perf_counter() - t0) * 1000
            infologger.debug(f"DB_RESULT | {'1 row' if row else '0 rows'} returned | {ms:.1f}ms")
            return serialize_row(row) if row else {}
        except Exception as exc:
            errorlogger.error(
                f"DB_ERROR | {exc} | query={query.strip()[:200]}",
                exc_info=True,
            )
            raise
