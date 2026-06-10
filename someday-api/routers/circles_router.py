from fastapi import APIRouter, Depends

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
