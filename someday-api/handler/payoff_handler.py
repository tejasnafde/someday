from app_util.db_util import DBUtil
from app_util.log_util import infologger
from common_helper.decorators import log_timing
from modules.circles import circles_helper as ch
from modules.payoff import payoff_helper as h


class PayoffHandler(DBUtil):

    @log_timing("payoff_handler.smart_pick")
    def smart_pick(self, circle_id: str, user_id: str) -> tuple[int, dict | str]:
        infologger.info(f"PayoffHandler.smart_pick | circle_id={circle_id} user_id={user_id}")
        if not ch.get_member_role(self, circle_id, user_id):
            return 404, "Circle not found or you are not a member"
        result = h.smart_pick(self, circle_id, user_id)
        if not result:
            # An empty shortlist is a normal state, not an error: answer 200 so
            # it does not page the 404 alert.
            return 200, {"pick": None, "reason": "Nothing to pick yet. The shortlist is empty or everything on it is already planned."}
        return 200, {"pick": result, "reason": None}

    @log_timing("payoff_handler.spin")
    def spin(self, circle_id: str, user_id: str) -> tuple[int, dict | str]:
        infologger.info(f"PayoffHandler.spin | circle_id={circle_id} user_id={user_id}")
        shortlist = h.spin(self, circle_id, user_id)
        if not shortlist:
            return 404, "Nothing to spin - the shortlist is empty or everything on it is already planned"
        return 200, {"shortlist": shortlist}
