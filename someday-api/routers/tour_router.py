from fastapi import APIRouter, Depends

from app_util.log_util import infologger
from common_helper.auth_helper import jwt_required
from common_helper.decorators import log_timing
from common_helper.response_helper import create_response
from handler.tour_handler import TourHandler
from schemas.tour_schema import TourSeenRequest

router = APIRouter()
handler = TourHandler()


@router.post("/seen")
@log_timing("POST /tour/seen")
async def mark_seen(request: TourSeenRequest, current_user: dict = Depends(jwt_required)):
    """Merge the given tour step ids into the user's seen set."""
    infologger.info(f"POST /tour/seen | user_id={current_user['sub']} step_ids={request.step_ids}")
    status, result = handler.mark_seen(current_user["sub"], request.step_ids)
    return create_response(status, result)


@router.post("/reset")
@log_timing("POST /tour/reset")
async def reset(current_user: dict = Depends(jwt_required)):
    """Clear the user's seen set so the full tour replays (Settings → Replay tour)."""
    infologger.info(f"POST /tour/reset | user_id={current_user['sub']}")
    status, result = handler.reset(current_user["sub"])
    return create_response(status, result)
