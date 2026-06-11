import json

from app_util.db_util import DBUtil
from app_util.log_util import infologger
from common_helper.decorators import log_timing
from modules.tour import tour_helper as th
from modules.tour import tour_queries as tq


class TourHandler(DBUtil):

    @log_timing("tour_handler.mark_seen")
    def mark_seen(self, user_id: str, step_ids: list[str]) -> tuple[int, dict | str]:
        infologger.info(f"TourHandler.mark_seen | user_id={user_id} step_ids={step_ids}")
        rows = self.execute_query_with_value(tq.GET_TOUR_STATE, {"user_id": user_id})
        if not rows:
            infologger.warning(f"TourHandler.mark_seen | user not found | user_id={user_id}")
            return 404, "User not found"
        current = (rows[0].get("tour_state") or {}).get("seen", [])
        merged = th.merge_seen(current, step_ids)
        updated = self.execute_query_with_value_returning(
            tq.UPDATE_TOUR_STATE,
            {"user_id": user_id, "tour_state": json.dumps({"seen": merged})},
        )
        if not updated:
            infologger.warning(f"TourHandler.mark_seen | update matched no row | user_id={user_id}")
            return 404, "User not found"
        infologger.info(f"TourHandler.mark_seen | merged {len(step_ids)} ids, total seen={len(merged)} | user_id={user_id}")
        return 200, {"tour_state": updated["tour_state"]}

    @log_timing("tour_handler.reset")
    def reset(self, user_id: str) -> tuple[int, dict | str]:
        infologger.info(f"TourHandler.reset | user_id={user_id}")
        updated = self.execute_query_with_value_returning(
            tq.UPDATE_TOUR_STATE,
            {"user_id": user_id, "tour_state": json.dumps({"seen": []})},
        )
        if not updated:
            infologger.warning(f"TourHandler.reset | user not found | user_id={user_id}")
            return 404, "User not found"
        return 200, {"tour_state": updated["tour_state"]}
