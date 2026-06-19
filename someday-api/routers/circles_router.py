from fastapi import APIRouter, Depends, File, UploadFile
from pydantic import BaseModel

from app_util.log_util import infologger
from common_helper.auth_helper import jwt_required
from common_helper.decorators import log_timing
from common_helper.response_helper import create_response
from handler.circles_handler import CirclesHandler
from schemas.circles_schema import CreateCircleRequest, UpdateCircleRequest

router = APIRouter()
handler = CirclesHandler()


@router.get("")
@log_timing("GET /circles")
async def list_my_circles(current_user: dict = Depends(jwt_required)):
    infologger.info(f"GET /circles | user_id={current_user['sub']}")
    status, result = handler.get_my_circles(current_user["sub"])
    return create_response(status, result)


@router.post("")
@log_timing("POST /circles")
async def create_circle(request: CreateCircleRequest, current_user: dict = Depends(jwt_required)):
    infologger.info(f"POST /circles | user_id={current_user['sub']} payload={request.model_dump()}")
    status, result = handler.create_circle(request, current_user["sub"])
    return create_response(status, result)


@router.get("/{circle_id}")
@log_timing("GET /circles/:id")
async def get_circle(circle_id: str, current_user: dict = Depends(jwt_required)):
    infologger.info(f"GET /circles/{circle_id} | user_id={current_user['sub']}")
    status, result = handler.get_circle(circle_id, current_user["sub"])
    return create_response(status, result)


@router.patch("/{circle_id}")
@log_timing("PATCH /circles/:id")
async def update_circle(
    circle_id: str, request: UpdateCircleRequest, current_user: dict = Depends(jwt_required)
):
    infologger.info(f"PATCH /circles/{circle_id} | user_id={current_user['sub']} payload={request.model_dump()}")
    status, result = handler.update_circle(circle_id, request, current_user["sub"])
    return create_response(status, result)


@router.delete("/{circle_id}")
@log_timing("DELETE /circles/:id")
async def delete_circle(circle_id: str, current_user: dict = Depends(jwt_required)):
    infologger.info(f"DELETE /circles/{circle_id} | user_id={current_user['sub']}")
    status, result = handler.delete_circle(circle_id, current_user["sub"])
    return create_response(status, result)


@router.post("/{circle_id}/photo")
@log_timing("POST /circles/:id/photo")
async def upload_photo(circle_id: str, file: UploadFile = File(...), current_user: dict = Depends(jwt_required)):
    """Upload a circle photo (members only; pre-resized image ≤2MB)."""
    infologger.info(f"POST /circles/{circle_id}/photo | user_id={current_user['sub']} type={file.content_type}")
    content = await file.read()
    status, result = handler.upload_photo(circle_id, current_user["sub"], content, file.content_type or "")
    return create_response(status, result)


@router.post("/join/{token}")
@log_timing("POST /circles/join/:token")
async def join_circle(token: str, current_user: dict = Depends(jwt_required)):
    infologger.info(f"POST /circles/join | user_id={current_user['sub']}")
    status, result = handler.join_circle(token, current_user["sub"])
    return create_response(status, result)


@router.post("/{circle_id}/leave")
@log_timing("POST /circles/:id/leave")
async def leave_circle(circle_id: str, current_user: dict = Depends(jwt_required)):
    infologger.info(f"POST /circles/{circle_id}/leave | user_id={current_user['sub']}")
    status, result = handler.leave_circle(circle_id, current_user["sub"])
    return create_response(status, result)


class RoleRequest(BaseModel):
    role: str  # admin | member | owner


@router.patch("/{circle_id}/members/{target_id}")
@log_timing("PATCH /circles/:id/members/:user_id")
async def set_member_role(circle_id: str, target_id: str, request: RoleRequest,
                          current_user: dict = Depends(jwt_required)):
    infologger.info(
        f"PATCH /circles/{circle_id}/members/{target_id} | actor={current_user['sub']} role={request.role}"
    )
    status, result = handler.set_member_role(circle_id, current_user["sub"], target_id, request.role)
    return create_response(status, result)


@router.delete("/{circle_id}/members/{target_id}")
@log_timing("DELETE /circles/:id/members/:user_id")
async def remove_member(circle_id: str, target_id: str, current_user: dict = Depends(jwt_required)):
    infologger.info(f"DELETE /circles/{circle_id}/members/{target_id} | actor={current_user['sub']}")
    status, result = handler.remove_member(circle_id, current_user["sub"], target_id)
    return create_response(status, result)


@router.get("/{circle_id}/tags")
@log_timing("GET /circles/:id/tags")
async def list_tags(circle_id: str, current_user: dict = Depends(jwt_required)):
    infologger.info(f"GET /circles/{circle_id}/tags | user_id={current_user['sub']}")
    status, result = handler.list_tags(circle_id, current_user["sub"])
    return create_response(status, result)


@router.post("/{circle_id}/rotate-invite")
@log_timing("POST /circles/:id/rotate-invite")
async def rotate_invite(circle_id: str, current_user: dict = Depends(jwt_required)):
    """Owner-only: invalidates the current invite link and returns a new token."""
    infologger.info(f"POST /circles/{circle_id}/rotate-invite | user_id={current_user['sub']}")
    status, result = handler.rotate_invite(circle_id, current_user["sub"])
    return create_response(status, result)
