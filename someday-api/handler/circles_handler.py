from app_util.db_util import DBUtil
from app_util.log_util import infologger, errorlogger
from common_helper.decorators import log_timing
from modules.circles import circles_helper as h
from schemas.circles_schema import CreateCircleRequest, UpdateCircleRequest


class CirclesHandler(DBUtil):

    @log_timing("circles_handler.get_my_circles")
    def get_my_circles(self, user_id: str) -> tuple[int, list]:
        infologger.info(f"CirclesHandler.get_my_circles | user_id={user_id}")
        circles = h.get_my_circles(self, user_id)
        return 200, circles

    @log_timing("circles_handler.get_circle")
    def get_circle(self, circle_id: str, user_id: str) -> tuple[int, dict | str]:
        infologger.info(f"CirclesHandler.get_circle | circle_id={circle_id} user_id={user_id}")
        circle = h.get_circle_with_members(self, circle_id, user_id)
        if not circle:
            return 404, "Circle not found or you are not a member"
        return 200, circle

    @log_timing("circles_handler.create_circle")
    def create_circle(self, request: CreateCircleRequest, user_id: str) -> tuple[int, dict]:
        infologger.info(f"CirclesHandler.create_circle | user_id={user_id} name={request.name!r}")
        circle = h.create_circle(self, request.name, request.emoji, user_id)
        return 201, circle

    @log_timing("circles_handler.update_circle")
    def update_circle(self, circle_id: str, request: UpdateCircleRequest, user_id: str) -> tuple[int, dict | str]:
        infologger.info(f"CirclesHandler.update_circle | circle_id={circle_id} user_id={user_id}")
        circle = h.update_circle(self, circle_id, user_id, request.name, request.emoji)
        if not circle:
            return 404, "Circle not found or you are not the owner"
        return 200, circle

    @log_timing("circles_handler.delete_circle")
    def delete_circle(self, circle_id: str, user_id: str) -> tuple[int, str]:
        infologger.info(f"CirclesHandler.delete_circle | circle_id={circle_id} user_id={user_id}")
        h.delete_circle(self, circle_id, user_id)
        return 200, "Circle deleted"

    @log_timing("circles_handler.join_circle")
    def join_circle(self, token: str, user_id: str) -> tuple[int, dict | str]:
        infologger.info(f"CirclesHandler.join_circle | user_id={user_id}")
        circle = h.join_circle_by_token(self, token, user_id)
        if not circle:
            return 404, "Invalid or expired invite link"
        return 200, {"message": "Joined circle", "circle_id": str(circle["id"]), "name": circle["name"]}

    @log_timing("circles_handler.leave_circle")
    def leave_circle(self, circle_id: str, user_id: str) -> tuple[int, str]:
        infologger.info(f"CirclesHandler.leave_circle | circle_id={circle_id} user_id={user_id}")
        h.leave_circle(self, circle_id, user_id)
        return 200, "Left circle"
