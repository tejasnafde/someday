import time

import httpx

from app_util.db_util import DBUtil
from app_util.log_util import infologger, errorlogger
from common_helper.decorators import log_timing
from common_helper.storage_helper import upload_public_image
from config.settings import settings
from modules.account import account_helper as ah
from modules.circles import circles_helper as ch


UPSERT_USER = """
    INSERT INTO public.users (id, email, display_name, status)
    VALUES (:id, :email, :display_name, 1)
    ON CONFLICT (id) DO UPDATE
        SET email = EXCLUDED.email
        -- A deleted account keeps its scrubbed row: never write the email back.
        WHERE public.users.status <> -1
    RETURNING id, email, display_name, avatar_url
"""

SET_PUSH_TOKEN = """
    UPDATE public.users SET push_token = :token WHERE id = :user_id AND status = 1
"""

GET_USER = """
    SELECT id, email, display_name, avatar_url, city, tour_state
    FROM public.users
    WHERE id = :user_id AND status = 1
"""

UPDATE_USER = """
    UPDATE public.users
    SET display_name = COALESCE(:display_name, display_name),
        avatar_url   = COALESCE(:avatar_url, avatar_url),
        -- Tri-state: NULL preserves, empty string clears, value sets.
        city = CASE WHEN :city IS NULL THEN city
                    WHEN :city = '' THEN NULL
                    ELSE :city END
    WHERE id = :user_id AND status = 1
    RETURNING id, email, display_name, avatar_url, city
"""


class AuthHandler(DBUtil):

    @log_timing("auth_handler.verify")
    def verify(self, user_id: str, email: str) -> tuple[int, dict]:
        infologger.info(f"AuthHandler.verify | user_id={user_id} email={email}")
        user = self.execute_query_with_value_returning(
            UPSERT_USER,
            {"id": user_id, "email": email, "display_name": email.split("@")[0]},
        )
        if not user:
            infologger.warning(f"AuthHandler.verify | account deleted | user_id={user_id}")
            return 410, "This account was deleted"
        infologger.info(f"AuthHandler.verify | upserted user_id={user_id}")
        return 200, {"user": user}

    @log_timing("auth_handler.update_me")
    def update_me(
        self, user_id: str, display_name: str | None, avatar_url: str | None, city: str | None = None
    ) -> tuple[int, dict | str]:
        infologger.info(f"AuthHandler.update_me | user_id={user_id} display_name={display_name!r} city={city!r}")
        user = self.execute_query_with_value_returning(
            UPDATE_USER,
            {"user_id": user_id, "display_name": display_name, "avatar_url": avatar_url, "city": city},
        )
        if not user:
            return 404, "User not found"
        return 200, {"user": user}

    @log_timing("auth_handler.upload_avatar")
    def upload_avatar(self, user_id: str, content: bytes, content_type: str) -> tuple[int, dict | str]:
        infologger.info(f"AuthHandler.upload_avatar | user_id={user_id} bytes={len(content)}")
        ext = {"image/webp": "webp", "image/jpeg": "jpg", "image/png": "png"}.get(content_type)
        if not ext:
            return 400, "Image must be webp, jpeg, or png"
        url = upload_public_image("avatars", f"{user_id}.{ext}", content, content_type)
        if not url:
            return 502, "Upload failed"
        busted = f"{url}?v={int(time.time())}"
        user = self.execute_query_with_value_returning(
            UPDATE_USER, {"user_id": user_id, "display_name": None, "avatar_url": busted}
        )
        return 200, {"user": user}

    @log_timing("auth_handler.webview_session")
    def webview_session(self, user_id: str, email: str) -> tuple[int, dict | str]:
        """
        Mint an independent Supabase session for the mobile WebView.

        Supabase rotates refresh tokens: if the native app and the WebView
        share one session, the first refresh invalidates the other and
        reuse-detection revokes the whole family - both get signed out.
        A separately minted session has its own refresh-token family.
        """
        infologger.info(f"AuthHandler.webview_session | user_id={user_id} email={email}")
        # A native token outlives the deletion by up to an hour. Minting a
        # magic link for its email would sign a fresh account in.
        if ah.is_deleted_user(self, user_id):
            infologger.warning(f"AuthHandler.webview_session | account deleted | user_id={user_id}")
            return 410, "This account was deleted"
        if not settings.SUPABASE_SERVICE_ROLE_KEY:
            errorlogger.error("AuthHandler.webview_session | SUPABASE_SERVICE_ROLE_KEY not configured")
            return 500, "Server is not configured for webview sessions"
        try:
            admin_headers = {
                "apikey": settings.SUPABASE_SERVICE_ROLE_KEY,
                "Authorization": f"Bearer {settings.SUPABASE_SERVICE_ROLE_KEY}",
            }
            link = httpx.post(
                f"{settings.SUPABASE_URL}/auth/v1/admin/generate_link",
                headers=admin_headers,
                json={"type": "magiclink", "email": email},
                timeout=15,
            )
            link.raise_for_status()
            session = httpx.post(
                f"{settings.SUPABASE_URL}/auth/v1/verify",
                headers={"apikey": settings.SUPABASE_ANON_KEY},
                json={"type": "magiclink", "token_hash": link.json()["hashed_token"]},
                timeout=15,
            )
            session.raise_for_status()
            data = session.json()
            infologger.info(f"AuthHandler.webview_session | minted independent session | email={email}")
            return 200, {
                "access_token": data["access_token"],
                "refresh_token": data["refresh_token"],
            }
        except httpx.HTTPError as exc:
            errorlogger.error(f"AuthHandler.webview_session | supabase error | {exc}", exc_info=True)
            return 502, "Could not mint webview session"

    @log_timing("auth_handler.set_push_token")
    def set_push_token(self, user_id: str, token: str | None) -> tuple[int, str]:
        infologger.info(f"AuthHandler.set_push_token | user_id={user_id} set={'yes' if token else 'cleared'}")
        self.execute_query_with_value_without_output(SET_PUSH_TOKEN, {"user_id": user_id, "token": token})
        return 200, "ok"

    @log_timing("auth_handler.get_me")
    def get_me(self, user_id: str) -> tuple[int, dict | str]:
        infologger.info(f"AuthHandler.get_me | user_id={user_id}")
        rows = self.execute_query_with_value(GET_USER, {"user_id": user_id})
        if not rows:
            infologger.warning(f"AuthHandler.get_me | user not found | user_id={user_id}")
            return 404, "User not found"
        user = rows[0]
        circles = ch.get_my_circles(self, user_id)
        return 200, {"user": user, "circles": circles}

    @log_timing("auth_handler.delete_account")
    def delete_account(
        self, user_id: str, claims: dict, apple_authorization_code: str | None = None
    ) -> tuple[int, dict | str]:
        """Delete the caller's account. The DB transaction is the source of
        truth; Apple revoke, auth and storage cleanup after it only log on failure."""
        apple = ah.is_apple_user(claims)
        infologger.info(
            f"AuthHandler.delete_account | user_id={user_id} apple={apple} has_code={bool(apple_authorization_code)}"
        )
        result = ah.delete_account_rows(self, user_id)
        if result is None:
            return 404, "User not found"
        if apple and apple_authorization_code:
            if not ah.revoke_apple_tokens(user_id, apple_authorization_code):
                errorlogger.error(f"AuthHandler.delete_account | Apple tokens NOT revoked | user_id={user_id}")
        elif apple:
            errorlogger.error(f"AuthHandler.delete_account | Apple user sent no authorization code, not revoked | user_id={user_id}")
        elif apple_authorization_code:
            infologger.warning(f"AuthHandler.delete_account | code sent by a non-Apple user, ignored | user_id={user_id}")
        if not ah.delete_auth_user(user_id):
            errorlogger.error(f"AuthHandler.delete_account | auth user NOT deleted, DB already committed | user_id={user_id}")
        ah.delete_files(user_id, result["files"])
        infologger.info(
            f"AuthHandler.delete_account | done | user_id={user_id} "
            f"transferred={len(result['transferred'])} deleted_circles={len(result['deleted_circles'])}"
        )
        return 200, {"message": "Account deleted"}
