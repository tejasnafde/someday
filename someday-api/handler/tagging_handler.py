from app_util.db_util import DBUtil
from app_util.log_util import errorlogger, infologger
from common_helper.decorators import log_timing
from modules.tagging import tagging_helper as h


class TaggingHandler(DBUtil):
    @log_timing("tagging_handler.auto_tag_intent")
    def auto_tag_intent(self, intent_id: str) -> None:
        """Background job - must never raise into the task runner."""
        infologger.info(f"TaggingHandler.auto_tag_intent | intent_id={intent_id}")
        try:
            h.auto_tag_intent(self, intent_id)
        except Exception as exc:
            errorlogger.error(
                f"TaggingHandler.auto_tag_intent | failed | intent_id={intent_id} | {exc}"
            )
