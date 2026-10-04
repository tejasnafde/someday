"""Sign in with Apple "Hide my email" users carry a privaterelay.appleid.com
address. The API must store it and mint the WebView session for it unchanged."""

import httpx

from app_util.db_util import DBUtil
from config.settings import settings
from handler.auth_handler import AuthHandler

RELAY = "x7k2qpz9ab@privaterelay.appleid.com"


def test_verify_stores_relay_email(monkeypatch):
    seen = {}

    def fake_returning(self, q, p):
        seen.update(p)
        return {"id": p["id"], "email": p["email"], "display_name": p["display_name"], "avatar_url": None}

    monkeypatch.setattr(DBUtil, "execute_query_with_value_returning", fake_returning)
    status, result = AuthHandler().verify("u1", RELAY)
    assert status == 200
    assert seen["email"] == RELAY
    assert seen["display_name"] == "x7k2qpz9ab"


def test_webview_session_mints_for_relay_email(monkeypatch):
    sent = []

    def fake_post(url, headers, json, timeout):
        sent.append(json)
        body = {"hashed_token": "h"} if url.endswith("generate_link") else {"access_token": "a", "refresh_token": "r"}
        return httpx.Response(200, json=body, request=httpx.Request("POST", url))

    monkeypatch.setattr(settings, "SUPABASE_SERVICE_ROLE_KEY", "service-key")
    monkeypatch.setattr("modules.account.account_helper.is_deleted_user", lambda db, uid: False)
    monkeypatch.setattr(httpx, "post", fake_post)
    status, result = AuthHandler().webview_session("u1", RELAY)
    assert status == 200
    assert sent[0]["email"] == RELAY
