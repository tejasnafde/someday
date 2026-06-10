"""DBUtil — base class for all handlers."""

import json
import time
import uuid

import pandas as pd
from sqlalchemy import create_engine
from sqlalchemy import text as sql_text
from sqlalchemy.pool import QueuePool

from app_util.log_util import errorlogger, infologger
from config.settings import settings


def row_to_dict(row) -> dict:
    """Convert a SQLAlchemy row to a dict with UUIDs pre-cast to str.

    pandas' ujson serialiser can't handle uuid.UUID objects so we convert
    them before the row enters a DataFrame. datetime and everything else
    is left as-is for pandas to handle via to_json(date_format='iso').
    """
    return {k: str(v) if isinstance(v, uuid.UUID) else v for k, v in row._mapping.items()}


def df_to_records(df: pd.DataFrame) -> list[dict]:
    """Convert a DataFrame to a JSON-safe list of dicts via pandas serialiser.

    date_format='iso' keeps timestamps as readable ISO strings.
    NaN → None, numpy scalars → Python primitives — all handled by pandas.
    """
    if df.empty:
        return []
    return json.loads(df.to_json(orient="records", date_format="iso"))


class DBUtil:
    engine = None

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

    def execute_query_with_value(self, query: str, params: dict) -> list[dict]:
        infologger.debug(f"DB_QUERY | {query.strip()}")
        infologger.debug(f"DB_PARAMS | {params}")
        t0 = time.perf_counter()
        try:
            with self.get_connection() as conn:
                result = conn.execute(sql_text(query), params)
                rows = [row_to_dict(row) for row in result]
            df = pd.DataFrame(rows) if rows else pd.DataFrame()
            ms = (time.perf_counter() - t0) * 1000
            infologger.debug(f"DB_RESULT | {len(df)} rows | {ms:.1f}ms")
            return df_to_records(df)
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
            if not row:
                infologger.debug(f"DB_RESULT | 0 rows returned | {ms:.1f}ms")
                return {}
            df = pd.DataFrame([row_to_dict(row)])
            infologger.debug(f"DB_RESULT | 1 row returned | {ms:.1f}ms")
            return df_to_records(df)[0]
        except Exception as exc:
            errorlogger.error(
                f"DB_ERROR | {exc} | query={query.strip()[:200]}",
                exc_info=True,
            )
            raise
