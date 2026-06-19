from fastapi import APIRouter, Depends

from app_util.log_util import infologger
from common_helper.auth_helper import jwt_required
from common_helper.decorators import log_timing
from common_helper.response_helper import create_response
from handler.notifications_handler import NotificationsHandler
from schemas.notifications_schema import NotificationFeedOut, OkOut

router = APIRouter()
handler = NotificationsHandler()


@router.get("/notifications", response_model=NotificationFeedOut)
@log_timing("GET /notifications")
async def get_notifications(current_user: dict = Depends(jwt_required)):
    infologger.info(f"GET /notifications | user_id={current_user['sub']}")
    status, result = handler.get_notifications(current_user["sub"])
    return create_response(status, result)


@router.post("/notifications/seen", response_model=OkOut)
@log_timing("POST /notifications/seen")
async def mark_seen(current_user: dict = Depends(jwt_required)):
    infologger.info(f"POST /notifications/seen | user_id={current_user['sub']}")
    status, result = handler.mark_seen(current_user["sub"])
    return create_response(status, result)
