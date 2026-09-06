import uuid

from app_util.db_util import DBUtil
from app_util.log_util import errorlogger, infologger
from common_helper.decorators import log_timing
from common_helper.storage_helper import upload_public_image
from modules.circles import circles_helper as ch
from modules.intents import intents_helper as h
from schemas.intents_schema import CreateIntentRequest, UpdateIntentRequest

COUNT_CREATED_INTENTS = """
    SELECT COUNT(*) AS count
    FROM public.intents
    WHERE created_by = :user_id AND status = 1
"""


class IntentsHandler(DBUtil):
    @log_timing("intents_handler.count_created_intents")
    def count_created_intents(self, user_id: str) -> int:
        infologger.info(f"IntentsHandler.count_created_intents | user_id={user_id}")
        rows = self.execute_query_with_value(COUNT_CREATED_INTENTS, {"user_id": user_id})
        return int(rows[0]["count"]) if rows else 0

    @log_timing("intents_handler.list_intents")
    def list_intents(
        self,
        circle_id: str,
        user_id: str,
        task_status: str | None,
        category: str | None,
        tag: str | None,
        tags: list[str] | None,
        shortlist: bool,
        cursor: str | None = None,
        limit: int = 50,
    ) -> tuple[int, dict | str]:
        infologger.info(
            f"IntentsHandler.list_intents | circle_id={circle_id} "
            f"shortlist={shortlist} task_status={task_status} tags={tags} cursor={cursor!r}"
        )
        try:
            ch.assert_member(self, circle_id, user_id)
        except ValueError:
            return 403, "Not a member of this circle"
        page = h.list_intents(
            self, circle_id, user_id, task_status, category, tag, tags, shortlist, cursor, limit
        )
        return 200, page

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
        infologger.info(f"IntentsHandler.update_intent | intent_id={intent_id} user_id={user_id}")
        existing = h.get_intent(self, intent_id, user_id)
        if not existing:
            return 404, "Intent not found"
        updates = request.model_dump(exclude_none=True)
        if not updates:
            return 400, "No fields to update"
        intent = h.update_intent(self, intent_id, updates)
        if not intent:
            return 404, "Intent not found"
        return 200, intent

    @log_timing("intents_handler.delete_intent")
    def delete_intent(self, intent_id: str, user_id: str) -> tuple[int, str]:
        infologger.info(f"IntentsHandler.delete_intent | intent_id={intent_id} user_id={user_id}")
        existing = h.get_intent(self, intent_id, user_id)
        if not existing:
            return 404, "Intent not found"
        h.delete_intent(self, intent_id)
        return 200, "Intent deleted"

    @log_timing("intents_handler.toggle_reaction")
    def toggle_reaction(self, intent_id: str, user_id: str) -> tuple[int, dict]:
        infologger.info(f"IntentsHandler.toggle_reaction | intent_id={intent_id} user_id={user_id}")
        if not h.get_intent(self, intent_id, user_id):
            return 404, "Intent not found"
        added = h.toggle_reaction(self, intent_id, user_id)
        return 200, {"reacted": added}

    @log_timing("intents_handler.refresh_preview")
    def refresh_preview(self, intent_id: str, user_id: str) -> tuple[int, dict | str]:
        from handler.unfurl_handler import fetch_link_meta

        infologger.info(f"IntentsHandler.refresh_preview | intent_id={intent_id} user_id={user_id}")
        if not h.get_intent(self, intent_id, user_id):
            return 404, "Intent not found"
        row = h.refresh_preview(self, intent_id, fetch_link_meta)
        if not row:
            return 404, "No URL on this intent or no preview available"
        return 200, row

    @log_timing("intents_handler.upload_memory_photo")
    def upload_memory_photo(
        self, intent_id: str, user_id: str, content: bytes, content_type: str
    ) -> tuple[int, dict | str]:
        infologger.info(
            f"IntentsHandler.upload_memory_photo | intent_id={intent_id} user_id={user_id} bytes={len(content)}"
        )
        if not h.get_intent(self, intent_id, user_id):
            return 404, "Intent not found"
        ext = {"image/webp": "webp", "image/jpeg": "jpg", "image/png": "png"}.get(content_type)
        if not ext:
            return 400, "Image must be webp, jpeg, or png"
        path = f"{intent_id}/{uuid.uuid4().hex}.{ext}"
        url = upload_public_image("memories", path, content, content_type)
        if not url:
            return 502, "Upload failed"
        return 200, {"url": url}

    @log_timing("intents_handler.toggle_boost")
    def toggle_boost(self, intent_id: str, user_id: str) -> tuple[int, dict]:
        infologger.info(f"IntentsHandler.toggle_boost | intent_id={intent_id} user_id={user_id}")
        if not h.get_intent(self, intent_id, user_id):
            return 404, "Intent not found"
        added = h.toggle_boost(self, intent_id, user_id)
        return 200, {"boosted": added}
