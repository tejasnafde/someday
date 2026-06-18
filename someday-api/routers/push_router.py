from fastapi import APIRouter, Depends

from app_util.log_util import infologger
from common_helper.auth_helper import jwt_required
from common_helper.decorators import log_timing
from common_helper.response_helper import create_response
from handler.push_handler import PushHandler
from schemas.push_schema import WebPushSubscription

router = APIRouter()
handler = PushHandler()


@router.post("/push/subscribe")
@log_timing("POST /push/subscribe")
async def subscribe(body: WebPushSubscription, current_user: dict = Depends(jwt_required)):
    infologger.info(f"POST /push/subscribe | user_id={current_user['sub']}")
    status, result = handler.subscribe(current_user["sub"], body.endpoint, body.p256dh, body.auth)
    return create_response(status, result)


@router.delete("/push/subscribe")
@log_timing("DELETE /push/subscribe")
async def unsubscribe(body: WebPushSubscription, current_user: dict = Depends(jwt_required)):
    infologger.info(f"DELETE /push/subscribe | user_id={current_user['sub']}")
    status, result = handler.unsubscribe(current_user["sub"], body.endpoint)
    return create_response(status, result)
