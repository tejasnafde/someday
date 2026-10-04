"""Sign in with Apple token revocation on account deletion (no DB, no network)."""

import json

import httpx
import jwt
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import ec

from config.settings import settings
from handler.auth_handler import AuthHandler
from modules.account import account_helper

PRIVATE = ec.generate_private_key(ec.SECP256R1())
P8 = PRIVATE.private_bytes(
    serialization.Encoding.PEM, serialization.PrivateFormat.PKCS8, serialization.NoEncryption()
).decode()
KEY = {"key_id": "KID123", "team_id": "TEAM123", "client_id": "app.someday.capture", "p8": P8}
APPLE = {"sub": "u1", "app_metadata": {"provider": "apple", "providers": ["apple"]}}
GOOGLE = {"sub": "u1", "app_metadata": {"provider": "google", "providers": ["google"]}}


def fake_apple(monkeypatch, revoke_status=200):
    """Route safe_client to a MockTransport and record every Apple call."""
    calls = []

    def handler(request: httpx.Request) -> httpx.Response:
        form = dict(httpx.QueryParams(request.content.decode()))
        calls.append((str(request.url), form))
        if str(request.url) == settings.APPLE_TOKEN_URL:
            return httpx.Response(200, json={"refresh_token": "r-tok", "access_token": "a-tok"})
        return httpx.Response(revoke_status, json={} if revoke_status == 200 else {"error": "invalid_client"})

    monkeypatch.setattr(settings, "SOMEDAY_SIWA_KEY", json.dumps(KEY))
    monkeypatch.setattr(account_helper, "safe_client", lambda **kw: httpx.Client(transport=httpx.MockTransport(handler)))
    return calls


def stub_deletion(monkeypatch):
    deleted = []
    monkeypatch.setattr(account_helper, "delete_account_rows", lambda db, uid: deleted.append(uid) or {
        "files": {}, "transferred": [], "deleted_circles": []})
    monkeypatch.setattr(account_helper, "delete_auth_user", lambda uid: True)
    monkeypatch.setattr(account_helper, "delete_files", lambda uid, files: None)
    return deleted


def test_client_secret_claims_and_headers():
    token = account_helper.apple_client_secret(KEY, now=1_000)
    header = jwt.get_unverified_header(token)
    assert header["alg"] == "ES256" and header["kid"] == "KID123"
    claims = jwt.decode(token, PRIVATE.public_key(), algorithms=["ES256"], audience="https://appleid.apple.com",
                        options={"verify_exp": False})
    assert claims == {"iss": "TEAM123", "sub": "app.someday.capture", "aud": "https://appleid.apple.com",
                      "iat": 1_000, "exp": 1_000 + settings.APPLE_CLIENT_SECRET_TTL_SECONDS}


def test_code_is_exchanged_then_refresh_token_revoked(monkeypatch):
    calls = fake_apple(monkeypatch)
    deleted = stub_deletion(monkeypatch)
    status, _ = AuthHandler().delete_account("u1", APPLE, "auth-code")
    assert status == 200 and deleted == ["u1"]
    (token_url, token_form), (revoke_url, revoke_form) = calls
    assert token_url == settings.APPLE_TOKEN_URL
    assert token_form["code"] == "auth-code" and token_form["grant_type"] == "authorization_code"
    assert token_form["client_id"] == "app.someday.capture" and token_form["client_secret"]
    assert revoke_url == settings.APPLE_REVOKE_URL
    assert revoke_form["token"] == "r-tok" and revoke_form["token_type_hint"] == "refresh_token"


def test_revoke_failure_still_deletes(monkeypatch):
    calls = fake_apple(monkeypatch, revoke_status=400)
    deleted = stub_deletion(monkeypatch)
    status, _ = AuthHandler().delete_account("u1", APPLE, "auth-code")
    assert status == 200 and deleted == ["u1"] and len(calls) == 2


def test_non_apple_user_never_calls_apple(monkeypatch):
    calls = fake_apple(monkeypatch)
    deleted = stub_deletion(monkeypatch)
    # Even a client that sends a code cannot make a Google user trigger Apple calls.
    status, _ = AuthHandler().delete_account("u1", GOOGLE, "auth-code")
    assert status == 200 and deleted == ["u1"] and calls == []


def test_apple_user_without_code_still_deletes(monkeypatch):
    calls = fake_apple(monkeypatch)
    deleted = stub_deletion(monkeypatch)
    status, _ = AuthHandler().delete_account("u1", APPLE)
    assert status == 200 and deleted == ["u1"] and calls == []
