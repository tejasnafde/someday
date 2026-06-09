from app_util.db_util import DBUtil
from app_util.log_util import infologger, errorlogger
from common_helper.decorators import log_timing
from modules.circles import circles_helper as ch


_UPSERT_USER = """
    INSERT INTO public.users (id, email, display_name, status)
    VALUES (:id, :email, :display_name, 1)
    ON CONFLICT (id) DO UPDATE
        SET email = EXCLUDED.email
    RETURNING id, email, display_name, avatar_url
"""

_GET_USER = """
    SELECT id, email, display_name, avatar_url
    FROM public.users
    WHERE id = :user_id AND status = 1
"""


class AuthHandler(DBUtil):

    @log_timing("auth_handler.verify")
    def verify(self, user_id: str, email: str) -> tuple[int, dict]:
        """
        Upsert the user row from Supabase auth payload.
        Called once after magic-link verification on the client.
        """
        infologger.info(f"AuthHandler.verify | user_id={user_id} email={email}")
        user = self.execute_query_with_value_returning(
            _UPSERT_USER,
            {"id": user_id, "email": email, "display_name": email.split("@")[0]},
        )
        infologger.info(f"AuthHandler.verify | upserted user_id={user_id}")
        return 200, {"user": user}

    @log_timing("auth_handler.get_me")
    def get_me(self, user_id: str) -> tuple[int, dict | str]:
        infologger.info(f"AuthHandler.get_me | user_id={user_id}")
        rows = self.execute_query_with_value(_GET_USER, {"user_id": user_id})
        if not rows:
            infologger.warning(f"AuthHandler.get_me | user not found | user_id={user_id}")
            return 404, "User not found"
        user = rows[0]
        circles = ch.get_my_circles(self, user_id)
        return 200, {"user": user, "circles": circles}
