import uuid
from datetime import datetime, timezone

from app_util.db_util import DBUtil
from app_util.log_util import errorlogger, infologger
from common_helper.decorators import log_timing
from common_helper.notify import Notify
from common_helper.storage_helper import upload_public_image
from modules.intents import intents_helper as ih
from modules.moments import moments_helper as h
from modules.moments import moments_queries as q


class MomentsHandler(DBUtil):
    def __init__(self):
        super().__init__()
        self.notify = Notify()

    @log_timing("moments_handler.tick")
    def tick(self) -> tuple[int, dict]:
        """Cron entry point: draw this week's schedule, fill pings, send due ones.

        Every step is idempotent, so overlapping ticks are harmless."""
        drawn = h.draw_week_schedules(self)
        pings = h.ensure_pings(self)
        sent = h.send_due_pings(self, self.notify)
        infologger.info(f"MomentsHandler.tick | drawn={drawn} pings={pings} sent={sent}")
        return 200, {"drawn": drawn, "pings": pings, "sent": sent}

    @log_timing("moments_handler.list_moments")
    def list_moments(self, circle_id: str, user_id: str, cursor: str | None, limit: int) -> tuple[int, dict | str]:
        infologger.info(f"MomentsHandler.list_moments | circle_id={circle_id} user_id={user_id}")
        page = h.list_moments(self, circle_id, user_id, cursor, limit)
        return 200, page

    @log_timing("moments_handler.get_moment")
    def get_moment(self, moment_id: str, user_id: str) -> tuple[int, dict | str]:
        infologger.info(f"MomentsHandler.get_moment | moment_id={moment_id} user_id={user_id}")
        moment = h.moment_with_posts(self, moment_id, user_id)
        if not moment:
            return 404, "Moment not found"
        return 200, moment

    @log_timing("moments_handler.create_post")
    def create_post(
        self, moment_id: str, user_id: str, content: bytes, content_type: str, caption: str | None
    ) -> tuple[int, dict | str]:
        infologger.info(f"MomentsHandler.create_post | moment_id={moment_id} user_id={user_id} bytes={len(content)}")
        rows = self.execute_query_with_value(q.GET_MOMENT_FOR_MEMBER, {"moment_id": moment_id, "user_id": user_id})
        if not rows:
            return 404, "Moment not found"
        moment = rows[0]

        tz_rows = self.execute_query_with_value(q.GET_USER_TIMEZONE, {"user_id": user_id})
        poster_tz = tz_rows[0]["timezone"] if tz_rows else "UTC"
        now_utc = datetime.now(timezone.utc)
        if not h.can_post(h.as_date(moment["moment_date"]), poster_tz, now_utc):
            return 400, "This moment is closed"

        ext = {"image/webp": "webp", "image/jpeg": "jpg", "image/png": "png"}.get(content_type)
        if not ext:
            return 400, "Image must be webp, jpeg, or png"
        path = f"{moment_id}/{user_id}/{uuid.uuid4().hex}.{ext}"
        photo_url = upload_public_image("moments", path, content, content_type)
        if not photo_url:
            return 502, "Upload failed"

        late = False
        ping_rows = self.execute_query_with_value(q.GET_MY_PING, {"moment_id": moment_id, "user_id": user_id})
        if ping_rows:
            ping_at = datetime.fromisoformat(str(ping_rows[0]["ping_at"]).replace(" ", "T"))
            late = (now_utc - ping_at).total_seconds() > h.LATE_GRACE_SECONDS

        caption = (caption or "").strip()[:140] or None
        row = self.execute_query_with_value_returning(
            q.INSERT_POST,
            {"moment_id": moment_id, "user_id": user_id, "photo_url": photo_url,
             "caption": caption, "tz": poster_tz, "late": late},
        )
        if not row:
            return 409, "You already posted to this moment"
        # Return the whole moment so the client can render the reveal directly.
        return 201, h.moment_with_posts(self, moment_id, user_id)

    @log_timing("moments_handler.someday_from_post")
    def someday_from_post(self, post_id: str, user_id: str) -> tuple[int, dict | str]:
        """One tap on a friend's moment photo seeds the circle's list."""
        infologger.info(f"MomentsHandler.someday_from_post | post_id={post_id} user_id={user_id}")
        rows = self.execute_query_with_value(q.GET_POST_FOR_MEMBER, {"post_id": post_id, "viewer_id": user_id})
        if not rows:
            return 404, "Post not found"
        post = rows[0]
        author = post["author_name"] or "a friend"
        title = post["caption"] or f"That thing from {author}'s moment"
        intent = ih.create_intent(
            self,
            circle_id=str(post["circle_id"]),
            user_id=user_id,
            title=title[:120],
            url=None,
            note=f"From {author}'s Meanwhile moment on {post['moment_date']}",
            category=None,
            tags=[],
            link_meta={"title": None, "image": post["photo_url"], "site": None, "description": None},
        )
        if intent is None:
            return 403, "Not a member of this circle"
        return 201, intent

    @log_timing("moments_handler.set_timezone")
    def set_timezone(self, user_id: str, tz_name: str) -> tuple[int, dict | str]:
        row = self.execute_query_with_value_returning(
            q.UPDATE_USER_TIMEZONE, {"user_id": user_id, "timezone": tz_name}
        )
        if not row:
            return 404, "User not found"
        return 200, {"timezone": row["timezone"]}
