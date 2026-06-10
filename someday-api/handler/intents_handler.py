from app_util.db_util import DBUtil
from app_util.log_util import infologger, errorlogger
from common_helper.decorators import log_timing
from modules.circles import circles_helper as ch
from modules.intents import intents_helper as h
from schemas.intents_schema import CreateIntentRequest, UpdateIntentRequest


class IntentsHandler(DBUtil):

    @log_timing("intents_handler.list_intents")
    def list_intents(
        self,
        circle_id: str,
        user_id: str,
        task_status: str | None,
        category: str | None,
        shortlist: bool,
    ) -> tuple[int, list | str]:
        infologger.info(
            f"IntentsHandler.list_intents | circle_id={circle_id} "
            f"shortlist={shortlist} task_status={task_status}"
        )
        try:
            ch.assert_member(self, circle_id, user_id)
        except ValueError:
            return 403, "Not a member of this circle"
        intents = h.list_intents(self, circle_id, user_id, task_status, category, shortlist)
        return 200, intents

    @log_timing("intents_handler.get_intent")
    def get_intent(self, intent_id: str, user_id: str) -> tuple[int, dict | str]:
        infologger.info(f"IntentsHandler.get_intent | intent_id={intent_id}")
        intent = h.get_intent(self, intent_id, user_id)
        if not intent:
            return 404, "Intent not found"
        return 200, intent

    @log_timing("intents_handler.create_intent")
    def create_intent(
        self, circle_id: str, request: CreateIntentRequest, user_id: str, link_meta: dict | None
    ) -> tuple[int, dict | str]:
        infologger.info(
            f"IntentsHandler.create_intent | circle_id={circle_id} "
            f"user_id={user_id} title={request.title!r}"
        )
        intent = h.create_intent(
            self,
            circle_id=circle_id,
            user_id=user_id,
            title=request.title,
            url=request.url,
            note=request.note,
            category=request.category,
            tags=request.tags,
            link_meta=link_meta,
        )
        if intent is None:
            return 403, "Not a member of this circle"
        return 201, intent

    @log_timing("intents_handler.update_intent")
    def update_intent(
        self, intent_id: str, request: UpdateIntentRequest, user_id: str
    ) -> tuple[int, dict | str]:
        infologger.info(f"IntentsHandler.update_intent | intent_id={intent_id}")
        updates = request.model_dump(exclude_none=True)
        if not updates:
            return 400, "No fields to update"
        intent = h.update_intent(self, intent_id, updates)
        if not intent:
            return 404, "Intent not found"
        return 200, intent

    @log_timing("intents_handler.delete_intent")
    def delete_intent(self, intent_id: str, user_id: str) -> tuple[int, str]:
        infologger.info(f"IntentsHandler.delete_intent | intent_id={intent_id}")
        h.delete_intent(self, intent_id)
        return 200, "Intent deleted"

    @log_timing("intents_handler.toggle_reaction")
    def toggle_reaction(self, intent_id: str, user_id: str) -> tuple[int, dict]:
        infologger.info(f"IntentsHandler.toggle_reaction | intent_id={intent_id} user_id={user_id}")
        added = h.toggle_reaction(self, intent_id, user_id)
        return 200, {"reacted": added}

    @log_timing("intents_handler.toggle_boost")
    def toggle_boost(self, intent_id: str, user_id: str) -> tuple[int, dict]:
        infologger.info(f"IntentsHandler.toggle_boost | intent_id={intent_id} user_id={user_id}")
        added = h.toggle_boost(self, intent_id, user_id)
        return 200, {"boosted": added}
