"""Test configuration — env vars must be set before importing app modules."""

import os

import pytest
from httpx import ASGITransport, AsyncClient

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
def mock_jwt():
    """Bypass JWT verification — returns a synthetic user payload.

    Monkeypatching the module attribute does not work because FastAPI captures
    the dependency callable at import time; dependency_overrides is the
    supported seam.
    """
    test_user = {
        "sub": "00000000-0000-0000-0000-000000000001",
        "email": "test@example.com",
        "role": "authenticated",
    }
    from common_helper.auth_helper import verify_supabase_jwt
    app.dependency_overrides[verify_supabase_jwt] = lambda: test_user
    yield test_user
    app.dependency_overrides.pop(verify_supabase_jwt, None)
