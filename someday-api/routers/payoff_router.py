from fastapi import APIRouter, Depends

from app_util.log_util import infologger
from common_helper.auth_helper import jwt_required
from common_helper.decorators import log_timing
from common_helper.response_helper import create_response
from handler.payoff_handler import PayoffHandler
from schemas.payoff_schema import SmartPickOut, SpinOut

router = APIRouter()
handler = PayoffHandler()


@router.get("/circles/{circle_id}/payoff/smart", response_model=SmartPickOut)
@log_timing("GET /circles/:id/payoff/smart")
async def smart_pick(circle_id: str, current_user: dict = Depends(jwt_required)):
    infologger.info(f"GET /circles/{circle_id}/payoff/smart | user_id={current_user['sub']}")
    status, result = handler.smart_pick(circle_id, current_user["sub"])
    return create_response(status, result)


@router.get("/circles/{circle_id}/payoff/spin", response_model=SpinOut)
@log_timing("GET /circles/:id/payoff/spin")
async def spin(circle_id: str, current_user: dict = Depends(jwt_required)):
    infologger.info(f"GET /circles/{circle_id}/payoff/spin | user_id={current_user['sub']}")
    status, result = handler.spin(circle_id, current_user["sub"])
    return create_response(status, result)
