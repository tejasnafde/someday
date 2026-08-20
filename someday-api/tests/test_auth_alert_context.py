import hashlib
from datetime import UTC, datetime

import jwt
import pytest
from fastapi import HTTPException
from fastapi.security import HTTPAuthorizationCredentials
from jwt.exceptions import PyJWKClientConnectionError, PyJWKClientError
from starlette.requests import Request

from common_helper import auth_helper


def test_token_diagnostics_are_correlatable_and_secret_safe():
    expires_at = datetime(2026, 8, 19, 10, 0, tzinfo=UTC)
    token = jwt.encode(
        {"sub": "user-123", "email": "person@example.com", "exp": expires_at},
        "test-secret-that-is-at-least-32-bytes",
        algorithm="HS256",
    )

    diagnostics = auth_helper.token_diagnostics(token)

    assert diagnostics == {
        "fingerprint": f"sha256:{hashlib.sha256(token.encode()).hexdigest()[:12]}",
        "token_length": len(token),
        "segments": 3,
        "subject": "user-123",
        "email": "person@example.com",
        "expires_at": "2026-08-19T10:00:00+00:00",
    }
    assert token not in str(diagnostics)


def test_jwt_failures_are_classified_for_actionable_alerts():
    cases = [
        (jwt.ExpiredSignatureError("expired"), "expired"),
        (jwt.InvalidSignatureError("bad signature"), "invalid_signature"),
        (jwt.DecodeError("not enough segments"), "malformed"),
        (PyJWKClientConnectionError("network down"), "jwks_unavailable"),
        (PyJWKClientError("Unable to find a signing key that matches"), "unknown_signing_key"),
        (jwt.InvalidAudienceError("wrong aud"), "invalid_audience"),
    ]

    assert [(auth_helper.classify_jwt_error(exc)) for exc, _ in cases] == [
        expected for _, expected in cases
    ]


def test_jwt_verification_attaches_failure_context_to_the_request(monkeypatch):
    token = "bogus.jwt"
    request = Request({"type": "http", "method": "GET", "path": "/circles", "headers": []})

    def reject(_token):
        raise jwt.DecodeError("Not enough segments")

    monkeypatch.setattr(auth_helper.jwks_client, "get_signing_key_from_jwt", reject)

    with pytest.raises(HTTPException) as raised:
        auth_helper.verify_supabase_jwt(
            request,
            HTTPAuthorizationCredentials(scheme="Bearer", credentials=token),
        )

    assert raised.value.status_code == 401
    assert request.state.auth_alert == {
        "verification": "failed",
        "fingerprint": f"sha256:{hashlib.sha256(token.encode()).hexdigest()[:12]}",
        "token_length": len(token),
        "segments": 2,
        "reason": "malformed",
    }
