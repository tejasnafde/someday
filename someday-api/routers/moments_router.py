from zoneinfo import ZoneInfo

from fastapi import APIRouter, BackgroundTasks, Depends, File, Form, Query, UploadFile
from fastapi.responses import JSONResponse
from pydantic import BaseModel, field_validator

from app_util.log_util import infologger
from common_helper.auth_helper import jwt_required
from common_helper.decorators import log_timing
from common_helper.response_helper import create_response
from config.settings import settings
from handler.moments_handler import MomentsHandler
from handler.tagging_handler import TaggingHandler

router = APIRouter()
handler = MomentsHandler()
tagging = TaggingHandler()


class TimezoneRequest(BaseModel):
    timezone: str

    @field_validator("timezone")
    def timezone_valid(cls, v: str) -> str:
        v = v.strip()
        try:
            ZoneInfo(v)
        except Exception:
            raise ValueError("unknown IANA timezone")
        return v


@router.post("/moments/tick")
@log_timing("POST /moments/tick")
async def tick(token: str = Query(default="")):
    """Cloud Scheduler entry point. Shared-token auth, same pattern as the
    Cloud Build webhook. Idempotent - safe to call at any frequency."""
    if not settings.MOMENTS_TICK_TOKEN or token != settings.MOMENTS_TICK_TOKEN:
        infologger.warning("POST /moments/tick | bad token")
        return JSONResponse(status_code=401, content={"message": "bad token"})
    status, result = handler.tick()
    return create_response(status, result)


@router.get("/circles/{circle_id}/moments")
@log_timing("GET /circles/:id/moments")
async def list_moments(
    circle_id: str,
    current_user: dict = Depends(jwt_required),
    cursor: str | None = Query(default=None),
    limit: int = Query(default=20, ge=1, le=100),
):
    infologger.info(f"GET /circles/{circle_id}/moments | user_id={current_user['sub']}")
    status, result = handler.list_moments(circle_id, current_user["sub"], cursor, limit)
    return create_response(status, result)


@router.get("/moments/{moment_id}")
@log_timing("GET /moments/:id")
async def get_moment(moment_id: str, current_user: dict = Depends(jwt_required)):
    infologger.info(f"GET /moments/{moment_id} | user_id={current_user['sub']}")
    status, result = handler.get_moment(moment_id, current_user["sub"])
    return create_response(status, result)


@router.post("/moments/{moment_id}/posts")
@log_timing("POST /moments/:id/posts")
async def create_post(
    moment_id: str,
    current_user: dict = Depends(jwt_required),
    photo: UploadFile = File(...),
    caption: str | None = Form(default=None),
):
    infologger.info(f"POST /moments/{moment_id}/posts | user_id={current_user['sub']}")
    content = await photo.read()
    status, result = handler.create_post(
        moment_id, current_user["sub"], content, photo.content_type or "", caption
    )
    return create_response(status, result)


@router.post("/moments/posts/{post_id}/someday")
@log_timing("POST /moments/posts/:id/someday")
async def someday_from_post(
    post_id: str,
    background_tasks: BackgroundTasks,
    current_user: dict = Depends(jwt_required),
):
    infologger.info(f"POST /moments/posts/{post_id}/someday | user_id={current_user['sub']}")
    status, result = handler.someday_from_post(post_id, current_user["sub"])
    if status == 201 and settings.TAGGER_ENABLED and not result["tags"]:
        background_tasks.add_task(tagging.auto_tag_intent, result["id"])
    return create_response(status, result)


@router.post("/me/timezone")
@log_timing("POST /me/timezone")
async def set_timezone(request: TimezoneRequest, current_user: dict = Depends(jwt_required)):
    infologger.info(f"POST /me/timezone | user_id={current_user['sub']} tz={request.timezone}")
    status, result = handler.set_timezone(current_user["sub"], request.timezone)
    return create_response(status, result)
