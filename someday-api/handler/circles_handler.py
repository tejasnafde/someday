import time

from app_util.db_util import DBUtil
from common_helper.storage_helper import upload_public_image
from app_util.log_util import infologger
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
        circle = h.update_circle(
            self, circle_id, user_id, request.name, request.emoji, request.moments_cadence
        )
        if not circle:
            return 404, "Circle not found or you are not the owner"
        return 200, circle

    @log_timing("circles_handler.delete_circle")
    def delete_circle(self, circle_id: str, user_id: str) -> tuple[int, str]:
        infologger.info(f"CirclesHandler.delete_circle | circle_id={circle_id} user_id={user_id}")
        h.delete_circle(self, circle_id, user_id)
        return 200, "Circle deleted"

    @log_timing("circles_handler.upload_photo")
    def upload_photo(self, circle_id: str, user_id: str, content: bytes, content_type: str) -> tuple[int, dict | str]:
        infologger.info(f"CirclesHandler.upload_photo | circle_id={circle_id} user_id={user_id}")
        try:
            h.assert_member(self, circle_id, user_id)
        except ValueError:
            return 403, "Not a member of this circle"
        if content_type not in {"image/webp", "image/jpeg", "image/png"}:
            return 400, "Image must be webp, jpeg, or png"
        # Deterministic path keyed by circle id - no schema change needed;
        # clients derive the URL and cache-bust with ?v=
        url = upload_public_image("circle-photos", circle_id, content, content_type)
        if not url:
            return 502, "Upload failed"
        return 200, {"photo_url": f"{url}?v={int(time.time())}"}

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
        circle = h.get_circle_with_members(self, circle_id, user_id)
        if not circle:
            return 404, "Circle not found or you are not a member"
        if circle["owner_id"] == user_id:
            return 409, "Transfer ownership before leaving - promote another member first"
        h.leave_circle(self, circle_id, user_id)
        return 200, "Left circle"

    @log_timing("circles_handler.set_member_role")
    def set_member_role(self, circle_id: str, actor_id: str, target_id: str, role: str) -> tuple[int, dict | str]:
        """role ∈ {admin, member, owner}.
           'admin'/'member': only owner+admins; admins can't touch owner/other admins.
           'owner': owner-only - transfers ownership atomically in one transaction."""
        infologger.info(
            f"CirclesHandler.set_member_role | circle_id={circle_id} actor={actor_id} target={target_id} role={role}"
        )
        if role not in {"admin", "member", "owner"}:
            return 400, "role must be admin, member, or owner"
        if actor_id == target_id and role != "owner":
            return 400, "Cannot change your own role"

        circle = h.get_circle_with_members(self, circle_id, actor_id)
        if not circle:
            return 404, "Circle not found or you are not a member"

        actor_role = h.get_member_role(self, circle_id, actor_id)
        target_role = h.get_member_role(self, circle_id, target_id)
        if not target_role:
            return 404, "Member not found in this circle"

        if role == "owner":
            if actor_role != "owner":
                return 403, "Only the owner can transfer ownership"
            h.transfer_ownership(self, circle_id, actor_id, target_id)
            return 200, {"message": "Ownership transferred", "new_owner_id": target_id}

        if not h.can_manage_members(actor_role):
            return 403, "Only the owner or admins can change roles"
        if target_role == "owner":
            return 403, "Cannot change the owner's role - transfer ownership first"
        if actor_role == "admin" and target_role == "admin":
            return 403, "Admins can't demote other admins - ask the owner"

        updated = h.set_member_role(self, circle_id, target_id, role)
        return 200, updated or {"user_id": target_id, "role": role}

    @log_timing("circles_handler.remove_member")
    def remove_member(self, circle_id: str, actor_id: str, target_id: str) -> tuple[int, str]:
        """Owner+admins remove members. Admins can't remove owner or other admins."""
        infologger.info(f"CirclesHandler.remove_member | circle_id={circle_id} actor={actor_id} target={target_id}")
        if actor_id == target_id:
            return 400, "Use Leave instead of removing yourself"
        actor_role = h.get_member_role(self, circle_id, actor_id)
        target_role = h.get_member_role(self, circle_id, target_id)
        if not target_role:
            return 404, "Member not found in this circle"
        if not h.can_manage_members(actor_role):
            return 403, "Only the owner or admins can remove members"
        if target_role == "owner":
            return 403, "Cannot remove the owner"
        if actor_role == "admin" and target_role == "admin":
            return 403, "Admins can't remove other admins - ask the owner"
        h.remove_member(self, circle_id, target_id)
        return 200, "Member removed"

    @log_timing("circles_handler.list_tags")
    def list_tags(self, circle_id: str, user_id: str) -> tuple[int, list | str]:
        infologger.info(f"CirclesHandler.list_tags | circle_id={circle_id} user_id={user_id}")
        try:
            h.assert_member(self, circle_id, user_id)
        except ValueError:
            return 403, "Not a member of this circle"
        return 200, h.list_tags(self, circle_id)

    @log_timing("circles_handler.rotate_invite")
    def rotate_invite(self, circle_id: str, user_id: str) -> tuple[int, dict | str]:
        infologger.info(f"CirclesHandler.rotate_invite | circle_id={circle_id} user_id={user_id}")
        row = h.rotate_invite_token(self, circle_id, user_id)
        if not row:
            return 403, "Only the circle owner can rotate the invite link"
        return 200, {"invite_token": row["invite_token"]}
