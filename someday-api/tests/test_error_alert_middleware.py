import jwt
import pytest
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from httpx import ASGITransport, AsyncClient

from common_helper import auth_helper, error_alert
from routers import auth_router


@pytest.mark.anyio
async def test_middleware_reports_the_error_body_and_request_context_without_changing_response(
    monkeypatch,
):
    captured = []
    monkeypatch.setattr(error_alert, "discord_alert", lambda *args, **kwargs: captured.append(kwargs))

    app = FastAPI()
    app.add_middleware(error_alert.StructuredErrorAlertMiddleware)

    @app.get("/failure")
    async def failure(request: Request):
        request.state.auth_alert = {"reason": "malformed", "fingerprint": "sha256:abc123"}
        return JSONResponse(status_code=401, content={"detail": "Invalid or expired token"})

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get(
            "/failure",
            headers={
                "X-Someday-Client": "native/1.15.0",
                "X-Cloud-Trace-Context": "trace-123/span-456;o=1",
                "User-Agent": "okhttp/5",
            },
        )

    assert response.status_code == 401
    assert response.json() == {"detail": "Invalid or expired token"}
    assert len(captured) == 1
    assert captured[0]["status"] == 401
    assert captured[0]["method"] == "GET"
    assert captured[0]["path"] == "/failure"
    assert captured[0]["error_message"] == "Invalid or expired token"
    assert captured[0]["request_id"] == "trace-123"
    assert captured[0]["client"] == "native/1.15.0"
    assert captured[0]["user_agent"] == "okhttp/5"
    assert captured[0]["auth_context"] == {
        "reason": "malformed",
        "fingerprint": "sha256:abc123",
    }
    assert captured[0]["duration_ms"] >= 0


@pytest.mark.anyio
async def test_production_app_emits_one_structured_alert_for_a_malformed_jwt(client, monkeypatch):
    captured = []
    monkeypatch.setattr(error_alert, "discord_alert", lambda *args, **kwargs: captured.append(kwargs))

    def reject(_token):
        raise jwt.DecodeError("Not enough segments")

    monkeypatch.setattr(auth_helper.jwks_client, "get_signing_key_from_jwt", reject)

    response = await client.get(
        "/circles",
        headers={
            "Authorization": "Bearer bogus.jwt",
            "X-Someday-Client": "native/1.15.0",
        },
    )

    assert response.status_code == 401
    assert len(captured) == 1
    assert captured[0]["error_message"] == "Invalid or expired token"
    assert captured[0]["auth_context"]["reason"] == "malformed"
    assert captured[0]["auth_context"]["segments"] == 2
    assert "bogus.jwt" not in str(captured[0])


@pytest.mark.anyio
async def test_middleware_alerts_once_for_an_unhandled_exception(monkeypatch):
    captured = []
    monkeypatch.setattr(error_alert, "discord_alert", lambda *args, **kwargs: captured.append(kwargs))

    app = FastAPI()
    app.add_middleware(error_alert.StructuredErrorAlertMiddleware)

    @app.get("/explode")
    async def explode():
        raise RuntimeError("database unavailable")

    async with AsyncClient(
        transport=ASGITransport(app=app, raise_app_exceptions=False),
        base_url="http://test",
    ) as client:
        response = await client.get("/explode")

    assert response.status_code == 500
    assert len(captured) == 1
    assert captured[0]["status"] == 500
    assert captured[0]["error_message"] == "database unavailable"
    assert isinstance(captured[0]["exc"], RuntimeError)


@pytest.mark.anyio
async def test_middleware_explains_a_401_with_no_credentials(monkeypatch):
    captured = []
    monkeypatch.setattr(error_alert, "discord_alert", lambda *args, **kwargs: captured.append(kwargs))

    app = FastAPI()
    app.add_middleware(error_alert.StructuredErrorAlertMiddleware)

    @app.get("/private")
    async def private():
        return JSONResponse(status_code=401, content={"detail": "Not authenticated"})

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        await client.get("/private")

    assert captured[0]["auth_context"] == {"reason": "missing_credentials"}


@pytest.mark.anyio
async def test_middleware_uses_the_route_template_instead_of_sensitive_path_values(monkeypatch):
    captured = []
    monkeypatch.setattr(error_alert, "discord_alert", lambda *args, **kwargs: captured.append(kwargs))

    app = FastAPI()
    app.add_middleware(error_alert.StructuredErrorAlertMiddleware)

    @app.get("/join/{invite_token}")
    async def join(invite_token: str):
        return JSONResponse(status_code=400, content={"message": "invalid invite"})

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        await client.get("/join/super-secret-invite")

    assert captured[0]["path"] == "/join/{invite_token}"
    assert "super-secret-invite" not in str(captured[0])


@pytest.mark.anyio
async def test_client_reported_errors_include_the_reporting_client(client, monkeypatch):
    captured = []
    monkeypatch.setattr(auth_router, "discord_alert", lambda *args, **kwargs: captured.append((args, kwargs)))

    response = await client.post(
        "/auth/client-error",
        headers={"X-Someday-Client": "web", "User-Agent": "Chrome/Test"},
        json={"context": "google_oauth_exchange", "message": "exchange failed"},
    )

    assert response.status_code == 200
    assert len(captured) == 1
    args, kwargs = captured[0]
    assert args == (400, "CLIENT", "/auth/client-error")
    assert kwargs["error_message"] == "google_oauth_exchange: exchange failed"
    assert kwargs["client"] == "web"
    assert kwargs["user_agent"] == "Chrome/Test"
