from app_util.db_util import DBUtil
from app_util.log_util import infologger
from common_helper.decorators import log_timing
from modules.push.push_queries import DELETE_WEB_PUSH_SUBSCRIPTION, UPSERT_WEB_PUSH_SUBSCRIPTION


class PushHandler(DBUtil):

    @log_timing("push_handler.subscribe")
    def subscribe(self, user_id: str, endpoint: str, p256dh: str, auth: str) -> tuple[int, dict]:
        infologger.info(f"PushHandler.subscribe | user_id={user_id}")
        self.execute_query_with_value_without_output(
            UPSERT_WEB_PUSH_SUBSCRIPTION,
            {"user_id": user_id, "endpoint": endpoint, "p256dh": p256dh, "auth": auth},
        )
        return 200, {"ok": True}

    @log_timing("push_handler.unsubscribe")
    def unsubscribe(self, user_id: str, endpoint: str) -> tuple[int, dict]:
        infologger.info(f"PushHandler.unsubscribe | user_id={user_id}")
        self.execute_query_with_value_without_output(
            DELETE_WEB_PUSH_SUBSCRIPTION,
            {"user_id": user_id, "endpoint": endpoint},
        )
        return 200, {"ok": True}
