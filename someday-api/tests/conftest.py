"""
Test configuration.

Tests use httpx.AsyncClient against the FastAPI app.
DB calls are mocked at the DBUtil level — no real Supabase connection needed.

Env vars are loaded from .env.test if it exists, otherwise inline defaults below.
"""

import os
import pytest
from httpx import AsyncClient, ASGITransport
from unittest.mock import MagicMock, patch

# Set test env before importing app modules that read settings
os.environ.setdefault("APP_ENV", "test")
os.environ.setdefault("SUPABASE_URL", "https://test.supabase.co")
os.environ.setdefault("SUPABASE_ANON_KEY", "test-anon-key")
os.environ.setdefault("SUPABASE_JWT_SECRET", "test-jwt-secret-32-chars-minimum!!")
os.environ.setdefault("DATABASE_URL", "postgresql://test:test@localhost:5432/test")
os.environ.setdefault("LOG_LEVEL", "WARNING")

from main import app  # noqa: E402 — must come after env setup


@pytest.fixture
def anyio_backend():
    return "asyncio"


@pytest.fixture
async def client():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        yield ac


@pytest.fixture
def mock_jwt(monkeypatch):
    """Bypass JWT verification — returns a synthetic user payload."""
    test_user = {
        "sub": "00000000-0000-0000-0000-000000000001",
        "email": "test@example.com",
        "role": "authenticated",
    }
    import common_helper.auth_helper as auth
    monkeypatch.setattr(auth, "verify_supabase_jwt", lambda credentials: test_user)
    return test_user
