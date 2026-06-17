from app_util.db_util import DBUtil
from app_util.log_util import infologger
from common_helper.decorators import log_timing
from modules.notifications import notifications_helper as h


class NotificationsHandler(DBUtil):

    @log_timing("notifications_handler.get_notifications")
    def get_notifications(self, user_id: str) -> tuple[int, dict]:
        infologger.info(f"NotificationsHandler.get_notifications | user_id={user_id}")
        return 200, h.get_notifications(self, user_id)

    @log_timing("notifications_handler.mark_seen")
    def mark_seen(self, user_id: str) -> tuple[int, dict]:
        infologger.info(f"NotificationsHandler.mark_seen | user_id={user_id}")
        h.mark_all_seen(self, user_id)
        return 200, {"ok": True}
